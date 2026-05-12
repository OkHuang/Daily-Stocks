# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- **Python**: `D:\Anaconda\envs\Stock_env\python.exe` (conda env `Stock_env`)
- **Git**: 提交时不要添加 `Co-Authored-By` 行，即不要在 commit message 中包含任何 co-author 信息

## Commands

```bash
# 运行选股（主入口）
python run.py
python run.py --date 20240217 --top-n 20
python run.py --strategies ma_cross,rsi_oversold --verbose

# 数据收集
python -m src.data.collect --mode full
python -m src.data.collect --mode incremental
python -m src.data.collect --mode full --source csi300 --start 20130101
python -m src.data.collect --mode incremental --source failed

# 测试
pytest
pytest test/test_strategies.py -k "ma_cross"

# 安装依赖
pip install -r requirements.txt
```

## Architecture

A 股量化选股系统，基于技术指标和可配置策略。

**数据流**: `Pipeline` → `StockPool`（获取股票池）→ `LocalStore`（SQLite 缓存）→ `StrategyRunner`（多进程批量执行）→ `SignalAggregator`（加权合并）→ `Formatter`（CSV/Excel/Markdown 输出）

**核心模块**:
- `src/engine/pipeline.py` — 流程编排器，协调所有模块顺序执行，支持上下文管理器自动清理资源。
- `src/engine/strategy_runner.py` — 从 `strategies.yaml` 加载已启用策略，通过 `ProcessPoolExecutor` 多进程并行执行，预计算 MA/EMA/RSI/MACD/KDJ 等共享指标。
- `src/engine/signal_aggregator.py` — 多策略信号加权合并，支持 weighted_sum、weighted_avg、AND、OR 四种聚合方式。
- `src/config/config_manager.py` — 加载 `settings.yaml`，通过 python-dotenv 读取 `.env` 中的 `TUSHARE_TOKEN`，校验必要配置项。
- `src/data/fetcher.py` — Tushare API 封装（`BaseFetcher` / `TushareFetcher`），含频率限制和自动重试。
- `src/data/local_store.py` — SQLite 存储，WAL 模式，线程安全连接，含数据验证和向量化校验。
- `src/data/stock_pool.py` — 股票池解析（全 A 股、指数成分股、自定义列表）。
- `src/data/collect.py` — 独立数据收集脚本（全量/增量模式）。

**策略模式**: 所有策略继承 `Strategy`（ABC，`src/strategies/base.py`），实现 `calculate(df) -> pd.Series` 返回 0-1 信号强度。`StrategyMixin` 提供共享的预处理和信号构建方法。新增策略需注册到 `StrategyRunner._load_strategies()` 的 `strategy_registry` 并在 `strategies.yaml` 中配置。

**配置**: 两份 YAML 文件 — `settings.yaml`（全局配置）和 `strategies.yaml`（策略参数和启用状态）。敏感信息（Tushare Token）通过 `.env` 文件管理，不写入代码或配置文件。

**数据格式**: 策略输入 DataFrame 需要 `trade_date, open, high, low, close, volume, amount` 列。`StrategyRunner._precompute_indicators()` 自动添加 MA/EMA/RSI/MACD/KDJ 列。

**并发**: `StrategyRunner` 使用 `ProcessPoolExecutor` 多进程执行（绕过 GIL，适合 CPU 密集的 pandas 操作）。数据在主进程预加载，通过进程间序列化传递给子进程。`LocalStore` 使用线程本地连接。

## Conventions

- 注释统一使用中文。
- `run.py` 入口将 `src/` 加入 `sys.path`，因此 `src/` 内的导入使用裸路径（如 `from data.fetcher import ...`）。
- 股票代码遵循 Tushare 格式：`000001.SZ`、`600000.SH`。
- 指数成分股文件在 `stock_code/` 目录下，每行一个代码。
- 生成物输出到 `reports/`、日志到 `logs/`、数据库到 `database/`（均已 gitignore）。
