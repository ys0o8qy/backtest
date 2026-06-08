from __future__ import annotations

import math
from statistics import mean, pstdev

from akquant.models import BacktestResult, Fill, OrderSide


def calculate_metrics(result: BacktestResult) -> dict[str, float | int]:
    values = [point.total_value for point in result.equity_curve]
    initial = result.config.initial_cash
    final = values[-1] if values else initial
    cumulative_return = (final / initial) - 1 if initial else 0.0
    daily_returns = _daily_returns(values)
    annualized_return = _annualized_return(cumulative_return, len(values))
    annualized_volatility = pstdev(daily_returns) * math.sqrt(252) if len(daily_returns) > 1 else 0.0
    sharpe = annualized_return / annualized_volatility if annualized_volatility else 0.0
    max_drawdown = _max_drawdown(values)
    calmar = annualized_return / abs(max_drawdown) if max_drawdown else 0.0
    total_turnover_notional = sum(fill.quantity * fill.price for fill in result.fills)
    average_equity = mean(values) if values else initial

    return {
        "initial_value": round(initial, 6),
        "final_value": round(final, 6),
        "cumulative_return": round(cumulative_return, 6),
        "annualized_return": round(annualized_return, 6),
        "annualized_volatility": round(annualized_volatility, 6),
        "sharpe": round(sharpe, 6),
        "max_drawdown": round(max_drawdown, 6),
        "calmar": round(calmar, 6),
        "trade_count": len(result.fills),
        "win_rate": round(_win_rate(result.fills), 6),
        "turnover": round(total_turnover_notional / average_equity, 6) if average_equity else 0.0,
        "total_commission": round(sum(fill.commission for fill in result.fills), 6),
        "total_stamp_duty": round(sum(fill.stamp_duty for fill in result.fills), 6),
        "total_slippage_cost": round(sum(fill.slippage_cost for fill in result.fills), 6),
    }


def _daily_returns(values: list[float]) -> list[float]:
    returns = []
    for previous, current in zip(values, values[1:]):
        if previous:
            returns.append((current / previous) - 1)
    return returns


def _annualized_return(cumulative_return: float, periods: int) -> float:
    if periods <= 1:
        return cumulative_return
    return (1 + cumulative_return) ** (252 / (periods - 1)) - 1


def _max_drawdown(values: list[float]) -> float:
    peak = None
    max_drawdown = 0.0
    for value in values:
        peak = value if peak is None else max(peak, value)
        if peak:
            max_drawdown = min(max_drawdown, (value / peak) - 1)
    return max_drawdown


def _win_rate(fills: list[Fill]) -> float:
    open_buy: Fill | None = None
    wins = 0
    closed = 0
    for fill in fills:
        if fill.side is OrderSide.BUY:
            open_buy = fill
        elif open_buy is not None:
            closed += 1
            if fill.price > open_buy.price:
                wins += 1
            open_buy = None
    return wins / closed if closed else 0.0
