"""
技术指标计算模块 - Technical Indicators Module

该模块使用 Pandas 实现常用技术指标的计算，不依赖 TA-Lib。
This module implements common technical indicators using Pandas, without TA-Lib dependency.
"""

import pandas as pd
import numpy as np
from typing import Union, Tuple


def calculate_ma(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """
    计算简单移动平均线 (Simple Moving Average, SMA/MA)

    参数 (Parameters):
        df: 包含价格数据的 DataFrame (DataFrame containing price data)
        period: 均线周期 (MA period)
        column: 价格列名 (Price column name)

    返回 (Returns):
        pd.Series: 移动平均线序列 (Moving average series)
    """
    return df[column].rolling(window=period).mean()


def calculate_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """
    计算指数移动平均线 (Exponential Moving Average, EMA)

    参数 (Parameters):
        df: 包含价格数据的 DataFrame (DataFrame containing price data)
        period: 均线周期 (EMA period)
        column: 价格列名 (Price column name)

    返回 (Returns):
        pd.Series: 指数移动平均线序列 (EMA series)
    """
    return df[column].ewm(span=period, adjust=False).mean()


def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
    """
    计算相对强弱指标 (Relative Strength Index, RSI)

    RSI = 100 - (100 / (1 + RS))
    其中 RS = 平均上涨幅度 / 平均下跌幅度
    Where RS = Average gain / Average loss

    参数 (Parameters):
        df: 包含价格数据的 DataFrame (DataFrame containing price data)
        period: RSI 计算周期 (RSI calculation period)
        column: 价格列名 (Price column name)

    返回 (Returns):
        pd.Series: RSI 值序列 (RSI value series)
    """
    # 计算价格变化
    # Calculate price changes
    delta = df[column].diff()

    # 分离上涨和下跌
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # Wilder's 使用指数加权平均，alpha = 1/period
    alpha = 1 / period
    avg_gains = gains.ewm(alpha=alpha, adjust=False).mean()
    avg_losses = losses.ewm(alpha=alpha, adjust=False).mean()

    # 计算 RS 和 RSI
    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    column: str = 'close'
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算 MACD 指标 (Moving Average Convergence Divergence)

    参数 (Parameters):
        df: 包含价格数据的 DataFrame (DataFrame containing price data)
        fast_period: 快线周期，默认 12 (Fast line period, default 12)
        slow_period: 慢线周期，默认 26 (Slow line period, default 26)
        signal_period: 信号线周期，默认 9 (Signal line period, default 9)
        column: 价格列名 (Price column name)

    返回 (Returns):
        Tuple[pd.Series, pd.Series, pd.Series]: (DIF, DEA, MACD柱状图) (DIF, DEA, MACD Histogram)
    """
    # 计算快速和慢速 EMA
    # Calculate fast and slow EMAs
    ema_fast = calculate_ema(df, fast_period, column)
    ema_slow = calculate_ema(df, slow_period, column)

    # 计算 DIF (差离值/快线)
    # Calculate DIF (Difference/Fast Line)
    dif = ema_fast - ema_slow

    # 计算 DEA (信号线/慢线)
    # Calculate DEA (Signal/Slow Line)
    dea = dif.ewm(span=signal_period, adjust=False).mean()

    # 计算 MACD 柱状图
    # Calculate MACD Histogram
    macd = (dif - dea) * 2

    return dif, dea, macd


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    column: str = 'close'
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算布林带 (Bollinger Bands)

    中轨 = MA(period)
    上轨 = 中轨 + std_dev * 标准差
    下轨 = 中轨 - std_dev * 标准差
    Middle Band = MA(period)
    Upper Band = Middle Band + std_dev * Std Dev
    Lower Band = Middle Band - std_dev * Std Dev

    参数 (Parameters):
        df: 包含价格数据的 DataFrame (DataFrame containing price data)
        period: 均线周期 (MA period)
        std_dev: 标准差倍数 (Standard deviation multiplier)
        column: 价格列名 (Price column name)

    返回 (Returns):
        Tuple[pd.Series, pd.Series, pd.Series]: (上轨, 中轨, 下轨) (Upper, Middle, Lower)
    """
    # 计算中轨（移动平均）
    # Calculate middle band (moving average)
    middle_band = calculate_ma(df, period, column)

    # 计算标准差
    # Calculate standard deviation
    std = df[column].rolling(window=period).std()

    # 计算上轨和下轨
    # Calculate upper and lower bands
    upper_band = middle_band + std_dev * std
    lower_band = middle_band - std_dev * std

    return upper_band, middle_band, lower_band


def calculate_kdj(
    df: pd.DataFrame,
    n_period: int = 9,
    m1_period: int = 3,
    m2_period: int = 3
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算 KDJ 指标 (Stochastic Oscillator)

    参数 (Parameters):
        df: 包含 OHLC 价格数据的 DataFrame (DataFrame containing OHLC price data)
        n_period: RSV 计算周期，默认 9 (RSV calculation period, default 9)
        m1_period: K 值平滑周期，默认 3 (K smoothing period, default 3)
        m2_period: D 值平滑周期，默认 3 (D smoothing period, default 3)

    返回 (Returns):
        Tuple[pd.Series, pd.Series, pd.Series]: (K, D, J)

    示例 (Example):
        >>> k, d, j = calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)
        >>> # 同花顺标准参数 KDJ(9,3,3)
    """
    # 计算 RSV (未成熟随机值)
    # Calculate RSV (Raw Stochastic Value)
    low_min = df['low'].rolling(window=n_period).min()
    high_max = df['high'].rolling(window=n_period).max()

    # 计算价格区间，避免除零错误
    # Calculate price range, avoid division by zero
    price_range = high_max - low_min

    # 当最高价等于最低价时，RSV 设为 0
    rsv = ((df['close'] - low_min) / price_range.replace(0, np.nan) * 100).fillna(0)

    # 计算 K 值 (使用 m1_period 对 RSV 进行平滑)
    # 使用公式: K = K_昨日 × (m1-1)/m1 + RSV_今日 × 1/m1
    k = rsv.ewm(alpha=1/m1_period, adjust=False).mean()

    # 计算 D 值 (使用 m2_period 对 K 进行平滑)
    # 使用公式: D = D_昨日 × (m2-1)/m2 + K_今日 × 1/m2
    d = k.ewm(alpha=1/m2_period, adjust=False).mean()

    # 计算 J 值
    j = 3 * k - 2 * d

    return k, d, j


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    计算平均真实波幅 (Average True Range, ATR)

    TR = max(高-低, |高-昨收|, |低-昨收|)
    ATR = MA(TR, period)

    参数 (Parameters):
        df: 包含 OHLC 价格数据的 DataFrame (DataFrame containing OHLC price data)
        period: ATR 计算周期 (ATR calculation period)

    返回 (Returns):
        pd.Series: ATR 值序列 (ATR value series)
    """
    # 计算真实波幅 (True Range)
    # Calculate True Range
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())

    # 取三个值中的最大值作为 TR（转换为 Series 保持索引）
    # Take the maximum of the three values as TR (convert to Series to keep index)
    tr = pd.Series(
        np.maximum.reduce([high_low, high_close, low_close]),
        index=df.index
    )

    # 计算 ATR
    # Calculate ATR
    atr = tr.rolling(window=period).mean()

    return atr


def calculate_bbi(
    df: pd.DataFrame,
    p1: int = 3,
    p2: int = 6,
    p3: int = 12,
    p4: int = 24,
    column: str = 'close'
) -> pd.Series:
    """
    计算 BBI 多空指标 (Bull and Bear Index)

    返回 (Returns):
        pd.Series: BBI 值序列 (BBI value series)

    示例 (Example):
        >>> bbi = calculate_bbi(df, p1=3, p2=6, p3=12, p4=24)
        >>> # 同花顺标准参数 BBI(3,6,12,24)
    """
    # 计算四个不同周期的移动平均线
    # Calculate four moving averages with different periods
    ma1 = calculate_ma(df, period=p1, column=column)
    ma2 = calculate_ma(df, period=p2, column=column)
    ma3 = calculate_ma(df, period=p3, column=column)
    ma4 = calculate_ma(df, period=p4, column=column)

    # 计算 BBI（四条均线的平均值）
    # Calculate BBI (average of four MAs)
    bbi = (ma1 + ma2 + ma3 + ma4) / 4

    return bbi


def calculate_zhixing_short_trend(
    df: pd.DataFrame,
    period: int = 10,
    column: str = 'close'
) -> pd.Series:
    """计算知行短期趋势线（双重 EMA）"""
    ema1 = df[column].ewm(span=period, adjust=False).mean()
    trend = ema1.ewm(span=period, adjust=False).mean()
    return trend


def calculate_zhixing_bull_bear(
    df: pd.DataFrame,
    p1: int = 14,
    p2: int = 28,
    p3: int = 57,
    p4: int = 114,
    column: str = 'close'
) -> pd.Series:
    """
    计算知行多空线 (Zhixing Bull and Bear Line)

    知行多空线是多个不同周期移动平均线的平均值，类似于 BBI 指标。
    Zhixing bull and bear line is the average of multiple MAs with different periods,
    similar to the BBI indicator.

    计算公式 (Formula):
        知行多空线 = (MA(p1) + MA(p2) + MA(p3) + MA(p4)) / 4
        Bull Bear Line = (MA14 + MA28 + MA57 + MA114) / 4

    与 BBI 的区别 (Difference from BBI):
        - BBI 使用 (3, 6, 12, 24) 周期，更偏短期
        - 知行多空线使用 (14, 28, 57, 114) 周期，更偏中长期
        - 适合判断中长期多空趋势 (Suitable for medium-to-long term trend)

    使用方法 (Usage):
        - 价格 > 知行多空线: 多头市场 (Price above line: bullish)
        - 价格 < 知行多空线: 空头市场 (Price below line: bearish)

    参数 (Parameters):
        df: 包含价格数据的 DataFrame (DataFrame containing price data)
        p1: 第一条均线周期，默认 14 (First MA period, default 14)
        p2: 第二条均线周期，默认 28 (Second MA period, default 28)
        p3: 第三条均线周期，默认 57 (Third MA period, default 57)
        p4: 第四条均线周期，默认 114 (Fourth MA period, default 114)
        column: 价格列名 (Price column name)

    返回 (Returns):
        pd.Series: 知行多空线序列 (Zhixing bull and bear line series)

    示例 (Example):
        >>> zb_line = calculate_zhixing_bull_bear(df, p1=14, p2=28, p3=57, p4=114)
        >>> # (MA14 + MA28 + MA57 + MA114) / 4
    """
    # 计算四个不同周期的移动平均线
    # Calculate four moving averages with different periods
    ma1 = calculate_ma(df, period=p1, column=column)
    ma2 = calculate_ma(df, period=p2, column=column)
    ma3 = calculate_ma(df, period=p3, column=column)
    ma4 = calculate_ma(df, period=p4, column=column)

    # 计算知行多空线（四条均线的平均值）
    # Calculate Zhixing bull and bear line (average of four MAs)
    bull_bear_line = (ma1 + ma2 + ma3 + ma4) / 4

    return bull_bear_line
