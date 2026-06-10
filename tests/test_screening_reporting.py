from __future__ import annotations

import json
from datetime import date

import pandas as pd

from akquant.screening import RankingSpec, ScreenConfig, ScreeningRule, run_screen
from akquant.screening_reporting import write_screening_markdown_report


def test_write_screening_markdown_report_contains_selected_stocks_and_filter_funnel(tmp_path):
    snapshot = pd.DataFrame(
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
            }
        ]
    )
    config = ScreenConfig(
        id="value_screen",
        name="低估值高股息",
        filters=[ScreeningRule("pe_ttm", ">", 0)],
        ranking=[RankingSpec("pe_ttm", ascending=True, weight=1.0)],
        top_n=10,
    )
    pool = run_screen(snapshot, config)
    output = tmp_path / "screen.md"

    write_screening_markdown_report(pool, output)

    content = output.read_text(encoding="utf-8")
    assert "# AKQuant A股估值筛选报告" in content
    assert "筛选漏斗" in content
    assert "低估高息" in content
    assert "value_score" in content


def test_write_screening_markdown_report_serializes_config_snapshot_as_json(tmp_path):
    snapshot = pd.DataFrame(
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
            }
        ]
    )
    config = ScreenConfig(
        id="value_screen",
        name="低估值高股息",
        as_of_date=date(2026, 6, 10),
        filters=[ScreeningRule("pe_ttm", ">", 0)],
        ranking=[RankingSpec("pe_ttm", ascending=True, weight=1.0)],
        top_n=10,
    )
    pool = run_screen(snapshot, config)
    output = tmp_path / "screen.md"

    write_screening_markdown_report(pool, output)

    content = output.read_text(encoding="utf-8")
    assert "```json" in content
    json_payload = content.split("```json", 1)[1].split("```", 1)[0].strip()
    assert json.loads(json_payload)["as_of_date"] == "2026-06-10"
