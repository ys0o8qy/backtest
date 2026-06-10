# AKQuant

AKQuant is a local A-share quantitative research and backtesting MVP. It now has two execution paths:

- V0.1 deterministic local engine for single-symbol strategy tests.
- V0.2 AKShare + Backtrader path for multi-asset portfolio allocation backtests.
- V0.3 portfolio comparison path for running multiple allocation configs under one data/cost policy.
- V0.4 A-share valuation screening path for PE/PB/dividend-yield stock pools.

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
- Builtin portfolio registry:
  - `all_weather`
  - `stock_bond_60_40`
  - `equity_only`
  - `bond_only`
- YAML/JSON custom portfolio configs.
- Multi-portfolio comparison report with metrics, equity curves, drawdowns, selected assets, and fallback summary.
- Latest A-share valuation snapshot normalization from AKShare.
- PE/PB/dividend-yield filtering and weighted value ranking.
- Reusable `StockPool` output with filter funnel, selected rows, and warnings.
- Local factor snapshot cache for saved screening inputs.
- Markdown/CSV valuation screening report export.

## What Is Not Implemented Yet

- Streamlit/Dash UI.
- Factor attribution and industry attribution.
- Historical valuation stock-pool backtesting.
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

## Compare Multiple Portfolios

```bash
uv run python -m akquant.cli compare \
  --portfolio all_weather \
  --portfolio stock_bond_60_40 \
  --portfolio custom.yaml \
  --start 2006-01-01 \
  --end 2026-06-09 \
  --rebalance quarterly \
  --out /tmp/akquant-comparison-report.md
```

`--portfolio` accepts either a builtin portfolio id or a YAML/JSON config path. The comparison path uses the same date range, same data fallback policy, and same Backtrader execution model for each portfolio.

Example custom config:

```yaml
id: custom_60_40
name: Custom 60/40
rebalance: quarterly
initial_cash: 100000
cost_model:
  commission_rate: 0.0003
  slippage_perc: 0.0005
data_policy:
  min_coverage_ratio: 0.95
targets:
  - asset_class: equity
    weight: 0.6
    candidates:
      - { symbol: "510300", name: "沪深300ETF", kind: "etf" }
      - { symbol: "000300", name: "沪深300指数", kind: "index" }
  - asset_class: bond
    weight: 0.4
    candidates:
      - { symbol: "511010", name: "国债ETF", kind: "etf" }
      - { symbol: "000012", name: "国债指数", kind: "index" }
```

## Screen A-Share Valuation Factors

```bash
uv run python -m akquant.cli screen \
  --as-of latest \
  --factor-cache-dir .akquant/factors \
  --pe-max 15 \
  --pb-max 1.5 \
  --dividend-yield-min 0.03 \
  --market-cap-min 5000000000 \
  --turnover-amount-min 50000000 \
  --top 50 \
  --out /tmp/akquant-screen-report.md \
  --csv-out /tmp/akquant-screen.csv
```

The screen path currently targets the latest AKShare snapshot. It excludes ST and suspended stocks by default, ranks candidates by low PE, low PB, and high dividend yield, then writes an auditable stock pool report.

When `--factor-cache-dir` is provided with `--as-of latest`, AKQuant saves the fetched valuation snapshot into that cache. To screen from a saved snapshot without calling AKShare again:

```bash
uv run python -m akquant.cli screen \
  --as-of 2026-06-10 \
  --factor-cache-dir .akquant/factors \
  --pe-max 15 \
  --pb-max 1.5 \
  --dividend-yield-min 0.03 \
  --top 50 \
  --out /tmp/akquant-screen-2026-06-10.md
```

For full historical valuation backtests, add a stricter historical factor reconstruction path before running periodic stock-pool rebalancing.

## Architecture Notes

Project engineering standards are documented in [`docs/project-standards.md`](docs/project-standards.md).

The stable portfolio-comparison architecture uses these boundaries:

```text
AKShare provider
  -> PortfolioConfig / registry / config loader
  -> portfolio runner
  -> Backtrader execution
  -> metrics and comparison report
```

The core domain objects are:

- `PortfolioConfig`: allocation, rebalance cadence, cost model, and data policy.
- `SelectedAssetData`: actual ETF or index selected for each asset class.
- `BacktraderPortfolioResult`: one auditable backtest run.
- `ComparisonReport`: comparable metrics and tables across multiple runs.

The valuation screening architecture adds:

```text
AKShare latest stock snapshot
  -> fundamentals normalization
  -> screening filters and ranking
  -> StockPool
  -> Markdown/CSV report
```

The implemented screening domain objects are:

- `ScreenConfig`: filter, ranking, and Top N rules.
- `ScreeningRule`: one field-level filter.
- `RankingSpec`: one weighted factor rank.
- `StockPool`: selected rows, filter funnel, configuration snapshot, and warnings.

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
