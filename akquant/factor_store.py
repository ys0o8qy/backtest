from __future__ import annotations

import ast
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


class FactorStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, as_of_date: date, frame: pd.DataFrame, metadata: dict[str, object] | None = None) -> None:
        payload = dict(metadata or {})
        payload["as_of_date"] = as_of_date.isoformat()
        payload.setdefault("field_version", "valuation_snapshot_v1")
        _encode_frame(frame).to_csv(self._snapshot_path(as_of_date), index=False)
        self._metadata_path(as_of_date).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_snapshot(self, as_of_date: date) -> tuple[pd.DataFrame, dict[str, object]]:
        available = self._available_dates()
        candidates = [value for value in available if value <= as_of_date]
        if not candidates:
            raise FileNotFoundError(f"no factor snapshot available on or before {as_of_date}")
        selected_date = max(candidates)
        frame = _decode_frame(pd.read_csv(self._snapshot_path(selected_date), dtype={"symbol": str}))
        if "symbol" in frame.columns:
            frame["symbol"] = frame["symbol"].str.zfill(6)
        metadata = json.loads(self._metadata_path(selected_date).read_text(encoding="utf-8"))
        return frame, metadata

    def _snapshot_path(self, as_of_date: date) -> Path:
        return self.root / f"{as_of_date.isoformat()}.csv"

    def _metadata_path(self, as_of_date: date) -> Path:
        return self.root / f"{as_of_date.isoformat()}.json"

    def _available_dates(self) -> list[date]:
        dates: list[date] = []
        for path in self.root.glob("*.csv"):
            try:
                dates.append(date.fromisoformat(path.stem))
            except ValueError:
                continue
        return sorted(dates)


def _encode_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "data_quality_flags" in result.columns:
        result["data_quality_flags"] = result["data_quality_flags"].map(
            lambda value: json.dumps(_list_value(value), ensure_ascii=False)
        )
    return result


def _decode_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "data_quality_flags" in result.columns:
        result["data_quality_flags"] = result["data_quality_flags"].map(_decode_list_value)
    return result


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None or (not isinstance(value, list) and pd.isna(value)):
        return []
    return [value]


def _decode_list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None or pd.isna(value):
        return []
    if not isinstance(value, str):
        return [value]
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        try:
            decoded = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            decoded = value
    return decoded if isinstance(decoded, list) else [decoded]
