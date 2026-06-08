from __future__ import annotations

from pathlib import Path

from akquant.analytics import calculate_metrics
from akquant.models import BacktestResult


def write_markdown_report(result: BacktestResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = calculate_metrics(result)
    path.write_text(_render_report(result, metrics), encoding="utf-8")
    return path


def _render_report(result: BacktestResult, metrics: dict[str, float | int]) -> str:
    lines = [
        "# AKQuant 回测报告",
        "",
        "## 运行摘要",
        "",
        f"- 标的：`{result.config.symbol}`",
        f"- 初始资金：{result.config.initial_cash:.2f}",
        f"- 短均线窗口：{result.config.short_window}",
        f"- 长均线窗口：{result.config.long_window}",
        f"- 目标仓位：{result.config.target_allocation:.2%}",
        f"- 回测区间：{result.bars[0].date} 至 {result.bars[-1].date}",
        "",
        "## 关键指标",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        f"| 期末权益 | {metrics['final_value']:.2f} |",
        f"| 累计收益 | {_pct(metrics['cumulative_return'])} |",
        f"| 年化收益 | {_pct(metrics['annualized_return'])} |",
        f"| 年化波动率 | {_pct(metrics['annualized_volatility'])} |",
        f"| 夏普比率 | {metrics['sharpe']:.4f} |",
        f"| 最大回撤 | {_pct(metrics['max_drawdown'])} |",
        f"| 卡玛比率 | {metrics['calmar']:.4f} |",
        f"| 换手率 | {metrics['turnover']:.4f} |",
        f"| 胜率 | {_pct(metrics['win_rate'])} |",
        "",
        "## 成本汇总",
        "",
        "| 成本 | 金额 |",
        "| --- | ---: |",
        f"| 手续费 | {metrics['total_commission']:.2f} |",
        f"| 印花税 | {metrics['total_stamp_duty']:.2f} |",
        f"| 滑点成本 | {metrics['total_slippage_cost']:.2f} |",
        "",
        "## 交易明细",
        "",
        "| 日期 | 标的 | 方向 | 数量 | 价格 | 手续费 | 印花税 | 现金变化 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for fill in result.fills:
        lines.append(
            "| "
            f"{fill.date} | {fill.symbol} | {fill.side.value} | {fill.quantity} | "
            f"{fill.price:.4f} | {fill.commission:.2f} | {fill.stamp_duty:.2f} | {fill.cash_delta:.2f} |"
        )

    lines.extend(
        [
            "",
            "## 拒单明细",
            "",
            "| 日期 | 标的 | 方向 | 数量 | 原因 | 说明 |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    if result.rejections:
        for rejection in result.rejections:
            lines.append(
                "| "
                f"{rejection.date} | {rejection.symbol} | {rejection.side.value} | "
                f"{rejection.requested_quantity} | {rejection.reason_code} | {rejection.reason_message} |"
            )
    else:
        lines.append("| - | - | - | 0 | NONE | 无拒单 |")

    lines.extend(["", "## 风险提示", ""])
    for warning in result.warnings:
        lines.append(f"- {warning}")

    lines.extend(["", "## 配置附录", ""])
    lines.append(f"- 手续费率：{result.config.rule_config.commission_rate}")
    lines.append(f"- 最低手续费：{result.config.rule_config.min_commission}")
    lines.append(f"- 印花税率：{result.config.rule_config.stamp_duty_rate}")
    lines.append(f"- 滑点：{result.config.rule_config.slippage_bps} bps")
    lines.append(f"- 整手数量：{result.config.rule_config.board_lot_size}")
    return "\n".join(lines) + "\n"


def _pct(value: float | int) -> str:
    return f"{float(value) * 100:.2f}%"
