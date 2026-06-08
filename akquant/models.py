from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Bar:
    date: date
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    adjustment: str = "none"
    source: str = "unknown"
    is_trading: bool = True
    is_halted: bool = False


@dataclass(frozen=True)
class RuleConfig:
    commission_rate: float = 0.0003
    min_commission: float = 5.0
    stamp_duty_rate: float = 0.001
    slippage_bps: float = 5.0
    board_lot_size: int = 100
    block_limit_trades: bool = True


@dataclass(frozen=True)
class OrderIntent:
    date: date
    symbol: str
    side: OrderSide
    quantity: int
    requested_price: float | None = None
    reason: str = ""


@dataclass(frozen=True)
class Fill:
    date: date
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    commission: float
    stamp_duty: float
    slippage_cost: float
    cash_delta: float


@dataclass(frozen=True)
class RejectedOrder:
    date: date
    symbol: str
    side: OrderSide
    requested_quantity: int
    reason_code: str
    reason_message: str


@dataclass(frozen=True)
class RuleDecision:
    fill: Fill | None = None
    rejection: RejectedOrder | None = None


@dataclass
class Position:
    quantity: int = 0
    sellable_quantity: int = 0
    pending_lots: list[tuple[date, int]] = field(default_factory=list)


@dataclass
class PortfolioState:
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)

    def position_for(self, symbol: str) -> Position:
        if symbol not in self.positions:
            self.positions[symbol] = Position()
        return self.positions[symbol]

    def add_position(self, symbol: str, quantity: int, price: float, trade_date: date) -> None:
        del price
        position = self.position_for(symbol)
        position.quantity += quantity
        position.pending_lots.append((trade_date, quantity))

    def reduce_position(self, symbol: str, quantity: int) -> None:
        position = self.position_for(symbol)
        position.quantity -= quantity
        position.sellable_quantity -= quantity
        if position.quantity < 0 or position.sellable_quantity < 0:
            raise ValueError("position quantity cannot be negative")

    def release_t_plus_one_positions(self, current_date: date) -> None:
        for position in self.positions.values():
            still_pending: list[tuple[date, int]] = []
            for trade_date, quantity in position.pending_lots:
                if trade_date < current_date:
                    position.sellable_quantity += quantity
                else:
                    still_pending.append((trade_date, quantity))
            position.pending_lots = still_pending


@dataclass(frozen=True)
class BacktestConfig:
    symbol: str
    initial_cash: float
    short_window: int
    long_window: int
    target_allocation: float
    rule_config: RuleConfig = field(default_factory=RuleConfig)


@dataclass(frozen=True)
class EquityPoint:
    date: date
    cash: float
    position_value: float
    total_value: float


@dataclass(frozen=True)
class BacktestResult:
    config: BacktestConfig
    bars: list[Bar]
    equity_curve: list[EquityPoint]
    fills: list[Fill]
    rejections: list[RejectedOrder]
    warnings: list[str]
