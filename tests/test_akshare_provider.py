from __future__ import annotations

from datetime import date

import pandas as pd

from akquant.akshare_provider import AkshareProvider, DataSourceKind, fetch_all_index_returns, fetch_index_returns
from akquant.portfolios import AssetCandidate, AssetTarget, select_asset_data


class FakeAkshare:
    def index_stock_info(self):
        return pd.DataFrame(
            {
                "index_code": ["000300", "000012"],
                "display_name": ["沪深300", "国债指数"],
                "publish_date": ["2005/4/8", "2003/1/2"],
            }
        )

    def fund_etf_hist_em(self, symbol: str, period: str, start_date: str, end_date: str, adjust: str):
        assert period == "daily"
        assert adjust == "hfq"
        return pd.DataFrame(
            {
                "日期": ["2018-01-02", "2018-01-03"],
                "开盘": [1.0, 1.1],
                "收盘": [1.1, 1.2],
                "最高": [1.2, 1.3],
                "最低": [0.9, 1.0],
                "成交量": [1000, 1000],
                "成交额": [10000, 11000],
            }
        )

    def index_zh_a_hist(self, symbol: str, period: str, start_date: str, end_date: str):
        assert period == "daily"
        return pd.DataFrame(
            {
                "日期": ["2006-01-04", "2006-01-05", "2026-01-05"],
                "开盘": [100.0, 101.0, 300.0],
                "收盘": [101.0, 102.0, 303.0],
                "最高": [102.0, 103.0, 306.0],
                "最低": [99.0, 100.0, 299.0],
                "成交量": [100, 100, 100],
                "成交额": [10000, 10200, 30300],
            }
        )


def test_select_asset_data_prefers_etf_but_falls_back_to_index_when_coverage_is_short():
    provider = AkshareProvider(ak_module=FakeAkshare())
    target = AssetTarget(
        asset_class="equity",
        weight=0.30,
        candidates=[
            AssetCandidate(symbol="510300", name="沪深300ETF", kind=DataSourceKind.ETF),
            AssetCandidate(symbol="000300", name="沪深300指数", kind=DataSourceKind.INDEX),
        ],
    )

    selected = select_asset_data(
        provider=provider,
        target=target,
        start=date(2006, 1, 1),
        end=date(2026, 1, 5),
        min_coverage_ratio=0.95,
    )

    assert selected.candidate.symbol == "000300"
    assert selected.candidate.kind is DataSourceKind.INDEX
    assert "ETF 510300 coverage" in " ".join(selected.warnings)
    assert selected.data.index.min().date() == date(2006, 1, 4)
    assert selected.data.index.max().date() == date(2026, 1, 5)


def test_fetch_index_returns_builds_wide_return_table_for_multiple_indices():
    provider = AkshareProvider(ak_module=FakeAkshare())

    returns = fetch_index_returns(
        provider=provider,
        symbols=["000300", "000012"],
        start=date(2006, 1, 1),
        end=date(2026, 1, 5),
    )

    assert list(returns.columns) == ["000300", "000012"]
    assert returns.index.name == "date"
    assert returns.iloc[0]["000300"] > 0


def test_fetch_all_index_returns_uses_akshare_index_catalog():
    provider = AkshareProvider(ak_module=FakeAkshare())

    returns = fetch_all_index_returns(provider=provider, start=date(2006, 1, 1), end=date(2026, 1, 5))

    assert list(returns.columns) == ["000300", "000012"]
    assert returns.index.name == "date"
