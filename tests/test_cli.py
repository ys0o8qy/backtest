from datetime import date
from pathlib import Path
import sys

import pandas as pd

import akquant.cli as cli_module
from akquant.akshare_provider import AkshareProvider
from akquant.cli import main
from akquant.factor_store import FactorStore


def test_cli_generates_markdown_report(tmp_path):
    output = tmp_path / "cli-report.md"

    exit_code = main(
        [
            "--data",
            "tests/fixtures/sample_bars.csv",
            "--symbol",
            "000001",
            "--initial-cash",
            "10000",
            "--short-window",
            "2",
            "--long-window",
            "3",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    assert output.exists()
    assert "# AKQuant 回测报告" in output.read_text(encoding="utf-8")


def test_portfolio_cli_generates_backtrader_multi_asset_report(tmp_path):
    output = tmp_path / "portfolio-report.md"

    exit_code = main(
        [
            "portfolio",
            "--feed",
            "stock=tests/fixtures/portfolio_stock.csv",
            "--feed",
            "bond=tests/fixtures/portfolio_bond.csv",
            "--weight",
            "stock=0.6",
            "--weight",
            "bond=0.4",
            "--initial-cash",
            "100000",
            "--rebalance",
            "monthly",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    report = output.read_text(encoding="utf-8")
    assert "# AKQuant 组合回测报告" in report
    assert "Backtrader" in report
    assert "stock" in report
    assert "bond" in report


def test_main_reads_sys_argv_when_called_from_module_entrypoint(tmp_path, monkeypatch):
    output = tmp_path / "portfolio-report.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "akquant",
            "portfolio",
            "--feed",
            "stock=tests/fixtures/portfolio_stock.csv",
            "--feed",
            "bond=tests/fixtures/portfolio_bond.csv",
            "--weight",
            "stock=0.6",
            "--weight",
            "bond=0.4",
            "--out",
            str(output),
        ],
    )

    exit_code = main()

    assert exit_code == 0
    assert "# AKQuant 组合回测报告" in output.read_text(encoding="utf-8")


class FakeAkshareForCliAllWeather:
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


def test_all_weather_cli_uses_akshare_provider_and_reports_selected_assets(tmp_path, monkeypatch):
    output = tmp_path / "all-weather.md"
    monkeypatch.setattr(cli_module, "AkshareProvider", lambda: AkshareProvider(ak_module=FakeAkshareForCliAllWeather()))

    exit_code = main(
        [
            "all-weather",
            "--start",
            "2006-01-01",
            "--end",
            "2026-01-05",
            "--initial-cash",
            "100000",
            "--rebalance",
            "yearly",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    report = output.read_text(encoding="utf-8")
    assert "# AKQuant 全天候组合回测报告" in report
    assert "ETF 优先" in report
    assert "INDEX" in report


def test_compare_cli_runs_builtin_and_custom_portfolios(tmp_path, monkeypatch):
    output = tmp_path / "comparison.md"
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        """
id: custom_60_40
name: Custom 60/40
rebalance: yearly
targets:
  - asset_class: equity
    weight: 0.6
    candidates:
      - { symbol: "510300", name: "沪深300ETF", kind: "etf" }
      - { symbol: "000300", name: "沪深300指数", kind: "index" }
  - asset_class: bond
    weight: 0.4
    candidates:
      - { symbol: "511010", name: "国债ETF", kind: "etf" }
      - { symbol: "000012", name: "国债指数", kind: "index" }
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "AkshareProvider", lambda: AkshareProvider(ak_module=FakeAkshareForCliAllWeather()))

    exit_code = main(
        [
            "compare",
            "--portfolio",
            "all_weather",
            "--portfolio",
            str(custom),
            "--start",
            "2006-01-01",
            "--end",
            "2026-01-05",
            "--rebalance",
            "yearly",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    report = output.read_text(encoding="utf-8")
    assert "# AKQuant 多组合对比报告" in report
    assert "收益率排名" in report
    assert "最大回撤对比" in report
    assert "年度收益对比" in report
    assert "custom_60_40" in report
    assert "fallback" in report.lower()


class FakeFundamentalProviderForScreen:
    def fetch_latest_valuation_snapshot(self):
        from datetime import date

        return pd.DataFrame(
            [
                {
                    "as_of_date": date(2026, 6, 10),
                    "data_date": date(2026, 6, 10),
                    "symbol": "000001",
                    "name": "低估高息",
                    "close": 10.0,
                    "pe_ttm": 8.0,
                    "pe_dynamic": 8.0,
                    "pe_static": None,
                    "pb": 0.8,
                    "dividend_yield": 0.05,
                    "market_cap": 100_000_000_000,
                    "float_market_cap": 90_000_000_000,
                    "turnover_amount": 100_000_000,
                    "industry": "bank",
                    "is_st": False,
                    "is_suspended": False,
                    "listing_age_days": 1000,
                    "data_quality_flags": [],
                },
                {
                    "as_of_date": date(2026, 6, 10),
                    "data_date": date(2026, 6, 10),
                    "symbol": "000002",
                    "name": "负PE",
                    "close": 20.0,
                    "pe_ttm": -1.0,
                    "pe_dynamic": -1.0,
                    "pe_static": None,
                    "pb": 1.0,
                    "dividend_yield": 0.04,
                    "market_cap": 80_000_000_000,
                    "float_market_cap": 70_000_000_000,
                    "turnover_amount": 100_000_000,
                    "industry": "real_estate",
                    "is_st": False,
                    "is_suspended": False,
                    "listing_age_days": 1000,
                    "data_quality_flags": [],
                },
            ]
        )


class FakeFundamentalProviderWithSpecialStatus:
    def fetch_latest_valuation_snapshot(self):
        from datetime import date

        return pd.DataFrame(
            [
                {
                    "as_of_date": date(2026, 6, 10),
                    "data_date": date(2026, 6, 10),
                    "symbol": "000003",
                    "name": "ST高息",
                    "close": 10.0,
                    "pe_ttm": 6.0,
                    "pe_dynamic": 6.0,
                    "pe_static": None,
                    "pb": 0.6,
                    "dividend_yield": 0.08,
                    "market_cap": 30_000_000_000,
                    "float_market_cap": 20_000_000_000,
                    "turnover_amount": 60_000_000,
                    "industry": "test",
                    "is_st": True,
                    "is_suspended": False,
                    "listing_age_days": 1000,
                    "data_quality_flags": [],
                },
                {
                    "as_of_date": date(2026, 6, 10),
                    "data_date": date(2026, 6, 10),
                    "symbol": "000004",
                    "name": "普通低估",
                    "close": 10.0,
                    "pe_ttm": 8.0,
                    "pe_dynamic": 8.0,
                    "pe_static": None,
                    "pb": 0.8,
                    "dividend_yield": 0.05,
                    "market_cap": 30_000_000_000,
                    "float_market_cap": 20_000_000_000,
                    "turnover_amount": 60_000_000,
                    "industry": "test",
                    "is_st": False,
                    "is_suspended": False,
                    "listing_age_days": 1000,
                    "data_quality_flags": [],
                },
            ]
        )


class FailingFundamentalProvider:
    def fetch_latest_valuation_snapshot(self):
        raise AssertionError("provider should not be called when loading cached factor snapshot")


def test_screen_cli_generates_value_screen_report_and_csv(tmp_path, monkeypatch):
    output = tmp_path / "screen.md"
    csv_output = tmp_path / "screen.csv"
    monkeypatch.setattr(cli_module, "FundamentalDataProvider", lambda: FakeFundamentalProviderForScreen())

    exit_code = main(
        [
            "screen",
            "--as-of",
            "latest",
            "--pe-max",
            "15",
            "--pb-max",
            "1.5",
            "--dividend-yield-min",
            "0.03",
            "--top",
            "10",
            "--out",
            str(output),
            "--csv-out",
            str(csv_output),
        ]
    )

    assert exit_code == 0
    report = output.read_text(encoding="utf-8")
    assert "# AKQuant A股估值筛选报告" in report
    assert "低估高息" in report
    assert csv_output.exists()
    assert "000001" in csv_output.read_text(encoding="utf-8")


def test_screen_cli_latest_saves_factor_snapshot_when_cache_dir_is_given(tmp_path, monkeypatch):
    output = tmp_path / "screen.md"
    cache_dir = tmp_path / "factors"
    monkeypatch.setattr(cli_module, "FundamentalDataProvider", lambda: FakeFundamentalProviderForScreen())

    exit_code = main(
        [
            "screen",
            "--as-of",
            "latest",
            "--factor-cache-dir",
            str(cache_dir),
            "--pe-max",
            "15",
            "--pb-max",
            "1.5",
            "--dividend-yield-min",
            "0.03",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    assert (cache_dir / "2026-06-10.csv").exists()
    assert (cache_dir / "2026-06-10.json").exists()


def test_screen_cli_loads_cached_factor_snapshot_for_specific_date(tmp_path, monkeypatch):
    output = tmp_path / "cached-screen.md"
    cache_dir = tmp_path / "factors"
    FactorStore(cache_dir).save_snapshot(
        as_of_date=date(2026, 6, 10),
        frame=pd.DataFrame(
            [
                {
                    "as_of_date": date(2026, 6, 10),
                    "data_date": date(2026, 6, 10),
                    "symbol": "000001",
                    "name": "缓存低估",
                    "close": 10.0,
                    "pe_ttm": 8.0,
                    "pe_dynamic": 8.0,
                    "pe_static": None,
                    "pb": 0.8,
                    "dividend_yield": 0.05,
                    "market_cap": 100_000_000_000,
                    "float_market_cap": 90_000_000_000,
                    "turnover_amount": 100_000_000,
                    "industry": "bank",
                    "is_st": False,
                    "is_suspended": False,
                    "listing_age_days": 1000,
                    "data_quality_flags": ["cached"],
                }
            ]
        ),
    )
    monkeypatch.setattr(cli_module, "FundamentalDataProvider", lambda: FailingFundamentalProvider())

    exit_code = main(
        [
            "screen",
            "--as-of",
            "2026-06-10",
            "--factor-cache-dir",
            str(cache_dir),
            "--pe-max",
            "15",
            "--pb-max",
            "1.5",
            "--dividend-yield-min",
            "0.03",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    assert "缓存低估" in output.read_text(encoding="utf-8")


def test_screen_cli_include_st_allows_st_candidates(tmp_path, monkeypatch):
    output = tmp_path / "screen-include-st.md"
    monkeypatch.setattr(cli_module, "FundamentalDataProvider", lambda: FakeFundamentalProviderWithSpecialStatus())

    exit_code = main(
        [
            "screen",
            "--as-of",
            "latest",
            "--include-st",
            "--pe-max",
            "15",
            "--pb-max",
            "1.5",
            "--dividend-yield-min",
            "0.03",
            "--top",
            "1",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    report = output.read_text(encoding="utf-8")
    assert "ST高息" in report
