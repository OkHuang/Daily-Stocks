"""RSI超卖策略"""

import pandas as pd
from typing import Dict, Any
from .base import Strategy, StrategyMixin
from utils.indicators import calculate_rsi


class RSIOversoldStrategy(Strategy, StrategyMixin):
    """RSI 低于阈值时产生买入信号"""

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'period': 14,
            'threshold': 30,
            'weight': 1.0
        }
        if params:
            default_params.update(params)
        super().__init__(name="RSI Oversold", params=default_params)

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        threshold = self.params['threshold']
        weight = self.params.get('weight', 1.0)

        # 使用统一的预处理方法
        df = self.preprocess_data(df)

        # 计算 RSI
        df['rsi'] = calculate_rsi(df, period=period, column='close')

        # RSI 低于阈值，且昨日 RSI 不低于阈值（避免重复信号）
        oversold = (
            (df['rsi'] < threshold) &
            (df['rsi'].shift(1) >= threshold)
        )

        # 生成信号序列
        signals = pd.Series(0.0, index=df.index)
        signals[oversold] = 1.0 * weight

        # 使用统一的信号构建方法
        return self.build_signals(signals, df)
