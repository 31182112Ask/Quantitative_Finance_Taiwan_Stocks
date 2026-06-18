from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from src.backtest.benchmark import BenchmarkConfig, RecommendedStrategyBenchmark, write_benchmark_report
from src.backtest.event_backtester import SimpleDailyBacktester
from src.config import PROJECT_ROOT, ensure_project_dirs, load_yaml
from src.data_sources.data_cache import CsvDataCache
from src.data_sources.intraday_quote import LocalIntradayQuoteProvider
from src.data_sources.mock_data import make_mock_daily, make_mock_intraday
from src.data_sources.twse_official import TwseOfficialDailyClient, write_twse_daily_csv
from src.data_sources.twse_daily import LocalDailyCsvSource
from src.data_sources.tw_market_data import TwMarketDataProvider
from src.execution.manual_order_ticket import write_manual_order_ticket
from src.execution.signal_exporter import export_approved_manual_tickets
from src.market.cost_model import CostConfig, TaiwanStockCostModel
from src.market.universe import build_universe
from src.reports.report_builder import write_market_summary, write_performance_report, write_signal_report
from src.risk.risk_manager import RiskLimits, RiskManager, RiskState
from src.strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from src.strategies.t_plus_one_swing import TPlusOneSwingStrategy
from src.ui.server import run as run_ui_server
from src.paper.paper_account import PaperAccount
from src.paper.paper_engine import PaperEngine

TAIPEI = ZoneInfo("Asia/Taipei")


def _models() -> tuple[TaiwanStockCostModel, RiskManager]:
    cfg = load_yaml("config/risk.yaml")
    cost_model = TaiwanStockCostModel(CostConfig.from_mapping(cfg.get("cost", {})))
    risk_manager = RiskManager(RiskLimits.from_mapping(cfg.get("risk", {})))
    return cost_model, risk_manager


def fetch_daily(args: argparse.Namespace) -> None:
    ensure_project_dirs()
    cache = CsvDataCache(PROJECT_ROOT / "data")
    path = PROJECT_ROOT / "data" / "daily" / "daily.csv"
    if path.exists() and not args.mock:
        frame = LocalDailyCsvSource(PROJECT_ROOT / "data" / "daily").load("daily.csv")
        print(f"Loaded existing local daily CSV: {len(frame)} rows")
        return
    frame = make_mock_daily()
    cache.write(frame, "daily/daily.csv")
    print("Wrote mock demo daily data to data/daily/daily.csv")


def fetch_twse_daily_cmd(args: argparse.Namespace) -> None:
    ensure_project_dirs()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    client = TwseOfficialDailyClient()
    frame = client.fetch_range(args.stocks, start, end)
    output = PROJECT_ROOT / args.output
    write_twse_daily_csv(frame, output)
    print(f"Wrote TWSE official daily data: {len(frame)} rows -> {output}")


def build_universe_cmd(args: argparse.Namespace) -> None:
    risk_cfg = load_yaml("config/risk.yaml").get("risk", {})
    daily = LocalDailyCsvSource(PROJECT_ROOT / "data" / "daily").load("daily.csv")
    if daily.empty:
        daily = make_mock_daily()
    universe = build_universe(daily, float(risk_cfg.get("min_avg_turnover_20d", 50_000_000)))
    CsvDataCache(PROJECT_ROOT / "data").write(universe, "processed/universe.csv")
    write_market_summary(PROJECT_ROOT / "reports" / "daily", len(universe), ["Universe built from local or mock demo daily data."])
    print(f"Built universe with {len(universe)} symbols")


def backtest_cmd(args: argparse.Namespace) -> None:
    cost_model, _ = _models()
    daily = LocalDailyCsvSource(PROJECT_ROOT / "data" / "daily").load("daily.csv")
    if daily.empty:
        daily = make_mock_daily()
    if args.strategy != "t_plus_one_swing":
        print("Opening range breakout is available for signal scans; first-version backtest uses t_plus_one_swing daily bars.")
    result = SimpleDailyBacktester(cost_model=cost_model).run_t_plus_one(daily)
    out = PROJECT_ROOT / "reports" / "daily"
    out.mkdir(parents=True, exist_ok=True)
    result.trades.to_csv(out / "backtest_trades.csv", index=False)
    result.equity_curve.to_csv(out / "backtest_equity_curve.csv", index=False)
    write_performance_report(out, result.metrics)
    print(f"Backtest complete: {int(result.metrics['trade_count'])} trades")


def benchmark_cmd(args: argparse.Namespace) -> None:
    cost_model, _ = _models()
    data_path = PROJECT_ROOT / args.data_file
    if not data_path.exists():
        raise FileNotFoundError(f"Benchmark data file not found: {data_path}")
    daily = pd.read_csv(data_path)
    result = RecommendedStrategyBenchmark(cost_model).run(
        daily,
        BenchmarkConfig(
            start_date=date.fromisoformat(args.start),
            end_date=date.fromisoformat(args.end),
            initial_cash=args.initial_cash,
            lot_size=args.lot_size,
            allow_mock=args.allow_mock,
        ),
    )
    trades_path, equity_path, report_path = write_benchmark_report(result, PROJECT_ROOT / "reports" / "daily", args.label)
    print(
        "Benchmark complete: "
        f"ending_equity={result.summary['ending_equity']:.2f}, "
        f"return_pct={result.summary['return_pct']:.4f}, "
        f"trades={result.summary['trade_count']}; "
        f"report={report_path}"
    )


def paper_run_cmd(args: argparse.Namespace) -> None:
    cost_model, risk_manager = _models()
    daily = LocalDailyCsvSource(PROJECT_ROOT / "data" / "daily").load("daily.csv")
    if daily.empty:
        daily = make_mock_daily()
    strategy = TPlusOneSwingStrategy(cost_model=cost_model)
    now = datetime.now(TAIPEI)
    signal = strategy.generate(daily, str(daily.iloc[-1]["stock_id"]), now)
    engine = PaperEngine(PaperAccount(), cost_model)
    if signal.side == "BUY" and signal.entry_price and signal.stop_loss:
        state = RiskState(equity=engine.account.cash)
        decision = risk_manager.evaluate_entry(
            stock_id=signal.stock_id,
            side=signal.side,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            current_time=now.replace(hour=10, minute=0, second=0, microsecond=0),
            state=state,
            avg_turnover_20d=100_000_000,
            data_is_fresh=True,
        )
        if decision.approved:
            engine.apply_signal(signal, decision.size.quantity)
    engine.mark_equity(now.date().isoformat(), {str(daily.iloc[-1]["stock_id"]): float(daily.iloc[-1]["close"])})
    engine.write_reports(PROJECT_ROOT / "reports" / "paper_trading")
    print("Paper run complete. Reports written to reports/paper_trading")


def intraday_scan_cmd(args: argparse.Namespace) -> None:
    cost_model, risk_manager = _models()
    trade_date = args.date
    if args.mock:
        intraday = make_mock_intraday(args.stock_id, trade_date)
        status = "mock demo intraday data, not realtime"
    else:
        loaded = LocalIntradayQuoteProvider(PROJECT_ROOT / "data" / "intraday").load(args.stock_id, trade_date)
        intraday = loaded.data
        status = loaded.status
    now = datetime.fromisoformat(f"{trade_date} {args.time}").replace(tzinfo=TAIPEI)
    signal = OpeningRangeBreakoutStrategy(cost_model=cost_model).generate(intraday, args.stock_id, now)
    decisions = []
    if signal.side == "BUY" and signal.entry_price and signal.stop_loss:
        decisions.append(risk_manager.evaluate_entry(
            stock_id=signal.stock_id,
            side=signal.side,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            current_time=now,
            state=RiskState(equity=args.equity),
            avg_turnover_20d=args.avg_turnover_20d,
            data_is_fresh=args.mock or not intraday.empty,
        ))
        export_approved_manual_tickets([signal], decisions, PROJECT_ROOT / "reports" / "intraday")
    else:
        write_manual_order_ticket([], PROJECT_ROOT / "reports" / "intraday")
    signal_frame = pd.DataFrame([signal.to_dict()])
    write_signal_report(PROJECT_ROOT / "reports" / "intraday", signal_frame, blocked_count=sum(not d.approved for d in decisions))
    print(f"Intraday scan complete: {status}; signal={signal.side}")


def build_report_cmd(args: argparse.Namespace) -> None:
    ensure_project_dirs()
    write_market_summary(PROJECT_ROOT / "reports" / "daily", 0, ["Run build-universe for a populated universe count."])
    write_signal_report(PROJECT_ROOT / "reports" / "intraday", pd.DataFrame())
    write_performance_report(PROJECT_ROOT / "reports" / "paper_trading", {})
    print("Report templates written.")


def ui_cmd(args: argparse.Namespace) -> None:
    run_ui_server(args.host, args.port)



def fetch_all_stocks_cmd(args: argparse.Namespace) -> None:
    ensure_project_dirs()
    provider = TwMarketDataProvider()
    stocks = provider.fetch_all_stock_list(refresh=True)
    output = PROJECT_ROOT / "data" / "processed" / "all_stocks.csv"
    provider.save_stock_list_csv(stocks, output)
    twse_count = sum(1 for s in stocks if s.market == "twse")
    tpex_count = sum(1 for s in stocks if s.market == "tpex")
    print(f"Fetched {len(stocks)} stocks: {twse_count} TWSE + {tpex_count} TPEX -> {output}")


def fetch_all_daily_cmd(args: argparse.Namespace) -> None:
    ensure_project_dirs()
    provider = TwMarketDataProvider()
    frame = provider.fetch_all_market_daily(args.date, args.market)
    if frame.empty:
        print(f"No data for {args.date} (may be non-trading day)")
        return
    output = PROJECT_ROOT / args.output
    provider.save_daily_csv(frame, output)
    print(f"Fetched {len(frame)} stocks for {args.date} -> {output}")


def fetch_bulk_history_cmd(args: argparse.Namespace) -> None:
    ensure_project_dirs()
    provider = TwMarketDataProvider()
    stock_ids = args.stocks
    if args.all:
        stocks = provider.fetch_all_stock_list(refresh=True)
        stock_ids = [s.stock_id for s in stocks]
        print(f"Fetching history for ALL {len(stock_ids)} stocks...")
    def progress(c, t, sid):
        print(f"  [{c}/{t}] {sid}")
    frame = provider.fetch_bulk_history(stock_ids, args.start, args.end, args.source, progress_callback=progress)
    output = PROJECT_ROOT / args.output
    provider.save_daily_csv(frame, output)
    print(f"Fetched {len(frame)} rows for {len(stock_ids)} stocks -> {output}")


def fetch_realtime_cmd(args: argparse.Namespace) -> None:
    provider = TwMarketDataProvider()
    frame = provider.fetch_realtime(args.stocks)
    if frame.empty:
        print("No realtime data (market may be closed)")
        return
    for _, row in frame.iterrows():
        print(f"  {row['stock_id']} {row['stock_name']}: price={row['price']} vol={row['volume']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Taiwan stock research assistant. Manual outputs only.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch-daily")
    p.add_argument("--mock", action="store_true", help="write explicitly marked mock demo daily data")
    p.set_defaults(func=fetch_daily)

    p = sub.add_parser("fetch-twse-daily")
    p.add_argument("--stocks", nargs="+", default=["2330", "2317"])
    p.add_argument("--start", default="2026-01-01")
    p.add_argument("--end", default="2026-05-31")
    p.add_argument("--output", default="data/daily/twse_2026_05_benchmark.csv")
    p.set_defaults(func=fetch_twse_daily_cmd)

    p = sub.add_parser("build-universe")
    p.set_defaults(func=build_universe_cmd)

    p = sub.add_parser("backtest")
    p.add_argument("--strategy", default="t_plus_one_swing", choices=["t_plus_one_swing", "opening_range_breakout"])
    p.set_defaults(func=backtest_cmd)

    p = sub.add_parser("benchmark")
    p.add_argument("--data-file", default="data/daily/twse_2026_05_benchmark.csv")
    p.add_argument("--start", default="2026-05-01")
    p.add_argument("--end", default="2026-05-31")
    p.add_argument("--initial-cash", type=float, default=10_000)
    p.add_argument("--lot-size", type=int, default=1)
    p.add_argument("--label", default="benchmark")
    p.add_argument("--allow-mock", action="store_true")
    p.set_defaults(func=benchmark_cmd)

    p = sub.add_parser("paper-run")
    p.set_defaults(func=paper_run_cmd)

    p = sub.add_parser("intraday-scan")
    p.add_argument("--stock-id", default="2330")
    p.add_argument("--date", default="2026-06-18")
    p.add_argument("--time", default="10:00:00")
    p.add_argument("--equity", type=float, default=1_000_000)
    p.add_argument("--avg-turnover-20d", type=float, default=100_000_000)
    p.add_argument("--mock", action="store_true", help="use explicitly marked mock demo intraday data")
    p.set_defaults(func=intraday_scan_cmd)

    p = sub.add_parser("build-report")
    p.set_defaults(func=build_report_cmd)

    p = sub.add_parser("ui")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=ui_cmd)

    p = sub.add_parser("fetch-all-stocks", help="Fetch all TWSE+TPEX stock list")
    p.set_defaults(func=fetch_all_stocks_cmd)

    p = sub.add_parser("fetch-all-daily", help="Fetch all-market daily for one date")
    p.add_argument("--date", default=date.today().isoformat())
    p.add_argument("--market", default="all", choices=["all", "twse", "tpex"])
    p.add_argument("--output", default="data/daily/all_market_daily.csv")
    p.set_defaults(func=fetch_all_daily_cmd)

    p = sub.add_parser("fetch-bulk-history", help="Fetch historical data for multiple stocks")
    p.add_argument("--stocks", nargs="*", default=["2330", "2317"])
    p.add_argument("--all", action="store_true", help="Fetch ALL listed stocks")
    p.add_argument("--start", default="2026-01-01")
    p.add_argument("--end", default="2026-06-18")
    p.add_argument("--source", default="twse", choices=["twse", "finmind", "yfinance"])
    p.add_argument("--output", default="data/daily/bulk_history.csv")
    p.set_defaults(func=fetch_bulk_history_cmd)

    p = sub.add_parser("fetch-realtime", help="Fetch realtime quotes (market hours only)")
    p.add_argument("--stocks", nargs="+", default=["2330", "2317"])
    p.set_defaults(func=fetch_realtime_cmd)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
