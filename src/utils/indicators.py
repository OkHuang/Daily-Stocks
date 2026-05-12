"""技术指标计算模块，使用 Pandas 实现常用指标，不依赖 TA-Lib。"""

import pandas as pd
import numpy as np
from typing import Union, Tuple


def calculate_ma(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """计算简单移动平均线"""
    return df[column].rolling(window=period).mean()


def calculate_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """计算指数移动平均线"""
    return df[column].ewm(span=period, adjust=False).mean()


def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
    """计算相对强弱指标 (RSI)，使用 Wilder's 指数加权平均法"""
    # 计算价格变化
    delta = df[column].diff()

    # 分离上涨和下跌
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # Wilder's 使用指数加权平均，alpha = 1/period
    alpha = 1 / period
    avg_gains = gains.ewm(alpha=alpha, adjust=False).mean()
    avg_losses = losses.ewm(alpha=alpha, adjust=False).mean()

    # 计算 RS 和 RSI
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
    """计算 MACD 指标，返回 (DIF, DEA, MACD柱状图)"""
    # 计算快速和慢速 EMA
    ema_fast = calculate_ema(df, fast_period, column)
    ema_slow = calculate_ema(df, slow_period, column)

    # 计算 DIF (差离值/快线)
    dif = ema_fast - ema_slow

    # 计算 DEA (信号线/慢线)
    dea = dif.ewm(span=signal_period, adjust=False).mean()

    # 计算 MACD 柱状图
    macd = (dif - dea) * 2

    return dif, dea, macd


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    column: str = 'close'
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算布林带，返回 (上轨, 中轨, 下轨)"""
    # 计算中轨（移动平均）
    middle_band = calculate_ma(df, period, column)

    # 计算标准差
    std = df[column].rolling(window=period).std()

    # 计算上轨和下轨
    upper_band = middle_band + std_dev * std
    lower_band = middle_band - std_dev * std

    return upper_band, middle_band, lower_band


def calculate_kdj(
    df: pd.DataFrame,
    n_period: int = 9,
    m1_period: int = 3,
    m2_period: int = 3
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算 KDJ 指标，同花顺标准参数 KDJ(9,3,3)"""
    # 计算 RSV (未成熟随机值)
    low_min = df['low'].rolling(window=n_period).min()
    high_max = df['high'].rolling(window=n_period).max()

    # 避免除零错误：当最高价等于最低价时 RSV 设为 0
    price_range = high_max - low_min
    rsv = ((df['close'] - low_min) / price_range.replace(0, np.nan) * 100).fillna(0)

    # 计算 K 值: K = K_昨日 × (m1-1)/m1 + RSV_今日 × 1/m1
    k = rsv.ewm(alpha=1/m1_period, adjust=False).mean()

    # 计算 D 值: D = D_昨日 × (m2-1)/m2 + K_今日 × 1/m2
    d = k.ewm(alpha=1/m2_period, adjust=False).mean()

    # 计算 J 值
    j = 3 * k - 2 * d

    return k, d, j


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算平均真实波幅 (ATR)"""
    # 计算真实波幅的三个分量
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())

    # 取三个值中的最大值作为 TR（转换为 Series 保持索引）
    tr = pd.Series(
        np.maximum.reduce([high_low, high_close, low_close]),
        index=df.index
    )

    # 计算 ATR
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
    """计算 BBI 多空指标，同花顺标准参数 BBI(3,6,12,24)"""
    # 计算四个不同周期的移动平均线
    ma1 = calculate_ma(df, period=p1, column=column)
    ma2 = calculate_ma(df, period=p2, column=column)
    ma3 = calculate_ma(df, period=p3, column=column)
    ma4 = calculate_ma(df, period=p4, column=column)

    # 计算 BBI（四条均线的平均值）
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
    计算知行多空线

    与 BBI 的区别：BBI 使用 (3,6,12,24) 偏短期，知行多空线使用 (14,28,57,114) 偏中长期。
    价格 > 多空线为多头市场，价格 < 多空线为空头市场。
    """
    # 计算四个不同周期的移动平均线
    ma1 = calculate_ma(df, period=p1, column=column)
    ma2 = calculate_ma(df, period=p2, column=column)
    ma3 = calculate_ma(df, period=p3, column=column)
    ma4 = calculate_ma(df, period=p4, column=column)

    # 计算知行多空线（四条均线的平均值）
    bull_bear_line = (ma1 + ma2 + ma3 + ma4) / 4

    return bull_bear_line
