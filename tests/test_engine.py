from pathlib import Path

from akquant.data import load_bars_csv
from akquant.engine import run_backtest
from akquant.models import BacktestConfig, OrderSide, RuleConfig


FIXTURE = Path("tests/fixtures/sample_bars.csv")


def test_load_bars_csv_returns_valid_sorted_fixture_bars():
    bars, warnings = load_bars_csv(FIXTURE, symbol="000001")

    assert warnings == []
    assert len(bars) == 10
    assert bars[0].symbol == "000001"
    assert bars[0].close == 10.0
    assert bars[-1].close == 9.9
    assert bars[0].date < bars[-1].date


def test_dual_moving_average_backtest_produces_auditable_fills_and_equity_curve():
    bars, warnings = load_bars_csv(FIXTURE, symbol="000001")
    config = BacktestConfig(
        symbol="000001",
        initial_cash=10_000.0,
        short_window=2,
        long_window=3,
        target_allocation=1.0,
        rule_config=RuleConfig(slippage_bps=5),
    )

    result = run_backtest(config, bars, warnings=warnings)

    assert len(result.equity_curve) == len(bars)
    assert [fill.side for fill in result.fills] == [OrderSide.BUY, OrderSide.SELL]
    assert result.fills[0].quantity == 900
    assert result.fills[0].commission == 5.0
    assert result.fills[1].stamp_duty > 0
    assert result.rejections == []
    assert result.equity_curve[-1].total_value < config.initial_cash
    assert "research only" in " ".join(result.warnings).lower()
