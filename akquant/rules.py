from __future__ import annotations

from akquant.models import Bar, Fill, OrderIntent, OrderSide, PortfolioState, RejectedOrder, RuleConfig, RuleDecision


def evaluate_order(intent: OrderIntent, bar: Bar, state: PortfolioState, config: RuleConfig) -> RuleDecision:
    if intent.quantity <= 0:
        return _reject(intent, "LOT_SIZE_TOO_SMALL", "order quantity must be positive")
    if not bar.is_trading or bar.is_halted:
        return _reject(intent, "HALTED", "symbol is not tradable on this date")

    quantity = _round_to_lot(intent.quantity, config.board_lot_size)
    if quantity <= 0:
        return _reject(intent, "LOT_SIZE_TOO_SMALL", "rounded quantity is below one board lot")

    base_price = intent.requested_price if intent.requested_price is not None else bar.close
    fill_price = _fill_price(base_price, intent.side, config.slippage_bps)
    notional = fill_price * quantity
    commission = _commission(notional, config)
    stamp_duty = notional * config.stamp_duty_rate if intent.side is OrderSide.SELL else 0.0
    slippage_cost = abs(fill_price - base_price) * quantity

    if intent.side is OrderSide.BUY:
        total_cash_needed = notional + commission
        if state.cash + 1e-9 < total_cash_needed:
            return _reject(intent, "INSUFFICIENT_CASH", "cash cannot cover notional and commission")
        cash_delta = -total_cash_needed
    else:
        position = state.position_for(intent.symbol)
        if position.quantity < quantity:
            return _reject(intent, "INSUFFICIENT_POSITION", "position quantity is insufficient")
        if position.sellable_quantity < quantity:
            return _reject(intent, "T_PLUS_ONE_RESTRICTED", "sellable quantity is restricted by T+1")
        cash_delta = notional - commission - stamp_duty

    return RuleDecision(
        fill=Fill(
            date=intent.date,
            symbol=intent.symbol,
            side=intent.side,
            quantity=quantity,
            price=round(fill_price, 6),
            commission=round(commission, 6),
            stamp_duty=round(stamp_duty, 6),
            slippage_cost=round(slippage_cost, 6),
            cash_delta=round(cash_delta, 6),
        )
    )


def apply_fill(fill: Fill, state: PortfolioState) -> None:
    state.cash = round(state.cash + fill.cash_delta, 6)
    if fill.side is OrderSide.BUY:
        state.add_position(fill.symbol, fill.quantity, fill.price, fill.date)
    else:
        state.reduce_position(fill.symbol, fill.quantity)


def _round_to_lot(quantity: int, lot_size: int) -> int:
    return (quantity // lot_size) * lot_size


def _fill_price(base_price: float, side: OrderSide, slippage_bps: float) -> float:
    slippage = slippage_bps / 10_000
    if side is OrderSide.BUY:
        return base_price * (1 + slippage)
    return base_price * (1 - slippage)


def _commission(notional: float, config: RuleConfig) -> float:
    return max(config.min_commission, notional * config.commission_rate)


def _reject(intent: OrderIntent, reason_code: str, reason_message: str) -> RuleDecision:
    return RuleDecision(
        rejection=RejectedOrder(
            date=intent.date,
            symbol=intent.symbol,
            side=intent.side,
            requested_quantity=intent.quantity,
            reason_code=reason_code,
            reason_message=reason_message,
        )
    )
