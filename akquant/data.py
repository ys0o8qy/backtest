from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from akquant.models import Bar


def load_bars_csv(path: str | Path, symbol: str | None = None) -> tuple[list[Bar], list[str]]:
    bars: list[Bar] = []
    warnings: list[str] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if symbol is not None and row["symbol"] != symbol:
                continue
            bars.append(
                Bar(
                    date=date.fromisoformat(row["date"]),
                    symbol=row["symbol"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    amount=float(row["amount"]),
                    adjustment=row.get("adjustment", "none"),
                    source=row.get("source", "csv"),
                    is_trading=_parse_bool(row.get("is_trading", "true")),
                    is_halted=_parse_bool(row.get("is_halted", "false")),
                )
            )

    bars.sort(key=lambda bar: bar.date)
    _validate_bars(bars)
    warnings.extend(_quality_warnings(bars))
    return bars, warnings


def _validate_bars(bars: list[Bar]) -> None:
    seen: set[tuple[str, date]] = set()
    for bar in bars:
        key = (bar.symbol, bar.date)
        if key in seen:
            raise ValueError(f"duplicate bar for {bar.symbol} on {bar.date}")
        seen.add(key)
        if min(bar.open, bar.high, bar.low, bar.close) <= 0:
            raise ValueError(f"non-positive price for {bar.symbol} on {bar.date}")
        if bar.high < bar.low:
            raise ValueError(f"high is below low for {bar.symbol} on {bar.date}")
        if bar.volume < 0:
            raise ValueError(f"negative volume for {bar.symbol} on {bar.date}")


def _quality_warnings(bars: list[Bar]) -> list[str]:
    warnings: list[str] = []
    if not bars:
        warnings.append("No bars matched the requested symbol.")
        return warnings
    symbols = {bar.symbol for bar in bars}
    if len(symbols) > 1:
        warnings.append("Multiple symbols were loaded; V0.1 engine expects a single symbol per run.")
    if any(not bar.is_trading or bar.is_halted for bar in bars):
        warnings.append("Some bars are marked non-trading or halted.")
    return warnings


def _parse_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
