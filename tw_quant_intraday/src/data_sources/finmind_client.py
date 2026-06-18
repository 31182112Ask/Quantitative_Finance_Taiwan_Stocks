from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import requests


@dataclass(frozen=True)
class FinMindClient:
    token: str | None = None
    base_url: str = "https://api.finmindtrade.com/api/v4/data"

    def fetch_taiwan_stock_price(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_id,
            "start_date": start_date,
            "end_date": end_date,
        }
        if self.token:
            params["token"] = self.token
        response = requests.get(self.base_url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != 200:
            raise RuntimeError(f"FinMind request failed: {payload.get('msg')}")
        return pd.DataFrame(payload.get("data", []))
