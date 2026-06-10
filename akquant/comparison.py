from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from akquant.akshare_provider import AkshareProvider
from akquant.backtrader_engine import BacktraderPortfolioResult
from akquant.metrics import drawdown_curve, metrics_from_equity_curve, monthly_returns, yearly_returns
from akquant.portfolio_runner import run_portfolio_config
from akquant.portfolios import PortfolioConfig, SelectedAssetData


@dataclass(frozen=True)
class ComparisonReport:
    runs: list[BacktraderPortfolioResult]
    selected_assets: dict[str, list[SelectedAssetData]]
    metrics_table: pd.DataFrame
    equity_curves: pd.DataFrame
    drawdown_curves: pd.DataFrame
    monthly_return_table: pd.DataFrame
    yearly_return_table: pd.DataFrame
    selected_asset_table: pd.DataFrame
    fallback_summary: pd.DataFrame


def run_comparison(
    provider: AkshareProvider,
    configs: list[PortfolioConfig],
    start: date,
    end: date,
) -> ComparisonReport:
    runs: list[BacktraderPortfolioResult] = []
    selected_by_portfolio: dict[str, list[SelectedAssetData]] = {}
    for config in configs:
        result, selected = run_portfolio_config(provider=provider, config=config, start=start, end=end)
        runs.append(result)
        selected_by_portfolio[config.id] = selected

    return ComparisonReport(
        runs=runs,
        selected_assets=selected_by_portfolio,
        metrics_table=_metrics_table(runs),
        equity_curves=_equity_curves(runs),
        drawdown_curves=_drawdown_curves(runs),
        monthly_return_table=_period_return_table(runs, monthly_returns),
        yearly_return_table=_period_return_table(runs, yearly_returns),
        selected_asset_table=_selected_asset_table(selected_by_portfolio),
        fallback_summary=_fallback_summary(runs),
    )


def _metrics_table(runs: list[BacktraderPortfolioResult]) -> pd.DataFrame:
    rows = {run.portfolio_id: metrics_from_equity_curve(run.equity_curve) for run in runs}
    table = pd.DataFrame.from_dict(rows, orient="index")
    table.index.name = "portfolio_id"
    return table


def _equity_curves(runs: list[BacktraderPortfolioResult]) -> pd.DataFrame:
    columns = [run.equity_curve["value"].rename(run.portfolio_id) for run in runs]
    result = pd.concat(columns, axis=1).sort_index() if columns else pd.DataFrame()
    result.index.name = "date"
    return result


def _drawdown_curves(runs: list[BacktraderPortfolioResult]) -> pd.DataFrame:
    columns = [drawdown_curve(run.equity_curve).rename(run.portfolio_id) for run in runs]
    result = pd.concat(columns, axis=1).sort_index() if columns else pd.DataFrame()
    result.index.name = "date"
    return result


def _period_return_table(runs: list[BacktraderPortfolioResult], calculator) -> pd.DataFrame:
    columns = [calculator(run.equity_curve).rename(run.portfolio_id) for run in runs]
    result = pd.concat(columns, axis=1).sort_index() if columns else pd.DataFrame()
    result.index.name = "date"
    return result


def _selected_asset_table(selected_by_portfolio: dict[str, list[SelectedAssetData]]) -> pd.DataFrame:
    rows = []
    for portfolio_id, selected_assets in selected_by_portfolio.items():
        for selected in selected_assets:
            rows.append(
                {
                    "portfolio_id": portfolio_id,
                    "asset_class": selected.target.asset_class,
                    "weight": selected.target.weight,
                    "symbol": selected.candidate.symbol,
                    "name": selected.candidate.name,
                    "data_kind": selected.candidate.kind.value,
                }
            )
    return pd.DataFrame(rows)


def _fallback_summary(runs: list[BacktraderPortfolioResult]) -> pd.DataFrame:
    rows = []
    for run in runs:
        for warning in run.warnings:
            if "coverage" in warning.lower() or "fallback" in warning.lower():
                rows.append({"portfolio_id": run.portfolio_id, "warning": warning})
    return pd.DataFrame(rows)
