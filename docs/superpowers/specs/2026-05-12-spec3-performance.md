# Spec 3: 性能优化

日期: 2026-05-12
父文档: [2026-05-12-deep-optimization-design.md](2026-05-12-deep-optimization-design.md) 第四部分 + 第三部分 3.2

## 依赖关系

- **前置依赖**: Spec 2（strategy_runner.py 中的 bug 必须先修复，否则会基于错误代码做性能重构）
- **后续影响**: Spec 4 的代码清理会在此基础上精简注释和 docstring

## 范围

多进程并行、向量化验证、消除不必要的拷贝。

## 变更清单

### 3.1 并行策略改为多进程

- **文件**: `src/engine/strategy_runner.py`
- **当前状态**（Spec 2 完成后）: `strategy_registry` 已补全，bug 5/6/7 已修复，`_precompute_indicators` 的 MACD/KDJ 调用已正确
- **变更**:
  - `ThreadPoolExecutor` 改为 `ProcessPoolExecutor`
  - **SQLite 跨进程方案**: SQLite 连接不能序列化，多进程并发写会 `database is locked`
    - 新增 `_preload_stock_data(stock_list, local_store) -> Dict[str, pd.DataFrame]` 方法：在主进程中遍历 stock_list，从 local_store 加载所有 DataFrame
    - `run()` 方法：先调用 `_preload_stock_data` 预加载，再提交给进程池
    - `_run_single_stock` 改为静态方法或模块级函数（ProcessPoolExecutor 需要 pickle），签名改为 `(stock_code: str, df: pd.DataFrame, strategies_config: dict) -> Dict[str, float]`，不再接收 `local_store` 和 `fetcher`
    - 子进程中数据不足 50 条时跳过并返回空 dict
    - 删除 `_indicator_cache` 及其 `clear()` 调用
  - Worker 数量: `min(os.cpu_count() or 1, 4)`
  - import 改为 `from concurrent.futures import ProcessPoolExecutor, as_completed`
  - **子进程 import 路径**: 子进程是独立 Python 进程，不继承 `sys.path`。模块级函数内部需设置路径：
    ```python
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
    ```
  - **策略实例化**: 策略类只持有 `name` 和 `params` dict，可 pickle。最简方案：将 strategies.yaml 路径传给子进程，子进程自行加载和实例化策略（复用 `_load_strategies` 逻辑）。

### 3.2 validate_daily_data 向量化

- **文件**: `src/data/local_store.py` 的 `validate_daily_data` 方法
- **变更**:
  - 删除整个 `for idx, row in df.iterrows()` 循环（行 529-586）
  - 用向量化操作替换：
    ```python
    price_cols = ['open', 'high', 'low', 'close']
    volume_cols = ['vol', 'amount']
    all_cols = price_cols + volume_cols

    # 负数检查
    neg_mask = df[all_cols] < 0
    for col in all_cols:
        neg_count = neg_mask[col].sum()
        if neg_count > 0:
            result['errors'].append(f"{col} 存在 {neg_count} 行负数值")

    # 价格逻辑检查（需排除 NaN 行，NaN 比较结果为 False 不会误报，
    # 但用 notna 过滤更明确）
    valid = df[['high', 'low', 'open', 'close']].notna().all(axis=1)
    df_valid = df[valid]
    logic_errors = []
    if (df_valid['high'] < df_valid['low']).any():
        logic_errors.append(f"{(df_valid['high'] < df_valid['low']).sum()} 行 high < low")
    if (df_valid['high'] < df_valid['open']).any():
        logic_errors.append(f"{(df_valid['high'] < df_valid['open']).sum()} 行 high < open")
    # ... 其他逻辑（high < close, low > open, low > close）
    if logic_errors:
        result['is_valid'] = False
        result['errors'].extend(logic_errors)

    # 缺失值统计（按行汇总）
    missing_per_row = df[all_cols].isna().sum(axis=1)
    all_nan_count = (missing_per_row == 6).sum()
    partial_nan_count = ((missing_per_row > 0) & (missing_per_row < 6)).sum()
    # 生成汇总警告而非逐行记录
    ```
  - 错误格式从逐行记录改为按类型汇总（如"3 行存在 high < low"）
  - 重复检查保持不变（已经是向量化的）

### 3.3 删除不必要的 DataFrame 拷贝

- `src/engine/strategy_runner.py:107`: 删除 `df = df.copy()`（每只股票数据已独立加载，无需拷贝）
- `src/utils/indicators.py` 的 `calculate_zhixing_short_trend`（行 310-321）：
  ```python
  # 修改前（创建临时 DataFrame）
  temp_df = df.copy()
  temp_df['__ema1__'] = ema1
  trend = calculate_ema(temp_df, period=period, column='__ema1__')

  # 修改后（直接在 Series 上操作）
  ema1 = df[column].ewm(span=period, adjust=False).mean()
  trend = ema1.ewm(span=period, adjust=False).mean()
  ```

## 涉及文件

| 文件 | 操作 |
|------|------|
| `src/engine/strategy_runner.py` | 3.1（多进程重构）, 3.3（删 copy） |
| `src/data/local_store.py` | 3.2（向量化验证） |
| `src/utils/indicators.py` | 3.3（删 copy） |

## 与其他 Spec 的交叉文件

- `src/engine/strategy_runner.py`: Spec 2 修复了 bug，本 spec 重构并行逻辑。顺序：先 Spec 2 再本 spec。
- `src/data/local_store.py`: 仅本 spec 修改。Spec 2 不涉及此文件。
- `src/utils/indicators.py`: 仅本 spec 修改。
