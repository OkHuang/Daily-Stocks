"""股票池管理，支持全A股、指数成分股和失败股票列表"""

from typing import List, Union
from pathlib import Path
import logging


class StockPool:
    """股票池管理类，支持多种来源"""

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
        self.source = source
        self.token = token
        self.logger = logger or logging.getLogger(__name__)
        self._stock_list = None
        self._api = None

        # 设置 stock_code 目录
        if stock_code_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.stock_code_dir = project_root / "stock_code"
        else:
            self.stock_code_dir = Path(stock_code_dir)

    def get_stock_list(self) -> List[str]:
        """获取股票池列表"""
        if self._stock_list is None:
            if self.source == "all_a":
                self._stock_list = self.get_all_a_stocks()
            elif self.source in self.STOCK_CODE_FILES:
                self._stock_list = self._get_from_file(self.source)
            else:
                raise ValueError(
                    f"Unknown stock pool source: {self.source}. "
                    f"Supported sources: 'all_a', {', '.join(self.STOCK_CODE_FILES.keys())}"
                )
        return self._stock_list

    def get_all_a_stocks(self) -> List[str]:
        """获取全部A股代码列表"""
        self._init_api()

        try:
            df = self._api.stock_basic(
                exchange='',
                list_status='L',
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
        """从 stock_code 文件夹读取股票列表"""
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
