from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from akquant.akshare_provider import AkshareProvider
from akquant.all_weather import run_all_weather_backtest
from akquant.all_weather_reporting import write_all_weather_markdown_report
from akquant.backtrader_engine import BacktraderPortfolioConfig, run_backtrader_portfolio
from akquant.comparison import run_comparison
from akquant.comparison_reporting import write_comparison_markdown_report
from akquant.config_loader import load_portfolio_config
from akquant.data import load_bars_csv
from akquant.engine import run_backtest
from akquant.models import BacktestConfig, RuleConfig
from akquant.portfolio_reporting import write_portfolio_markdown_report
from akquant.portfolio_registry import get_builtin_portfolio, list_builtin_portfolios
from akquant.reporting import write_markdown_report


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "portfolio":
        return _portfolio_main(argv[1:])
    if argv and argv[0] == "all-weather":
        return _all_weather_main(argv[1:])
    if argv and argv[0] == "compare":
        return _compare_main(argv[1:])
    return _single_strategy_main(argv)


def _single_strategy_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an AKQuant V0.1 daily-bar backtest.")
    parser.add_argument("--data", required=True, help="CSV file containing normalized daily bars.")
    parser.add_argument("--symbol", required=True, help="A-share symbol to backtest.")
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--short-window", type=int, default=5)
    parser.add_argument("--long-window", type=int, default=20)
    parser.add_argument("--target-allocation", type=float, default=1.0)
    parser.add_argument("--commission-rate", type=float, default=0.0003)
    parser.add_argument("--min-commission", type=float, default=5.0)
    parser.add_argument("--stamp-duty-rate", type=float, default=0.001)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--out", required=True, help="Markdown report output path.")
    args = parser.parse_args(argv)

    bars, warnings = load_bars_csv(Path(args.data), symbol=args.symbol)
    config = BacktestConfig(
        symbol=args.symbol,
        initial_cash=args.initial_cash,
        short_window=args.short_window,
        long_window=args.long_window,
        target_allocation=args.target_allocation,
        rule_config=RuleConfig(
            commission_rate=args.commission_rate,
            min_commission=args.min_commission,
            stamp_duty_rate=args.stamp_duty_rate,
            slippage_bps=args.slippage_bps,
        ),
    )
    result = run_backtest(config, bars, warnings=warnings)
    write_markdown_report(result, args.out)
    return 0


def _portfolio_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an AKQuant V0.2 Backtrader portfolio backtest.")
    parser.add_argument("--feed", action="append", required=True, help="Named CSV feed, for example stock=path.csv.")
    parser.add_argument("--weight", action="append", required=True, help="Target weight, for example stock=0.6.")
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--rebalance", choices=["monthly", "quarterly", "yearly", "once"], default="monthly")
    parser.add_argument("--commission-rate", type=float, default=0.0003)
    parser.add_argument("--slippage-perc", type=float, default=0.0005)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    data = {name: _load_portfolio_csv(path) for name, path in (_parse_key_value(item) for item in args.feed)}
    weights = {name: float(value) for name, value in (_parse_key_value(item) for item in args.weight)}
    result = run_backtrader_portfolio(
        data=data,
        config=BacktraderPortfolioConfig(
            initial_cash=args.initial_cash,
            weights=weights,
            rebalance=args.rebalance,
            commission_rate=args.commission_rate,
            slippage_perc=args.slippage_perc,
        ),
    )
    write_portfolio_markdown_report(result, args.out)
    return 0


def _all_weather_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a 20-year all-weather portfolio backtest with AKShare and Backtrader.")
    parser.add_argument("--start", required=True, help="Start date, YYYY-MM-DD.")
    parser.add_argument("--end", required=True, help="End date, YYYY-MM-DD.")
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--rebalance", choices=["monthly", "quarterly", "yearly", "once"], default="quarterly")
    parser.add_argument("--min-coverage-ratio", type=float, default=0.95)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    workflow = run_all_weather_backtest(
        provider=AkshareProvider(),
        start=_parse_date(args.start),
        end=_parse_date(args.end),
        initial_cash=args.initial_cash,
        rebalance=args.rebalance,
        min_coverage_ratio=args.min_coverage_ratio,
    )
    write_all_weather_markdown_report(workflow, args.out)
    return 0


def _compare_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare multiple AKQuant portfolio configurations.")
    parser.add_argument("--portfolio", action="append", required=True, help="Builtin portfolio id or YAML/JSON config path.")
    parser.add_argument("--start", required=True, help="Start date, YYYY-MM-DD.")
    parser.add_argument("--end", required=True, help="End date, YYYY-MM-DD.")
    parser.add_argument("--rebalance", choices=["monthly", "quarterly", "yearly", "once"], default=None)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    configs = [_load_portfolio_reference(reference) for reference in args.portfolio]
    if args.rebalance:
        configs = [_replace_rebalance(config, args.rebalance) for config in configs]
    report = run_comparison(
        provider=AkshareProvider(),
        configs=configs,
        start=_parse_date(args.start),
        end=_parse_date(args.end),
    )
    write_comparison_markdown_report(report, args.out)
    return 0


def _parse_key_value(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise ValueError(f"expected key=value format, got {value!r}")
    key, raw = value.split("=", 1)
    if not key or not raw:
        raise ValueError(f"expected key=value format, got {value!r}")
    return key, raw


def _load_portfolio_csv(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    rename_map = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
    }
    frame = frame.rename(columns=rename_map)
    if "date" not in frame.columns:
        raise ValueError(f"portfolio feed {path} must include date column")
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.set_index("date").sort_index()
    if "volume" not in frame.columns:
        frame["volume"] = 0
    if "openinterest" not in frame.columns:
        frame["openinterest"] = 0
    return frame


def _parse_date(value: str):
    return pd.Timestamp(value).date()


def _load_portfolio_reference(reference: str):
    if reference in list_builtin_portfolios():
        return get_builtin_portfolio(reference)
    return load_portfolio_config(reference)


def _replace_rebalance(config, rebalance: str):
    from dataclasses import replace

    return replace(config, rebalance=rebalance)


if __name__ == "__main__":
    raise SystemExit(main())
