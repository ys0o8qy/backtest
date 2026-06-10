from __future__ import annotations

import math

import pandas as pd


def metrics_from_equity_curve(equity_curve: pd.DataFrame) -> dict[str, float]:
    values = equity_curve["value"].astype(float)
    if values.empty:
        return _empty_metrics()
    returns = values.pct_change().dropna()
    cumulative_return = values.iloc[-1] / values.iloc[0] - 1 if values.iloc[0] else 0.0
    annualized_return = (1 + cumulative_return) ** (252 / max(len(values) - 1, 1)) - 1
    annualized_volatility = returns.std(ddof=0) * math.sqrt(252) if len(returns) > 1 else 0.0
    sharpe = annualized_return / annualized_volatility if annualized_volatility else 0.0
    drawdown = drawdown_curve(equity_curve)
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
    calmar = annualized_return / abs(max_drawdown) if max_drawdown else 0.0
    return {
        "cumulative_return": round(float(cumulative_return), 6),
        "annualized_return": round(float(annualized_return), 6),
        "annualized_volatility": round(float(annualized_volatility), 6),
        "sharpe": round(float(sharpe), 6),
        "max_drawdown": round(float(max_drawdown), 6),
        "calmar": round(float(calmar), 6),
    }


def drawdown_curve(equity_curve: pd.DataFrame) -> pd.Series:
    values = equity_curve["value"].astype(float)
    peaks = values.cummax()
    drawdown = values / peaks - 1
    drawdown.name = "drawdown"
    return drawdown


def monthly_returns(equity_curve: pd.DataFrame) -> pd.Series:
    values = equity_curve["value"].astype(float)
    monthly = values.resample("ME").last().pct_change().dropna()
    monthly.name = "monthly_return"
    return monthly


def yearly_returns(equity_curve: pd.DataFrame) -> pd.Series:
    values = equity_curve["value"].astype(float)
    yearly = values.resample("YE").last().pct_change().dropna()
    yearly.name = "yearly_return"
    return yearly


def rolling_return(equity_curve: pd.DataFrame, window: int = 252) -> pd.Series:
    values = equity_curve["value"].astype(float)
    result = values.pct_change(window).dropna()
    result.name = "rolling_return"
    return result


def rolling_drawdown(equity_curve: pd.DataFrame, window: int = 252) -> pd.Series:
    values = equity_curve["value"].astype(float)
    rolling_peak = values.rolling(window=window, min_periods=1).max()
    result = values / rolling_peak - 1
    result.name = "rolling_drawdown"
    return result


def _empty_metrics() -> dict[str, float]:
    return {
        "cumulative_return": 0.0,
        "annualized_return": 0.0,
        "annualized_volatility": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
        "calmar": 0.0,
    }
