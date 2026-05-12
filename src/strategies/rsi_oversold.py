"""
RSI超卖策略 - RSI Oversold Strategy

该模块实现了相对强弱指标（RSI）超卖策略。
This module implements the Relative Strength Index (RSI) oversold strategy.
"""

import pandas as pd
from typing import Dict, Any
from .base import Strategy, StrategyMixin
from utils.indicators import calculate_rsi


class RSIOversoldStrategy(Strategy, StrategyMixin):
    """
    RSI 超卖策略
    RSI Oversold Strategy

    当RSI指标低于阈值时产生买入信号。
    Generates buy signals when RSI indicator falls below the threshold.
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化 RSI 超卖策略
        Initialize RSI oversold strategy

        参数 (Parameters):
            params: 策略参数 (Strategy parameters):
                - period: RSI 计算周期（默认14）(RSI calculation period, default 14)
                - threshold: 超卖阈值（默认30）(Oversold threshold, default 30)
                - weight: 信号权重（默认1.0）(Signal weight, default 1.0)
        """
        default_params = {
            'period': 14,
            'threshold': 30,
            'weight': 1.0
        }
        if params:
            default_params.update(params)
        super().__init__(name="RSI Oversold", params=default_params)

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        计算 RSI 超卖信号
        Calculate RSI oversold signals

        参数 (Parameters):
            df: 股票行情数据 (Stock market data)

        返回 (Returns):
            pd.Series: 信号序列，索引为交易日期 (Signal series with trading dates as index)
        """
        period = self.params['period']
        threshold = self.params['threshold']
        weight = self.params.get('weight', 1.0)

        # 使用统一的预处理方法
        # Use unified preprocessing method
        df = self.preprocess_data(df)

        # 计算 RSI
        # Calculate RSI
        df['rsi'] = calculate_rsi(df, period=period, column='close')

        # 计算超卖信号
        # Calculate oversold signals
        # RSI 低于阈值，且昨日 RSI 不低于阈值（避免重复信号）
        # RSI is below threshold, and yesterday's RSI was not below threshold (avoid duplicate signals)
        oversold = (
            (df['rsi'] < threshold) &
            (df['rsi'].shift(1) >= threshold)
        )

        # 生成信号序列
        # Generate signal series
        signals = pd.Series(0.0, index=df.index)
        signals[oversold] = 1.0 * weight

        # 使用统一的信号构建方法
        # Use unified signal building method
        return self.build_signals(signals, df)

