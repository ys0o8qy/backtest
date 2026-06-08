# AKQuant

AKQuant is a local A-share quantitative research and backtesting MVP. It now has two execution paths:

- V0.1 deterministic local engine for single-symbol strategy tests.
- V0.2 AKShare + Backtrader path for multi-asset portfolio allocation backtests.

The V0.1 core loop from `docs/akquant-prd-architecture.md` remains available:

```text
load daily bars -> run dual moving average strategy -> apply A-share rules -> calculate metrics -> export Markdown report
```

The V0.2 allocation loop is:

```text
AKShare ETF/index data -> ETF-first fallback selection -> Backtrader target-weight rebalance -> Markdown report
```

## What Is Implemented

- CSV daily-bar loader with basic data validation.
- Dual moving average strategy.
- A-share market-rule checks:
  - T+1 sell restriction.
  - 100-share board lot rounding.
  - commission and minimum commission.
  - sell-side stamp duty.
  - fixed basis-point slippage.
  - halt/non-trading rejection.
- Daily event-loop backtest engine.
- Equity curve, fills, rejected orders, warnings, and cost records.
- Performance metrics and Markdown report export.
- CLI runner.
- AKShare ETF/index provider:
  - ETF historical data via `fund_etf_hist_em`.
  - A-share index historical data via `index_zh_a_hist`.
  - wide index return tables for analysis.
- Backtrader multi-asset target-weight backtests.
- All-weather portfolio template with ETF-first and index-fallback selection.

## What Is Not Implemented Yet

- Streamlit/Dash UI.
- Factor attribution and industry attribution.
- Precise intraday limit-up/limit-down queue modeling.
- Live trading or broker connectivity.

## Run Tests

```bash
uv run --with pytest pytest -q
```

## Run the Sample Backtest

```bash
uv run python -m akquant.cli \
  --data tests/fixtures/sample_bars.csv \
  --symbol 000001 \
  --initial-cash 10000 \
  --short-window 2 \
  --long-window 3 \
  --out /tmp/akquant-report.md
```

Open `/tmp/akquant-report.md` to inspect the generated report.

## Run a Multi-Asset CSV Portfolio Backtest

```bash
uv run python -m akquant.cli portfolio \
  --feed stock=tests/fixtures/portfolio_stock.csv \
  --feed bond=tests/fixtures/portfolio_bond.csv \
  --weight stock=0.6 \
  --weight bond=0.4 \
  --initial-cash 100000 \
  --rebalance monthly \
  --out /tmp/akquant-portfolio-report.md
```

This path uses Backtrader and supports `monthly`, `quarterly`, `yearly`, and `once` rebalancing.

## Run an AKShare All-Weather Backtest

```bash
uv run python -m akquant.cli all-weather \
  --start 2006-01-01 \
  --end 2026-06-08 \
  --initial-cash 100000 \
  --rebalance quarterly \
  --out /tmp/akquant-all-weather-report.md
```

The all-weather template uses real tradable ETFs first. If an ETF does not provide enough coverage for the requested range, AKQuant automatically switches that asset class to an index proxy and records the fallback in the report.

Default all-weather targets:

| Asset Class | Weight | ETF First | Index Fallback |
| --- | ---: | --- | --- |
| equity | 30.00% | `510300` 沪深300ETF | `000300` 沪深300指数 |
| long_bond | 40.00% | `511010` 国债ETF | `000012` 国债指数 |
| commodity | 7.50% | `159985` 豆粕ETF | `000066` 上证商品指数 |
| gold | 7.50% | `518880` 黄金ETF | `000066` 上证商品指数代理 |
| cash | 15.00% | `511880` 货币ETF | `000012` 国债指数代理 |

The index proxy path is useful for long-horizon analysis, but it is not the same as a fully tradable ETF backtest.

## Index Return Data

Use `akquant.akshare_provider.fetch_index_returns()` to build a wide daily return table for selected indices:

```python
from datetime import date

from akquant.akshare_provider import AkshareProvider, fetch_index_returns

provider = AkshareProvider()
returns = fetch_index_returns(
    provider=provider,
    symbols=["000300", "000012", "000066"],
    start=date(2006, 1, 1),
    end=date(2026, 6, 8),
)
```

Use `fetch_all_index_returns()` to pull the AKShare index catalog through `index_stock_info()` and build a wide return table for the full catalog:

```python
from datetime import date

from akquant.akshare_provider import AkshareProvider, fetch_all_index_returns

provider = AkshareProvider()
returns = fetch_all_index_returns(
    provider=provider,
    start=date(2006, 1, 1),
    end=date(2026, 6, 8),
)
```

For quick experiments, pass `limit=20` to restrict the first N indices from the catalog.

## Data Format

The V0.1 CSV loader expects normalized daily bars:

```text
date,symbol,open,high,low,close,volume,amount,adjustment,source
2026-01-02,000001,10.00,10.20,9.90,10.00,100000,1000000,qfq,fixture
```

Optional columns:

- `is_trading`
- `is_halted`

## Research Boundary

This project is for historical research and backtesting only. Backtest results do not represent future returns and do not constitute investment advice.
