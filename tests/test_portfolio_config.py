from __future__ import annotations

import pytest

from akquant.akshare_provider import DataSourceKind
from akquant.config_loader import load_portfolio_config
from akquant.portfolio_registry import get_builtin_portfolio, list_builtin_portfolios
from akquant.portfolios import AssetCandidate, AssetTarget, CostModel, DataPolicy, PortfolioConfig


def test_portfolio_config_rejects_weights_that_do_not_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        PortfolioConfig(
            id="bad",
            name="Bad Portfolio",
            targets=[
                AssetTarget(
                    asset_class="equity",
                    weight=0.8,
                    candidates=[AssetCandidate("510300", "沪深300ETF", DataSourceKind.ETF)],
                )
            ],
        )


def test_builtin_portfolio_registry_returns_stable_config_snapshots():
    names = list_builtin_portfolios()

    assert {"all_weather", "stock_bond_60_40", "equity_only", "bond_only"}.issubset(names)
    config = get_builtin_portfolio("stock_bond_60_40")
    assert config.id == "stock_bond_60_40"
    assert config.rebalance == "quarterly"
    assert sum(target.weight for target in config.targets) == 1.0
    assert config.data_policy.min_coverage_ratio == 0.95


def test_custom_yaml_loads_to_portfolio_config(tmp_path):
    config_file = tmp_path / "custom.yaml"
    config_file.write_text(
        """
id: custom_mix
name: Custom Mix
rebalance: monthly
initial_cash: 200000
cost_model:
  commission_rate: 0.0002
  slippage_perc: 0.0004
data_policy:
  min_coverage_ratio: 0.90
targets:
  - asset_class: equity
    weight: 0.6
    candidates:
      - { symbol: "510300", name: "沪深300ETF", kind: "etf" }
      - { symbol: "000300", name: "沪深300指数", kind: "index" }
  - asset_class: bond
    weight: 0.4
    candidates:
      - { symbol: "511010", name: "国债ETF", kind: "etf" }
      - { symbol: "000012", name: "国债指数", kind: "index" }
""",
        encoding="utf-8",
    )

    config = load_portfolio_config(config_file)

    assert isinstance(config, PortfolioConfig)
    assert config.id == "custom_mix"
    assert config.initial_cash == 200000
    assert config.cost_model == CostModel(commission_rate=0.0002, slippage_perc=0.0004)
    assert config.data_policy == DataPolicy(min_coverage_ratio=0.90)
    assert config.targets[0].candidates[0].kind is DataSourceKind.ETF
