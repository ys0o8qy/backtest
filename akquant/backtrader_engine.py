from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import backtrader as bt
import pandas as pd


@dataclass(frozen=True)
class BacktraderPortfolioConfig:
    initial_cash: float
    weights: dict[str, float]
    rebalance: str = "monthly"
    commission_rate: float = 0.0003
    slippage_perc: float = 0.0005
    portfolio_id: str = "portfolio"
    config_snapshot: dict[str, object] | None = None


@dataclass(frozen=True)
class BacktraderPortfolioResult:
    run_id: str
    portfolio_id: str
    config_snapshot: dict[str, object]
    initial_cash: float
    final_value: float
    equity_curve: pd.DataFrame
    rebalance_count: int
    rebalance_records: list[dict[str, object]]
    final_positions: dict[str, float]
    orders_or_trades: list[dict[str, object]]
    weights: dict[str, float]
    warnings: list[str]


class TargetWeightRebalanceStrategy(bt.Strategy):
    params = (
        ("weights", {}),
        ("rebalance", "monthly"),
    )

    def __init__(self) -> None:
        self.equity_records: list[dict[str, object]] = []
        self.rebalance_dates: list[object] = []
        self.rebalance_records: list[dict[str, object]] = []
        self.order_records: list[dict[str, object]] = []
        self._last_period_key = None

    def next(self) -> None:
        current_date = self.datas[0].datetime.date(0)
        if self._should_rebalance(current_date):
            targets: dict[str, float] = {}
            for data in self.datas:
                target = float(self.p.weights.get(data._name, 0.0))
                targets[data._name] = target
                self.order_target_percent(data=data, target=target)
            self.rebalance_dates.append(current_date)
            self.rebalance_records.append({"date": pd.Timestamp(current_date), "targets": targets})
            self._last_period_key = _period_key(current_date, self.p.rebalance)

        record = {"date": pd.Timestamp(current_date), "value": float(self.broker.getvalue())}
        for data in self.datas:
            record[f"{data._name}_close"] = float(data.close[0])
        self.equity_records.append(record)

    def _should_rebalance(self, current_date) -> bool:
        key = _period_key(current_date, self.p.rebalance)
        return key != self._last_period_key

    def notify_order(self, order) -> None:
        if order.status not in {order.Completed, order.Canceled, order.Margin, order.Rejected}:
            return
        self.order_records.append(
            {
                "date": pd.Timestamp(self.datas[0].datetime.date(0)),
                "asset": order.data._name,
                "status": order.getstatusname(),
                "size": float(order.executed.size),
                "price": float(order.executed.price),
                "value": float(order.executed.value),
                "commission": float(order.executed.comm),
            }
        )


def run_backtrader_portfolio(data: dict[str, pd.DataFrame], config: BacktraderPortfolioConfig) -> BacktraderPortfolioResult:
    warnings = _validate_inputs(data, config)
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(config.initial_cash)
    cerebro.broker.setcommission(commission=config.commission_rate)
    if config.slippage_perc:
        cerebro.broker.set_slippage_perc(config.slippage_perc)

    for name, frame in data.items():
        feed_frame = _prepare_feed_frame(frame)
        feed = bt.feeds.PandasData(dataname=feed_frame)
        cerebro.adddata(feed, name=name)

    cerebro.addstrategy(TargetWeightRebalanceStrategy, weights=config.weights, rebalance=config.rebalance)
    strategies = cerebro.run()
    strategy = strategies[0]
    equity_curve = pd.DataFrame(strategy.equity_records)
    if not equity_curve.empty:
        equity_curve = equity_curve.set_index("date")
        equity_curve.index.name = "date"

    return BacktraderPortfolioResult(
        run_id=f"backtrader-{uuid4().hex}",
        portfolio_id=config.portfolio_id,
        config_snapshot=config.config_snapshot or _config_snapshot(config),
        initial_cash=config.initial_cash,
        final_value=float(cerebro.broker.getvalue()),
        equity_curve=equity_curve,
        rebalance_count=len(strategy.rebalance_dates),
        rebalance_records=strategy.rebalance_records,
        final_positions={data._name: float(strategy.getposition(data).size) for data in strategy.datas},
        orders_or_trades=strategy.order_records,
        weights=dict(config.weights),
        warnings=warnings,
    )


def _prepare_feed_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"data feed is missing columns: {missing}")
    prepared = frame.copy()
    prepared.index = pd.to_datetime(prepared.index)
    prepared = prepared.sort_index()
    if "openinterest" not in prepared.columns:
        prepared["openinterest"] = 0
    return prepared[["open", "high", "low", "close", "volume", "openinterest"]]


def _validate_inputs(data: dict[str, pd.DataFrame], config: BacktraderPortfolioConfig) -> list[str]:
    if not data:
        raise ValueError("at least one data feed is required")
    if abs(sum(config.weights.values()) - 1.0) > 1e-6:
        raise ValueError("portfolio weights must sum to 1.0")
    missing_data = set(config.weights) - set(data)
    if missing_data:
        raise ValueError(f"weights reference missing data feeds: {sorted(missing_data)}")

    warnings: list[str] = []
    unused_data = set(data) - set(config.weights)
    if unused_data:
        warnings.append(f"Data feeds without target weights will be held at 0%: {sorted(unused_data)}")
    return warnings


def _config_snapshot(config: BacktraderPortfolioConfig) -> dict[str, object]:
    return {
        "initial_cash": config.initial_cash,
        "weights": dict(config.weights),
        "rebalance": config.rebalance,
        "commission_rate": config.commission_rate,
        "slippage_perc": config.slippage_perc,
        "portfolio_id": config.portfolio_id,
    }


def _period_key(current_date, rebalance: str):
    if rebalance == "monthly":
        return current_date.year, current_date.month
    if rebalance == "quarterly":
        return current_date.year, (current_date.month - 1) // 3
    if rebalance == "yearly":
        return (current_date.year,)
    if rebalance == "once":
        return ("once",)
    raise ValueError("rebalance must be one of: monthly, quarterly, yearly, once")
