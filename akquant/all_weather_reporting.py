from __future__ import annotations

from pathlib import Path

from akquant.all_weather import AllWeatherBacktest
from akquant.portfolio_reporting import _render as render_portfolio_report


def write_all_weather_markdown_report(workflow: AllWeatherBacktest, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _render(workflow)
    path.write_text(content, encoding="utf-8")
    return path


def _render(workflow: AllWeatherBacktest) -> str:
    base = render_portfolio_report(workflow.result).replace("# AKQuant 组合回测报告", "# AKQuant 全天候组合回测报告", 1)
    lines = [
        "# AKQuant 全天候组合回测报告",
        "",
        "## 数据选择",
        "",
        "- 选择规则：真实可交易 ETF 优先；若 ETF 不满足请求区间覆盖，则自动切换到指数代理。",
        "- 报告中的 INDEX 表示指数代理数据，不等同于可直接交易标的。",
        "",
        "| 资产类别 | 权重 | 使用代码 | 使用名称 | 数据类型 |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for selected in workflow.selected_assets:
        lines.append(
            f"| {selected.target.asset_class} | {selected.target.weight * 100:.2f}% | "
            f"{selected.candidate.symbol} | {selected.candidate.name} | {selected.candidate.kind.value.upper()} |"
        )
    _, _, tail = base.partition("## 运行摘要")
    lines.extend(["", "## 运行摘要" + tail])
    return "\n".join(lines)
