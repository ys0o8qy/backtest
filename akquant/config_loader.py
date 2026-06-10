from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from akquant.akshare_provider import DataSourceKind
from akquant.portfolios import AssetCandidate, AssetTarget, CostModel, DataPolicy, PortfolioConfig


def load_portfolio_config(path: str | Path) -> PortfolioConfig:
    config_path = Path(path)
    raw = config_path.read_text(encoding="utf-8")
    if config_path.suffix.lower() == ".json":
        payload = json.loads(raw)
    else:
        payload = yaml.safe_load(raw)
    if not isinstance(payload, dict):
        raise ValueError("portfolio config must be a mapping")
    return portfolio_config_from_mapping(payload)


def portfolio_config_from_mapping(payload: dict[str, Any]) -> PortfolioConfig:
    targets = [
        AssetTarget(
            asset_class=str(target["asset_class"]),
            weight=float(target["weight"]),
            candidates=[
                AssetCandidate(
                    symbol=str(candidate["symbol"]),
                    name=str(candidate.get("name", candidate["symbol"])),
                    kind=DataSourceKind(str(candidate["kind"])),
                )
                for candidate in target["candidates"]
            ],
        )
        for target in payload["targets"]
    ]
    cost_payload = payload.get("cost_model", {})
    data_policy_payload = payload.get("data_policy", {})
    return PortfolioConfig(
        id=str(payload["id"]),
        name=str(payload.get("name", payload["id"])),
        targets=targets,
        rebalance=str(payload.get("rebalance", "quarterly")),
        initial_cash=float(payload.get("initial_cash", 100_000.0)),
        cost_model=CostModel(
            commission_rate=float(cost_payload.get("commission_rate", 0.0003)),
            slippage_perc=float(cost_payload.get("slippage_perc", 0.0005)),
        ),
        data_policy=DataPolicy(
            min_coverage_ratio=float(data_policy_payload.get("min_coverage_ratio", 0.95)),
            etf_first=bool(data_policy_payload.get("etf_first", True)),
        ),
    )
