from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Literal

import pandas as pd

from akquant.stock_pool import StockPool


Operator = Literal[">", ">=", "<", "<=", "==", "between", "not_null"]
NullPolicy = Literal["exclude", "worst", "neutral"]


@dataclass(frozen=True)
class ScreeningRule:
    field: str
    operator: Operator
    value: object = None


@dataclass(frozen=True)
class RankingSpec:
    field: str
    ascending: bool
    weight: float
    null_policy: NullPolicy = "exclude"


@dataclass(frozen=True)
class UniverseConfig:
    market: str = "all_a"
    exclude_st: bool = True
    exclude_suspended: bool = True
    min_listing_days: int | None = 180


@dataclass(frozen=True)
class ScreenConfig:
    id: str
    name: str
    as_of_date: date | Literal["latest"] = "latest"
    universe: UniverseConfig = field(default_factory=UniverseConfig)
    filters: list[ScreeningRule] = field(default_factory=list)
    ranking: list[RankingSpec] = field(default_factory=list)
    top_n: int = 50
    output_fields: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.top_n <= 0:
            raise ValueError("top_n must be positive")
        if any(spec.weight < 0 for spec in self.ranking):
            raise ValueError("ranking weights must be non-negative")
        total_weight = sum(spec.weight for spec in self.ranking)
        if self.ranking and abs(total_weight - 1.0) > 1e-6:
            raise ValueError("ranking weights must sum to 1.0")

    def snapshot(self) -> dict[str, object]:
        return asdict(self)


def run_screen(snapshot: pd.DataFrame, config: ScreenConfig) -> StockPool:
    working = snapshot.copy()
    as_of_date = _as_of_date(working, config)
    summary_rows = [{"step": "initial", "rule": "", "removed_count": 0, "remaining_count": len(working)}]
    warnings: list[str] = []

    working, universe_rows, universe_warnings = _apply_universe(working, config.universe)
    summary_rows.extend(universe_rows)
    warnings.extend(universe_warnings)

    for rule in config.filters:
        before = len(working)
        working = working[_mask_for_rule(working, rule)].copy()
        summary_rows.append(
            {
                "step": f"filter:{rule.field}",
                "rule": _rule_label(rule),
                "removed_count": before - len(working),
                "remaining_count": len(working),
            }
        )

    working = _apply_ranking(working, config.ranking)
    selected = working.head(config.top_n).reset_index(drop=True)
    if selected.empty:
        warnings.append("screen selected no stocks")

    return StockPool(
        pool_id=f"{config.id}-{as_of_date.isoformat()}",
        as_of_date=as_of_date,
        config_snapshot=config.snapshot(),
        selected=selected,
        rejected_summary=pd.DataFrame(summary_rows),
        warnings=warnings,
    )


def _apply_universe(frame: pd.DataFrame, universe: UniverseConfig) -> tuple[pd.DataFrame, list[dict[str, object]], list[str]]:
    working = frame.copy()
    summary_rows: list[dict[str, object]] = []
    warnings: list[str] = []

    if universe.exclude_st:
        working, row = _apply_universe_rule(working, "is_st", _false_or_missing_mask(working, "is_st"))
        summary_rows.append(row)

    if universe.exclude_suspended:
        working, row = _apply_universe_rule(
            working,
            "is_suspended",
            _false_or_missing_mask(working, "is_suspended"),
        )
        summary_rows.append(row)

    if universe.min_listing_days is not None:
        if "listing_age_days" not in working.columns or working["listing_age_days"].isna().all():
            warnings.append("listing_age_days unavailable; min_listing_days filter skipped")
        else:
            listing_age = pd.to_numeric(working["listing_age_days"], errors="coerce")
            mask = listing_age.isna() | (listing_age >= universe.min_listing_days)
            working, row = _apply_universe_rule(
                working,
                "listing_age_days",
                mask,
                rule=f"listing_age_days >= {universe.min_listing_days}",
            )
            summary_rows.append(row)

    return working, summary_rows, warnings


def _apply_universe_rule(
    frame: pd.DataFrame,
    field: str,
    mask: pd.Series | bool,
    rule: str | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    before = len(frame)
    if isinstance(mask, bool):
        resolved_mask = pd.Series([mask] * len(frame), index=frame.index)
    else:
        resolved_mask = mask.reindex(frame.index, fill_value=True)
    filtered = frame[resolved_mask].copy()
    return filtered, {
        "step": f"universe:{field}",
        "rule": rule or f"{field} == False",
        "removed_count": before - len(filtered),
        "remaining_count": len(filtered),
    }


def _false_or_missing_mask(frame: pd.DataFrame, field: str) -> pd.Series:
    if field not in frame.columns:
        return pd.Series([True] * len(frame), index=frame.index)
    return frame[field].fillna(False).astype(bool).eq(False)


def _mask_for_rule(frame: pd.DataFrame, rule: ScreeningRule) -> pd.Series:
    if rule.field not in frame.columns:
        raise ValueError(f"screening field does not exist: {rule.field}")
    series = frame[rule.field]
    if rule.operator == ">":
        return series > rule.value
    if rule.operator == ">=":
        return series >= rule.value
    if rule.operator == "<":
        return series < rule.value
    if rule.operator == "<=":
        return series <= rule.value
    if rule.operator == "==":
        return series == rule.value
    if rule.operator == "not_null":
        return series.notna()
    if rule.operator == "between":
        low, high = rule.value
        return (series >= low) & (series <= high)
    raise ValueError(f"unsupported screening operator: {rule.operator}")


def _apply_ranking(frame: pd.DataFrame, ranking: list[RankingSpec]) -> pd.DataFrame:
    if not ranking:
        return frame.copy()
    ranked = frame.copy()
    ranked["value_score"] = 0.0
    for spec in ranking:
        if spec.field not in ranked.columns:
            raise ValueError(f"ranking field does not exist: {spec.field}")
        ranked = _handle_nulls(ranked, spec)
        score = _rank_score(ranked[spec.field], ascending=spec.ascending)
        ranked[f"{spec.field}_rank_score"] = score
        ranked["value_score"] += score * spec.weight
    return ranked.sort_values(["value_score", "symbol"], ascending=[False, True])


def _handle_nulls(frame: pd.DataFrame, spec: RankingSpec) -> pd.DataFrame:
    if spec.null_policy == "exclude":
        return frame[frame[spec.field].notna()].copy()
    result = frame.copy()
    if spec.null_policy == "worst":
        fill_value = result[spec.field].max() if spec.ascending else result[spec.field].min()
        result[spec.field] = result[spec.field].fillna(fill_value)
    elif spec.null_policy == "neutral":
        result[spec.field] = result[spec.field].fillna(result[spec.field].median())
    else:
        raise ValueError(f"unsupported null policy: {spec.null_policy}")
    return result


def _rank_score(series: pd.Series, ascending: bool) -> pd.Series:
    if len(series) <= 1:
        return pd.Series([1.0] * len(series), index=series.index)
    rank = series.rank(method="min", ascending=ascending)
    return 1 - (rank - 1) / (len(series) - 1)


def _as_of_date(frame: pd.DataFrame, config: ScreenConfig) -> date:
    if config.as_of_date != "latest":
        return config.as_of_date
    if frame.empty or "as_of_date" not in frame.columns:
        return date.today()
    value = frame["as_of_date"].iloc[0]
    return pd.Timestamp(value).date()


def _rule_label(rule: ScreeningRule) -> str:
    return f"{rule.field} {rule.operator} {rule.value}"
