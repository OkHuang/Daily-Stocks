"""策略执行器模块"""

from typing import Dict, List, Any
import pandas as pd
import yaml
from pathlib import Path
import os
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

from strategies.base import Strategy
from strategies.ma_cross import MACrossStrategy
from strategies.rsi_oversold import RSIOversoldStrategy
from strategies.multi_indicator_combo import MultiIndicatorComboStrategy, LowVolatilityBullishStrategy
from strategies.zhixing_trend_strategy import ZhixingTrendStrategy
from utils.indicators import calculate_ma, calculate_ema, calculate_rsi, calculate_macd, calculate_kdj


def _worker_process_stock(stock_code: str, df_data: pd.DataFrame, config_path: str) -> Dict[str, float]:
    """子进程入口：对单只股票执行所有策略"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

    if df_data is None or len(df_data) < 50:
        return {}

    from engine.strategy_runner import StrategyRunner
    runner = StrategyRunner(config_path=config_path)
    runner._precompute_indicators(df_data)

    signals = {}
    for strategy_name, strategy in runner.strategies.items():
        try:
            signal = strategy.get_latest_signal(df_data)
            if signal > 0:
                signals[strategy_name] = signal
        except Exception:
            pass

    return signals


class StrategyRunner:
    """策略执行器，批量加载和执行多个选股策略"""

    def __init__(self, config_path: str = "strategies.yaml", logger: logging.Logger = None):
        self.config_path = config_path
        self.strategies: Dict[str, Strategy] = {}
        self.logger = logger or logging.getLogger(__name__)
        self._load_strategies()

    def _preload_stock_data(self, stock_list: List[str], local_store) -> Dict[str, pd.DataFrame]:
        """在主进程中预加载所有股票数据"""
        stock_data = {}
        for stock_code in stock_list:
            try:
                df = local_store.load_daily_data(stock_code)
                if df is not None and len(df) >= 50:
                    stock_data[stock_code] = df
            except Exception as e:
                self.logger.warning(f"加载 {stock_code} 数据失败: {e}")
        self.logger.info(f"预加载了 {len(stock_data)}/{len(stock_list)} 只股票的数据")
        return stock_data

    def _load_strategies(self):
        """从 strategies.yaml 加载并实例化已启用的策略"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Strategy config file not found: {self.config_path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        strategies_config = config.get('strategies', {})

        # 策略注册表
        strategy_registry = {
            'ma_cross': MACrossStrategy,
            'rsi_oversold': RSIOversoldStrategy,
            'multi_indicator_combo': MultiIndicatorComboStrategy,
            'low_volatility_bullish': LowVolatilityBullishStrategy,
            'zhixing_trend': ZhixingTrendStrategy,
        }

        # 实例化已启用的策略
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
        """预计算常用技术指标，避免每个策略重复计算"""
        if df is None or len(df) < 50:
            return df

        # 检查是否已经预计算过
        if '__precomputed__' in df.columns:
            return df

        n_before = len(df.columns)

        # 移动平均线
        df['ma5'] = calculate_ma(df, period=5, column='close')
        df['ma10'] = calculate_ma(df, period=10, column='close')
        df['ma20'] = calculate_ma(df, period=20, column='close')
        df['ma60'] = calculate_ma(df, period=60, column='close')

        # EMA
        df['ema12'] = calculate_ema(df, period=12, column='close')
        df['ema26'] = calculate_ema(df, period=26, column='close')

        # RSI
        df['rsi6'] = calculate_rsi(df, period=6, column='close')
        df['rsi12'] = calculate_rsi(df, period=12, column='close')
        df['rsi24'] = calculate_rsi(df, period=24, column='close')

        # MACD
        dif, dea, macd_hist = calculate_macd(df, fast_period=12, slow_period=26, signal_period=9, column='close')
        df['macd_dif'] = dif
        df['macd_dea'] = dea
        df['macd_histogram'] = macd_hist

        # KDJ
        k, d, j = calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)
        df['kdj_k'] = k
        df['kdj_d'] = d
        df['kdj_j'] = j

        # 标记已预计算
        df['__precomputed__'] = True

        self.logger.debug(f"Precomputed {len(df.columns) - n_before - 1} indicator columns")

        return df

    def run(
        self,
        stock_list: List[str],
        local_store,
        fetcher
    ) -> Dict[str, Dict[str, float]]:
        """执行所有策略（多进程并行）"""
        # 1. 在主进程预加载所有数据
        self.logger.info("预加载股票数据...")
        stock_data = self._preload_stock_data(stock_list, local_store)

        if not stock_data:
            self.logger.warning("没有足够的股票数据可供分析")
            return {}

        # 2. 多进程执行
        results = {}
        cpu_count = os.cpu_count() or 1
        max_workers = min(cpu_count, 4)

        self.logger.info(f"使用 {max_workers} 个进程处理 {len(stock_data)} 只股票")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _worker_process_stock,
                    stock_code,
                    df,
                    self.config_path
                ): stock_code
                for stock_code, df in stock_data.items()
            }

            for future in as_completed(futures):
                stock_code = futures[future]
                try:
                    stock_results = future.result(timeout=60)
                    if stock_results:
                        results[stock_code] = stock_results
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 时出错: {e}")

        self.logger.info(f"策略执行完成: {len(results)} 只股票产生信号")
        return results
