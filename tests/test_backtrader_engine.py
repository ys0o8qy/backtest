from __future__ import annotations

import pandas as pd

from akquant.backtrader_engine import BacktraderPortfolioConfig, run_backtrader_portfolio


def make_feed(closes: list[float]) -> pd.DataFrame:
    index = pd.to_datetime(["2026-01-02", "2026-02-02", "2026-03-02", "2026-04-02"])
    return pd.DataFrame(
        {
            "open": closes,
            "high": [value * 1.01 for value in closes],
            "low": [value * 0.99 for value in closes],
            "close": closes,
            "volume": [1000] * len(closes),
            "openinterest": [0] * len(closes),
        },
        index=index,
    )


def test_backtrader_portfolio_rebalances_multiple_assets_by_target_weight():
    data = {
        "stock": make_feed([100, 110, 120, 115]),
        "bond": make_feed([100, 101, 102, 103]),
    }
    config = BacktraderPortfolioConfig(
        initial_cash=100_000,
        weights={"stock": 0.6, "bond": 0.4},
        rebalance="monthly",
        commission_rate=0.0003,
    )

    result = run_backtrader_portfolio(data=data, config=config)

    assert result.final_value > 100_000
    assert len(result.equity_curve) == 4
    assert result.rebalance_count >= 2
    assert result.weights == {"stock": 0.6, "bond": 0.4}
    assert result.warnings == []
