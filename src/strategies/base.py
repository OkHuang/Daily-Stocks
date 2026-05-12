"""
策略基类模块 - Strategy Base Module

该模块定义了选股策略的抽象基类和策略混入类。
This module defines the abstract base class for stock selection strategies and strategy mixin class.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any


class Strategy(ABC):
    """
    选股策略抽象基类
    Abstract base class for stock selection strategies

    所有具体策略类必须继承此类并实现 calculate 方法。
    All concrete strategy classes must inherit from this class and implement the calculate method.
    """

    def __init__(self, name: str, params: Dict[str, Any] = None):
        """
        初始化策略
        Initialize strategy

        参数 (Parameters):
            name: 策略名称 (Strategy name)
            params: 策略参数字典 (Strategy parameters dictionary)
        """
        self.name = name
        self.params = params or {}

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        计算策略信号
        Calculate strategy signals

        根据股票历史行情数据计算策略信号。
        Calculates strategy signals based on historical stock data.

        参数 (Parameters):
            df: 股票行情数据，包含以下列 (Stock market data with following columns):
                - trade_date: 交易日期 (Trading date)
                - open: 开盘价 (Open price)
                - high: 最高价 (High price)
                - low: 最低价 (Low price)
                - close: 收盘价 (Close price)
                - volume: 成交量 (Volume)
                - amount: 成交额 (Amount)

        返回 (Returns):
            pd.Series: 策略信号，索引为交易日期 (Strategy signals with trading dates as index):
                - 值为 0-1 之间的浮点数，表示信号强度 (Values are floats between 0-1, indicating signal strength)
                - 0 表示无信号 (0 indicates no signal)
                - 1 表示强信号 (1 indicates strong signal)

        异常 (Raises):
            NotImplementedError: 子类必须实现此方法 (Subclasses must implement this method)
        """
        raise NotImplementedError("Subclasses must implement calculate()")

    def validate_signal(self, signal: float) -> bool:
        """
        验证信号有效性
        Validate signal validity

        参数 (Parameters):
            signal: 信号值 (Signal value)

        返回 (Returns):
            bool: 信号是否有效 (Whether the signal is valid)
        """
        # 默认验证规则：信号值在 0-1 之间
        # Default validation rule: signal value is between 0-1
        return 0 <= signal <= 1

    def get_latest_signal(self, df: pd.DataFrame) -> float:
        """
        获取最新的策略信号
        Get the latest strategy signal

        参数 (Parameters):
            df: 股票行情数据 (Stock market data)

        返回 (Returns):
            float: 最新交易日的信号值 (Signal value of the latest trading day)
        """
        signals = self.calculate(df)
        if len(signals) > 0:
            return signals.iloc[-1]
        return 0.0


class StrategyMixin:
    """
    策略混入类 - Strategy Mixin Class

    提供策略常用的辅助方法，避免代码重复。
    Provides common helper methods for strategies to avoid code duplication.
    """

    @staticmethod
    def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        统一的数据预处理
        Unified data preprocessing

        确保数据按日期升序排列，并重置索引。
        Ensures data is sorted by date in ascending order and resets index.

        参数 (Parameters):
            df: 股票行情数据 (Stock market data)

        返回 (Returns):
            pd.DataFrame: 预处理后的数据 (Preprocessed data)
        """
        # 确保按日期升序排列
        # Ensure sorted by date in ascending order
        df = df.sort_values('trade_date').reset_index(drop=True)
        return df

    @staticmethod
    def build_signals(signals: pd.Series, df: pd.DataFrame) -> pd.Series:
        """
        统一的信号序列构建
        Unified signal series building

        将信号序列映射到交易日期索引。
        Maps signal series to trading date index.

        参数 (Parameters):
            signals: 信号序列（索引为数字）(Signal series with numeric index)
            df: 股票行情数据 (Stock market data)

        返回 (Returns):
            pd.Series: 以交易日期为索引的信号序列 (Signal series with trading dates as index)
        """
        result = pd.Series(0.0, index=df['trade_date'])
        result.iloc[signals.index] = signals.values
        return result

    def validate_signal(self, signal: float) -> bool:
        """
        验证信号有效性
        Validate signal validity

        参数 (Parameters):
            signal: 信号值 (Signal value)

        返回 (Returns):
            bool: 信号是否有效 (Whether the signal is valid)
        """
        # 默认验证规则：信号值在 0-1 之间
        # Default validation rule: signal value is between 0-1
        return 0 <= signal <= 1
