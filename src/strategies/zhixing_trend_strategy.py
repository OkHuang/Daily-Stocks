"""
知行趋势策略 - Zhixing Trend Strategy

该模块实现了基于知行多空线和知行短期趋势线的选股策略。
This module implements a stock selection strategy based on Zhixing Bull-Bear Line and Zhixing Short-term Trend Line.

策略条件 (Strategy Conditions):
    1. 股价高于当日知行多空线价格
    2. 当前日J值 < 13
    3. 知行短期趋势线价格大于知行多空线价格
    4. 当日股价振幅小于4%
    5. 当日交易量小于最近12天交易量均量的52%
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import Strategy


class ZhixingTrendStrategy(Strategy):
    """
    知行趋势策略
    Zhixing Trend Strategy

    综合使用知行多空线、知行短期趋势线、KDJ、振幅和成交量进行选股。
    Combines Zhixing Bull-Bear Line, Zhixing Short-term Trend Line, KDJ, amplitude, and volume for stock selection.
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化知行趋势策略
        Initialize Zhixing trend strategy

        参数 (Parameters):
            params: 策略参数 (Strategy parameters):
                - zhixing_bb_p1: 知行多空线第一条均线周期（默认14）(Zhixing BB line MA1 period, default 14)
                - zhixing_bb_p2: 知行多空线第二条均线周期（默认28）(Zhixing BB line MA2 period, default 28)
                - zhixing_bb_p3: 知行多空线第三条均线周期（默认57）(Zhixing BB line MA3 period, default 57)
                - zhixing_bb_p4: 知行多空线第四条均线周期（默认114）(Zhixing BB line MA4 period, default 114)
                - short_trend_period: 知行短期趋势线周期（默认10）(Short-term trend line period, default 10)
                - j_threshold: J值阈值（默认13）(J value threshold, default 13)
                - amplitude_threshold: 振幅阈值（默认4%）(Amplitude threshold, default 4)
                - volume_ma_period: 成交量均线周期（默认12）(Volume MA period, default 12)
                - volume_ratio_threshold: 成交量比例阈值（默认52%）(Volume ratio threshold, default 52)
                - weight: 信号权重（默认1.0）(Signal weight, default 1.0)
        """
        default_params = {
            'zhixing_bb_p1': 14,
            'zhixing_bb_p2': 28,
            'zhixing_bb_p3': 57,
            'zhixing_bb_p4': 114,
            'short_trend_period': 10,
            'kdj_n_period': 9,
            'kdj_m1_period': 3,
            'kdj_m2_period': 3,
            'j_threshold': 13,
            'amplitude_threshold': 4.0,
            'volume_ma_period': 12,
            'volume_ratio_threshold': 52.0,
            'weight': 1.0
        }
        if params:
            default_params.update(params)
        super().__init__(name="Zhixing Trend", params=default_params)

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        计算知行趋势策略信号
        Calculate Zhixing trend strategy signals

        参数 (Parameters):
            df: 股票行情数据 (Stock market data)

        返回 (Returns):
            pd.Series: 信号序列，索引为交易日期 (Signal series with trading dates as index)
        """
        # 获取参数
        p1 = self.params['zhixing_bb_p1']
        p2 = self.params['zhixing_bb_p2']
        p3 = self.params['zhixing_bb_p3']
        p4 = self.params['zhixing_bb_p4']
        short_trend_period = self.params['short_trend_period']
        j_threshold = self.params['j_threshold']
        amplitude_threshold = self.params['amplitude_threshold']
        volume_ma_period = self.params['volume_ma_period']
        volume_ratio_threshold = self.params['volume_ratio_threshold']
        weight = self.params.get('weight', 1.0)

        # 确保 DataFrame 按日期升序排列
        df = df.sort_values('trade_date').reset_index(drop=True)

        # 数据不足时返回全0信号
        min_required = max(p4, volume_ma_period)
        if len(df) < min_required:
            return pd.Series(0.0, index=df['trade_date'])

        # 计算各项指标
        df = self._calculate_indicators(df)

        # 计算各个条件
        condition1 = df['close'] > df['zhixing_bb']  # 股价高于知行多空线
        condition2 = df['j'] < j_threshold  # J值小于阈值
        condition3 = df['short_trend'] > df['zhixing_bb']  # 短期趋势线高于多空线
        condition4 = df['amplitude'] < amplitude_threshold  # 振幅小于阈值
        condition5 = df['volume_ratio'] < volume_ratio_threshold  # 成交量比例小于阈值

        # 综合信号：所有条件都满足
        signals = (condition1 & condition2 & condition3 & condition4 & condition5).astype(float) * weight

        # 返回以交易日期为索引的信号序列
        result = pd.Series(0.0, index=df['trade_date'])
        result.iloc[signals.index] = signals.values

        return result

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所需的技术指标
        Calculate required technical indicators

        参数 (Parameters):
            df: 股票行情数据 (Stock market data)

        返回 (Returns):
            pd.DataFrame: 添加了指标列的DataFrame (DataFrame with indicator columns added)
        """
        # 1. 计算知行多空线
        ma1 = df['close'].rolling(window=self.params['zhixing_bb_p1']).mean()
        ma2 = df['close'].rolling(window=self.params['zhixing_bb_p2']).mean()
        ma3 = df['close'].rolling(window=self.params['zhixing_bb_p3']).mean()
        ma4 = df['close'].rolling(window=self.params['zhixing_bb_p4']).mean()
        df['zhixing_bb'] = (ma1 + ma2 + ma3 + ma4) / 4

        # 2. 计算知行短期趋势线（双重EMA）
        ema1 = df['close'].ewm(span=self.params['short_trend_period'], adjust=False).mean()
        df['short_trend'] = ema1.ewm(span=self.params['short_trend_period'], adjust=False).mean()

        # 3. 使用预计算的KDJ指标（如果参数匹配）或重新计算
        # Use precomputed KDJ indicators (if params match) or recalculate
        has_precomputed = '__precomputed__' in df.columns

        if (has_precomputed and
            self.params['kdj_n_period'] == 9 and
            self.params['kdj_m1_period'] == 3 and
            self.params['kdj_m2_period'] == 3):
            # 使用预计算的指标 (Use precomputed indicators)
            df['k'] = df['kdj_k']
            df['d'] = df['kdj_d']
            df['j'] = df['kdj_j']
        else:
            # 重新计算KDJ指标 (Recalculate KDJ indicators)
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

        # 4. 计算振幅
        # 振幅 = (最高价 - 最低价) / 最低价 * 100%
        df['amplitude'] = (df['high'] - df['low']) / df['low'] * 100

        # 5. 计算成交量比例
        volume_ma = df['vol'].rolling(window=self.params['volume_ma_period']).mean()
        df['volume_ratio'] = df['vol'] / volume_ma * 100

        return df
