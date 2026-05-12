"""多指标组合策略

策略条件：
    1. 最近60天内波动幅度 <= 100%
    2. BBI持续上升
    3. 当前日J值 < -1
    4. 当前日DIF > 0
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import Strategy


class MultiIndicatorComboStrategy(Strategy):
    """综合波动率、BBI、KDJ和MACD多指标选股"""

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'volatility_period': 60,
            'volatility_threshold': 100.0,  # 100%
            'bbi_p1': 3,
            'bbi_p2': 6,
            'bbi_p3': 12,
            'bbi_p4': 24,
            'bbi_rising_days': 3,
            'kdj_n_period': 9,
            'kdj_m1_period': 3,
            'kdj_m2_period': 3,
            'j_threshold': -1,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'weight': 1.0
        }
        if params:
            default_params.update(params)
        super().__init__(name="Multi-Indicator Combo", params=default_params)

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        # 获取参数
        volatility_period = self.params['volatility_period']
        volatility_threshold = self.params['volatility_threshold']
        bbi_p1 = self.params['bbi_p1']
        bbi_p2 = self.params['bbi_p2']
        bbi_p3 = self.params['bbi_p3']
        bbi_p4 = self.params['bbi_p4']
        bbi_rising_days = self.params['bbi_rising_days']
        j_threshold = self.params['j_threshold']
        weight = self.params.get('weight', 1.0)

        # 确保 DataFrame 按日期升序排列
        df = df.sort_values('trade_date').reset_index(drop=True)

        # 数据不足时返回全0信号
        min_required = max(volatility_period, bbi_p4, self.params['macd_slow'])
        if len(df) < min_required:
            return pd.Series(0.0, index=df['trade_date'])

        # 计算各项指标
        df = self._calculate_indicators(df)

        # 计算各个条件
        condition1 = self._check_volatility(df, volatility_period, volatility_threshold)
        condition2 = self._check_bbi_rising(df, bbi_rising_days)
        condition3 = df['j'] < j_threshold
        condition4 = df['dif'] > 0

        # 综合信号：所有条件都满足
        signals = (condition1 & condition2 & condition3 & condition4).astype(float) * weight

        # 返回以交易日期为索引的信号序列
        result = pd.Series(0.0, index=df['trade_date'])
        result.iloc[signals.index] = signals.values

        return result

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所需技术指标（优先使用预计算的指标）"""
        # 检查是否有预计算的指标
        has_precomputed = '__precomputed__' in df.columns

        # 1. 计算BBI多空指标
        df['ma3'] = df['close'].rolling(window=self.params['bbi_p1']).mean()
        df['ma6'] = df['close'].rolling(window=self.params['bbi_p2']).mean()
        df['ma12'] = df['close'].rolling(window=self.params['bbi_p3']).mean()
        df['ma24'] = df['close'].rolling(window=self.params['bbi_p4']).mean()
        df['bbi'] = (df['ma3'] + df['ma6'] + df['ma12'] + df['ma24']) / 4

        # 2. 使用预计算的KDJ指标（如果参数匹配）或重新计算
        if (has_precomputed and
            self.params['kdj_n_period'] == 9 and
            self.params['kdj_m1_period'] == 3 and
            self.params['kdj_m2_period'] == 3):
            df['k'] = df['kdj_k']
            df['d'] = df['kdj_d']
            df['j'] = df['kdj_j']
        else:
            n_period = self.params['kdj_n_period']
            low_min = df['low'].rolling(window=n_period).min()
            high_max = df['high'].rolling(window=n_period).max()
            price_range = high_max - low_min
            rsv = ((df['close'] - low_min) / price_range.replace(0, np.nan) * 100).fillna(0)

            m1_period = self.params['kdj_m1_period']
            m2_period = self.params['kdj_m2_period']
            df['k'] = rsv.ewm(alpha=1/m1_period, adjust=False).mean()
            df['d'] = df['k'].ewm(alpha=1/m2_period, adjust=False).mean()
            df['j'] = 3 * df['k'] - 2 * df['d']

        # 3. 使用预计算的MACD指标（如果参数匹配）或重新计算
        if (has_precomputed and
            self.params['macd_fast'] == 12 and
            self.params['macd_slow'] == 26 and
            self.params['macd_signal'] == 9):
            df['dif'] = df['macd_dif']
            df['dea'] = df['macd_dea']
        else:
            ema_fast = df['close'].ewm(span=self.params['macd_fast'], adjust=False).mean()
            ema_slow = df['close'].ewm(span=self.params['macd_slow'], adjust=False).mean()
            df['dif'] = ema_fast - ema_slow
            df['dea'] = df['dif'].ewm(span=self.params['macd_signal'], adjust=False).mean()

        return df

    def _check_volatility(self, df: pd.DataFrame, period: int, threshold: float) -> pd.Series:
        """波动幅度 = (最高价 - 最低价) / 最低价 * 100%"""
        # 计算最近N天的最高价和最低价
        rolling_high = df['high'].rolling(window=period).max()
        rolling_low = df['low'].rolling(window=period).min()

        # 计算波动幅度
        volatility = (rolling_high - rolling_low) / rolling_low * 100

        # 波动幅度 <= 阈值
        return volatility <= threshold

    def _check_bbi_rising(self, df: pd.DataFrame, days: int) -> pd.Series:
        """检查BBI是否连续N天上升"""
        # 检查BBI是否连续上升
        bbi_rising = df['bbi'] > df['bbi'].shift(1)

        # 滚动求和，检查最近N天是否都在上升
        rising_count = bbi_rising.rolling(window=days).sum()

        # 最近N天全部上升
        return rising_count >= days


class LowVolatilityBullishStrategy(Strategy):
    """低波动多头策略（简化版多指标组合），关注核心条件用于快速选股"""

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'volatility_period': 60,
            'volatility_threshold': 100.0,
            'bbi_rising_days': 3,
            'j_threshold': -1,
            'weight': 1.0
        }
        if params:
            default_params.update(params)
        super().__init__(name="Low Volatility Bullish", params=default_params)

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        volatility_period = self.params['volatility_period']
        volatility_threshold = self.params['volatility_threshold']
        bbi_rising_days = self.params['bbi_rising_days']
        j_threshold = self.params['j_threshold']
        weight = self.params.get('weight', 1.0)

        df = df.sort_values('trade_date').reset_index(drop=True)

        # 数据不足检查
        if len(df) < 60:
            return pd.Series(0.0, index=df['trade_date'])

        # 计算指标（使用utils中的函数）
        from utils.indicators import calculate_bbi, calculate_kdj, calculate_macd

        # BBI
        bbi = calculate_bbi(df, p1=3, p2=6, p3=12, p4=24)
        df['bbi'] = bbi

        # KDJ
        k, d, j = calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)
        df['j'] = j

        # MACD
        dif, dea, macd = calculate_macd(df, fast_period=12, slow_period=26, signal_period=9)
        df['dif'] = dif

        # 计算条件
        rolling_high = df['high'].rolling(window=volatility_period).max()
        rolling_low = df['low'].rolling(window=volatility_period).min()
        volatility = (rolling_high - rolling_low) / rolling_low * 100
        condition1 = volatility <= volatility_threshold

        bbi_rising = df['bbi'] > df['bbi'].shift(1)
        condition2 = bbi_rising.rolling(window=bbi_rising_days).sum() >= bbi_rising_days

        condition3 = df['j'] < j_threshold
        condition4 = df['dif'] > 0

        signals = (condition1 & condition2 & condition3 & condition4).astype(float) * weight

        result = pd.Series(0.0, index=df['trade_date'])
        result.iloc[signals.index] = signals.values

        return result
