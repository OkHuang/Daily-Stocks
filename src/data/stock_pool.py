"""
股票池管理模块 - Stock Pool Management Module

该模块负责获取和管理待选股票池。
This module is responsible for managing the pool of stocks to be analyzed.

数据来源 (Data Sources):
    1. 全部A股：通过 Tushare API 获取
    2. 指数成分股：从 stock_code 文件夹读取预生成的文件
    3. 失败股票：从 stock_code/failed_stocks.txt 读取
"""

from typing import List, Union
from pathlib import Path
import logging


class StockPool:
    """
    股票池管理类
    Stock pool manager

    支持的股票来源:
    - 'all_a': 全部A股（通过 Tushare API 获取）
    - 'csi300': 沪深300（从 stock_code/csi300.txt 读取）
    - 'sse50': 上证50（从 stock_code/sse50.txt 读取）
    - 'csi500': 中证500（从 stock_code/csi500.txt 读取）
    - 'csi1000': 中证1000（从 stock_code/csi1000.txt 读取）
    - 'sz50': 深证50（从 stock_code/sz50.txt 读取）
    - 'cyb50': 创业板50（从 stock_code/cyb50.txt 读取）
    - 'star50': 科创50（从 stock_code/star50.txt 读取）
    - 'failed': 获取失败的股票（从 stock_code/failed_stocks.txt 读取）
    """

    # 股票代码文件映射
    STOCK_CODE_FILES = {
        'csi300': 'csi300.txt',      # 沪深300
        'sse50': 'sse50.txt',         # 上证50
        'csi500': 'csi500.txt',       # 中证500
        'csi1000': 'csi1000.txt',     # 中证1000
        'sz50': 'sz50.txt',           # 深证50
        'cyb50': 'cyb50.txt',         # 创业板50
        'star50': 'star50.txt',       # 科创50
        'failed': 'failed_stocks.txt', # 获取失败的股票
    }

    def __init__(
        self,
        source: str = "all_a",
        token: str = None,
        logger: Union[logging.Logger, None] = None,
        stock_code_dir: str = None
    ):
        """
        初始化股票池
        Initialize stock pool

        参数 (Parameters):
            source: 股票池来源，支持:
                - 'all_a': 全部A股（使用 Tushare API 获取）
                - 'csi300', 'sse50', 'csi500' 等: 从 stock_code 文件夹读取
                - 'failed': 从 stock_code/failed_stocks.txt 读取
            token: Tushare API Token（用于获取全部A股时必需）
            logger: 日志记录器
            stock_code_dir: stock_code 文件夹路径（默认: 项目根目录/stock_code）
        """
        self.source = source
        self.token = token
        self.logger = logger or logging.getLogger(__name__)
        self._stock_list = None
        self._api = None

        # 设置 stock_code 目录
        if stock_code_dir is None:
            # 默认使用项目根目录下的 stock_code 文件夹
            project_root = Path(__file__).parent.parent.parent
            self.stock_code_dir = project_root / "stock_code"
        else:
            self.stock_code_dir = Path(stock_code_dir)

    def get_stock_list(self) -> List[str]:
        """
        获取股票池列表
        Get stock pool list

        返回 (Returns):
            List[str]: 股票代码列表 (List of stock codes)
        """
        if self._stock_list is None:
            if self.source == "all_a":
                # 使用 Tushare API 获取全部A股
                self._stock_list = self.get_all_a_stocks()
            elif self.source in self.STOCK_CODE_FILES:
                # 从 stock_code 文件夹读取
                self._stock_list = self._get_from_file(self.source)
            else:
                raise ValueError(
                    f"Unknown stock pool source: {self.source}. "
                    f"Supported sources: 'all_a', {', '.join(self.STOCK_CODE_FILES.keys())}"
                )
        return self._stock_list

    def get_all_a_stocks(self) -> List[str]:
        """
        获取全部A股代码列表
        Get all A-shares list

        返回 (Returns):
            List[str]: A股代码列表 (List of A-share codes)
        """
        self._init_api()

        try:
            df = self._api.stock_basic(
                exchange='',
                list_status='L',  # 只获取上市股票
                fields='ts_code'
            )

            if df is not None and len(df) > 0:
                self.logger.info(f"获取到 {len(df)} 只A股")
                return df['ts_code'].tolist()
            else:
                self.logger.error("获取股票列表失败")
                return []

        except Exception as e:
            self.logger.error(f"获取A股列表失败: {e}")
            return []

    def _init_api(self):
        """初始化 Tushare API"""
        if self._api is None:
            if not self.token:
                raise ValueError("Token is required for fetching stock list from API")

            import tushare as ts
            ts.set_token(self.token)
            self._api = ts.pro_api()
            self.logger.info("Tushare API initialized")

    def _get_from_file(self, source: str) -> List[str]:
        """
        从 stock_code 文件夹读取股票列表
        Get stock list from stock_code directory

        参数 (Parameters):
            source: 股票池来源（如 'csi300', 'sse50', 'failed' 等）

        返回 (Returns):
            List[str]: 股票代码列表 (List of stock codes)

        异常 (Raises):
            FileNotFoundError: 文件不存在 (File not found)
        """
        if source not in self.STOCK_CODE_FILES:
            raise ValueError(f"Unknown source: {source}")

        file_name = self.STOCK_CODE_FILES[source]
        file_path = self.stock_code_dir / file_name

        if not file_path.exists():
            raise FileNotFoundError(
                f"Stock code file not found: {file_path}\n"
                f"Please run: python -m src.data.stock_code_fetcher --index {source}"
            )

        self.logger.info(f"从文件读取股票代码: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                stock_list = []
                for line in f:
                    line = line.strip()
                    # 跳过注释行和空行
                    if line and not line.startswith('#'):
                        stock_list.append(line)

            self.logger.info(f"成功读取 {len(stock_list)} 只股票")
            return stock_list

        except Exception as e:
            self.logger.error(f"读取文件失败: {e}")
            raise
