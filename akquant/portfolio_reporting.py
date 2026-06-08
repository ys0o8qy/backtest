from __future__ import annotations

from pathlib import Path

from akquant.backtrader_engine import BacktraderPortfolioResult


def write_portfolio_markdown_report(result: BacktraderPortfolioResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render(result), encoding="utf-8")
    return path


def _render(result: BacktraderPortfolioResult) -> str:
    cumulative_return = result.final_value / result.initial_cash - 1 if result.initial_cash else 0.0
    lines = [
        "# AKQuant 组合回测报告",
        "",
        "## 运行摘要",
        "",
        "- 引擎：Backtrader",
        f"- 初始资金：{result.initial_cash:.2f}",
        f"- 期末权益：{result.final_value:.2f}",
        f"- 累计收益：{cumulative_return * 100:.2f}%",
        f"- 再平衡次数：{result.rebalance_count}",
        "",
        "## 目标持仓",
        "",
        "| 资产 | 权重 |",
        "| --- | ---: |",
    ]
    for symbol, weight in result.weights.items():
        lines.append(f"| {symbol} | {weight * 100:.2f}% |")

    lines.extend(["", "## 权益曲线", "", "| 日期 | 权益 |", "| --- | ---: |"])
    for row in result.equity_curve.itertuples():
        lines.append(f"| {row.Index.date()} | {row.value:.2f} |")

    lines.extend(["", "## 风险提示", ""])
    if result.warnings:
        for warning in result.warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- Research only: backtest results do not represent future returns or investment advice.")
    return "\n".join(lines) + "\n"
