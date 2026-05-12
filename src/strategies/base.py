"""策略基类模块"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any


class Strategy(ABC):
    """选股策略抽象基类"""

    def __init__(self, name: str, params: Dict[str, Any] = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """计算策略信号，返回 0-1 信号强度序列"""
        raise NotImplementedError("Subclasses must implement calculate()")

    def validate_signal(self, signal: float) -> bool:
        # 信号值须在 0-1 之间
        return 0 <= signal <= 1

    def get_latest_signal(self, df: pd.DataFrame) -> float:
        signals = self.calculate(df)
        if len(signals) > 0:
            return signals.iloc[-1]
        return 0.0


class StrategyMixin:
    """策略辅助方法混入类"""

    @staticmethod
    def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
        """确保数据按日期升序排列并重置索引"""
        df = df.sort_values('trade_date').reset_index(drop=True)
        return df

    @staticmethod
    def build_signals(signals: pd.Series, df: pd.DataFrame) -> pd.Series:
        """将信号序列映射到交易日期索引"""
        result = pd.Series(0.0, index=df['trade_date'])
        result.iloc[signals.index] = signals.values
        return result
