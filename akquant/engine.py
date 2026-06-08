from __future__ import annotations

from akquant.models import BacktestConfig, BacktestResult, Bar, EquityPoint, OrderSide, PortfolioState
from akquant.rules import apply_fill, evaluate_order
from akquant.strategies import DualMovingAverageStrategy


RESEARCH_ONLY_WARNING = "Research only: backtest results do not represent future returns or investment advice."


def run_backtest(config: BacktestConfig, bars: list[Bar], warnings: list[str] | None = None) -> BacktestResult:
    selected_bars = [bar for bar in bars if bar.symbol == config.symbol]
    if not selected_bars:
        raise ValueError(f"no bars available for symbol {config.symbol}")

    state = PortfolioState(cash=config.initial_cash)
    strategy = DualMovingAverageStrategy(config)
    fills = []
    rejections = []
    equity_curve = []
    result_warnings = list(warnings or [])
    result_warnings.append(RESEARCH_ONLY_WARNING)
    history: list[Bar] = []

    for bar in selected_bars:
        state.release_t_plus_one_positions(bar.date)
        history.append(bar)
        intent = strategy.generate_order(history, state)
        if intent is not None:
            decision = evaluate_order(intent, bar, state, config.rule_config)
            if decision.fill is not None:
                fills.append(decision.fill)
                apply_fill(decision.fill, state)
            if decision.rejection is not None:
                rejections.append(decision.rejection)

        position = state.position_for(config.symbol)
        position_value = position.quantity * bar.close
        equity_curve.append(
            EquityPoint(
                date=bar.date,
                cash=round(state.cash, 6),
                position_value=round(position_value, 6),
                total_value=round(state.cash + position_value, 6),
            )
        )

    return BacktestResult(
        config=config,
        bars=selected_bars,
        equity_curve=equity_curve,
        fills=fills,
        rejections=rejections,
        warnings=result_warnings,
    )


def final_position_quantity(result: BacktestResult) -> int:
    quantity = 0
    for fill in result.fills:
        if fill.side is OrderSide.BUY:
            quantity += fill.quantity
        else:
            quantity -= fill.quantity
    return quantity
