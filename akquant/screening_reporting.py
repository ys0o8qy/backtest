from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from akquant.stock_pool import StockPool


def write_screening_markdown_report(pool: StockPool, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render(pool), encoding="utf-8")
    return path


def write_screening_csv(pool: StockPool, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pool.selected.to_csv(path, index=False, encoding="utf-8")
    return path


def _render(pool: StockPool) -> str:
    selected = _presentation_frame(pool.selected)
    lines = [
        "# AKQuant A股估值筛选报告",
        "",
        "## 运行摘要",
        "",
        f"- 股票池：`{pool.pool_id}`",
        f"- 截面日期：{pool.as_of_date.isoformat()}",
        f"- 筛选名称：{pool.config_snapshot.get('name', '')}",
        f"- 入选数量：{len(pool.selected)}",
        "",
        "## 入选股票",
        "",
        _markdown_table(selected),
        "",
        "## 筛选漏斗",
        "",
        _markdown_table(pool.rejected_summary),
        "",
        "## 数据与筛选警告",
        "",
    ]
    if pool.warnings:
        lines.extend(f"- {warning}" for warning in pool.warnings)
    else:
        lines.append("- 无。")

    lines.extend(
        [
            "",
            "## 配置快照",
            "",
            f"```json\n{_json_dump(pool.config_snapshot)}\n```",
        ]
    )
    return "\n".join(lines) + "\n"


def _presentation_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    preferred = [
        "symbol",
        "name",
        "industry",
        "close",
        "pe_ttm",
        "pb",
        "dividend_yield",
        "market_cap",
        "turnover_amount",
        "value_score",
    ]
    columns = [column for column in preferred if column in frame.columns]
    result = frame[columns].copy()
    if "symbol" in result.columns:
        result["symbol"] = result["symbol"].astype(str).str.zfill(6)
    for column in ["dividend_yield", "value_score"]:
        if column in result.columns:
            result[column] = result[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    for column in ["close", "pe_ttm", "pb"]:
        if column in result.columns:
            result[column] = result[column].map(lambda value: "" if pd.isna(value) else f"{value:.2f}")
    return result


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "无数据。"
    return frame.to_markdown(index=False)


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=_json_default)


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)
