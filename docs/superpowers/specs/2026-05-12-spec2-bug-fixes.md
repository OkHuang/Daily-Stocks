# Spec 2: Bug 修复

日期: 2026-05-12
父文档: [2026-05-12-deep-optimization-design.md](2026-05-12-deep-optimization-design.md) 第二部分

## 依赖关系

- **前置依赖**: Spec 1（配置加载已统一，run.py 的 ConfigManager 已就位）
- **后续影响**: Spec 3 会重构 `strategy_runner.py` 的并行逻辑，本 spec 必须先修复该文件中的 bug，否则 Spec 3 会基于错误代码重构

## 范围

修复 7 个已发现的 bug，确保系统可以正确运行。

## 变更清单

### Bug 1: 策略注册表不完整

- **文件**: `src/engine/strategy_runner.py`
- **位置**: 行 17-19 的 import 区 + 行 65-68 的 `strategy_registry`
- **修复**:
  - 补充 import：`from strategies.multi_indicator_combo import MultiIndicatorComboStrategy, LowVolatilityBullishStrategy` 和 `from strategies.zhixing_trend_strategy import ZhixingTrendStrategy`
  - 在 `strategy_registry` 字典中补全：
    - `'multi_indicator_combo': MultiIndicatorComboStrategy`
    - `'low_volatility_bullish': LowVolatilityBullishStrategy`
    - `'zhixing_trend': ZhixingTrendStrategy`

### Bug 3: Pipeline 不应做数据更新

- **文件**: `src/engine/pipeline.py`
- **位置**: 行 138-145
- **问题**: 行 141 调用 `update_daily_data(stock_list)` 缺少 `fetcher` 参数（会崩溃），且设计上不合理（每次运行选股都全量获取 5000+ 股票数据）
- **修复**:
  - 保留行 140 的 `self.local_store._init_tables()`（确保表结构存在）
  - 删除行 141 的 `update_stats = self.local_store.update_daily_data(stock_list)`
  - 删除行 142-145 的相关日志（`Data update completed...`）
  - Pipeline 只负责加载已有数据、执行策略、输出结果。数据更新由 `collect.py` 单独负责。

### Bug 4: RSI 计算不一致

- **文件**: `src/strategies/rsi_oversold.py`
- **位置**: 行 63 调用 `self._calculate_rsi`，行 83-118 定义 `_calculate_rsi`
- **问题**: 策略类自行实现了 `_calculate_rsi`，用 `rolling().mean()`（SMA 方式），而 `indicators.py` 的 `calculate_rsi` 用 `ewm(alpha=1/period)`（Wilder's 方式），结果不同
- **修复**:
  - 删除 `_calculate_rsi` 方法（行 83-118）
  - 添加 import：`from utils.indicators import calculate_rsi`
  - 行 63 改为 `df['rsi'] = calculate_rsi(df, period=period, column='close')`

### Bug 5: calculate_macd 参数名 + 返回值双重错误

- **文件**: `src/engine/strategy_runner.py`
- **位置**: 行 128-131
- **问题**:
  - 参数名错误：`fast=12, slow=26, signal=9` → 函数签名是 `fast_period, slow_period, signal_period`
  - 返回值类型错误：返回 tuple `(dif, dea, macd)` 但代码当 DataFrame 用 `macd_df['dif']`
- **修复**:
  ```python
  dif, dea, macd_hist = calculate_macd(df, fast_period=12, slow_period=26, signal_period=9, column='close')
  df['macd_dif'] = dif
  df['macd_dea'] = dea
  df['macd_histogram'] = macd_hist
  ```

### Bug 6: calculate_kdj 返回值类型错误

- **文件**: `src/engine/strategy_runner.py`
- **位置**: 行 134-137
- **问题**: `calculate_kdj` 返回 tuple `(k, d, j)` 但代码当 DataFrame 用 `kdj_df['k']` 等
- **修复**:
  ```python
  k, d, j = calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)
  df['kdj_k'] = k
  df['kdj_d'] = d
  df['kdj_j'] = j
  ```

### Bug 7: _precompute_indicators 日志永远输出 -1

- **文件**: `src/engine/strategy_runner.py`
- **位置**: 行 143
- **问题**: `len(df.columns) - len(df.columns) - 1` 永远是 `-1`
- **修复**: 在预计算前记录列数 `n_before = len(df.columns)`，日志改为 `f"Precomputed {len(df.columns) - n_before} indicator columns"`

## 涉及文件

| 文件 | 操作 |
|------|------|
| `src/engine/strategy_runner.py` | Bug 1, 5, 6, 7 |
| `src/engine/pipeline.py` | Bug 3 |
| `src/strategies/rsi_oversold.py` | Bug 4 |

## 与其他 Spec 的交叉文件

- `src/engine/strategy_runner.py`: 本 spec 修复 bug（import、函数调用参数），Spec 3 重构并行逻辑（ThreadPoolExecutor → ProcessPoolExecutor）。本 spec 先修，Spec 3 后改。
- `src/engine/pipeline.py`: 本 spec 删除 update_daily_data 调用，Spec 3 不再涉及此文件。
- `src/strategies/rsi_oversold.py`: 仅本 spec 修改。
