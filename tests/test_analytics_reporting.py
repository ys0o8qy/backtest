from pathlib import Path

from akquant.analytics import calculate_metrics
from akquant.data import load_bars_csv
from akquant.engine import run_backtest
from akquant.models import BacktestConfig, RuleConfig
from akquant.reporting import write_markdown_report


def make_result():
    bars, warnings = load_bars_csv(Path("tests/fixtures/sample_bars.csv"), symbol="000001")
    return run_backtest(
        BacktestConfig(
            symbol="000001",
            initial_cash=10_000.0,
            short_window=2,
            long_window=3,
            target_allocation=1.0,
            rule_config=RuleConfig(slippage_bps=5),
        ),
        bars,
        warnings=warnings,
    )


def test_calculate_metrics_includes_returns_drawdown_costs_and_trade_behavior():
    result = make_result()

    metrics = calculate_metrics(result)

    assert metrics["cumulative_return"] < 0
    assert metrics["max_drawdown"] < 0
    assert metrics["total_commission"] == 10.0
    assert metrics["total_stamp_duty"] > 0
    assert metrics["total_slippage_cost"] > 0
    assert metrics["trade_count"] == 2
    assert metrics["turnover"] > 0


def test_markdown_report_contains_metrics_costs_trades_rejections_and_warnings(tmp_path):
    result = make_result()
    output = tmp_path / "report.md"

    write_markdown_report(result, output)

    report = output.read_text(encoding="utf-8")
    assert "# AKQuant 回测报告" in report
    assert "## 关键指标" in report
    assert "## 成本汇总" in report
    assert "## 交易明细" in report
    assert "## 拒单明细" in report
    assert "## 风险提示" in report
    assert "Research only" in report
