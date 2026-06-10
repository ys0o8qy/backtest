from __future__ import annotations

from datetime import date

import pandas as pd

from akquant.fundamentals import FundamentalDataProvider


class FakeAkshareFundamentals:
    def stock_zh_a_spot_em(self):
        return pd.DataFrame(
            {
                "代码": ["000001", "000002", "000003"],
                "名称": ["平安银行", "万科A", "ST测试"],
                "最新价": [10.0, 20.0, 5.0],
                "市盈率-动态": [8.0, -3.0, 12.0],
                "市净率": [0.9, 1.2, 1.1],
                "股息率": [0.04, None, 0.05],
                "总市值": [100_000_000_000, 80_000_000_000, 3_000_000_000],
                "流通市值": [90_000_000_000, 70_000_000_000, 2_000_000_000],
                "成交额": [100_000_000, 60_000_000, 10_000_000],
                "涨跌幅": [1.0, 0.5, 0.0],
            }
        )


class FakeAkshareDividendFundamentals:
    def stock_zh_a_spot_em(self):
        return pd.DataFrame(
            {
                "代码": ["000001", "000002"],
                "名称": ["平安银行", "万科A"],
                "最新价": [10.0, 20.0],
                "市盈率-动态": [8.0, 9.0],
                "市净率": [0.9, 1.2],
                "总市值": [100_000_000_000, 80_000_000_000],
                "流通市值": [90_000_000_000, 70_000_000_000],
                "成交额": [100_000_000, 60_000_000],
            }
        )

    def stock_fhps_em(self, date: str):
        assert date == "20251231"
        return pd.DataFrame(
            {
                "代码": ["000002"],
                "现金分红-股息率": [5.5],
            }
        )


class FakeAkshareMultiReportDividendFundamentals:
    def stock_zh_a_spot_em(self):
        return pd.DataFrame(
            {
                "代码": ["000001", "000002"],
                "名称": ["平安银行", "万科A"],
                "最新价": [10.0, 20.0],
                "市盈率-动态": [8.0, 9.0],
                "市净率": [0.9, 1.2],
                "总市值": [100_000_000_000, 80_000_000_000],
                "流通市值": [90_000_000_000, 70_000_000_000],
                "成交额": [100_000_000, 60_000_000],
            }
        )

    def stock_fhps_em(self, date: str):
        if date == "20251231":
            return pd.DataFrame({"代码": ["000002"], "现金分红-股息率": [5.5]})
        if date == "20250630":
            return pd.DataFrame({"代码": ["000001"], "现金分红-股息率": [3.0]})
        return pd.DataFrame(columns=["代码", "现金分红-股息率"])


def test_fetch_latest_valuation_snapshot_normalizes_spot_fields_and_flags_quality():
    provider = FundamentalDataProvider(ak_module=FakeAkshareFundamentals())

    snapshot = provider.fetch_latest_valuation_snapshot(as_of_date=date(2026, 6, 10))

    assert list(snapshot.columns) == [
        "as_of_date",
        "data_date",
        "symbol",
        "name",
        "close",
        "pe_ttm",
        "pe_dynamic",
        "pe_static",
        "pb",
        "dividend_yield",
        "market_cap",
        "float_market_cap",
        "turnover_amount",
        "industry",
        "is_st",
        "is_suspended",
        "listing_age_days",
        "data_quality_flags",
    ]
    first = snapshot.loc[snapshot["symbol"] == "000001"].iloc[0]
    assert first["pe_ttm"] == 8.0
    assert first["pb"] == 0.9
    assert first["dividend_yield"] == 0.04
    st = snapshot.loc[snapshot["symbol"] == "000003"].iloc[0]
    assert st["is_st"] is True
    missing_dividend = snapshot.loc[snapshot["symbol"] == "000002"].iloc[0]
    assert "missing_dividend_yield" in missing_dividend["data_quality_flags"]


def test_fetch_latest_valuation_snapshot_enriches_dividend_yield_from_report_distribution():
    provider = FundamentalDataProvider(ak_module=FakeAkshareDividendFundamentals())

    snapshot = provider.fetch_latest_valuation_snapshot(as_of_date=date(2026, 6, 10))

    enriched = snapshot.loc[snapshot["symbol"] == "000002"].iloc[0]
    assert enriched["dividend_yield"] == 0.055
    assert "missing_dividend_yield" not in enriched["data_quality_flags"]
    assert "dividend_yield_from_fhps" in enriched["data_quality_flags"]


def test_fetch_latest_valuation_snapshot_enriches_dividend_yield_across_report_dates():
    provider = FundamentalDataProvider(ak_module=FakeAkshareMultiReportDividendFundamentals())

    snapshot = provider.fetch_latest_valuation_snapshot(as_of_date=date(2026, 6, 10))

    first = snapshot.loc[snapshot["symbol"] == "000001"].iloc[0]
    second = snapshot.loc[snapshot["symbol"] == "000002"].iloc[0]
    assert first["dividend_yield"] == 0.03
    assert second["dividend_yield"] == 0.055
