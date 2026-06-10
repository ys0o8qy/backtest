from __future__ import annotations

from datetime import date

import pandas as pd

from akquant.akshare_provider import AkshareProvider, DataSourceKind
from akquant.comparison import run_comparison
from akquant.comparison_reporting import write_comparison_markdown_report
from akquant.portfolios import AssetCandidate, AssetTarget, PortfolioConfig


class FakeAkshareForComparison:
    def fund_etf_hist_em(self, symbol: str, period: str, start_date: str, end_date: str, adjust: str):
        return pd.DataFrame(
            {
                "日期": ["2020-01-02", "2020-02-03"],
                "开盘": [10.0, 10.0],
                "收盘": [10.0, 10.1],
                "最高": [10.1, 10.2],
                "最低": [9.9, 10.0],
                "成交量": [1000, 1000],
                "成交额": [10000, 10100],
            }
        )

    def index_zh_a_hist(self, symbol: str, period: str, start_date: str, end_date: str):
        closes = {
            "000300": [100.0, 120.0, 130.0, 125.0],
            "000012": [100.0, 102.0, 104.0, 106.0],
        }.get(symbol, [100.0, 101.0, 102.0, 103.0])
        return pd.DataFrame(
            {
                "日期": ["2006-01-04", "2006-02-06", "2006-03-06", "2026-01-05"],
                "开盘": closes,
                "收盘": closes,
                "最高": [value * 1.01 for value in closes],
                "最低": [value * 0.99 for value in closes],
                "成交量": [1000] * len(closes),
                "成交额": [value * 1000 for value in closes],
            }
        )


def make_config(portfolio_id: str, equity_weight: float) -> PortfolioConfig:
    return PortfolioConfig(
        id=portfolio_id,
        name=portfolio_id,
        rebalance="yearly",
        targets=[
            AssetTarget(
                asset_class="equity",
                weight=equity_weight,
                candidates=[
                    AssetCandidate("510300", "沪深300ETF", DataSourceKind.ETF),
                    AssetCandidate("000300", "沪深300指数", DataSourceKind.INDEX),
                ],
            ),
            AssetTarget(
                asset_class="bond",
                weight=1 - equity_weight,
                candidates=[
                    AssetCandidate("511010", "国债ETF", DataSourceKind.ETF),
                    AssetCandidate("000012", "国债指数", DataSourceKind.INDEX),
                ],
            ),
        ],
    )


def test_run_comparison_outputs_metrics_tables_assets_and_fallback_summary(tmp_path):
    provider = AkshareProvider(ak_module=FakeAkshareForComparison())
    report = run_comparison(
        provider=provider,
        configs=[make_config("aggressive", 0.8), make_config("balanced", 0.5)],
        start=date(2006, 1, 1),
        end=date(2026, 1, 5),
    )

    assert list(report.metrics_table.index) == ["aggressive", "balanced"]
    assert "cumulative_return" in report.metrics_table.columns
    assert "aggressive" in report.equity_curves.columns
    assert "balanced" in report.drawdown_curves.columns
    assert set(report.selected_asset_table["data_kind"]) == {"index"}
    assert not report.fallback_summary.empty

    output = tmp_path / "comparison.md"
    write_comparison_markdown_report(report, output)
    content = output.read_text(encoding="utf-8")
    assert "# AKQuant 多组合对比报告" in content
    assert "收益率排名" in content
    assert "fallback" in content.lower()
