# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- **Python**: `D:\Anaconda\envs\Stock_env\python.exe` (conda env `Stock_env`)
- **Git**: Do NOT add co-author lines to commits

## Commands

```bash
# Run the stock picker (main entry point)
python run.py
python run.py --date 20240217 --top-n 20
python run.py --strategies ma_cross,rsi_oversold --verbose

# Data collection (must run from src/ parent, uses -m invocation)
python -m src.data.collect --mode full
python -m src.data.collect --mode incremental
python -m src.data.collect --mode full --source csi300 --start 20130101
python -m src.data.collect --mode incremental --source failed

# Tests
pytest
pytest test/test_strategies.py -k "ma_cross"   # run single test file / pattern

# Install dependencies
pip install -r requirements.txt
```

## Architecture

The system is an A-share quantitative stock picker driven by technical indicators and configurable strategies.

**Data flow**: `Pipeline` (orchestrator) → `StockPool` (get universe) → `LocalStore` (SQLite cache) → `StrategyRunner` (batch execute) → `SignalAggregator` (weighted merge) → `Formatter` (CSV/Excel/Markdown output)

**Key modules**:
- `src/engine/pipeline.py` — Main workflow orchestrator. Coordinates all modules in sequence.
- `src/engine/strategy_runner.py` — Loads enabled strategies from `strategies.yaml`, runs them concurrently via `ThreadPoolExecutor`, and precomputes shared technical indicators to avoid redundant calculation.
- `src/engine/signal_aggregator.py` — Merges per-stock signals across strategies using configurable methods (weighted_sum, weighted_avg, AND, OR).
- `src/config/config_manager.py` — Loads `settings.yaml`, reads `.env` for `TUSHARE_TOKEN`, validates required keys.
- `src/data/fetcher.py` — Tushare API wrapper (`BaseFetcher` / `TushareFetcher`).
- `src/data/local_store.py` — SQLite storage with thread-local connections and incremental update.
- `src/data/stock_pool.py` — Resolves stock universe (all A-shares, index constituents, custom list).
- `src/data/collect.py` — Standalone data collection script (full/incremental modes).

**Strategy pattern**: All strategies inherit `Strategy` (ABC in `src/strategies/base.py`) with a `calculate(df) -> pd.Series` method returning 0–1 signal strength. `StrategyMixin` provides shared preprocessing. New strategies must be registered in `StrategyRunner._load_strategies()` and added to `strategies.yaml`.

**Configuration**: Two YAML files — `settings.yaml` (global: data source, storage, logging, output) and `strategies.yaml` (strategy params and enable/disable). Sensitive values (Tushare token) go in `.env`.

**Data schema**: Strategy input DataFrames require columns: `trade_date`, `open`, `high`, `low`, `close`, `volume`, `amount`. `StrategyRunner._precompute_indicators()` adds MA/EMA/RSI/MACD/KDJ columns automatically.

**Concurrency**: `StrategyRunner` uses `ThreadPoolExecutor` with `cpu_count * 2` workers. `LocalStore` uses thread-local connections and a lock for initialization safety.

## Conventions

- Bilingual comments (Chinese + English) throughout the codebase — maintain this pattern.
- The `run.py` entry point adds `src/` to `sys.path` — imports within `src/` are bare (e.g., `from data.fetcher import ...`).
- Stock codes follow Tushare format: `000001.SZ`, `600000.SH`.
- Index constituent files live in `stock_code/` as plain text (one code per line).
- Generated outputs go to `reports/`, logs to `logs/`, database to `database/` (all gitignored).
