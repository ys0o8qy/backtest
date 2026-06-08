from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from akquant.akshare_provider import AkshareProvider
from akquant.backtrader_engine import BacktraderPortfolioConfig, BacktraderPortfolioResult, run_backtrader_portfolio
from akquant.portfolios import SelectedAssetData, all_weather_targets, select_portfolio_data


@dataclass(frozen=True)
class AllWeatherBacktest:
    selected_assets: list[SelectedAssetData]
    result: BacktraderPortfolioResult


def run_all_weather_backtest(
    provider: AkshareProvider,
    start: date,
    end: date,
    initial_cash: float = 100_000.0,
    rebalance: str = "quarterly",
    min_coverage_ratio: float = 0.95,
) -> AllWeatherBacktest:
    selected = select_portfolio_data(
        provider=provider,
        targets=all_weather_targets(),
        start=start,
        end=end,
        min_coverage_ratio=min_coverage_ratio,
    )
    data = {item.target.asset_class: item.data for item in selected}
    weights = {item.target.asset_class: item.target.weight for item in selected}
    fallback_warnings = [warning for item in selected for warning in item.warnings]
    result = run_backtrader_portfolio(
        data=data,
        config=BacktraderPortfolioConfig(
            initial_cash=initial_cash,
            weights=weights,
            rebalance=rebalance,
        ),
    )
    result = BacktraderPortfolioResult(
        initial_cash=result.initial_cash,
        final_value=result.final_value,
        equity_curve=result.equity_curve,
        rebalance_count=result.rebalance_count,
        weights=result.weights,
        warnings=fallback_warnings + result.warnings,
    )
    return AllWeatherBacktest(selected_assets=selected, result=result)
