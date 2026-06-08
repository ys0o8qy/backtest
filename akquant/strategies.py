from __future__ import annotations

from akquant.models import Bar, BacktestConfig, OrderIntent, OrderSide, PortfolioState


class DualMovingAverageStrategy:
    def __init__(self, config: BacktestConfig) -> None:
        if config.short_window <= 0 or config.long_window <= 0:
            raise ValueError("moving average windows must be positive")
        if config.short_window >= config.long_window:
            raise ValueError("short_window must be less than long_window")
        if not 0 < config.target_allocation <= 1:
            raise ValueError("target_allocation must be within (0, 1]")
        self.config = config

    def generate_order(self, history: list[Bar], state: PortfolioState) -> OrderIntent | None:
        if len(history) < self.config.long_window:
            return None
        current = history[-1]
        short_ma = _moving_average(history, self.config.short_window)
        long_ma = _moving_average(history, self.config.long_window)
        position = state.position_for(current.symbol)

        if short_ma > long_ma and position.quantity == 0:
            portfolio_value = state.cash
            quantity = int((portfolio_value * self.config.target_allocation) / current.close)
            return OrderIntent(date=current.date, symbol=current.symbol, side=OrderSide.BUY, quantity=quantity)
        if short_ma < long_ma and position.quantity > 0:
            return OrderIntent(date=current.date, symbol=current.symbol, side=OrderSide.SELL, quantity=position.quantity)
        return None


def _moving_average(history: list[Bar], window: int) -> float:
    values = [bar.close for bar in history[-window:]]
    return sum(values) / window
