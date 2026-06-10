from __future__ import annotations

from dataclasses import replace
from datetime import date

from akquant.akshare_provider import AkshareProvider
from akquant.backtrader_engine import BacktraderPortfolioConfig, BacktraderPortfolioResult, run_backtrader_portfolio
from akquant.portfolios import PortfolioConfig, SelectedAssetData, select_portfolio_data


def run_portfolio_config(
    provider: AkshareProvider,
    config: PortfolioConfig,
    start: date,
    end: date,
) -> tuple[BacktraderPortfolioResult, list[SelectedAssetData]]:
    selected = select_portfolio_data(
        provider=provider,
        targets=config.targets,
        start=start,
        end=end,
        min_coverage_ratio=config.data_policy.min_coverage_ratio,
    )
    data = {item.target.asset_class: item.data for item in selected}
    weights = {item.target.asset_class: item.target.weight for item in selected}
    fallback_warnings = [warning for item in selected for warning in item.warnings]
    result = run_backtrader_portfolio(
        data=data,
        config=BacktraderPortfolioConfig(
            initial_cash=config.initial_cash,
            weights=weights,
            rebalance=config.rebalance,
            commission_rate=config.cost_model.commission_rate,
            slippage_perc=config.cost_model.slippage_perc,
            portfolio_id=config.id,
            config_snapshot=config.snapshot(),
        ),
    )
    return replace(result, warnings=fallback_warnings + result.warnings), selected
