"""
均线交叉策略 - Moving Average Crossover Strategy

该模块实现了移动平均线交叉策略。
This module implements the moving average crossover strategy.
"""

import pandas as pd
from typing import Dict, Any
from .base import Strategy, StrategyMixin


class MACrossStrategy(Strategy, StrategyMixin):
    """
    移动平均线交叉策略
    Moving Average Crossover Strategy

    当短期均线上穿长期均线时产生买入信号。
    Generates buy signals when the short-term moving average crosses above the long-term moving average.
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化均线交叉策略
        Initialize MA crossover strategy

        参数 (Parameters):
            params: 策略参数 (Strategy parameters):
                - short_period: 短期均线周期（默认5）(Short-term MA period, default 5)
                - long_period: 长期均线周期（默认20）(Long-term MA period, default 20)
                - weight: 信号权重（默认1.0）(Signal weight, default 1.0)
        """
        default_params = {
            'short_period': 5,
            'long_period': 20,
            'weight': 1.0
        }
        if params:
            default_params.update(params)
        super().__init__(name="MA Cross", params=default_params)

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        计算均线交叉信号
        Calculate MA crossover signals

        参数 (Parameters):
            df: 股票行情数据 (Stock market data)

        返回 (Returns):
            pd.Series: 信号序列，索引为交易日期 (Signal series with trading dates as index)
        """
        short_period = self.params['short_period']
        long_period = self.params['long_period']
        weight = self.params.get('weight', 1.0)

        # 使用统一的预处理方法
        # Use unified preprocessing method
        df = self.preprocess_data(df)

        # 计算移动平均线
        # Calculate moving averages
        df['ma_short'] = df['close'].rolling(window=short_period).mean()
        df['ma_long'] = df['close'].rolling(window=long_period).mean()

        # 计算交叉信号
        # Calculate crossover signals
        # 1. 判断短期均线是否上穿长期均线（金叉）
        #    Check if short MA crosses above long MA (golden cross)
        cross_above = (
            (df['ma_short'] > df['ma_long']) &
            (df['ma_short'].shift(1) <= df['ma_long'].shift(1))
        )

        # 生成信号序列
        # Generate signal series
        signals = pd.Series(0.0, index=df.index)

        # 金叉时产生买入信号
        # Generate buy signal on golden cross
        signals[cross_above] = 1.0 * weight

        # 使用统一的信号构建方法
        # Use unified signal building method
        return self.build_signals(signals, df)
