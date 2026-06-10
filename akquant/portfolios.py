from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

import pandas as pd

from akquant.akshare_provider import AkshareProvider, DataSourceKind, coverage_for


@dataclass(frozen=True)
class AssetCandidate:
    symbol: str
    name: str
    kind: DataSourceKind


@dataclass(frozen=True)
class AssetTarget:
    asset_class: str
    weight: float
    candidates: list[AssetCandidate]


@dataclass(frozen=True)
class CostModel:
    commission_rate: float = 0.0003
    slippage_perc: float = 0.0005


@dataclass(frozen=True)
class DataPolicy:
    min_coverage_ratio: float = 0.95
    etf_first: bool = True


@dataclass(frozen=True)
class PortfolioConfig:
    id: str
    name: str
    targets: list[AssetTarget]
    rebalance: str = "quarterly"
    initial_cash: float = 100_000.0
    cost_model: CostModel = field(default_factory=CostModel)
    data_policy: DataPolicy = field(default_factory=DataPolicy)

    def __post_init__(self) -> None:
        if self.rebalance not in {"monthly", "quarterly", "yearly", "once"}:
            raise ValueError("rebalance must be one of: monthly, quarterly, yearly, once")
        total_weight = sum(target.weight for target in self.targets)
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(f"portfolio target weights must sum to 1.0, got {total_weight:.6f}")
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")

    def snapshot(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SelectedAssetData:
    target: AssetTarget
    candidate: AssetCandidate
    data: pd.DataFrame
    warnings: list[str]


def all_weather_targets() -> list[AssetTarget]:
    return [
        AssetTarget(
            asset_class="equity",
            weight=0.30,
            candidates=[
                AssetCandidate("510300", "沪深300ETF", DataSourceKind.ETF),
                AssetCandidate("000300", "沪深300指数", DataSourceKind.INDEX),
            ],
        ),
        AssetTarget(
            asset_class="long_bond",
            weight=0.40,
            candidates=[
                AssetCandidate("511010", "国债ETF", DataSourceKind.ETF),
                AssetCandidate("000012", "国债指数", DataSourceKind.INDEX),
            ],
        ),
        AssetTarget(
            asset_class="commodity",
            weight=0.075,
            candidates=[
                AssetCandidate("159985", "豆粕ETF", DataSourceKind.ETF),
                AssetCandidate("000066", "上证商品指数", DataSourceKind.INDEX),
            ],
        ),
        AssetTarget(
            asset_class="gold",
            weight=0.075,
            candidates=[
                AssetCandidate("518880", "黄金ETF", DataSourceKind.ETF),
                AssetCandidate("000066", "上证商品指数代理", DataSourceKind.INDEX),
            ],
        ),
        AssetTarget(
            asset_class="cash",
            weight=0.15,
            candidates=[
                AssetCandidate("511880", "货币ETF", DataSourceKind.ETF),
                AssetCandidate("000012", "国债指数代理", DataSourceKind.INDEX),
            ],
        ),
    ]


def stock_bond_60_40_targets() -> list[AssetTarget]:
    return [
        AssetTarget(
            asset_class="equity",
            weight=0.60,
            candidates=[
                AssetCandidate("510300", "沪深300ETF", DataSourceKind.ETF),
                AssetCandidate("000300", "沪深300指数", DataSourceKind.INDEX),
            ],
        ),
        AssetTarget(
            asset_class="bond",
            weight=0.40,
            candidates=[
                AssetCandidate("511010", "国债ETF", DataSourceKind.ETF),
                AssetCandidate("000012", "国债指数", DataSourceKind.INDEX),
            ],
        ),
    ]


def equity_only_targets() -> list[AssetTarget]:
    return [
        AssetTarget(
            asset_class="equity",
            weight=1.0,
            candidates=[
                AssetCandidate("510300", "沪深300ETF", DataSourceKind.ETF),
                AssetCandidate("000300", "沪深300指数", DataSourceKind.INDEX),
            ],
        )
    ]


def bond_only_targets() -> list[AssetTarget]:
    return [
        AssetTarget(
            asset_class="bond",
            weight=1.0,
            candidates=[
                AssetCandidate("511010", "国债ETF", DataSourceKind.ETF),
                AssetCandidate("000012", "国债指数", DataSourceKind.INDEX),
            ],
        )
    ]


def select_asset_data(
    provider: AkshareProvider,
    target: AssetTarget,
    start: date,
    end: date,
    min_coverage_ratio: float = 0.95,
) -> SelectedAssetData:
    warnings: list[str] = []
    fallback_data: tuple[AssetCandidate, pd.DataFrame] | None = None
    for candidate in target.candidates:
        data = provider.fetch(candidate.symbol, candidate.kind, start=start, end=end)
        coverage = coverage_for(data, start=start, end=end)
        if coverage is None:
            warnings.append(f"{candidate.kind.value.upper()} {candidate.symbol} returned no data.")
            continue

        if coverage.covers_requested_range or coverage.ratio >= min_coverage_ratio:
            return SelectedAssetData(target=target, candidate=candidate, data=data, warnings=warnings)

        warnings.append(
            f"{candidate.kind.value.upper()} {candidate.symbol} coverage "
            f"{coverage.start} to {coverage.end} is below requested {start} to {end}."
        )
        if fallback_data is None:
            fallback_data = (candidate, data)

    if fallback_data is not None:
        candidate, data = fallback_data
        warnings.append(f"Using best available incomplete data for {target.asset_class}: {candidate.symbol}.")
        return SelectedAssetData(target=target, candidate=candidate, data=data, warnings=warnings)
    raise ValueError(f"no data available for asset class {target.asset_class}")


def select_portfolio_data(
    provider: AkshareProvider,
    targets: list[AssetTarget],
    start: date,
    end: date,
    min_coverage_ratio: float = 0.95,
) -> list[SelectedAssetData]:
    return [
        select_asset_data(
            provider=provider,
            target=target,
            start=start,
            end=end,
            min_coverage_ratio=min_coverage_ratio,
        )
        for target in targets
    ]
