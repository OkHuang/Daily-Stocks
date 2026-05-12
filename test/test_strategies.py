"""
策略模块单元测试 - Strategy Module Unit Tests

该文件包含策略模块的单元测试。
This file contains unit tests for the strategy module.
"""

import unittest
import pandas as pd
import numpy as np

from src.strategies.base import Strategy
from src.strategies.ma_cross import MACrossStrategy
from src.strategies.rsi_oversold import RSIOversoldStrategy


class TestStrategyBase(unittest.TestCase):
    """策略基类测试 (Strategy base class tests)"""

    def test_strategy_cannot_be_instantiated(self):
        """测试策略基类不能直接实例化 (Test that strategy base class cannot be directly instantiated)"""
        with self.assertRaises(TypeError):
            Strategy()


class TestMACrossStrategy(unittest.TestCase):
    """均线交叉策略测试 (MA crossover strategy tests)"""

    def setUp(self):
        """设置测试数据 (Set up test data)"""
        # 创建模拟数据
        # Create mock data
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        np.random.seed(42)

        # 生成有趋势的价格数据（短期均线会上穿长期均线）
        # Generate trending price data (short MA will cross above long MA)
        prices = 10 + np.cumsum(np.random.randn(50) * 0.5)

        self.df = pd.DataFrame({
            'trade_date': dates.strftime('%Y%m%d'),
            'open': prices * (1 + np.random.randn(50) * 0.01),
            'high': prices * (1 + abs(np.random.randn(50)) * 0.02),
            'low': prices * (1 - abs(np.random.randn(50)) * 0.02),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 50),
            'amount': prices * np.random.randint(1000000, 10000000, 50)
        })

    def test_strategy_initialization(self):
        """测试策略初始化 (Test strategy initialization)"""
        strategy = MACrossStrategy()
        self.assertEqual(strategy.name, "MA Cross")
        self.assertEqual(strategy.params['short_period'], 5)
        self.assertEqual(strategy.params['long_period'], 20)

    def test_strategy_with_custom_params(self):
        """测试自定义参数 (Test custom parameters)"""
        strategy = MACrossStrategy(params={'short_period': 10, 'long_period': 30})
        self.assertEqual(strategy.params['short_period'], 10)
        self.assertEqual(strategy.params['long_period'], 30)

    def test_calculate_returns_series(self):
        """测试 calculate 方法返回 Series (Test that calculate method returns Series)"""
        strategy = MACrossStrategy()
        signals = strategy.calculate(self.df)

        self.assertIsInstance(signals, pd.Series)
        self.assertEqual(len(signals), len(self.df))

    def test_signals_are_valid(self):
        """测试信号值有效 (Test that signal values are valid)"""
        strategy = MACrossStrategy()
        signals = strategy.calculate(self.df)

        # 所有信号值应该在 0-1 之间
        # All signal values should be between 0-1
        self.assertTrue((signals >= 0).all())
        self.assertTrue((signals <= 1).all())


class TestRSIOversoldStrategy(unittest.TestCase):
    """RSI 超卖策略测试 (RSI oversold strategy tests)"""

    def setUp(self):
        """设置测试数据 (Set up test data)"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        np.random.seed(42)

        # 生成包含下跌趋势的价格数据（可能触发 RSI 超卖）
        # Generate price data with downtrend (may trigger RSI oversold)
        prices = 20 + np.cumsum(np.random.randn(50) * 0.8)

        self.df = pd.DataFrame({
            'trade_date': dates.strftime('%Y%m%d'),
            'open': prices * (1 + np.random.randn(50) * 0.01),
            'high': prices * (1 + abs(np.random.randn(50)) * 0.02),
            'low': prices * (1 - abs(np.random.randn(50)) * 0.02),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 50),
            'amount': prices * np.random.randint(1000000, 10000000, 50)
        })

    def test_strategy_initialization(self):
        """测试策略初始化 (Test strategy initialization)"""
        strategy = RSIOversoldStrategy()
        self.assertEqual(strategy.name, "RSI Oversold")
        self.assertEqual(strategy.params['period'], 14)
        self.assertEqual(strategy.params['threshold'], 30)

    def test_calculate_returns_series(self):
        """测试 calculate 方法返回 Series (Test that calculate method returns Series)"""
        strategy = RSIOversoldStrategy()
        signals = strategy.calculate(self.df)

        self.assertIsInstance(signals, pd.Series)
        self.assertEqual(len(signals), len(self.df))

    def test_rsi_calculation(self):
        """测试 RSI 计算 (Test RSI calculation)"""
        strategy = RSIOversoldStrategy()
        rsi = strategy._calculate_rsi(self.df['close'], 14)

        # RSI 值应该在 0-100 之间（NaN 值忽略）
        # RSI values should be between 0-100 (NaN values are ignored)
        self.assertFalse((rsi < 0).any(), f"RSI has negative values: {rsi[rsi < 0].tolist()}")
        self.assertFalse((rsi > 100).any(), f"RSI exceeds 100: {rsi[rsi > 100].tolist()}")


if __name__ == '__main__':
    unittest.main()
