"""均线交叉策略"""

import pandas as pd
from typing import Dict, Any
from .base import Strategy, StrategyMixin


class MACrossStrategy(Strategy, StrategyMixin):
    """短期均线上穿长期均线时产生买入信号"""

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'short_period': 5,
            'long_period': 20,
            'weight': 1.0
        }
        if params:
            default_params.update(params)
        super().__init__(name="MA Cross", params=default_params)

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        short_period = self.params['short_period']
        long_period = self.params['long_period']
        weight = self.params.get('weight', 1.0)

        # 使用统一的预处理方法
        df = self.preprocess_data(df)

        # 计算移动平均线
        df['ma_short'] = df['close'].rolling(window=short_period).mean()
        df['ma_long'] = df['close'].rolling(window=long_period).mean()

        # 判断短期均线是否上穿长期均线（金叉）
        cross_above = (
            (df['ma_short'] > df['ma_long']) &
            (df['ma_short'].shift(1) <= df['ma_long'].shift(1))
        )

        # 金叉时产生买入信号
        signals = pd.Series(0.0, index=df.index)
        signals[cross_above] = 1.0 * weight

        # 使用统一的信号构建方法
        return self.build_signals(signals, df)
