# 技术指标模块文档

## 概述

本模块实现了常用的股票技术分析指标，不依赖 TA-Lib，使用 Pandas 和 NumPy 进行计算。

**模块路径**: `src/utils/indicators.py`

---

## 指标列表

### 1. 移动平均线 (MA)

**函数**: `calculate_ma(df, period, column='close')`

**说明**: 简单移动平均线（Simple Moving Average, SMA），计算指定周期内价格的平均值。

**计算公式**:
```
MA = (P1 + P2 + ... + Pn) / n
```

**参数**:
- `df`: 包含价格数据的 DataFrame
- `period`: 均线周期（如 5, 10, 20, 60）
- `column`: 价格列名，默认为 'close'

**返回**: pd.Series

**使用示例**:
```python
# 计算 5 日均线
ma5 = calculate_ma(df, period=5)

# 计算 20 日均线
ma20 = calculate_ma(df, period=20)
```

**应用场景**:
- MA5: 短期趋势
- MA10: 短期趋势
- MA20: 月线中期趋势
- MA60: 季线长期趋势

---

### 2. 指数移动平均线 (EMA)

**函数**: `calculate_ema(df, period, column='close')`

**说明**: 指数移动平均线（Exponential Moving Average），给予近期数据更高权重。

**计算公式**:
```
EMA今日 = EMA昨日 × (1 - α) + 价格今日 × α
其中 α = 2 / (period + 1)
```

**参数**:
- `df`: 包含价格数据的 DataFrame
- `period`: EMA 周期（如 12, 26）
- `column`: 价格列名，默认为 'close'

**返回**: pd.Series

**使用示例**:
```python
# 计算 12 日 EMA
ema12 = calculate_ema(df, period=12)

# 计算 26 日 EMA
ema26 = calculate_ema(df, period=26)
```

**特点**:
- 比 SMA 反应更快
- 近期数据权重更高
- 适合趋势跟踪

---

### 3. 相对强弱指标 (RSI)

**函数**: `calculate_rsi(df, period=14, column='close')`

**说明**: RSI（Relative Strength Index）衡量价格变动的速度和幅度，用于判断超买超卖。

**计算公式**:
```
RSI = 100 - (100 / (1 + RS))

其中:
RS = 平均上涨幅度 / 平均下跌幅度
```

使用 **Wilder's Smoothing** 方法计算平均值。

**参数**:
- `df`: 包含价格数据的 DataFrame
- `period`: RSI 计算周期，默认 14
- `column`: 价格列名，默认为 'close'

**返回**: pd.Series

**使用示例**:
```python
# 计算 14 日 RSI（标准）
rsi14 = calculate_rsi(df, period=14)

# 计算 6 日 RSI（短线）
rsi6 = calculate_rsi(df, period=6)

# 计算 24 日 RSI（长线）
rsi24 = calculate_rsi(df, period=24)
```

**读数范围**:
- **RSI > 70**: 超买区域，价格可能回调
- **RSI < 30**: 超卖区域，价格可能反弹
- **RSI = 50**: 多空平衡点

**交易信号**:
- 顶背离: 价格创新高但 RSI 未创新高 → 看跌
- 底背离: 价格创新低但 RSI 未创新低 → 看涨

---

### 4. MACD 指标

**函数**: `calculate_macd(df, fast_period=12, slow_period=26, signal_period=9, column='close')`

**说明**: MACD（Moving Average Convergence Divergence）趋势跟踪动量指标。

**计算公式**:
```
DIF (快线)  = EMA(12) - EMA(26)
DEA (信号线) = EMA(DIF, 9)
MACD (柱状图) = (DIF - DEA) × 2
```

**参数**:
- `df`: 包含价格数据的 DataFrame
- `fast_period`: 快线周期，默认 12
- `slow_period`: 慢线周期，默认 26
- `signal_period`: 信号线周期，默认 9
- `column`: 价格列名，默认为 'close'

**返回**: Tuple[pd.Series, pd.Series, pd.Series] - (DIF, DEA, MACD柱状图)

**使用示例**:
```python
# 计算标准 MACD(12, 26, 9)
dif, dea, macd = calculate_macd(df)

# 添加到 DataFrame
df['DIF'] = dif
df['DEA'] = dea
df['MACD'] = macd
```

**交易信号**:

**金叉（买入信号）**:
```python
# DIF 上穿 DEA
if (df['DIF'] > df['DEA']) & (df['DIF'].shift(1) <= df['DEA'].shift(1)):
    # 金叉，买入信号
    pass
```

**死叉（卖出信号）**:
```python
# DIF 下穿 DEA
if (df['DIF'] < df['DEA']) & (df['DIF'].shift(1) >= df['DEA'].shift(1)):
    # 死叉，卖出信号
    pass
```

**背离信号**:
- 顶背离: 价格新高但 DIF 未新高 → 看跌
- 底背离: 价格新低但 DIF 未新低 → 看涨

---

### 5. 布林带 (Bollinger Bands)

**函数**: `calculate_bollinger_bands(df, period=20, std_dev=2.0, column='close')`

**说明**: 布林带是基于统计学的波动率指标，由上轨、中轨、下轨组成。

**计算公式**:
```
中轨 = MA(period)
标准差 = STD(period)
上轨 = 中轨 + std_dev × 标准差
下轨 = 中轨 - std_dev × 标准差
```

**参数**:
- `df`: 包含价格数据的 DataFrame
- `period`: 均线周期，默认 20
- `std_dev`: 标准差倍数，默认 2.0
- `column`: 价格列名，默认为 'close'

**返回**: Tuple[pd.Series, pd.Series, pd.Series] - (上轨, 中轨, 下轨)

**使用示例**:
```python
# 计算标准布林带(20, 2)
upper, middle, lower = calculate_bollinger_bands(df)

# 计算带宽
bandwidth = (upper - lower) / middle * 100

# 计算价格在布林带中的位置
position = (close - lower) / (upper - lower) * 100
```

**应用场景**:

**1. 判断超买超卖**:
```python
# 价格触及上轨 → 超买
if close > upper:
    # 可能回调
    pass

# 价格触及下轨 → 超卖
if close < lower:
    # 可能反弹
    pass
```

**2. 判断波动率**:
```python
# 带宽收窄 → 可能突破
if bandwidth < threshold:
    # 注意突破机会
    pass

# 带宽扩大 → 高波动
if bandwidth > threshold:
    # 波动剧烈
    pass
```

**3. 价格挤压（突破前兆）**:
```
当布林带持续收窄时，表示市场在积蓄能量，
可能在近期发生方向性突破。
```

---

### 6. KDJ 指标

**函数**: `calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)`

**说明**: KDJ（Stochastic Oscillator）随机指标，是超买超卖类指标的代表。

**计算公式**:
```
RSV = (收盘价 - N日最低价) / (N日最高价 - N日最低价) × 100
K = RSV的m1日移动平均
D = K的m2日移动平均
J = 3 × K - 2 × D
```

**同花顺标准参数**: KDJ(9, 3, 3)

**参数**:
- `df`: 包含 OHLC 价格数据的 DataFrame
- `n_period`: RSV 计算周期，默认 9
- `m1_period`: K 值平滑周期，默认 3
- `m2_period`: D 值平滑周期，默认 3

**返回**: Tuple[pd.Series, pd.Series, pd.Series] - (K, D, J)

**使用示例**:
```python
# 计算标准 KDJ(9, 3, 3)
k, d, j = calculate_kdj(df)

# 自定义参数 KDJ(14, 3, 3)
k, d, j = calculate_kdj(df, n_period=14, m1_period=3, m2_period=3)
```

**读数范围**:
- **K/D > 80**: 超买区
- **K/D < 20**: 超卖区
- **J > 100 或 J < 0**: 极端值区域

**交易信号**:

**金叉**:
```python
# K 上穿 D，买入信号
if (k > d) & (k.shift(1) <= d.shift(1)):
    pass
```

**死叉**:
```python
# K 下穿 D，卖出信号
if (k < d) & (k.shift(1) >= d.shift(1)):
    pass
```

**特点**:
- 比 RSI 更敏感，适合短线交易
- J 值可以超前预警
- 在震荡市场效果最好

---

### 7. 平均真实波幅 (ATR)

**函数**: `calculate_atr(df, period=14)`

**说明**: ATR（Average True Range）衡量市场波动的剧烈程度，不考虑价格方向，只关注波动幅度。

**计算公式**:
```
TR = max(高-低, |高-昨收|, |低-昨收|)
ATR = MA(TR, period)
```

TR（True Range）真实波幅考虑了跳空缺口。

**参数**:
- `df`: 包含 OHLC 价格数据的 DataFrame
- `period`: ATR 计算周期，默认 14

**返回**: pd.Series

**使用示例**:
```python
# 计算 14 日 ATR（标准）
atr = calculate_atr(df, period=14)

# 计算 7 日 ATR（更敏感）
atr7 = calculate_atr(df, period=7)
```

**应用场景**:

**1. 设置止损位**:
```python
# ATR 止损策略
stop_loss = entry_price - atr * 2  # 2倍 ATR 作为止损
```

**2. 仓位管理**:
```python
# 根据波动率调整仓位
atr = calculate_atr(df, 14)
risk_per_share = atr * 2
account_risk = 1000
position_size = account_risk / risk_per_share
```

**3. 判断波动率**:
```python
# ATR 异常高 → 市场处于恐慌或狂热状态
if atr > atr.rolling(50).mean() * 1.5:
    pass
```

**特点**:
- ATR 值越大 → 市场波动越剧烈
- ATR 值越小 → 市场越平静
- 适合用于止损和仓位管理

---

### 8. BBI 多空指标

**函数**: `calculate_bbi(df, p1=3, p2=6, p3=12, p4=24, column='close')`

**说明**: BBI（Bull and Bear Index）多空指标，将多条不同周期的移动平均线综合为一个指标。

**计算公式**:
```
BBI = (MA(p1) + MA(p2) + MA(p3) + MA(p4)) / 4
```

**同花顺标准参数**: BBI(3, 6, 12, 24)

**参数**:
- `df`: 包含价格数据的 DataFrame
- `p1`: 第一条均线周期，默认 3
- `p2`: 第二条均线周期，默认 6
- `p3`: 第三条均线周期，默认 12
- `p4`: 第四条均线周期，默认 24
- `column`: 价格列名，默认为 'close'

**返回**: pd.Series

**使用示例**:
```python
# 计算标准 BBI(3, 6, 12, 24)
bbi = calculate_bbi(df)
```

**使用方法**:

**判断多空趋势**:
```python
# 价格 > BBI → 多头市场
if close > bbi:
    # 看涨
    pass

# 价格 < BBI → 空头市场
if close < bbi:
    # 看跌
    pass
```

**买卖信号**:
```python
# 价格上穿 BBI → 买入信号
if (close > bbi) & (close.shift(1) <= bbi.shift(1)):
    pass

# 价格下穿 BBI → 卖出信号
if (close < bbi) & (close.shift(1) >= bbi.shift(1)):
    pass
```

**特点**:
- 综合性强，整合多周期趋势
- 比单条均线更稳定
- 适合判断大趋势
- 滞后性依然存在

---

### 9. 知行短期趋势线

**函数**: `calculate_zhixing_short_trend(df, period=10, column='close')`

**说明**: 知行短期趋势线是双重指数移动平均线，对价格进行两次平滑。

**计算公式**:
```
知行短期趋势线 = EMA(EMA(收盘价, period), period)
```

**参数**:
- `df`: 包含价格数据的 DataFrame
- `period`: EMA 周期，默认 10
- `column`: 价格列名，默认为 'close'

**返回**: pd.Series

**使用示例**:
```python
# 计算知行短期趋势线 EMA(EMA, 10)
trend = calculate_zhixing_short_trend(df, period=10)
```

**特点**:
- 比单次 EMA 更平滑
- 滞后性稍大，但更稳定
- 适合识别短期趋势方向
- 过滤短期噪音

---

### 10. 知行多空线

**函数**: `calculate_zhixing_bull_bear(df, p1=14, p2=28, p3=57, p4=114, column='close')`

**说明**: 知行多空线是多个不同周期移动平均线的平均值，类似于 BBI 指标，但周期更长。

**计算公式**:
```
知行多空线 = (MA(p1) + MA(p2) + MA(p3) + MA(p4)) / 4
```

**标准参数**: (14, 28, 57, 114)

**参数**:
- `df`: 包含价格数据的 DataFrame
- `p1`: 第一条均线周期，默认 14
- `p2`: 第二条均线周期，默认 28
- `p3`: 第三条均线周期，默认 57
- `p4`: 第四条均线周期，默认 114
- `column`: 价格列名，默认为 'close'

**返回**: pd.Series

**使用示例**:
```python
# 计算知行多空线 (14, 28, 57, 114)
bull_bear_line = calculate_zhixing_bull_bear(df)
```

**与 BBI 的区别**:
- BBI 使用 (3, 6, 12, 24) 周期，更偏短期
- 知行多空线使用 (14, 28, 57, 114) 周期，更偏中长期
- 适合判断中长期多空趋势

**使用方法**:
```python
# 价格 > 知行多空线 → 多头市场
if close > bull_bear_line:
    pass

# 价格 < 知行多空线 → 空头市场
if close < bull_bear_line:
    pass
```

---

## 指标分类总结

### 趋势指标
- **MA** - 简单移动平均线
- **EMA** - 指数移动平均线
- **MACD** - 异同移动平均线
- **BBI** - 多空指标
- **知行短期趋势线** - 双重 EMA
- **知行多空线** - 中长期多空指标

### 超买超卖指标
- **RSI** - 相对强弱指标
- **KDJ** - 随机指标

### 波动率指标
- **布林带** - Bollinger Bands
- **ATR** - 平均真实波幅

---

## 组合使用建议

### 1. 趋势 + 超买超卖

```python
# MACD + RSI
if macd金叉 and rsi < 70:
    # 强买入信号
    pass

if macd死叉 and rsi > 30:
    # 强卖出信号
    pass
```

### 2. 趋势 + 波动率

```python
# 布林带 + MACD
if price突破上轨 and macd > 0:
    # 有效突破，买入
    pass
```

### 3. 多周期确认

```python
# 短期 + 中长期
if (close > 知行短期趋势线) and (close > 知行多空线):
    # 短期和中长期都看涨
    pass
```

### 4. 动态止损

```python
# ATR 动态止损
atr = calculate_atr(df, 14)
stop_loss = entry_price - atr * 2
```

---

## 注意事项

1. **滞后性**: 所有基于均线的指标都存在滞后性
2. **假信号**: 震荡市场容易产生假信号
3. **参数优化**: 不同股票和不同市场环境需要调整参数
4. **综合判断**: 不要单独依赖某一个指标
5. **风险控制**: 始终设置止损，控制风险

---

## 测试脚本

项目提供了完整的测试脚本，位于 `test/test_indicators.py`。

**运行测试**:
```bash
# 测试单只股票
python test/test_indicators.py --stock 000001.SZ

# 测试多只股票
python test/test_indicators.py --stock 000001.SZ,000002.SZ

# 显示最近30天数据
python test/test_indicators.py --stock 000001.SZ --days 30

# 导出数据为CSV
python test/test_indicators.py --stock 000001.SZ --export indicators.csv

# 查看数据库统计信息
python test/test_indicators.py --stats
```

---

## 代码示例

### 基础使用

```python
from src.utils.indicators import *

# 计算移动平均线
ma5 = calculate_ma(df, 5)
ma20 = calculate_ma(df, 20)

# 计算 RSI
rsi14 = calculate_rsi(df, 14)

# 计算 MACD
dif, dea, macd = calculate_macd(df)

# 计算 KDJ
k, d, j = calculate_kdj(df)
```

### 完整策略示例

```python
import pandas as pd
from src.utils.indicators import *

# 计算所有指标
df['ma5'] = calculate_ma(df, 5)
df['ma20'] = calculate_ma(df, 20)
df['ma60'] = calculate_ma(df, 60)
df['rsi14'] = calculate_rsi(df, 14)
df['dif'], df['dea'], df['macd'] = calculate_macd(df)
df['k'], df['d'], df['j'] = calculate_kdj(df)
df['bbi'] = calculate_bbi(df)

# 生成交易信号
df['signal'] = 0

# 均线多头排列
df.loc[(df['ma5'] > df['ma20']) & (df['ma20'] > df['ma60']), 'signal'] += 1

# RSI 不超买
df.loc[df['rsi14'] < 70, 'signal'] += 1

# MACD 金叉
df.loc[(df['dif'] > df['dea']) & (df['dif'].shift(1) <= df['dea'].shift(1)), 'signal'] += 2

# 综合信号
df['buy_signal'] = df['signal'] >= 3
df['sell_signal'] = df['signal'] <= 0
```

---

**最后更新**: 2026-02-20

**版本**: 1.0.0
