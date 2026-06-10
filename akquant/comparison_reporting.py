from __future__ import annotations

from pathlib import Path

import pandas as pd

from akquant.comparison import ComparisonReport


def write_comparison_markdown_report(report: ComparisonReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render(report), encoding="utf-8")
    return path


def _render(report: ComparisonReport) -> str:
    lines = [
        "# AKQuant 多组合对比报告",
        "",
        "## 组合对比总览",
        "",
        _markdown_table(report.metrics_table.reset_index()),
        "",
        "## 收益率排名",
        "",
        _markdown_table(_ranking(report.metrics_table, "cumulative_return")),
        "",
        "## 风险指标排名",
        "",
        _markdown_table(_ranking(report.metrics_table, "sharpe")),
        "",
        "## 最大回撤对比",
        "",
        _markdown_table(_ranking(report.metrics_table, "max_drawdown", ascending=False)),
        "",
        "## 年度收益对比",
        "",
        _markdown_table(report.yearly_return_table.reset_index()),
        "",
        "## 实际使用标的",
        "",
        _markdown_table(report.selected_asset_table),
        "",
        "## Fallback 和数据覆盖警告",
        "",
        _markdown_table(report.fallback_summary) if not report.fallback_summary.empty else "无 fallback 警告。",
        "",
        "## 配置附录",
        "",
    ]
    for run in report.runs:
        lines.append(f"- `{run.portfolio_id}`: {run.config_snapshot}")
    return "\n".join(lines) + "\n"


def _ranking(table: pd.DataFrame, column: str, ascending: bool = False) -> pd.DataFrame:
    if table.empty or column not in table.columns:
        return pd.DataFrame()
    return table[[column]].sort_values(column, ascending=ascending).reset_index()


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "无数据。"
    return frame.to_markdown(index=False)
