from datetime import date

from akquant.models import Bar, OrderIntent, OrderSide, PortfolioState, RuleConfig
from akquant.rules import evaluate_order


def make_bar(day: str, close: float = 10.0) -> Bar:
    return Bar(
        date=date.fromisoformat(day),
        symbol="000001",
        open=close,
        high=close * 1.01,
        low=close * 0.99,
        close=close,
        volume=100_000,
        amount=close * 100_000,
        adjustment="qfq",
        source="fixture",
    )


def test_buy_order_rounds_down_to_board_lot_and_charges_commission_and_slippage():
    state = PortfolioState(cash=10_000.0)
    config = RuleConfig(commission_rate=0.0003, min_commission=5.0, stamp_duty_rate=0.001, slippage_bps=10)
    intent = OrderIntent(date=date(2026, 1, 2), symbol="000001", side=OrderSide.BUY, quantity=250)

    decision = evaluate_order(intent, make_bar("2026-01-02", close=10.0), state, config)

    assert decision.fill is not None
    assert decision.fill.quantity == 200
    assert decision.fill.price == 10.01
    assert decision.fill.commission == 5.0
    assert decision.fill.stamp_duty == 0.0
    assert decision.fill.slippage_cost == 2.0
    assert decision.rejection is None


def test_sell_order_is_blocked_when_shares_are_not_t_plus_one_sellable():
    state = PortfolioState(cash=0.0)
    state.add_position(symbol="000001", quantity=200, price=10.0, trade_date=date(2026, 1, 2))
    config = RuleConfig()
    intent = OrderIntent(date=date(2026, 1, 2), symbol="000001", side=OrderSide.SELL, quantity=100)

    decision = evaluate_order(intent, make_bar("2026-01-02", close=10.0), state, config)

    assert decision.fill is None
    assert decision.rejection is not None
    assert decision.rejection.reason_code == "T_PLUS_ONE_RESTRICTED"


def test_sell_order_charges_stamp_duty_after_position_becomes_sellable():
    state = PortfolioState(cash=0.0)
    state.add_position(symbol="000001", quantity=200, price=10.0, trade_date=date(2026, 1, 2))
    state.release_t_plus_one_positions(current_date=date(2026, 1, 5))
    config = RuleConfig(commission_rate=0.0003, min_commission=5.0, stamp_duty_rate=0.001, slippage_bps=10)
    intent = OrderIntent(date=date(2026, 1, 5), symbol="000001", side=OrderSide.SELL, quantity=100)

    decision = evaluate_order(intent, make_bar("2026-01-05", close=10.0), state, config)

    assert decision.fill is not None
    assert decision.fill.quantity == 100
    assert decision.fill.price == 9.99
    assert decision.fill.commission == 5.0
    assert decision.fill.stamp_duty == 0.999
    assert decision.fill.slippage_cost == 1.0
    assert decision.rejection is None


def test_buy_order_is_rejected_when_cash_cannot_cover_price_and_costs():
    state = PortfolioState(cash=900.0)
    config = RuleConfig(commission_rate=0.0003, min_commission=5.0, slippage_bps=0)
    intent = OrderIntent(date=date(2026, 1, 2), symbol="000001", side=OrderSide.BUY, quantity=100)

    decision = evaluate_order(intent, make_bar("2026-01-02", close=10.0), state, config)

    assert decision.fill is None
    assert decision.rejection is not None
    assert decision.rejection.reason_code == "INSUFFICIENT_CASH"
