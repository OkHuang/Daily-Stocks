"""数据获取抽象接口和 Tushare Pro 实现"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import time
import logging


class BaseFetcher(ABC):
    """数据获取器抽象基类"""

    @abstractmethod
    def fetch_daily(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """获取单只股票的日线数据"""
        raise NotImplementedError("Subclasses must implement fetch_daily()")

    @abstractmethod
    def fetch_stock_list(self) -> Optional[pd.DataFrame]:
        """获取股票列表"""
        raise NotImplementedError("Subclasses must implement fetch_stock_list()")


class TushareFetcher(BaseFetcher):
    """Tushare Pro 数据获取器，支持自动重试和频率限制"""

    def __init__(
        self,
        token: str,
        api_config: dict = None,
        logger: Optional[logging.Logger] = None
    ):
        self.token = token

        # 使用配置文件中的参数，如果未提供则使用默认值
        if api_config is None:
            api_config = {}

        self.max_retries = api_config.get('max_retries', 3)
        self.retry_delay = api_config.get('retry_delay', 2.0)
        self.request_delay = api_config.get('request_delay', 0.3)

        self.logger = logger or logging.getLogger(__name__)
        self._api = None
        self._last_request_time = 0
        self._session = None

    def _init_api(self):
        """延迟初始化 Tushare API，避免未使用时建立连接"""
        if self._api is None:
            import tushare as ts
            ts.set_token(self.token)
            self._api = ts.pro_api()
            self.logger.info("Tushare API initialized")

    def _wait_for_rate_limit(self):
        """确保两次请求之间有足够间隔，避免触发频率限制"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time

        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            self.logger.debug(f"Rate limit: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _fetch_with_retry(
        self,
        fetch_func,
        *args,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """带重试机制的数据获取"""
        for attempt in range(self.max_retries):
            try:
                self._wait_for_rate_limit()

                df = fetch_func(*args, **kwargs)

                if df is not None and len(df) > 0:
                    self.logger.debug(f"Fetch successful on attempt {attempt + 1}")
                    return df
                else:
                    self.logger.warning(f"Fetch returned empty data on attempt {attempt + 1}")

            except Exception as e:
                error_msg = str(e)

                # 检查是否是频率限制错误
                if "每分钟" in error_msg or "频率" in error_msg or "限制" in error_msg:
                    self.logger.warning(f"Rate limit detected on attempt {attempt + 1}: {error_msg}")
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (attempt + 1)
                        self.logger.info(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue

                self.logger.error(f"Fetch failed on attempt {attempt + 1}: {error_msg}")

                if attempt < self.max_retries - 1:
                    self.logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(f"Max retries ({self.max_retries}) reached")

        return None

    def fetch_daily(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """从 Tushare 获取单只股票的日线数据"""
        self._init_api()

        def _fetch():
            return self._api.daily(
                ts_code=stock_code,
                start_date=start_date,
                end_date=end_date
            )

        df = self._fetch_with_retry(_fetch)

        if df is not None and len(df) > 0:
            self.logger.info(f"Successfully fetched {len(df)} records for {stock_code}")
        else:
            self.logger.error(f"Failed to fetch data for {stock_code}")

        return df

    def fetch_stock_list(self) -> Optional[pd.DataFrame]:
        """从 Tushare 获取股票列表"""
        self._init_api()

        def _fetch():
            return self._api.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,name,industry,list_date'
            )

        df = self._fetch_with_retry(_fetch)

        if df is not None and len(df) > 0:
            self.logger.info(f"Successfully fetched {len(df)} stocks")
        else:
            self.logger.error("Failed to fetch stock list")

        return df

    def cleanup(self):
        """释放 Tushare API 对象和相关网络连接"""
        if hasattr(self, '_session') and self._session is not None:
            self._session.close()
            self._session = None
            self.logger.debug("Closed HTTP session")

        self._api = None
        self.logger.info("Tushare API resources cleaned up")

    def __del__(self):
        """析构函数，确保资源被释放"""
        try:
            self.cleanup()
        except Exception:
            pass
