"""
数据获取模块 - Data Fetcher Module

该模块定义了数据获取的抽象接口和具体实现，用于从各种数据源获取A股行情数据。
This module defines the abstract interface and concrete implementations for fetching A-share market data.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import time
import logging


class BaseFetcher(ABC):
    """
    数据获取器抽象基类
    Abstract base class for data fetchers

    所有数据源实现需要继承此类并实现 fetch_daily 方法。
    All data source implementations should inherit from this class and implement the fetch_daily method.
    """

    @abstractmethod
    def fetch_daily(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取单只股票的日线数据
        Fetch daily market data for a single stock

        参数 (Parameters):
            stock_code: 股票代码，如 '000001.SZ' (Stock code, e.g., '000001.SZ')
            start_date: 开始日期，格式 'YYYYMMDD' (Start date, format 'YYYYMMDD')
            end_date: 结束日期，格式 'YYYYMMDD' (End date, format 'YYYYMMDD')

        返回 (Returns):
            pd.DataFrame: 包含以下列的日线数据 (Daily data with following columns):
                - trade_date: 交易日期 (Trading date)
                - open: 开盘价 (Open price)
                - high: 最高价 (High price)
                - low: 最低价 (Low price)
                - close: 收盘价 (Close price)
                - vol: 成交量 (Volume)
                - amount: 成交额 (Amount)

        异常 (Raises):
            NotImplementedError: 子类必须实现此方法 (Subclasses must implement this method)
        """
        raise NotImplementedError("Subclasses must implement fetch_daily()")

    @abstractmethod
    def fetch_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表
        Fetch the list of all stocks

        返回 (Returns):
            pd.DataFrame: 股票列表信息 (Stock list information):
                - ts_code: 股票代码 (Stock code)
                - name: 股票名称 (Stock name)
                - industry: 所属行业 (Industry)
                - list_date: 上市日期 (Listing date)
        """
        raise NotImplementedError("Subclasses must implement fetch_stock_list()")


class TushareFetcher(BaseFetcher):
    """
    Tushare Pro 数据获取器实现
    Tushare Pro data fetcher implementation

    使用 Tushare Pro API 获取A股行情数据。
    Uses Tushare Pro API to fetch A-share market data.

    功能特性 (Features):
    - 自动重试机制 (Automatic retry mechanism)
    - 频率限制处理 (Rate limit handling)
    - 错误日志记录 (Error logging)
    - 请求间隔控制 (Request interval control)
    """

    def __init__(
        self,
        token: str,
        api_config: dict = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化 Tushare 数据获取器
        Initialize Tushare fetcher

        参数 (Parameters):
            token: Tushare Pro API Token
            api_config: API 配置字典 (API config dict)，包含:
                - max_retries: 最大重试次数 (default: 3)
                - retry_delay: 重试延迟（秒）(default: 2.0)
                - request_delay: 请求间隔（秒）(default: 0.3)
            logger: 日志记录器 (Logger instance)
        """
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
        self._session = None  # 可选的 session 对象，用于高级 HTTP 管理

    def _init_api(self):
        """
        初始化 Tushare API 连接
        Initialize Tushare API connection

        该方法延迟初始化 API 对象，避免在未使用时建立连接。
        This method lazily initializes the API object to avoid establishing connections when not in use.
        """
        if self._api is None:
            import tushare as ts
            ts.set_token(self.token)
            self._api = ts.pro_api()
            self.logger.info("Tushare API initialized")

    def _wait_for_rate_limit(self):
        """
        等待以符合频率限制
        Wait to comply with rate limit

        确保两次请求之间有足够的间隔，避免触发频率限制。
        Ensures sufficient interval between requests to avoid triggering rate limits.
        """
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
        """
        带重试机制的数据获取
        Fetch data with retry mechanism

        参数 (Parameters):
            fetch_func: 数据获取函数 (Data fetching function)
            *args: 位置参数 (Positional arguments)
            **kwargs: 关键字参数 (Keyword arguments)

        返回 (Returns):
            Optional[pd.DataFrame]: 获取的数据，失败返回 None (Fetched data, None on failure)
        """
        for attempt in range(self.max_retries):
            try:
                # 频率限制控制 (Rate limit control)
                self._wait_for_rate_limit()

                # 执行请求 (Execute request)
                df = fetch_func(*args, **kwargs)

                if df is not None and len(df) > 0:
                    self.logger.debug(f"Fetch successful on attempt {attempt + 1}")
                    return df
                else:
                    self.logger.warning(f"Fetch returned empty data on attempt {attempt + 1}")

            except Exception as e:
                error_msg = str(e)

                # 检查是否是频率限制错误
                # Check if it's a rate limit error
                if "每分钟" in error_msg or "频率" in error_msg or "限制" in error_msg:
                    self.logger.warning(f"Rate limit detected on attempt {attempt + 1}: {error_msg}")
                    if attempt < self.max_retries - 1:
                        # 等待更长时间后重试
                        # Wait longer before retry
                        wait_time = self.retry_delay * (attempt + 1)
                        self.logger.info(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue

                # 其他错误
                # Other errors
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
        """
        从 Tushare 获取单只股票的日线数据
        Fetch daily market data for a single stock from Tushare

        参数 (Parameters):
            stock_code: 股票代码 (Stock code)
            start_date: 开始日期，格式 'YYYYMMDD' (Start date)
            end_date: 结束日期，格式 'YYYYMMDD' (End date)

        返回 (Returns):
            pd.DataFrame: 日线数据 (Daily data)
        """
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
        """
        从 Tushare 获取股票列表
        Fetch stock list from Tushare

        返回 (Returns):
            pd.DataFrame: 股票列表 (Stock list)
        """
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
        """
        清理 API 资源
        Cleanup API resources

        释放 Tushare API 对象和相关的网络连接。
        Release Tushare API object and related network connections.
        """
        if hasattr(self, '_session') and self._session is not None:
            self._session.close()
            self._session = None
            self.logger.debug("Closed HTTP session")

        self._api = None
        self.logger.info("Tushare API resources cleaned up")

    def __del__(self):
        """
        析构函数，确保资源被释放
        Destructor to ensure resources are released
        """
        try:
            self.cleanup()
        except Exception:
            # 在析构函数中忽略所有错误
            # Ignore all errors in destructor
            pass
