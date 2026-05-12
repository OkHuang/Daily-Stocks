# Stock Picker 深度优化设计文档

日期: 2026-05-12

## 概述

对 stock_picker 项目进行全面的代码审查和深度优化，涵盖安全修复、Bug 修复、架构统一、性能优化和代码清理。

## 第一部分：安全 — Token 泄露

### 问题

`settings.yaml` 中硬编码了 Tushare Token，若被 git 跟踪会泄露到远程仓库。

### 方案

1. 创建 `.env` 文件存放 token（`TUSHARE_TOKEN=xxx`），加入 `.gitignore`
2. `settings.yaml` 的 token 字段改为 `null`（YAML 原生空值，不用 `${VAR}` 语法，因为 `yaml.safe_load` 不支持变量替换）
3. `ConfigManager` 增加 `python-dotenv` 支持，启动时自动加载 `.env` 文件；`get_token()` 优先从 env var 读取，回退到 yaml 中的值
4. `run.py` 中的手动 token 检查（行 139-143）替换为 `ConfigManager.get_token()`，统一验证逻辑
5. 如果 `.gitignore` 未包含 `.env`，追加之

### 影响文件

- `settings.yaml` — token 改为 null
- `.env`（新建）— 存放实际 token
- `.gitignore`（新建或修改）
- `src/config/config_manager.py` — 增加 dotenv 加载
- `run.py` — token 检查改用 ConfigManager
- `requirements.txt` — 添加 python-dotenv

## 第二部分：Bug 修复（7 个）

### Bug 1：策略注册表不完整

- **文件**: `src/engine/strategy_runner.py:65-68`
- **问题**: 只注册了 `ma_cross` 和 `rsi_oversold`，`multi_indicator_combo` 和 `zhixing_trend` 虽在 `strategies.yaml` 启用但被静默忽略
- **修复**: 在 `strategy_registry` 字典中添加 `MultiIndicatorComboStrategy`、`LowVolatilityBullishStrategy`（disabled 但仍注册）和 `ZhixingTrendStrategy`，补充对应的 import

### Bug 2：引用不存在的模块

- **文件**: `run.py:158`
- **问题**: `from utils.date_utils import validate_date_format`，但 `utils/date_utils.py` 不存在，指定 `--date` 参数时会崩溃
- **修复**: 删除该 import，改用 `datetime.strptime` 内联验证日期格式，捕获 ValueError 即可

### Bug 3：Pipeline 缺少 fetcher 参数 + 设计问题

- **文件**: `src/engine/pipeline.py:141`
- **问题**: `self.local_store.update_daily_data(stock_list)` 缺少必需的 `fetcher` 参数，会崩溃
- **设计问题**: 即使补上 `fetcher`，这个调用会对全部 5000+ 股票做全量数据获取，每次 `python run.py` 都要跑几小时，不合理
- **修复**: 删除 Pipeline 中的 `update_daily_data` 调用。Pipeline 的职责是"加载已有数据 → 执行策略 → 输出"，数据更新由 `collect.py --mode incremental` 单独负责。Pipeline 只做 `_init_tables()` 和从 local_store 读取数据

### Bug 4：RSI 计算不一致

- **文件**: `src/strategies/rsi_oversold.py:83-118`
- **问题**: 策略类自行实现了 `_calculate_rsi`，用 `rolling().mean()`（SMA 方式），而 `indicators.py` 的 `calculate_rsi` 用 `ewm(alpha=1/period)`（Wilder's 方式），两种算法结果不同
- **修复**: 删除 `_calculate_rsi` 方法，改为调用 `utils/indicators.py` 中的 `calculate_rsi`

### Bug 5：calculate_macd 参数名 + 返回值类型双重错误

- **文件**: `src/engine/strategy_runner.py:128-131`
- **问题**:
  - 参数名错误：调用用 `fast=12, slow=26, signal=9`，但函数签名是 `fast_period=12, slow_period=26, signal_period=9`，会抛 TypeError
  - 返回值类型错误：`calculate_macd` 返回 tuple `(dif, dea, macd)`，但代码当 DataFrame 用 `macd_df['dif']`
- **修复**: 改为 `dif, dea, macd_hist = calculate_macd(df, fast_period=12, slow_period=26, signal_period=9, column='close')`，分别赋值

### Bug 6：calculate_kdj 返回值类型错误（同 Bug 5 模式）

- **文件**: `src/engine/strategy_runner.py:134-137`
- **问题**: `calculate_kdj` 返回 tuple `(k, d, j)`，但代码当 DataFrame 用 `kdj_df['k']`、`kdj_df['d']`、`kdj_df['j']`
- **修复**: 改为 `k, d, j = calculate_kdj(df, ...)`，分别赋值

### Bug 7：_precompute_indicators 的日志永远输出 -1

- **文件**: `src/engine/strategy_runner.py:143`
- **问题**: `len(df.columns) - len(df.columns) - 1` 表达式永远是 `-1`，两个相同的值相减为 0
- **修复**: 在预计算前记录列数 `n_before = len(df.columns)`，日志中用 `len(df.columns) - n_before`

## 第三部分：架构统一

### 3.1 统一配置加载

- **问题**: 3 套配置加载逻辑（`run.py` 的 `load_config`、`collect.py` 的 `load_config`、`ConfigManager`），且 `ConfigManager` 已实现验证但从未被使用
- **方案**:
  - 删除 `run.py` 和 `collect.py` 中的 `load_config` 函数
  - 统一使用 `ConfigManager.load_and_validate()`
  - **注意 import 路径差异**: `collect.py` 用 `from src.data...`，`config_manager.py` 用 `from data...`。需要在 `collect.py` 中统一为 `from src.config.config_manager import ConfigManager`，或在 ConfigManager 中统一路径风格

### 3.2 线程/进程安全

- **问题**: `strategy_runner.py:222` 的 `_indicator_cache.clear()` 在并发环境下有竞态条件
- **方案**: 改为多进程后自动解决（每个进程独立内存空间），删除 `_indicator_cache` 及相关引用

## 第四部分：性能优化

### 4.1 并行策略改为多进程

- **文件**: `src/engine/strategy_runner.py`
- **问题**: `ThreadPoolExecutor` 对 CPU 密集型 pandas 操作无实际加速（GIL 限制）
- **方案**: 改用 `ProcessPoolExecutor`
  - **SQLite 跨进程问题**: SQLite 连接不能序列化传递，多进程并发写会 `database is locked`
  - **解决方案**: 在主进程中预加载所有股票数据为 dict，将 DataFrame 直接传给子进程；子进程只做指标计算和策略执行，不碰数据库。如果子进程中数据不足 50 条，记录 warning 跳过（而非尝试 fetch 和 save）
  - 主进程收集结果，只返回信号 dict
  - 限制最大 worker 数为 `cpu_count`（不超过 4），避免内存爆炸

### 4.2 validate_daily_data 向量化

- **文件**: `src/data/local_store.py:529`
- **问题**: `iterrows()` 逐行校验，数据量大时极慢
- **方案**: 改用向量化 pandas 操作：
  - 负数检查: `(df[['open','high','low','close','vol','amount']] < 0)` 生成布尔矩阵，逐列统计错误行
  - 价格逻辑: `(df['high'] < df['low']).any()` 等向量比较
  - 缺失值: `df[['open','high','low','close','vol','amount']].isna()` 向量化统计
  - 重复检查: 保持不变（已经是向量化的）
  - 验证错误按类型汇总（如"5 行 high < low"），不再逐行逐条记录

### 4.3 删除不必要的 DataFrame 拷贝

- `strategy_runner.py:107`: `df = df.copy()` — 每只股票的数据已经独立加载，改为不拷贝直接操作
- `indicators.py:315`: `temp_df = df.copy()` — `calculate_zhixing_short_trend` 改为直接对 Series 做 `ewm` 操作：
  ```python
  ema1 = df[column].ewm(span=period, adjust=False).mean()
  trend = ema1.ewm(span=period, adjust=False).mean()
  ```

## 第五部分：代码清理

### 5.1 注释风格统一为中文

- **范围**: 所有 `.py` 文件
- **操作**: 删除所有英文注释和英文 docstring 部分，只保留中文

### 5.2 LLM 模块清理

- **文件**: `src/llm_integration/report_analyzer.py`, `src/llm_integration/prompt_templates.py`
- **操作**:
  - `PromptTemplates`: 保留 `__init__` 和三个模板 getter 方法（`_get_analysis_template`、`_get_summary_template`、`_get_risk_alert_template`，这些返回的是实际模板字符串，不是死代码）；保留 `fill_template`（可用）；删除 `format_stocks_for_prompt` 和 `generate_analysis_prompt`（纯 pass/TODO）
  - `ReportAnalyzer`: 保留 `__init__`；删除 `analyze_results`、`_call_llm_api`、`save_analysis_report`、`batch_analyze`（全部是 pass/TODO 或 NotImplementedError）

### 5.3 精简 docstring

- **范围**: 所有 `.py` 文件
- **操作**: 保留关键中文 docstring（说明 WHY 和非显而易见的细节），删除显而易见的参数类型说明和双语返回值描述。对签名中已体现的参数类型，不再在 docstring 中重复

### 5.4 其他细节清理

- 删除 `Formatter.__init__` 中的空 `pass`
- 删除 `StrategyMixin` 中重复的 `validate_signal` 方法（基类 `Strategy` 已有相同实现）
- 各包的 `__init__.py` 添加基本导出（方便外部 import）

## 不在本次范围内

- 新增功能（如新策略、新数据源）
- LLM 集成的实际实现
- 测试文件的重写或更新
- UI/前端改动
- `docs/` 目录下文档的更新
