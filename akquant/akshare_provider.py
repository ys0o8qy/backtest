from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

import pandas as pd


class DataSourceKind(str, Enum):
    ETF = "etf"
    INDEX = "index"


@dataclass(frozen=True)
class Coverage:
    start: date
    end: date
    ratio: float
    covers_requested_range: bool


class AkshareProvider:
    def __init__(self, ak_module: Any | None = None) -> None:
        if ak_module is None:
            import akshare as ak_module

        self.ak = ak_module

    def fetch(self, symbol: str, kind: DataSourceKind, start: date, end: date, adjust: str = "hfq") -> pd.DataFrame:
        if kind is DataSourceKind.ETF:
            return self.fetch_etf(symbol=symbol, start=start, end=end, adjust=adjust)
        if kind is DataSourceKind.INDEX:
            return self.fetch_index(symbol=symbol, start=start, end=end)
        raise ValueError(f"unsupported data source kind: {kind}")

    def fetch_etf(self, symbol: str, start: date, end: date, adjust: str = "hfq") -> pd.DataFrame:
        raw = self.ak.fund_etf_hist_em(
            symbol=symbol,
            period="daily",
            start_date=_compact_date(start),
            end_date=_compact_date(end),
            adjust=adjust,
        )
        return normalize_akshare_ohlcv(raw, symbol=symbol, source=f"etf:{symbol}")

    def fetch_index(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        raw = self.ak.index_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=_compact_date(start),
            end_date=_compact_date(end),
        )
        return normalize_akshare_ohlcv(raw, symbol=symbol, source=f"index:{symbol}")

    def fetch_index_catalog(self) -> pd.DataFrame:
        raw = self.ak.index_stock_info()
        rename_map = {
            "指数代码": "index_code",
            "指数名称": "display_name",
            "发布日期": "publish_date",
        }
        catalog = raw.rename(columns=rename_map).copy()
        if "index_code" not in catalog.columns:
            raise ValueError("AKShare index catalog is missing index_code column")
        if "display_name" not in catalog.columns:
            catalog["display_name"] = catalog["index_code"]
        if "publish_date" not in catalog.columns:
            catalog["publish_date"] = ""
        return catalog[["index_code", "display_name", "publish_date"]].drop_duplicates("index_code")


def normalize_akshare_ohlcv(frame: pd.DataFrame, symbol: str, source: str) -> pd.DataFrame:
    if frame.empty:
        return _empty_ohlcv()

    rename_map = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
    }
    data = frame.rename(columns=rename_map).copy()
    required = ["date", "open", "high", "low", "close"]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"AKShare response for {symbol} is missing columns: {missing}")

    if "volume" not in data.columns:
        data["volume"] = 0.0
    if "amount" not in data.columns:
        data["amount"] = 0.0

    data = data[["date", "open", "high", "low", "close", "volume", "amount"]]
    data["date"] = pd.to_datetime(data["date"])
    for column in ["open", "high", "low", "close", "volume", "amount"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["date", "open", "high", "low", "close"])
    data = data.sort_values("date").drop_duplicates("date", keep="last")
    data["symbol"] = symbol
    data["source"] = source
    data["openinterest"] = 0
    data = data.set_index("date")
    data.index.name = "date"
    return data[["open", "high", "low", "close", "volume", "amount", "openinterest", "symbol", "source"]]


def coverage_for(frame: pd.DataFrame, start: date, end: date) -> Coverage | None:
    if frame.empty:
        return None
    actual_start = frame.index.min().date()
    actual_end = frame.index.max().date()
    requested_days = max((end - start).days, 1)
    covered_days = max((min(actual_end, end) - max(actual_start, start)).days, 0)
    ratio = covered_days / requested_days
    covers_requested_range = actual_start <= start and actual_end >= end
    return Coverage(start=actual_start, end=actual_end, ratio=ratio, covers_requested_range=covers_requested_range)


def fetch_index_returns(provider: AkshareProvider, symbols: list[str], start: date, end: date) -> pd.DataFrame:
    returns = []
    for symbol in symbols:
        frame = provider.fetch_index(symbol=symbol, start=start, end=end)
        series = frame["close"].pct_change().dropna().rename(symbol)
        returns.append(series)
    if not returns:
        return pd.DataFrame()
    result = pd.concat(returns, axis=1).sort_index()
    result.index.name = "date"
    return result


def fetch_all_index_returns(
    provider: AkshareProvider,
    start: date,
    end: date,
    limit: int | None = None,
) -> pd.DataFrame:
    catalog = provider.fetch_index_catalog()
    symbols = [str(symbol) for symbol in catalog["index_code"].tolist()]
    if limit is not None:
        symbols = symbols[:limit]
    return fetch_index_returns(provider=provider, symbols=symbols, start=start, end=end)


def _compact_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _empty_ohlcv() -> pd.DataFrame:
    frame = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount", "openinterest", "symbol", "source"])
    frame.index = pd.DatetimeIndex([], name="date")
    return frame
