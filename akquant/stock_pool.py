from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class StockPool:
    pool_id: str
    as_of_date: date
    config_snapshot: dict[str, object]
    selected: pd.DataFrame
    rejected_summary: pd.DataFrame
    warnings: list[str]

    @property
    def selected_symbols(self) -> list[str]:
        return [str(symbol) for symbol in self.selected["symbol"].tolist()]
