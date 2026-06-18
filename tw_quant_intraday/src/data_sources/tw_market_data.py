"""Unified Taiwan stock data provider.

Aggregates data from multiple free public APIs:
- TWSE OpenAPI: listed company directory + all-market daily quotes (MI_INDEX)
- TPEX OpenAPI: OTC company directory + daily quotes
- TWSE MIS: realtime intraday quotes (during market hours)
- FinMind: alternative historical data
- yfinance: fallback via Yahoo Finance (.TW / .TWO suffix)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import requests

from src.data_sources.data_cache import DAILY_COLUMNS
from src.data_sources.twse_official import parse_number

logger = logging.getLogger(__name__)
Market = Literal["twse", "tpex", "all"]

_last_req: float = 0.0
REQ_INTERVAL = 3.5

def _throttle() -> None:
    global _last_req
    elapsed = time.time() - _last_req
    if elapsed < REQ_INTERVAL:
        time.sleep(REQ_INTERVAL - elapsed)
    _last_req = time.time()

def _get_json(url: str, params: dict | None = None, timeout: int = 30) -> Any:
    _throttle()
    r = requests.get(url, params=params, timeout=timeout,
                     headers={"User-Agent": "tw_quant/0.2", "Accept": "application/json"})
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()

@dataclass(frozen=True)
class StockInfo:
    stock_id: str
    stock_name: str
    market: Market
    industry: str = ""

def fetch_twse_stock_list() -> list[StockInfo]:
    try:
        data = _get_json("https://openapi.twse.com.tw/v1/opendata/t187ap03_L")
        return [StockInfo(str(d.get("公司代號","")).strip(), str(d.get("公司簡稱","")).strip(),
                          "twse", str(d.get("產業類別","")))
                for d in data if str(d.get("公司代號","")).strip() and len(str(d.get("公司代號","")).strip()) <= 6]
    except Exception as e:
        logger.warning("TWSE stock list failed: %s", e); return []

def fetch_tpex_stock_list() -> list[StockInfo]:
    try:
        data = _get_json("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O")
        result = []
        for d in data:
            code = str(d.get("SecuritiesCompanyCode", d.get("公司代號",""))).strip()
            name = str(d.get("CompanyName", d.get("公司簡稱",""))).strip()
            if code and name and len(code) <= 6:
                result.append(StockInfo(code, name, "tpex"))
        return result
    except Exception as e:
        logger.warning("TPEX stock list failed: %s", e); return []

def fetch_all_stock_list() -> list[StockInfo]:
    seen: set[str] = set()
    result: list[StockInfo] = []
    for s in fetch_twse_stock_list() + fetch_tpex_stock_list():
        if s.stock_id not in seen:
            seen.add(s.stock_id); result.append(s)
    return result

def fetch_twse_all_market_daily(trade_date: str) -> pd.DataFrame:
    """All TWSE stocks' daily OHLCV for one date via MI_INDEX."""
    dt = date.fromisoformat(trade_date)
    params = {"response": "json", "date": f"{dt:%Y%m%d}", "type": "ALL"}
    try:
        data = _get_json("https://www.twse.com.tw/exchangeReport/MI_INDEX", params)
    except Exception as e:
        logger.warning("MI_INDEX failed: %s", e); return pd.DataFrame(columns=DAILY_COLUMNS)
    if "OK" not in str(data.get("stat", "")):
        return pd.DataFrame(columns=DAILY_COLUMNS)
    raw = data.get("data9", data.get("data8", []))
    rows, now_s = [], pd.Timestamp.now(tz="Asia/Taipei").isoformat()
    for r in raw:
        try:
            o, h, l, c = parse_number(r[5]), parse_number(r[6]), parse_number(r[7]), parse_number(r[8])
            if o <= 0 or c <= 0: continue
            rows.append({"date": trade_date, "stock_id": str(r[0]).strip(), "stock_name": str(r[1]).strip(),
                          "open": o, "high": h, "low": l, "close": c,
                          "volume": parse_number(r[2]), "turnover": parse_number(r[4]),
                          "source": "twse_mi_index", "updated_at": now_s})
        except (ValueError, IndexError): continue
    return pd.DataFrame(rows, columns=DAILY_COLUMNS)

def fetch_tpex_daily(trade_date: str) -> pd.DataFrame:
    """All TPEX stocks' daily OHLCV for one date."""
    dt = date.fromisoformat(trade_date)
    roc = f"{dt.year - 1911}/{dt.month:02d}/{dt.day:02d}"
    params = {"l": "zh-tw", "d": roc, "se": "AL", "o": "json"}
    try:
        data = _get_json("https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php", params)
    except Exception as e:
        logger.warning("TPEX daily failed: %s", e); return pd.DataFrame(columns=DAILY_COLUMNS)
    rows, now_s = [], pd.Timestamp.now(tz="Asia/Taipei").isoformat()
    for r in data.get("aaData", []):
        try:
            sid = str(r[0]).strip()
            c = parse_number(str(r[2])); o = parse_number(str(r[4]))
            h = parse_number(str(r[5])); l = parse_number(str(r[6]))
            v = parse_number(str(r[8]))
            if o <= 0 or c <= 0 or len(sid) > 6: continue
            rows.append({"date": trade_date, "stock_id": sid, "stock_name": str(r[1]).strip(),
                          "open": o, "high": h, "low": l, "close": c, "volume": v,
                          "turnover": c * v, "source": "tpex_daily", "updated_at": now_s})
        except (ValueError, IndexError): continue
    return pd.DataFrame(rows, columns=DAILY_COLUMNS)

def fetch_realtime_quotes(stock_ids: list[str], market_hints: dict[str, Market] | None = None) -> pd.DataFrame:
    """Realtime quotes from TWSE MIS (works 09:00-13:30)."""
    if not stock_ids: return pd.DataFrame()
    hints = market_hints or {}
    parts = [f"{'tse' if hints.get(s,'twse')=='twse' else 'otc'}_{s}.tw" for s in stock_ids]
    all_rows: list[dict] = []
    for i in range(0, len(parts), 20):
        batch = "|".join(parts[i:i+20])
        try:
            _throttle()
            resp = requests.get(f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={batch}",
                                timeout=10, headers={"User-Agent": "tw_quant/0.2"})
            resp.raise_for_status()
            for item in resp.json().get("msgArray", []):
                all_rows.append({"stock_id": str(item.get("c","")), "stock_name": str(item.get("n","")),
                                  "price": float(item.get("z",0) or 0), "open": float(item.get("o",0) or 0),
                                  "high": float(item.get("h",0) or 0), "low": float(item.get("l",0) or 0),
                                  "yesterday_close": float(item.get("y",0) or 0),
                                  "volume": float(item.get("v",0) or 0), "source": "twse_mis_realtime"})
        except Exception as e:
            logger.warning("MIS failed: %s", e)
    return pd.DataFrame(all_rows)

def fetch_yfinance_daily(stock_id: str, start: str, end: str, market: Market = "twse") -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed"); return pd.DataFrame(columns=DAILY_COLUMNS)
    suffix = ".TW" if market == "twse" else ".TWO"
    try:
        df = yf.download(f"{stock_id}{suffix}", start=start, end=end, progress=False, auto_adjust=True)
    except Exception as e:
        logger.warning("yfinance failed: %s", e); return pd.DataFrame(columns=DAILY_COLUMNS)
    if df.empty: return pd.DataFrame(columns=DAILY_COLUMNS)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    now_s = pd.Timestamp.now(tz="Asia/Taipei").isoformat()
    return pd.DataFrame({"date": df.index.strftime("%Y-%m-%d"), "stock_id": stock_id, "stock_name": "",
                          "open": df["Open"].values, "high": df["High"].values, "low": df["Low"].values,
                          "close": df["Close"].values, "volume": df["Volume"].values,
                          "turnover": (df["Close"]*df["Volume"]).values, "source": "yfinance", "updated_at": now_s})

@dataclass
class TwMarketDataProvider:
    """Unified data provider for all Taiwan stock APIs."""
    request_interval: float = 3.5
    _stock_cache: list[StockInfo] = field(default_factory=list, repr=False)

    def fetch_all_stock_list(self, refresh: bool = False) -> list[StockInfo]:
        if self._stock_cache and not refresh: return self._stock_cache
        self._stock_cache = fetch_all_stock_list(); return self._stock_cache

    def get_market_for_stock(self, stock_id: str) -> Market:
        for s in self.fetch_all_stock_list():
            if s.stock_id == stock_id: return s.market
        return "twse"

    def fetch_all_market_daily(self, trade_date: str, markets: Market = "all") -> pd.DataFrame:
        frames = []
        if markets in ("all", "twse"): frames.append(fetch_twse_all_market_daily(trade_date))
        if markets in ("all", "tpex"): frames.append(fetch_tpex_daily(trade_date))
        if not frames: return pd.DataFrame(columns=DAILY_COLUMNS)
        return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["stock_id"], keep="first")

    def fetch_stock_history(self, stock_id: str, start: str, end: str, source: str = "twse") -> pd.DataFrame:
        if source == "yfinance":
            return fetch_yfinance_daily(stock_id, start, end, self.get_market_for_stock(stock_id))
        if source == "finmind":
            from src.data_sources.finmind_client import FinMindClient
            raw = FinMindClient().fetch_taiwan_stock_price(stock_id, start, end)
            if raw.empty: return pd.DataFrame(columns=DAILY_COLUMNS)
            now_s = pd.Timestamp.now(tz="Asia/Taipei").isoformat()
            return pd.DataFrame({"date": raw["date"], "stock_id": stock_id, "stock_name": "",
                                  "open": raw["open"], "high": raw["max"], "low": raw["min"], "close": raw["close"],
                                  "volume": raw["Trading_Volume"], "turnover": raw["Trading_money"],
                                  "source": "finmind", "updated_at": now_s})
        from src.data_sources.twse_official import TwseOfficialDailyClient
        return TwseOfficialDailyClient().fetch_range([stock_id], date.fromisoformat(start), date.fromisoformat(end))

    def fetch_bulk_history(self, stock_ids: list[str], start: str, end: str,
                           source: str = "twse", progress_callback: Any = None) -> pd.DataFrame:
        frames = []
        for i, sid in enumerate(stock_ids):
            try:
                df = self.fetch_stock_history(sid, start, end, source)
                if not df.empty: frames.append(df)
                if progress_callback: progress_callback(i+1, len(stock_ids), sid)
            except Exception as e:
                logger.warning("Failed %s: %s", sid, e)
        if not frames: return pd.DataFrame(columns=DAILY_COLUMNS)
        return pd.concat(frames, ignore_index=True).sort_values(["stock_id", "date"])

    def fetch_realtime(self, stock_ids: list[str]) -> pd.DataFrame:
        hints = {s.stock_id: s.market for s in self.fetch_all_stock_list() if s.stock_id in stock_ids}
        return fetch_realtime_quotes(stock_ids, hints)

    def save_daily_csv(self, frame: pd.DataFrame, path: str | Path) -> Path:
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(p, index=False); return p

    def save_stock_list_csv(self, stocks: list[StockInfo], path: str | Path) -> Path:
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"stock_id": s.stock_id, "stock_name": s.stock_name,
                        "market": s.market, "industry": s.industry} for s in stocks]).to_csv(p, index=False)
        return p
