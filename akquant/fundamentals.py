from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd


VALUATION_COLUMNS = [
    "as_of_date",
    "data_date",
    "symbol",
    "name",
    "close",
    "pe_ttm",
    "pe_dynamic",
    "pe_static",
    "pb",
    "dividend_yield",
    "market_cap",
    "float_market_cap",
    "turnover_amount",
    "industry",
    "is_st",
    "is_suspended",
    "listing_age_days",
    "data_quality_flags",
]


class FundamentalDataProvider:
    def __init__(self, ak_module: Any | None = None) -> None:
        if ak_module is None:
            import akshare as ak_module

        self.ak = ak_module

    def fetch_latest_valuation_snapshot(self, as_of_date: date | None = None) -> pd.DataFrame:
        snapshot_date = as_of_date or date.today()
        raw = self.ak.stock_zh_a_spot_em()
        frame = normalize_spot_valuation(raw, as_of_date=snapshot_date)
        return enrich_dividend_yield(frame, self.ak, as_of_date=snapshot_date)


def normalize_spot_valuation(raw: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in raw.iterrows():
        name = str(_get(row, ["名称", "name"], ""))
        close = _number(_get(row, ["最新价", "close"]))
        pe_dynamic = _number(_get(row, ["市盈率-动态", "动态市盈率", "pe_dynamic", "PE动态"]))
        pe_ttm = _number(_get(row, ["PE(TTM)", "市盈率TTM", "pe_ttm"], pe_dynamic))
        pe_static = _number(_get(row, ["市盈率-静态", "静态市盈率", "pe_static"]))
        pb = _number(_get(row, ["市净率", "pb"]))
        dividend_yield = _dividend_yield(_get(row, ["股息率", "dividend_yield"]))
        market_cap = _number(_get(row, ["总市值", "market_cap"]))
        float_market_cap = _number(_get(row, ["流通市值", "float_market_cap"]))
        turnover_amount = _number(_get(row, ["成交额", "turnover_amount"]))
        is_suspended = close is None or close <= 0
        flags = _quality_flags(
            pe_ttm=pe_ttm,
            pb=pb,
            dividend_yield=dividend_yield,
            close=close,
            turnover_amount=turnover_amount,
        )
        rows.append(
            {
                "as_of_date": as_of_date,
                "data_date": as_of_date,
                "symbol": str(_get(row, ["代码", "symbol"])).zfill(6),
                "name": name,
                "close": close,
                "pe_ttm": pe_ttm,
                "pe_dynamic": pe_dynamic,
                "pe_static": pe_static,
                "pb": pb,
                "dividend_yield": dividend_yield,
                "market_cap": market_cap,
                "float_market_cap": float_market_cap,
                "turnover_amount": turnover_amount,
                "industry": _get(row, ["行业", "industry"]),
                "is_st": bool("ST" in name.upper()),
                "is_suspended": bool(is_suspended),
                "listing_age_days": None,
                "data_quality_flags": flags,
            }
        )
    frame = pd.DataFrame(rows, columns=VALUATION_COLUMNS)
    if not frame.empty:
        frame["is_st"] = frame["is_st"].astype(object)
        frame["is_suspended"] = frame["is_suspended"].astype(object)
    return frame


def enrich_dividend_yield(frame: pd.DataFrame, ak_module: Any, as_of_date: date) -> pd.DataFrame:
    if frame.empty or "dividend_yield" not in frame.columns or not frame["dividend_yield"].isna().any():
        return frame
    if not hasattr(ak_module, "stock_fhps_em"):
        return frame

    dividend_frame = _fetch_distribution_dividend_yields(ak_module, as_of_date)
    if dividend_frame.empty:
        return frame

    result = frame.copy()
    result = result.merge(dividend_frame, how="left", on="symbol", suffixes=("", "_fhps"))
    needs_dividend = result["dividend_yield"].isna() & result["dividend_yield_fhps"].notna()
    result.loc[needs_dividend, "dividend_yield"] = result.loc[needs_dividend, "dividend_yield_fhps"]
    result["data_quality_flags"] = [
        _update_flags_after_dividend_enrichment(flags, enriched=enriched)
        for flags, enriched in zip(result["data_quality_flags"], needs_dividend, strict=False)
    ]
    return result.drop(columns=["dividend_yield_fhps"])


def _fetch_distribution_dividend_yields(ak_module: Any, as_of_date: date) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    seen_symbols: set[str] = set()
    for report_date in _candidate_dividend_report_dates(as_of_date):
        try:
            raw = ak_module.stock_fhps_em(date=report_date)
        except Exception:
            continue
        normalized = _normalize_distribution_dividend_yields(raw)
        if not normalized.empty:
            new_rows = normalized[~normalized["symbol"].isin(seen_symbols)].copy()
            if not new_rows.empty:
                frames.append(new_rows)
                seen_symbols.update(new_rows["symbol"].tolist())
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(columns=["symbol", "dividend_yield_fhps"])


def _candidate_dividend_report_dates(as_of_date: date) -> list[str]:
    dates: list[str] = []
    if as_of_date.month >= 9:
        dates.append(f"{as_of_date.year}0630")
    if as_of_date.month >= 5:
        dates.append(f"{as_of_date.year - 1}1231")
    dates.extend([f"{as_of_date.year - 1}0630", f"{as_of_date.year - 2}1231"])
    return list(dict.fromkeys(dates))


def _normalize_distribution_dividend_yields(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=["symbol", "dividend_yield_fhps"])
    rows = []
    for _, row in raw.iterrows():
        symbol = _get(row, ["代码", "symbol"])
        dividend_yield = _dividend_yield(_get(row, ["现金分红-股息率", "股息率", "dividend_yield"]))
        if symbol is None or dividend_yield is None:
            continue
        rows.append({"symbol": str(symbol).zfill(6), "dividend_yield_fhps": dividend_yield})
    return pd.DataFrame(rows, columns=["symbol", "dividend_yield_fhps"])


def _update_flags_after_dividend_enrichment(flags: list[str], enriched: bool) -> list[str]:
    if not enriched:
        return flags
    updated = [flag for flag in flags if flag != "missing_dividend_yield"]
    if "dividend_yield_from_fhps" not in updated:
        updated.append("dividend_yield_from_fhps")
    return updated


def _get(row, names: list[str], default=None):
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return default


def _number(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "").strip()
        if value in {"", "-", "--"}:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dividend_yield(value) -> float | None:
    number = _number(value)
    if number is None:
        return None
    return number / 100 if number > 1 else number


def _quality_flags(
    pe_ttm: float | None,
    pb: float | None,
    dividend_yield: float | None,
    close: float | None,
    turnover_amount: float | None,
) -> list[str]:
    flags: list[str] = []
    if pe_ttm is None:
        flags.append("missing_pe_ttm")
    if pb is None:
        flags.append("missing_pb")
    if dividend_yield is None:
        flags.append("missing_dividend_yield")
    elif dividend_yield > 0.20:
        flags.append("extreme_dividend_yield")
    if close is None or close <= 0:
        flags.append("invalid_close")
    if turnover_amount is None:
        flags.append("missing_turnover_amount")
    return flags
