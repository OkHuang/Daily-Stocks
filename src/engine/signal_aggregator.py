"""信号汇总模块"""

from typing import Dict, List
import pandas as pd


class SignalAggregator:
    """信号汇总器，提供加权平均、布尔与/或等多种信号合并方式"""

    def __init__(self, method: str = "weighted_sum"):
        self.method = method

    def aggregate(self, results: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        if not results:
            return pd.DataFrame()

        # 构建 DataFrame
        df_data = []
        for stock_code, signals in results.items():
            row = {'ts_code': stock_code}
            row.update(signals)
            row['signal_count'] = len(signals)
            df_data.append(row)

        df = pd.DataFrame(df_data)

        # 填充 NaN 为 0
        df = df.fillna(0)

        # 根据方法计算综合评分
        if self.method == "weighted_sum":
            # 加权求和（假设权重已在信号中体现）
            signal_columns = [col for col in df.columns if col not in ['ts_code', 'signal_count']]
            df['score'] = df[signal_columns].sum(axis=1)

        elif self.method == "weighted_avg":
            signal_columns = [col for col in df.columns if col not in ['ts_code', 'signal_count']]
            df['score'] = df[signal_columns].mean(axis=1)

        elif self.method == "and":
            # 布尔与：所有策略都有信号才得1分
            signal_columns = [col for col in df.columns if col not in ['ts_code', 'signal_count']]
            df['score'] = (df[signal_columns] > 0).all(axis=1).astype(int)

        elif self.method == "or":
            # 布尔或：任一策略有信号就得1分
            signal_columns = [col for col in df.columns if col not in ['ts_code', 'signal_count']]
            df['score'] = (df[signal_columns] > 0).any(axis=1).astype(int)

        # 按评分降序排序
        df = df.sort_values('score', ascending=False).reset_index(drop=True)

        return df

    def get_top_stocks(
        self,
        results: Dict[str, Dict[str, float]],
        top_n: int = 20
    ) -> pd.DataFrame:
        df = self.aggregate(results)
        return df.head(top_n)

    def filter_by_min_score(
        self,
        results: Dict[str, Dict[str, float]],
        min_score: float
    ) -> pd.DataFrame:
        df = self.aggregate(results)
        return df[df['score'] >= min_score].reset_index(drop=True)

    def filter_by_min_signals(
        self,
        results: Dict[str, Dict[str, float]],
        min_signals: int
    ) -> pd.DataFrame:
        df = self.aggregate(results)
        return df[df['signal_count'] >= min_signals].reset_index(drop=True)
