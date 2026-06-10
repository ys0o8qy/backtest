from __future__ import annotations

from akquant.portfolios import PortfolioConfig, all_weather_targets, bond_only_targets, equity_only_targets, stock_bond_60_40_targets


def list_builtin_portfolios() -> set[str]:
    return {"all_weather", "stock_bond_60_40", "equity_only", "bond_only"}


def get_builtin_portfolio(portfolio_id: str) -> PortfolioConfig:
    if portfolio_id == "all_weather":
        return PortfolioConfig(id="all_weather", name="A股全天候", targets=all_weather_targets(), rebalance="quarterly")
    if portfolio_id == "stock_bond_60_40":
        return PortfolioConfig(id="stock_bond_60_40", name="股债 60/40", targets=stock_bond_60_40_targets(), rebalance="quarterly")
    if portfolio_id == "equity_only":
        return PortfolioConfig(id="equity_only", name="纯股票", targets=equity_only_targets(), rebalance="quarterly")
    if portfolio_id == "bond_only":
        return PortfolioConfig(id="bond_only", name="纯债券", targets=bond_only_targets(), rebalance="quarterly")
    raise KeyError(f"unknown builtin portfolio: {portfolio_id}")
