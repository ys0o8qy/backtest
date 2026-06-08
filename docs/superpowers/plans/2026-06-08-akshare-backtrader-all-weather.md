# AKShare Backtrader All-Weather Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AKShare-backed, Backtrader-powered multi-asset allocation backtester with ETF-first and index-fallback asset selection, including an all-weather portfolio template and index return data utilities.

**Architecture:** Keep the existing V0.1 custom engine intact for deterministic unit tests, and add a V0.2 path beside it. `akshare_provider.py` fetches and normalizes AKShare ETF/index data into pandas frames, `portfolios.py` defines candidate assets and allocation templates, and `backtrader_engine.py` runs periodic target-weight rebalancing through Backtrader.

**Tech Stack:** Python 3.11+, pandas, AKShare, Backtrader, pytest.

---

## File Structure

- Create `akquant/akshare_provider.py`: AKShare ETF/index fetchers, normalizer, fallback coverage checks, index return table.
- Create `akquant/portfolios.py`: asset candidate dataclasses, all-weather portfolio template, candidate selection logic.
- Create `akquant/backtrader_engine.py`: Backtrader data-feed conversion, target-weight rebalancing strategy, result dataclasses.
- Modify `akquant/cli.py`: add `portfolio` subcommand while preserving old single-strategy CLI behavior.
- Modify `pyproject.toml`: add `akshare`, `backtrader`, and `pandas`.
- Modify `README.md`: document all-weather backtest and fallback semantics.
- Add tests for provider fallback, portfolio templates, index returns, Backtrader rebalancing, and CLI.

## Tasks

### Task 1: AKShare Provider and Fallback

- [ ] Write tests where ETF data starts too late and index data covers the requested 20-year window.
- [ ] Verify tests fail because `akquant.akshare_provider` and `akquant.portfolios` are missing.
- [ ] Implement normalized AKShare fetchers and fallback selection.
- [ ] Verify provider tests pass.

### Task 2: Backtrader Multi-Asset Engine

- [ ] Write tests with two synthetic pandas feeds and quarterly rebalance.
- [ ] Verify tests fail because `akquant.backtrader_engine` is missing.
- [ ] Implement Backtrader target-weight strategy and result extraction.
- [ ] Verify Backtrader tests pass.

### Task 3: CLI and Documentation

- [ ] Write tests for the `portfolio` CLI subcommand using fixture CSV data.
- [ ] Verify tests fail with missing CLI behavior.
- [ ] Implement `portfolio` subcommand and README examples.
- [ ] Run full test suite.

### Task 4: Manual Verification

- [ ] Run `uv run --with pytest pytest -q`.
- [ ] Run a fixture-based portfolio CLI command and inspect the Markdown output.
- [ ] If AKShare dependencies can be installed, run an import smoke test for `akshare`, `backtrader`, and `pandas`.

