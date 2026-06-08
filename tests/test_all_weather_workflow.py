from __future__ import annotations

from datetime import date

import pandas as pd

from akquant.akshare_provider import AkshareProvider
from akquant.all_weather import run_all_weather_backtest


class FakeAkshareForAllWeather:
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
        return pd.DataFrame(
            {
                "日期": ["2006-01-04", "2006-02-06", "2026-01-05"],
                "开盘": [100.0, 101.0, 120.0],
                "收盘": [101.0, 102.0, 121.0],
                "最高": [102.0, 103.0, 122.0],
                "最低": [99.0, 100.0, 119.0],
                "成交量": [1000, 1000, 1000],
                "成交额": [101000, 102000, 121000],
            }
        )


def test_all_weather_workflow_uses_etf_first_then_index_fallback_and_runs_backtrader():
    provider = AkshareProvider(ak_module=FakeAkshareForAllWeather())

    workflow = run_all_weather_backtest(
        provider=provider,
        start=date(2006, 1, 1),
        end=date(2026, 1, 5),
        initial_cash=100_000,
        rebalance="yearly",
    )

    assert workflow.result.final_value > 0
    assert workflow.result.rebalance_count >= 1
    assert len(workflow.selected_assets) == 5
    assert all(selected.candidate.kind.value == "index" for selected in workflow.selected_assets)
    assert any("coverage" in warning for warning in workflow.result.warnings)
