from pathlib import Path
import sys

import pandas as pd

import akquant.cli as cli_module
from akquant.akshare_provider import AkshareProvider
from akquant.cli import main


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
