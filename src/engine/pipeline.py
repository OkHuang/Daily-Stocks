"""主流程编排模块"""

from typing import Dict, Any, List
import pandas as pd
from pathlib import Path

from data.fetcher import BaseFetcher, TushareFetcher
from data.local_store import LocalStore
from data.stock_pool import StockPool
from engine.strategy_runner import StrategyRunner
from engine.signal_aggregator import SignalAggregator
from outputs.formatter import Formatter
from utils.logger import setup_logger


class Pipeline:
    """选股流程主控制器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logger(
            level=config['logging']['level'],
            log_file=config['logging']['file'],
            console=config['logging']['console']
        )

        # 初始化各模块
        self.fetcher = self._init_fetcher()
        self.local_store = LocalStore(db_path=config['storage']['path'])
        self.stock_pool = StockPool(
            source=config['stock_pool']['source'],
            custom_file=config['stock_pool'].get('custom_list')
        )
        self.strategy_runner = StrategyRunner(config.get('strategies_config'))
        self.signal_aggregator = SignalAggregator()
        self.formatter = Formatter()

    def _cleanup_resources(self):
        """关闭数据库连接、清理 API 对象等"""
        if hasattr(self, 'local_store') and self.local_store:
            try:
                self.local_store.close()
                self.logger.debug("Closed local_store connection")
            except Exception as e:
                self.logger.error(f"Error closing local_store: {e}")

        if hasattr(self, 'fetcher') and self.fetcher:
            try:
                self.fetcher.cleanup()
                self.logger.debug("Cleaned up fetcher resources")
            except Exception as e:
                self.logger.error(f"Error cleaning up fetcher: {e}")

        self.logger.info("All resources cleaned up")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_resources()
        return False

    def _init_fetcher(self) -> BaseFetcher:
        provider = self.config['data_source']['provider']
        token = self.config['data_source']['token']

        if provider == "tushare":
            return TushareFetcher(token=token)
        else:
            raise ValueError(f"Unsupported data provider: {provider}")

    def run(self, date: str = None) -> pd.DataFrame:
        try:
            self.logger.info("Starting stock selection pipeline...")

            # 1. 获取股票池
            self.logger.info("Fetching stock pool...")
            stock_list = self.stock_pool.get_stock_list()
            self.logger.info(f"Total stocks in pool: {len(stock_list)}")

            # 2. 初始化数据库表结构（数据更新由 collect.py 负责）
            self.local_store._init_tables()

            # 3. 执行策略
            self.logger.info("Executing strategies...")
            results = self.strategy_runner.run(
                stock_list=stock_list,
                local_store=self.local_store,
                fetcher=self.fetcher
            )

            # 4. 汇总信号
            self.logger.info("Aggregating signals...")
            final_results = self.signal_aggregator.aggregate(results)

            # 5. 排序并返回前 N 只股票
            top_n = self.config['output'].get('top_n', 20)
            final_results = final_results.head(top_n)

            # 6. 输出结果
            self.logger.info("Outputting results...")
            self._save_results(final_results, date)

            self.logger.info("Pipeline completed successfully!")
            return final_results

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            raise
        finally:
            # 确保资源总是被清理
            self._cleanup_resources()

    def _save_results(self, results: pd.DataFrame, date: str = None):
        # 确定输出目录
        output_path = Path(self.config['output']['path'])
        output_path.mkdir(parents=True, exist_ok=True)

        # 确定文件名
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime("%Y%m%d")

        base_name = f"{date}_result"

        # 根据配置格式输出
        formats = self.config['output'].get('formats', ['csv'])

        for fmt in formats:
            if fmt == 'csv':
                file_path = output_path / f"{base_name}.csv"
                self.formatter.to_csv(results, file_path)
                self.logger.info(f"Results saved to: {file_path}")
            elif fmt == 'excel':
                file_path = output_path / f"{base_name}.xlsx"
                self.formatter.to_excel(results, file_path)
                self.logger.info(f"Results saved to: {file_path}")
            elif fmt == 'markdown':
                file_path = output_path / f"{base_name}.md"
                self.formatter.to_markdown(results, file_path)
                self.logger.info(f"Results saved to: {file_path}")

        # 打印摘要
        self.formatter.print_summary(results)
