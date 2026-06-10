from __future__ import annotations

from datetime import date

import pandas as pd

from akquant.screening import RankingSpec, ScreenConfig, ScreeningRule, UniverseConfig, run_screen


def make_snapshot() -> pd.DataFrame:
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
                "pe_ttm": -5.0,
                "pe_dynamic": -5.0,
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
            {
                "as_of_date": date(2026, 6, 10),
                "data_date": date(2026, 6, 10),
                "symbol": "000003",
                "name": "ST低成交",
                "close": 5.0,
                "pe_ttm": 10.0,
                "pe_dynamic": 10.0,
                "pe_static": None,
                "pb": 1.0,
                "dividend_yield": 0.06,
                "market_cap": 5_000_000_000,
                "float_market_cap": 4_000_000_000,
                "turnover_amount": 1_000_000,
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
                "name": "合格但较差",
                "close": 8.0,
                "pe_ttm": 14.0,
                "pe_dynamic": 14.0,
                "pe_static": None,
                "pb": 1.4,
                "dividend_yield": 0.031,
                "market_cap": 60_000_000_000,
                "float_market_cap": 50_000_000_000,
                "turnover_amount": 80_000_000,
                "industry": "industrial",
                "is_st": False,
                "is_suspended": False,
                "listing_age_days": 800,
                "data_quality_flags": [],
            },
        ]
    )


def test_run_screen_filters_snapshot_and_scores_top_n_stock_pool():
    config = ScreenConfig(
        id="value_screen",
        name="低估值高股息",
        as_of_date="latest",
        filters=[
            ScreeningRule("is_st", "==", False),
            ScreeningRule("is_suspended", "==", False),
            ScreeningRule("pe_ttm", ">", 0),
            ScreeningRule("pe_ttm", "<=", 15),
            ScreeningRule("pb", "<=", 1.5),
            ScreeningRule("dividend_yield", ">=", 0.03),
            ScreeningRule("market_cap", ">=", 5_000_000_000),
            ScreeningRule("turnover_amount", ">=", 50_000_000),
        ],
        ranking=[
            RankingSpec("pe_ttm", ascending=True, weight=0.4),
            RankingSpec("pb", ascending=True, weight=0.3),
            RankingSpec("dividend_yield", ascending=False, weight=0.3),
        ],
        top_n=2,
    )

    pool = run_screen(make_snapshot(), config)

    assert pool.pool_id == "value_screen-2026-06-10"
    assert list(pool.selected["symbol"]) == ["000001", "000004"]
    assert "value_score" in pool.selected.columns
    assert pool.selected.iloc[0]["value_score"] > pool.selected.iloc[1]["value_score"]
    assert pool.rejected_summary.iloc[0]["remaining_count"] == 4
    assert pool.rejected_summary.iloc[-1]["remaining_count"] == 2
    assert pool.warnings == []


def test_run_screen_applies_universe_config_before_explicit_filters():
    snapshot = make_snapshot()
    suspended = snapshot.iloc[[0]].copy()
    suspended["symbol"] = "000005"
    suspended["name"] = "停牌"
    suspended["is_suspended"] = True
    new_stock = snapshot.iloc[[0]].copy()
    new_stock["symbol"] = "000006"
    new_stock["name"] = "新股"
    new_stock["listing_age_days"] = 30
    snapshot = pd.concat([snapshot, suspended, new_stock], ignore_index=True)
    config = ScreenConfig(
        id="universe_screen",
        name="基础股票池",
        universe=UniverseConfig(exclude_st=True, exclude_suspended=True, min_listing_days=180),
        filters=[ScreeningRule("pe_ttm", ">", 0)],
        ranking=[RankingSpec("pe_ttm", ascending=True, weight=1.0)],
        top_n=10,
    )

    pool = run_screen(snapshot, config)

    assert "000003" not in pool.selected_symbols
    assert "000005" not in pool.selected_symbols
    assert "000006" not in pool.selected_symbols
    assert "universe:is_st" in pool.rejected_summary["step"].tolist()
    assert "universe:is_suspended" in pool.rejected_summary["step"].tolist()
    assert "universe:listing_age_days" in pool.rejected_summary["step"].tolist()


def test_screen_config_rejects_negative_ranking_weights():
    try:
        ScreenConfig(
            id="bad_weights",
            name="bad",
            ranking=[
                RankingSpec("pe_ttm", ascending=True, weight=1.2),
                RankingSpec("pb", ascending=True, weight=-0.2),
            ],
        )
    except ValueError as exc:
        assert "ranking weights must be non-negative" in str(exc)
    else:
        raise AssertionError("negative ranking weights should fail")
