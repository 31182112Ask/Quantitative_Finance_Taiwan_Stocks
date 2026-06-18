from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from src.backtest.benchmark import BenchmarkConfig, RecommendedStrategyBenchmark, write_benchmark_report
from src.config import PROJECT_ROOT, load_yaml
from src.data_sources.intraday_quote import LocalIntradayQuoteProvider
from src.data_sources.mock_data import make_mock_intraday
from src.data_sources.twse_daily import LocalDailyCsvSource
from src.data_sources.twse_official import TwseOfficialDailyClient, write_twse_daily_csv
from src.execution.manual_order_ticket import signal_to_ticket_row, write_manual_order_ticket
from src.market.cost_model import CostConfig, TaiwanStockCostModel
from src.risk.risk_manager import RiskDecision, RiskLimits, RiskManager, RiskState
from src.strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from src.strategies.t_plus_one_swing import TPlusOneSwingStrategy

TAIPEI = ZoneInfo("Asia/Taipei")


@dataclass(frozen=True)
class StrategyScanRequest:
    strategy: str = "t_plus_one_swing"
    stock_id: str = "2330"
    daily_file: str = "data/daily/twse_2026_05_benchmark.csv"
    trade_date: str = "2026-05-29"
    trade_time: str = "10:00:00"
    equity: float = 10_000
    avg_turnover_20d: float | None = None
    intraday_source: str = "local"
    write_ticket: bool = True


@dataclass(frozen=True)
class BenchmarkUiRequest:
    data_file: str = "data/daily/twse_2026_05_benchmark.csv"
    start: str = "2026-05-01"
    end: str = "2026-05-31"
    initial_cash: float = 10_000
    lot_size: int = 1
    label: str = "ui_benchmark"
    allow_mock: bool = False
    write_files: bool = True


def _models() -> tuple[TaiwanStockCostModel, RiskManager]:
    cfg = load_yaml("config/risk.yaml")
    cost_model = TaiwanStockCostModel(CostConfig.from_mapping(cfg.get("cost", {})))
    risk_manager = RiskManager(RiskLimits.from_mapping(cfg.get("risk", {})))
    return cost_model, risk_manager


def _safe_project_path(relative_path: str) -> Path:
    path = (PROJECT_ROOT / relative_path).resolve()
    root = PROJECT_ROOT.resolve()
    if root != path and root not in path.parents:
        raise ValueError(f"path must stay inside project root: {relative_path}")
    return path


def _jsonable(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _decision_to_dict(decision: RiskDecision | None) -> dict[str, Any] | None:
    if decision is None:
        return None
    payload = asdict(decision)
    return _jsonable(payload)


def _avg_turnover(daily: pd.DataFrame, stock_id: str) -> float:
    stock = daily[daily["stock_id"].astype(str) == str(stock_id)].copy()
    if stock.empty:
        return 0.0
    stock["turnover_calc"] = stock["close"].astype(float) * stock["volume"].astype(float)
    return float(stock["turnover_calc"].tail(20).mean())


def list_data_files() -> list[str]:
    files = sorted((PROJECT_ROOT / "data" / "daily").glob("*.csv"))
    return [str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") for path in files]


def run_strategy_scan(request: StrategyScanRequest) -> dict[str, Any]:
    cost_model, risk_manager = _models()
    current_time = datetime.fromisoformat(f"{request.trade_date} {request.trade_time}").replace(tzinfo=TAIPEI)
    source_status = "ok"
    daily_path = _safe_project_path(request.daily_file)
    if daily_path.exists():
        daily = pd.read_csv(daily_path)
    else:
        daily = LocalDailyCsvSource(PROJECT_ROOT / "data" / "daily").load("daily.csv")

    if request.strategy == "opening_range_breakout":
        if request.intraday_source == "mock":
            intraday = make_mock_intraday(request.stock_id, request.trade_date)
            source_status = "mock demo intraday data, not realtime"
        else:
            loaded = LocalIntradayQuoteProvider(PROJECT_ROOT / "data" / "intraday").load(request.stock_id, request.trade_date)
            intraday = loaded.data
            source_status = loaded.status
        signal = OpeningRangeBreakoutStrategy(cost_model=cost_model).generate(intraday, request.stock_id, current_time)
        data_is_fresh = request.intraday_source == "mock" or not intraday.empty
    elif request.strategy == "t_plus_one_swing":
        if daily.empty:
            raise ValueError("daily.csv is empty or missing; fetch local daily data before scanning")
        signal = TPlusOneSwingStrategy(cost_model=cost_model).generate(daily, request.stock_id, current_time)
        source_status = "local daily CSV"
        data_is_fresh = True
    else:
        raise ValueError(f"unsupported strategy: {request.strategy}")

    decision: RiskDecision | None = None
    ticket_files: dict[str, str] | None = None
    ticket_row: dict[str, Any] | None = None
    avg_turnover = request.avg_turnover_20d
    if avg_turnover is None:
        avg_turnover = _avg_turnover(daily, request.stock_id) if not daily.empty else 0.0

    if signal.side == "BUY" and signal.entry_price is not None and signal.stop_loss is not None:
        decision = risk_manager.evaluate_entry(
            stock_id=signal.stock_id,
            side=signal.side,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            current_time=current_time,
            state=RiskState(equity=request.equity),
            avg_turnover_20d=float(avg_turnover),
            data_is_fresh=data_is_fresh,
        )
        if decision.approved:
            ticket_row = signal_to_ticket_row(signal, decision.size.quantity, "; ".join(decision.notes))

    if request.write_ticket:
        rows = [ticket_row] if ticket_row else []
        csv_path, md_path = write_manual_order_ticket(rows, PROJECT_ROOT / "reports" / "intraday")
        ticket_files = {
            "csv": str(csv_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "md": str(md_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        }

    return {
        "signal": signal.to_dict(),
        "risk_decision": _decision_to_dict(decision),
        "ticket": _jsonable(ticket_row),
        "ticket_files": ticket_files,
        "source_status": source_status,
        "avg_turnover_20d": avg_turnover,
        "mode": "manual_ticket_only",
        "safety": "no broker login, no app automation, no automatic order submission",
    }


def run_benchmark_ui(request: BenchmarkUiRequest) -> dict[str, Any]:
    data_path = _safe_project_path(request.data_file)
    if not data_path.exists():
        raise FileNotFoundError(f"benchmark data file not found: {request.data_file}")
    daily = pd.read_csv(data_path)
    cost_model, _ = _models()
    result = RecommendedStrategyBenchmark(cost_model).run(
        daily,
        BenchmarkConfig(
            start_date=date.fromisoformat(request.start),
            end_date=date.fromisoformat(request.end),
            initial_cash=float(request.initial_cash),
            lot_size=int(request.lot_size),
            allow_mock=bool(request.allow_mock),
        ),
    )
    files: dict[str, str | None]
    if request.write_files:
        trades_path, equity_path, report_path = write_benchmark_report(result, PROJECT_ROOT / "reports" / "daily", request.label)
        files = {
            "trades": str(trades_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "equity_curve": str(equity_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "report": str(report_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        }
    else:
        files = {"trades": None, "equity_curve": None, "report": None}
    trades = result.trades.fillna("").to_dict(orient="records")
    equity = result.equity_curve.fillna("").to_dict(orient="records")
    return {
        "summary": _jsonable(result.summary),
        "metrics": _jsonable(result.metrics),
        "trades": _jsonable(trades),
        "equity_curve": _jsonable(equity),
        "files": files,
    }


def fetch_twse_for_ui(stock_ids: list[str], start: str, end: str, output: str) -> dict[str, Any]:
    output_path = _safe_project_path(output)
    frame = TwseOfficialDailyClient().fetch_range(stock_ids, date.fromisoformat(start), date.fromisoformat(end))
    write_twse_daily_csv(frame, output_path)
    return {
        "rows": int(len(frame)),
        "file": str(output_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "stocks": stock_ids,
        "start": start,
        "end": end,
    }
