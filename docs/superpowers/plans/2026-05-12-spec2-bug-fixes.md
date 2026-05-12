# Spec 2: Bug 修复 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 7 个已发现的 bug（策略注册缺失、模块引用不存在、参数错误、计算不一致等），使系统能正确运行。

**Architecture:** 本 plan 修复 strategy_runner.py 中的 4 个 bug（注册表、MACD/KDJ 调用、日志）、pipeline.py 中的 1 个 bug（错误的数据更新调用）、rsi_oversold.py 中的 1 个 bug（RSI 算法不一致）。修复后的代码是 Spec 3 性能优化的基础。

**Tech Stack:** pandas, numpy（现有依赖）

**前置依赖:** Plan 1（Spec 1）已完成

---

## 文件结构

| 文件 | 操作 | Bug |
|------|------|-----|
| `src/engine/strategy_runner.py` | 修改 | Bug 1, 5, 6, 7 |
| `src/engine/pipeline.py` | 修改 | Bug 3 |
| `src/strategies/rsi_oversold.py` | 修改 | Bug 4 |

---

### Task 1: 修复 strategy_runner.py 的 Bug 1（策略注册表）

**Files:**
- Modify: `src/engine/strategy_runner.py:17-19` (import 区)
- Modify: `src/engine/strategy_runner.py:65-68` (strategy_registry)

- [ ] **Step 1: 补充缺失的策略 import**

在 `src/engine/strategy_runner.py` 文件顶部，现有 import（行 17-19）之后添加:
```python
from strategies.multi_indicator_combo import MultiIndicatorComboStrategy, LowVolatilityBullishStrategy
from strategies.zhixing_trend_strategy import ZhixingTrendStrategy
```

- [ ] **Step 2: 补全策略注册表**

将 `strategy_registry` 字典（行 65-68）从:
```python
        strategy_registry = {
            'ma_cross': MACrossStrategy,
            'rsi_oversold': RSIOversoldStrategy,
        }
```
改为:
```python
        strategy_registry = {
            'ma_cross': MACrossStrategy,
            'rsi_oversold': RSIOversoldStrategy,
            'multi_indicator_combo': MultiIndicatorComboStrategy,
            'low_volatility_bullish': LowVolatilityBullishStrategy,
            'zhixing_trend': ZhixingTrendStrategy,
        }
```

- [ ] **Step 3: 验证策略加载**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
from engine.strategy_runner import StrategyRunner
runner = StrategyRunner('strategies.yaml')
print('Loaded strategies:', list(runner.strategies.keys()))
print('Expected: ma_cross, rsi_oversold, multi_indicator_combo, zhixing_trend')
assert 'multi_indicator_combo' in runner.strategies, 'multi_indicator_combo missing!'
assert 'zhixing_trend' in runner.strategies, 'zhixing_trend missing!'
print('Bug 1 fixed: all 4 enabled strategies registered')
"
```
Expected: `Loaded strategies: ['ma_cross', 'rsi_oversold', 'multi_indicator_combo', 'zhixing_trend']` 以及 `Bug 1 fixed`

- [ ] **Step 4: 提交**

```bash
git add src/engine/strategy_runner.py
git commit -m "fix: 补全策略注册表，注册 multi_indicator_combo 和 zhixing_trend"
```

---

### Task 2: 修复 strategy_runner.py 的 Bug 5 + 6 + 7（MACD/KDJ 调用 + 日志）

**Files:**
- Modify: `src/engine/strategy_runner.py:82-145` (_precompute_indicators 方法)

- [ ] **Step 1: 修复 MACD 调用（Bug 5）**

将 `_precompute_indicators` 方法中的行 128-131:
```python
        # MACD
        macd_df = calculate_macd(df, fast=12, slow=26, signal=9, column='close')
        df['macd_dif'] = macd_df['dif']
        df['macd_dea'] = macd_df['dea']
        df['macd_histogram'] = macd_df['histogram']
```
改为:
```python
        # MACD
        dif, dea, macd_hist = calculate_macd(df, fast_period=12, slow_period=26, signal_period=9, column='close')
        df['macd_dif'] = dif
        df['macd_dea'] = dea
        df['macd_histogram'] = macd_hist
```

- [ ] **Step 2: 修复 KDJ 调用（Bug 6）**

将行 134-137:
```python
        # KDJ
        kdj_df = calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)
        df['kdj_k'] = kdj_df['k']
        df['kdj_d'] = kdj_df['d']
        df['kdj_j'] = kdj_df['j']
```
改为:
```python
        # KDJ
        k, d, j = calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)
        df['kdj_k'] = k
        df['kdj_d'] = d
        df['kdj_j'] = j
```

- [ ] **Step 3: 修复预计算列数日志（Bug 7）**

在 `_precompute_indicators` 方法中，`df = df.copy()` 之后（或删除 copy 后的等效位置），`df['__precomputed__'] = True` 之前，添加列数记录:
```python
        n_before = len(df.columns)
```

将行 143 的日志:
```python
        self.logger.debug(f"Precomputed {len(df.columns) - len(df.columns) - 1} indicator columns")
```
改为:
```python
        self.logger.debug(f"Precomputed {len(df.columns) - n_before - 1} indicator columns")
```
（`-1` 是因为 `__precomputed__` 标记列本身不算指标列）

- [ ] **Step 4: 验证 _precompute_indicators 不报错**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
import pandas as pd
from engine.strategy_runner import StrategyRunner

runner = StrategyRunner('strategies.yaml')
# 构造一个足够长的测试 DataFrame
df = pd.DataFrame({
    'trade_date': pd.date_range('2024-01-01', periods=100, freq='D').strftime('%Y%m%d'),
    'open': range(100),
    'high': range(1, 101),
    'low': range(100),
    'close': range(100),
    'vol': range(100),
    'amount': range(100),
})
df = df.astype(float)
result = runner._precompute_indicators(df)
print(f'Columns after precompute: {len(result.columns)}')
assert 'macd_dif' in result.columns, 'macd_dif missing!'
assert 'kdj_k' in result.columns, 'kdj_k missing!'
print('Bug 5+6+7 fixed: MACD and KDJ precomputed correctly')
"
```
Expected: 无 TypeError，输出 `Bug 5+6+7 fixed`

- [ ] **Step 5: 提交**

```bash
git add src/engine/strategy_runner.py
git commit -m "fix: 修复 MACD/KDJ 返回值类型和参数名错误，修复预计算列数日志"
```

---

### Task 3: 修复 pipeline.py 的 Bug 3（删除不合理的 update_daily_data 调用）

**Files:**
- Modify: `src/engine/pipeline.py:138-145`

- [ ] **Step 1: 删除 update_daily_data 调用，保留 _init_tables**

将 `pipeline.py` 的 `run` 方法中行 138-145:
```python
            # 2. 更新本地数据
            # 2. Update local data
            self.logger.info("Updating local data...")
            self.local_store._init_tables()
            update_stats = self.local_store.update_daily_data(stock_list)
            self.logger.info(
                f"Data update completed: {update_stats['success']} success, "
                f"{update_stats['failed']} failed"
            )
```
改为:
```python
            # 2. 初始化数据库表结构（数据更新由 collect.py 负责）
            self.local_store._init_tables()
```

- [ ] **Step 2: 验证 pipeline 不再调用 update_daily_data**

Run:
```bash
cd d:/DeepLearning/stock_picker
grep -n "update_daily_data" src/engine/pipeline.py
```
Expected: 无输出（该调用已完全删除）

- [ ] **Step 3: 提交**

```bash
git add src/engine/pipeline.py
git commit -m "fix: 删除 Pipeline 中的 update_daily_data 调用，数据更新由 collect.py 负责"
```

---

### Task 4: 修复 rsi_oversold.py 的 Bug 4（RSI 计算不一致）

**Files:**
- Modify: `src/strategies/rsi_oversold.py`

- [ ] **Step 1: 删除 _calculate_rsi 方法，改用统一指标函数**

在 `src/strategies/rsi_oversold.py` 文件顶部 import 区，将:
```python
import pandas as pd
from typing import Dict, Any
from .base import Strategy, StrategyMixin
```
改为:
```python
import pandas as pd
from typing import Dict, Any
from .base import Strategy, StrategyMixin
from ..utils.indicators import calculate_rsi
```

将 `calculate` 方法中行 63:
```python
        df['rsi'] = self._calculate_rsi(df['close'], period)
```
改为:
```python
        df['rsi'] = calculate_rsi(df, period=period, column='close')
```

删除整个 `_calculate_rsi` 方法（行 83-118），即从 `def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:` 开始到 `return rsi` 的整个方法体。

- [ ] **Step 2: 验证 RSI 策略使用统一的计算方法**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
from strategies.rsi_oversold import RSIOversoldStrategy
s = RSIOversoldStrategy()
# 确认不再有 _calculate_rsi 方法
assert not hasattr(s, '_calculate_rsi'), '_calculate_rsi should be removed!'
print('Bug 4 fixed: RSI strategy uses unified calculate_rsi from indicators.py')
"
```
Expected: `Bug 4 fixed: RSI strategy uses unified calculate_rsi from indicators.py`

- [ ] **Step 3: 提交**

```bash
git add src/strategies/rsi_oversold.py
git commit -m "fix: RSI 策略改用 indicators.py 的统一 calculate_rsi，删除重复实现"
```

---

### Task 5: 端到端验证

- [ ] **Step 1: 验证策略加载和指标计算完整流程**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
from engine.strategy_runner import StrategyRunner

runner = StrategyRunner('strategies.yaml')
print(f'已注册策略 ({len(runner.strategies)}): {list(runner.strategies.keys())}')

assert len(runner.strategies) >= 4, f'期望至少 4 个策略，实际 {len(runner.strategies)}'
for name in ['ma_cross', 'rsi_oversold', 'multi_indicator_combo', 'zhixing_trend']:
    assert name in runner.strategies, f'{name} 未注册!'

print('所有验证通过')
"
```
Expected: `已注册策略 (4/5): [...]` 和 `所有验证通过`

- [ ] **Step 2: 验证 pipeline 导入正常**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
from config.config_manager import ConfigManager
from engine.pipeline import Pipeline
config = ConfigManager.load_and_validate()
# 不实际运行（需要数据库），只验证初始化不报错
print('Pipeline import OK')
"
```
Expected: `Pipeline import OK`

- [ ] **Step 3: 最终提交**

```bash
git status
git add -A
git commit -m "chore: Spec 2 完成 — 修复 7 个 Bug"
```
