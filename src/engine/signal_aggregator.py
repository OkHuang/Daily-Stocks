"""
信号汇总模块 - Signal Aggregator Module

该模块负责汇总和加权合并各策略信号。
This module is responsible for aggregating and weighting signals from various strategies.
"""

from typing import Dict, List
import pandas as pd


class SignalAggregator:
    """
    信号汇总器
    Signal aggregator

    提供多种信号合并方式，如加权平均、布尔与/或等。
    Provides various signal combination methods such as weighted average, boolean AND/OR, etc.
    """

    def __init__(self, method: str = "weighted_sum"):
        """
        初始化信号汇总器
        Initialize signal aggregator

        参数 (Parameters):
            method: 信号合并方法 (Signal combination method):
                - 'weighted_sum': 加权求和 (Weighted sum)
                - 'weighted_avg': 加权平均 (Weighted average)
                - 'and': 布尔与（所有策略都有信号）(Boolean AND: all strategies have signals)
                - 'or': 布尔或（任一策略有信号）(Boolean OR: any strategy has signal)
        """
        self.method = method

    def aggregate(self, results: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        """
        汇总所有股票的策略信号
        Aggregate strategy signals for all stocks

        参数 (Parameters):
            results: 策略执行结果 (Strategy execution results):
                - 键: 股票代码 (Key: stock code)
                - 值: 策略信号字典 (Value: strategy signal dictionary)

        返回 (Returns):
            pd.DataFrame: 汇总结果，包含以下列 (Aggregated results with following columns):
                - ts_code: 股票代码 (Stock code)
                - score: 综合评分 (Composite score)
                - signal_count: 有信号的策略数量 (Number of strategies with signals)
                - [strategy_names]: 各策略信号 (Signals for each strategy)
        """
        if not results:
            return pd.DataFrame()

        # 构建 DataFrame
        # Build DataFrame
        df_data = []
        for stock_code, signals in results.items():
            row = {'ts_code': stock_code}
            row.update(signals)
            row['signal_count'] = len(signals)
            df_data.append(row)

        df = pd.DataFrame(df_data)

        # 填充 NaN 为 0
        # Fill NaN with 0
        df = df.fillna(0)

        # 根据方法计算综合评分
        # Calculate composite score based on method
        if self.method == "weighted_sum":
            # 加权求和（假设权重已在信号中体现）
            # Weighted sum (assuming weights are already reflected in signals)
            signal_columns = [col for col in df.columns if col not in ['ts_code', 'signal_count']]
            df['score'] = df[signal_columns].sum(axis=1)

        elif self.method == "weighted_avg":
            # 加权平均
            # Weighted average
            signal_columns = [col for col in df.columns if col not in ['ts_code', 'signal_count']]
            df['score'] = df[signal_columns].mean(axis=1)

        elif self.method == "and":
            # 布尔与：所有策略都有信号才得1分
            # Boolean AND: score is 1 only if all strategies have signals
            signal_columns = [col for col in df.columns if col not in ['ts_code', 'signal_count']]
            df['score'] = (df[signal_columns] > 0).all(axis=1).astype(int)

        elif self.method == "or":
            # 布尔或：任一策略有信号就得1分
            # Boolean OR: score is 1 if any strategy has signal
            signal_columns = [col for col in df.columns if col not in ['ts_code', 'signal_count']]
            df['score'] = (df[signal_columns] > 0).any(axis=1).astype(int)

        # 按评分降序排序
        # Sort by score in descending order
        df = df.sort_values('score', ascending=False).reset_index(drop=True)

        return df

    def get_top_stocks(
        self,
        results: Dict[str, Dict[str, float]],
        top_n: int = 20
    ) -> pd.DataFrame:
        """
        获取评分前 N 的股票
        Get top N stocks by score

        参数 (Parameters):
            results: 策略执行结果 (Strategy execution results)
            top_n: 返回前 N 只股票 (Return top N stocks)

        返回 (Returns):
            pd.DataFrame: 前 N 只股票 (Top N stocks)
        """
        df = self.aggregate(results)
        return df.head(top_n)

    def filter_by_min_score(
        self,
        results: Dict[str, Dict[str, float]],
        min_score: float
    ) -> pd.DataFrame:
        """
        根据最小评分筛选股票
        Filter stocks by minimum score

        参数 (Parameters):
            results: 策略执行结果 (Strategy execution results)
            min_score: 最小评分阈值 (Minimum score threshold)

        返回 (Returns):
            pd.DataFrame: 筛选后的股票 (Filtered stocks)
        """
        df = self.aggregate(results)
        return df[df['score'] >= min_score].reset_index(drop=True)

    def filter_by_min_signals(
        self,
        results: Dict[str, Dict[str, float]],
        min_signals: int
    ) -> pd.DataFrame:
        """
        根据最小信号数量筛选股票
        Filter stocks by minimum number of signals

        参数 (Parameters):
            results: 策略执行结果 (Strategy execution results)
            min_signals: 最小信号数量 (Minimum number of signals)

        返回 (Returns):
            pd.DataFrame: 筛选后的股票 (Filtered stocks)
        """
        df = self.aggregate(results)
        return df[df['signal_count'] >= min_signals].reset_index(drop=True)
