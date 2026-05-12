"""
策略执行器模块 - Strategy Runner Module

该模块负责批量执行多个选股策略。
This module is responsible for batch executing multiple stock selection strategies.
"""

from typing import Dict, List, Any
import pandas as pd
import yaml
from pathlib import Path
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from strategies.base import Strategy
from strategies.ma_cross import MACrossStrategy
from strategies.rsi_oversold import RSIOversoldStrategy
from utils.indicators import calculate_ma, calculate_ema, calculate_rsi, calculate_macd, calculate_kdj


class StrategyRunner:
    """
    策略执行器
    Strategy runner

    负责加载策略配置，批量执行多个策略，返回所有股票的信号结果。
    Responsible for loading strategy configurations, batch executing multiple strategies, and returning signal results for all stocks.
    """

    def __init__(self, config_path: str = "strategies.yaml", logger: logging.Logger = None):
        """
        初始化策略执行器
        Initialize strategy runner

        参数 (Parameters):
            config_path: 策略配置文件路径 (Strategy configuration file path)
            logger: 日志记录器 (Logger instance)
        """
        self.config_path = config_path
        self.strategies: Dict[str, Strategy] = {}
        self.logger = logger or logging.getLogger(__name__)
        self._indicator_cache = {}  # 技术指标缓存 (Technical indicator cache)
        self._load_strategies()

    def _load_strategies(self):
        """
        从配置文件加载策略
        Load strategies from configuration file

        读取 strategies.yaml，实例化已启用的策略。
        Reads strategies.yaml and instantiates enabled strategies.
        """
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Strategy config file not found: {self.config_path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        strategies_config = config.get('strategies', {})

        # 策略注册表
        # Strategy registry
        strategy_registry = {
            'ma_cross': MACrossStrategy,
            'rsi_oversold': RSIOversoldStrategy,
        }

        # 实例化已启用的策略
        # Instantiate enabled strategies
        for strategy_name, strategy_config in strategies_config.items():
            if strategy_config.get('enabled', False):
                strategy_class = strategy_registry.get(strategy_name)
                if strategy_class:
                    params = strategy_config.get('params', {})
                    self.strategies[strategy_name] = strategy_class(params=params)
                    self.logger.info(f"Loaded strategy: {strategy_name}")
                else:
                    self.logger.warning(f"Unknown strategy: {strategy_name}")

    def _precompute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        预计算常用技术指标并缓存
        Precompute common technical indicators and cache them

        这个方法会在 DataFrame 中添加常用的技术指标列，
        避免每个策略重复计算相同的指标。

        This method adds common technical indicator columns to the DataFrame,
        avoiding repeated calculations in each strategy.

        参数 (Parameters):
            df: 原始数据 (Original data)

        返回 (Returns):
            pd.DataFrame: 添加了指标列的数据 (Data with indicator columns added)
        """
        if df is None or len(df) < 50:
            return df

        # 检查是否已经预计算过
        # Check if already precomputed
        if '__precomputed__' in df.columns:
            return df

        df = df.copy()

        # 预计算常用指标
        # Precompute common indicators

        # 移动平均线 (Moving averages)
        df['ma5'] = calculate_ma(df, period=5, column='close')
        df['ma10'] = calculate_ma(df, period=10, column='close')
        df['ma20'] = calculate_ma(df, period=20, column='close')
        df['ma60'] = calculate_ma(df, period=60, column='close')

        # EMA (Exponential moving averages)
        df['ema12'] = calculate_ema(df, period=12, column='close')
        df['ema26'] = calculate_ema(df, period=26, column='close')

        # RSI (Relative strength index)
        df['rsi6'] = calculate_rsi(df, period=6, column='close')
        df['rsi12'] = calculate_rsi(df, period=12, column='close')
        df['rsi24'] = calculate_rsi(df, period=24, column='close')

        # MACD
        macd_df = calculate_macd(df, fast=12, slow=26, signal=9, column='close')
        df['macd_dif'] = macd_df['dif']
        df['macd_dea'] = macd_df['dea']
        df['macd_histogram'] = macd_df['histogram']

        # KDJ
        kdj_df = calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)
        df['kdj_k'] = kdj_df['k']
        df['kdj_d'] = kdj_df['d']
        df['kdj_j'] = kdj_df['j']

        # 标记已预计算
        # Mark as precomputed
        df['__precomputed__'] = True

        self.logger.debug(f"Precomputed {len(df.columns) - len(df.columns) - 1} indicator columns")

        return df

    def run(
        self,
        stock_list: List[str],
        local_store,
        fetcher
    ) -> Dict[str, Dict[str, float]]:
        """
        执行所有策略
        Execute all strategies

        对每只股票应用所有已启用的策略，计算信号。
        Applies all enabled strategies to each stock and calculates signals.

        参数 (Parameters):
            stock_list: 股票代码列表 (List of stock codes)
            local_store: 本地存储实例 (Local storage instance)
            fetcher: 数据获取器实例 (Data fetcher instance)

        返回 (Returns):
            Dict[str, Dict[str, float]]: 策略执行结果 (Strategy execution results):
                - 外层字典键: 股票代码 (Outer dict key: stock code)
                - 内层字典键: 策略名称 (Inner dict key: strategy name)
                - 内层字典值: 信号强度 (Inner dict value: signal strength)
        """
        results = {}

        # 根据系统资源动态调整线程数
        # Dynamically adjust thread count based on system resources
        cpu_count = os.cpu_count() or 1
        max_workers = min(len(stock_list), cpu_count * 2)

        self.logger.info(f"Using {max_workers} workers for {len(stock_list)} stocks")

        # 使用线程池并发执行策略
        # Use thread pool to execute strategies concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._run_single_stock, stock_code, local_store, fetcher): stock_code
                for stock_code in stock_list
            }

            for future in as_completed(futures):
                stock_code = futures[future]
                try:
                    # 添加超时控制，防止任务卡死
                    # Add timeout control to prevent tasks from hanging
                    stock_results = future.result(timeout=30)
                    if stock_results:
                        results[stock_code] = stock_results
                except Exception as e:
                    self.logger.error(f"Error processing {stock_code}: {e}")

        self.logger.info(f"Strategy execution completed: {len(results)} stocks processed")
        return results

    def _run_single_stock(
        self,
        stock_code: str,
        local_store,
        fetcher
    ) -> Dict[str, float]:
        """
        对单只股票执行所有策略
        Execute all strategies for a single stock

        参数 (Parameters):
            stock_code: 股票代码 (Stock code)
            local_store: 本地存储实例 (Local storage instance)
            fetcher: 数据获取器实例 (Data fetcher instance)

        返回 (Returns):
            Dict[str, float]: 策略信号字典 (Strategy signal dictionary)
        """
        # 清空指标缓存（每只股票独立计算）
        # Clear indicator cache (independent calculation per stock)
        self._indicator_cache.clear()

        # 1. 尝试从本地加载数据
        # 1. Try to load data from local storage
        df = local_store.load_daily_data(stock_code)

        # 2. 如果本地数据不足，从数据源获取
        # 2. Fetch from data source if local data is insufficient
        if df is None or len(df) < 50:
            df = fetcher.fetch_daily(stock_code)
            if df is not None and len(df) > 0:
                local_store.save_daily_data(df)

        # 3. 预计算技术指标（避免重复计算）
        # 3. Precompute technical indicators (avoid repeated calculations)
        if df is not None and len(df) >= 50:
            df = self._precompute_indicators(df)

        # 4. 执行所有策略
        # 4. Execute all strategies
        signals = {}
        for strategy_name, strategy in self.strategies.items():
            try:
                signal = strategy.get_latest_signal(df)
                if signal > 0:
                    signals[strategy_name] = signal
            except Exception as e:
                self.logger.error(f"Error in {strategy_name} for {stock_code}: {e}")

        return signals
