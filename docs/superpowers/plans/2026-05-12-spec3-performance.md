# Spec 3: 性能优化 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将策略并行执行从多线程改为多进程（突破 GIL 限制），将数据验证从逐行 iterrows 改为向量化操作，消除不必要的 DataFrame 拷贝。

**Architecture:** 主进程预加载所有股票数据为 dict，通过 ProcessPoolExecutor 分发给子进程。子进程接收 DataFrame + strategies.yaml 路径，在子进程内实例化策略并计算信号，返回信号 dict。validate_daily_data 从逐行循环改为 pandas 向量化操作。

**Tech Stack:** ProcessPoolExecutor（标准库），pandas 向量化操作

**前置依赖:** Plan 1（Spec 1）、Plan 2（Spec 2）已完成

---

## 文件结构

| 文件 | 操作 | 变更 |
|------|------|------|
| `src/engine/strategy_runner.py` | 重构 | 多进程、删 copy、删 cache |
| `src/data/local_store.py` | 修改 | validate_daily_data 向量化 |
| `src/utils/indicators.py` | 修改 | calculate_zhixing_short_trend 删 copy |

---

### Task 1: strategy_runner.py — 改为多进程并行

**Files:**
- Modify: `src/engine/strategy_runner.py`（整体重构 run 方法和 _run_single_stock）

这是最大的改动。将整个 strategy_runner.py 的并行逻辑从多线程改为多进程。

- [ ] **Step 1: 在文件顶部添加模块级子进程函数**

在 `src/engine/strategy_runner.py` 文件中，`class StrategyRunner:` 之前，添加模块级函数（子进程入口）:

```python
def _worker_process_stock(stock_code: str, df_data: pd.DataFrame, config_path: str) -> Dict[str, float]:
    """子进程入口函数：对单只股票执行所有策略。

    此函数在子进程中运行，需要独立设置 import 路径并实例化策略。
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

    if df_data is None or len(df_data) < 50:
        return {}

    from engine.strategy_runner import StrategyRunner
    runner = StrategyRunner(config_path=config_path)
    runner._precompute_indicators(df_data)

    signals = {}
    for strategy_name, strategy in runner.strategies.items():
        try:
            signal = strategy.get_latest_signal(df_data)
            if signal > 0:
                signals[strategy_name] = signal
        except Exception:
            pass

    return signals
```

- [ ] **Step 2: 添加 _preload_stock_data 方法**

在 `StrategyRunner` 类中，`_run_single_stock` 方法之前添加:

```python
    def _preload_stock_data(self, stock_list: List[str], local_store) -> Dict[str, pd.DataFrame]:
        """在主进程中预加载所有股票数据，避免子进程访问 SQLite。"""
        stock_data = {}
        for stock_code in stock_list:
            try:
                df = local_store.load_daily_data(stock_code)
                if df is not None and len(df) >= 50:
                    stock_data[stock_code] = df
            except Exception as e:
                self.logger.warning(f"加载 {stock_code} 数据失败: {e}")
        self.logger.info(f"预加载了 {len(stock_data)}/{len(stock_list)} 只股票的数据")
        return stock_data
```

- [ ] **Step 3: 重构 run 方法**

将 `run` 方法整体替换为:

```python
    def run(
        self,
        stock_list: List[str],
        local_store,
        fetcher
    ) -> Dict[str, Dict[str, float]]:
        """执行所有策略（多进程并行）。"""
        # 1. 在主进程预加载所有数据
        self.logger.info("预加载股票数据...")
        stock_data = self._preload_stock_data(stock_list, local_store)

        if not stock_data:
            self.logger.warning("没有足够的股票数据可供分析")
            return {}

        # 2. 多进程执行
        results = {}
        cpu_count = os.cpu_count() or 1
        max_workers = min(cpu_count, 4)

        self.logger.info(f"使用 {max_workers} 个进程处理 {len(stock_data)} 只股票")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _worker_process_stock,
                    stock_code,
                    df,
                    self.config_path
                ): stock_code
                for stock_code, df in stock_data.items()
            }

            for future in as_completed(futures):
                stock_code = futures[future]
                try:
                    stock_results = future.result(timeout=60)
                    if stock_results:
                        results[stock_code] = stock_results
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 时出错: {e}")

        self.logger.info(f"策略执行完成: {len(results)} 只股票产生信号")
        return results
```

- [ ] **Step 4: 删除旧的 _run_single_stock 方法和 _indicator_cache**

删除 `_run_single_stock` 方法（已被 `_worker_process_stock` 替代）。

删除 `__init__` 中的 `self._indicator_cache = {}`。

- [ ] **Step 5: 更新 import**

将文件顶部的:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
```
改为:
```python
from concurrent.futures import ProcessPoolExecutor, as_completed
```

- [ ] **Step 6: 验证多进程策略执行**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
from engine.strategy_runner import StrategyRunner
print('StrategyRunner import OK')
print('ProcessPoolExecutor ready')
"
```
Expected: 无 import 错误

- [ ] **Step 7: 提交**

```bash
git add src/engine/strategy_runner.py
git commit -m "perf: 策略执行从多线程改为多进程，主进程预加载数据"
```

---

### Task 2: strategy_runner.py — 删除不必要的 df.copy()

**Files:**
- Modify: `src/engine/strategy_runner.py` (_precompute_indicators 方法)

- [ ] **Step 1: 删除 df.copy()**

在 `_precompute_indicators` 方法中，删除:
```python
        df = df.copy()
```
直接操作传入的 df（预加载阶段每只股票的数据已是独立 DataFrame）。

- [ ] **Step 2: 提交**

```bash
git add src/engine/strategy_runner.py
git commit -m "perf: 删除 _precompute_indicators 中不必要的 df.copy()"
```

---

### Task 3: indicators.py — 删除 calculate_zhixing_short_trend 中的 df.copy()

**Files:**
- Modify: `src/utils/indicators.py:276-321` (calculate_zhixing_short_trend)

- [ ] **Step 1: 重写 calculate_zhixing_short_trend**

将整个 `calculate_zhixing_short_trend` 函数替换为:

```python
def calculate_zhixing_short_trend(
    df: pd.DataFrame,
    period: int = 10,
    column: str = 'close'
) -> pd.Series:
    """计算知行短期趋势线（双重 EMA）。"""
    ema1 = df[column].ewm(span=period, adjust=False).mean()
    trend = ema1.ewm(span=period, adjust=False).mean()
    return trend
```

关键变化: 不再创建临时 DataFrame，直接在 Series 上做双重 ewm。

- [ ] **Step 2: 验证结果一致**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
import pandas as pd
from utils.indicators import calculate_zhixing_short_trend

df = pd.DataFrame({'close': range(100)})
result = calculate_zhixing_short_trend(df, period=10)
print(f'结果长度: {len(result)}')
assert len(result) == 100
assert not result.isna().all()
print('calculate_zhixing_short_trend OK')
"
```
Expected: `calculate_zhixing_short_trend OK`

- [ ] **Step 3: 提交**

```bash
git add src/utils/indicators.py
git commit -m "perf: calculate_zhixing_short_trend 消除不必要的 DataFrame 拷贝"
```

---

### Task 4: local_store.py — validate_daily_data 向量化

**Files:**
- Modify: `src/data/local_store.py` (validate_daily_data 方法)

- [ ] **Step 1: 替换逐行校验为向量化操作**

将 `validate_daily_data` 方法中，`# 逐行验证数据` 注释之后的整个 `for idx, row in df.iterrows():` 循环（约行 529-586），替换为:

```python
        # 向量化数据验证
        price_cols = ['open', 'high', 'low', 'close']
        volume_cols = ['vol', 'amount']
        all_cols = price_cols + volume_cols

        # 负数检查
        neg_mask = df[all_cols] < 0
        for col in all_cols:
            neg_count = neg_mask[col].sum()
            if neg_count > 0:
                result['errors'].append(f"{col} 存在 {neg_count} 行负数值")
                result['stats']['invalid_records'] += neg_count

        if result['errors']:
            result['is_valid'] = False

        # 价格逻辑检查（排除含 NaN 的行）
        valid_mask = df[price_cols].notna().all(axis=1)
        df_valid = df[valid_mask]

        logic_checks = [
            (df_valid['high'] < df_valid['low'], "high < low"),
            (df_valid['high'] < df_valid['open'], "high < open"),
            (df_valid['high'] < df_valid['close'], "high < close"),
            (df_valid['low'] > df_valid['open'], "low > open"),
            (df_valid['low'] > df_valid['close'], "low > close"),
        ]
        for mask, desc in logic_checks:
            error_count = mask.sum()
            if error_count > 0:
                result['is_valid'] = False
                result['errors'].append(f"{error_count} 行价格逻辑错误: {desc}")
                result['stats']['invalid_records'] += error_count

        # 缺失值统计
        missing_per_row = df[all_cols].isna().sum(axis=1)
        all_nan_count = (missing_per_row == len(all_cols)).sum()
        partial_nan_count = ((missing_per_row > 0) & (missing_per_row < len(all_cols))).sum()
        result['stats']['missing_values'] = int(missing_per_row.sum())

        if all_nan_count > 0:
            result['warnings'].append(f"{all_nan_count} 行所有字段为空（可能停牌）")
        if partial_nan_count > 0:
            result['warnings'].append(f"{partial_nan_count} 行部分字段为空")
```

注意: 保留 `validate_daily_data` 中此代码块之前的部分（列检查、数据类型转换）和之后的部分（重复检查、日志输出）。

- [ ] **Step 2: 验证向量化校验功能**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
import pandas as pd
from data.local_store import LocalStore

store = LocalStore(db_path=':memory:')

# 正常数据
good_df = pd.DataFrame({
    'ts_code': ['000001.SZ'] * 5,
    'trade_date': ['20240101', '20240102', '20240103', '20240104', '20240105'],
    'open': [10.0, 10.5, 11.0, 10.8, 10.9],
    'high': [10.5, 11.0, 11.5, 11.0, 11.2],
    'low': [9.8, 10.2, 10.5, 10.5, 10.6],
    'close': [10.2, 10.8, 11.2, 10.9, 11.0],
    'vol': [1000.0] * 5,
    'amount': [10000.0] * 5,
})
r = store.validate_daily_data(good_df)
assert r['is_valid'], f'正常数据应该通过验证: {r[\"errors\"]}'
print('正常数据: PASS')

# 异常数据（high < low）
bad_df = good_df.copy()
bad_df.loc[0, 'high'] = 9.0  # high < low
r = store.validate_daily_data(bad_df)
assert not r['is_valid'], '异常数据应该不通过验证'
assert any('high < low' in e for e in r['errors'])
print('异常数据检测: PASS')

print('validate_daily_data 向量化验证通过')
"
```
Expected: 三个 PASS

- [ ] **Step 3: 提交**

```bash
git add src/data/local_store.py
git commit -m "perf: validate_daily_data 从逐行 iterrows 改为向量化操作"
```

---

### Task 5: 端到端验证

- [ ] **Step 1: 验证 strategy_runner 多进程 import 正常**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
from engine.strategy_runner import StrategyRunner, _worker_process_stock
print('多进程 worker 函数 import OK')
"
```
Expected: `多进程 worker 函数 import OK`

- [ ] **Step 2: 最终提交**

```bash
git status
git add -A
git commit -m "chore: Spec 3 完成 — 性能优化"
```
