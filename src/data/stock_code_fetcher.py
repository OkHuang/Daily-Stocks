#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票代码获取脚本 - Stock Code Fetcher

使用 akshare 获取各种指数成分股代码，并保存到文件。
支持：沪深300、上证500、上证50、中证500、中证1000等指数。

使用方法:
    # 获取沪深300成分股
    python -m data.stock_code_fetcher --index csi300

    # 获取上证500成分股
    python -m data.stock_code_fetcher --index sse50

    # 获取所有支持的指数
    python -m data.stock_code_fetcher --all

    # 列出支持的指数
    python -m data.stock_code_fetcher --list
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class StockCodeFetcher:
    """
    股票代码获取器

    使用 akshare 获取各种指数成分股代码
    """

    # 支持的指数配置
    SUPPORTED_INDICES = {
        'csi300': {
            'name': '沪深300',
            'symbol': '000300',
            'file_name': 'csi300.txt',
            'description': '沪深300成分股'
        },
        'sse50': {
            'name': '上证50',
            'symbol': '000016',
            'file_name': 'sse50.txt',
            'description': '上证50成分股'
        },
        'csi500': {
            'name': '中证500',
            'symbol': '000905',
            'file_name': 'csi500.txt',
            'description': '中证500成分股'
        },
        'csi1000': {
            'name': '中证1000',
            'symbol': '000852',
            'file_name': 'csi1000.txt',
            'description': '中证1000成分股'
        },
        'sz50': {
            'name': '深证50',
            'symbol': '399330',
            'file_name': 'sz50.txt',
            'description': '深证50成分股'
        },
        'cyb50': {
            'name': '创业板50',
            'symbol': '399673',
            'file_name': 'cyb50.txt',
            'description': '创业板50成分股'
        },
        'star50': {
            'name': '科创50',
            'symbol': '000688',
            'file_name': 'star50.txt',
            'description': '科创50成分股'
        }
    }

    def __init__(self, output_dir: str = None, logger: logging.Logger = None):
        """
        初始化股票代码获取器

        参数:
            output_dir: 输出目录路径
            logger: 日志记录器
        """
        if output_dir is None:
            # 默认输出到项目根目录下的 stock_code 文件夹
            output_dir = project_root / "stock_code"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logger or logging.getLogger(__name__)
        self._akshare = None

    def _init_akshare(self):
        """延迟初始化 akshare"""
        if self._akshare is None:
            try:
                import akshare as ak
                self._akshare = ak
                self.logger.info("akshare initialized successfully")
            except ImportError:
                raise ImportError(
                    "akshare 未安装，请运行: pip install akshare"
                )

    def _convert_to_tushare_code(self, code: str) -> str:
        """
        转换为 Tushare 格式的股票代码

        参数:
            code: 股票代码（6位数字）

        返回:
            str: Tushare格式代码（如 000001.SZ）
        """
        code = str(code).zfill(6)  # 补齐6位

        if code.startswith('6'):
            return f"{code}.SH"  # 上交所
        elif code.startswith('0') or code.startswith('3'):
            return f"{code}.SZ"  # 深交所
        elif code.startswith('8') or code.startswith('4'):
            return f"{code}.BJ"  # 北交所
        else:
            return code

    def fetch_index_stocks(self, index_key: str) -> Optional[List[str]]:
        """
        获取指数成分股代码

        参数:
            index_key: 指数代码键（如 'csi300', 'sse50'）

        返回:
            Optional[List[str]]: 股票代码列表，失败返回 None
        """
        if index_key not in self.SUPPORTED_INDICES:
            self.logger.error(f"不支持的指数: {index_key}")
            self.logger.error(
                f"支持的指数: {', '.join(self.SUPPORTED_INDICES.keys())}"
            )
            return None

        index_config = self.SUPPORTED_INDICES[index_key]
        self.logger.info(f"正在获取 {index_config['name']} 成分股...")
        self.logger.info(
            f"指数代码: {index_config['symbol']}, "
            f"描述: {index_config['description']}"
        )

        try:
            self._init_akshare()

            # 优先使用中证指数公司官方数据（无重复）
            try:
                df = self._akshare.index_stock_cons_csindex(symbol=index_config['symbol'])
                # 中证指数数据源：证券代码在第5列（索引4）
                code_column_index = 4
                data_source = "中证指数公司官方数据"
                self.logger.info("使用中证指数公司官方数据源")
            except Exception as e:
                # 如果中证指数数据源失败，降级使用新浪数据源
                self.logger.warning(f"中证指数数据源不可用: {e}")
                self.logger.info("降级使用新浪数据源")
                df = self._akshare.index_stock_cons(symbol=index_config['symbol'])
                # 新浪数据源：品种代码列
                code_column_name = '品种代码'
                code_column_index = None
                data_source = "新浪数据源"

            if df is None or len(df) == 0:
                self.logger.error(f"获取 {index_config['name']} 成分股失败：返回数据为空")
                return None

            # 获取股票代码
            if code_column_index is not None:
                # 使用列索引
                stock_codes = [
                    self._convert_to_tushare_code(code)
                    for code in df.iloc[:, code_column_index].tolist()
                ]
            else:
                # 使用列名
                stock_codes = [
                    self._convert_to_tushare_code(code)
                    for code in df[code_column_name].tolist()
                ]

            # 去重并记录
            original_count = len(stock_codes)
            stock_codes = list(dict.fromkeys(stock_codes))  # 保持顺序的去重
            unique_count = len(stock_codes)

            self.logger.info(f"数据源: {data_source}")

            if original_count != unique_count:
                self.logger.warning(
                    f"检测到重复数据: {original_count} -> {unique_count} "
                    f"(去重 {original_count - unique_count} 个)"
                )
            else:
                self.logger.info(f"无重复数据 ({unique_count} 只)")

            self.logger.info(
                f"成功获取 {unique_count} 只 {index_config['name']} 成分股"
            )

            return stock_codes

        except Exception as e:
            self.logger.error(f"获取 {index_config['name']} 成分股失败: {e}")
            return None

    def save_to_file(
        self,
        stock_codes: List[str],
        file_name: str,
        index_name: str = None
    ) -> bool:
        """
        保存股票代码到文件

        参数:
            stock_codes: 股票代码列表
            file_name: 文件名
            index_name: 指数名称（用于文件头注释）

        返回:
            bool: 是否成功
        """
        if not stock_codes:
            self.logger.error("股票代码列表为空，无法保存")
            return False

        file_path = self.output_dir / file_name

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入文件头
                if index_name:
                    f.write(f"# {index_name} 成分股\n")
                    f.write(f"# 总数: {len(stock_codes)} 只\n")
                    f.write(f"# 更新时间: {self._get_current_time()}\n")
                    f.write("#" + "=" * 50 + "\n\n")

                # 写入股票代码
                for code in stock_codes:
                    f.write(f"{code}\n")

            self.logger.info(f"已保存 {len(stock_codes)} 只股票到: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"保存文件失败: {e}")
            return False

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def fetch_and_save(self, index_key: str) -> bool:
        """
        获取并保存指数成分股

        参数:
            index_key: 指数代码键

        返回:
            bool: 是否成功
        """
        index_config = self.SUPPORTED_INDICES.get(index_key)

        if not index_config:
            self.logger.error(f"不支持的指数: {index_key}")
            return False

        # 获取股票代码
        stock_codes = self.fetch_index_stocks(index_key)

        if not stock_codes:
            return False

        # 保存到文件
        file_name = index_config['file_name']
        index_name = index_config['name']

        return self.save_to_file(stock_codes, file_name, index_name)

    def fetch_all_and_save(self) -> Dict[str, bool]:
        """
        获取所有支持的指数成分股并保存

        返回:
            Dict[str, bool]: 各指数的获取结果
        """
        results = {}

        self.logger.info("=" * 60)
        self.logger.info("开始获取所有支持的指数成分股")
        self.logger.info("=" * 60)

        for index_key in self.SUPPORTED_INDICES.keys():
            self.logger.info(f"\n处理: {index_key}")
            results[index_key] = self.fetch_and_save(index_key)

        self.logger.info("\n" + "=" * 60)
        self.logger.info("所有指数成分股获取完成")
        self.logger.info("=" * 60)

        # 统计结果
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        self.logger.info(f"成功: {success_count}/{total_count}")
        self.logger.info(f"失败: {total_count - success_count}/{total_count}")

        return results

    def list_supported_indices(self):
        """列出所有支持的指数"""
        print("=" * 60)
        print("支持的指数列表")
        print("=" * 60)

        for key, config in self.SUPPORTED_INDICES.items():
            print(f"\n指数代码: {key}")
            print(f"  名称: {config['name']}")
            print(f"  symbol: {config['symbol']}")
            print(f"  文件名: {config['file_name']}")
            print(f"  描述: {config['description']}")

        print("\n" + "=" * 60)
        print(f"总计: {len(self.SUPPORTED_INDICES)} 个指数")
        print("=" * 60)


def setup_logger(level: str = 'INFO') -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger('stock_code_fetcher')
    logger.setLevel(getattr(logging, level))

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level))

    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='股票代码获取脚本 - Stock Code Fetcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例 (Examples):
  # 获取沪深300成分股
  python -m data.stock_code_fetcher --index csi300

  # 获取上证50成分股
  python -m data.stock_code_fetcher --index sse50

  # 获取所有支持的指数
  python -m data.stock_code_fetcher --all

  # 列出支持的指数
  python -m data.stock_code_fetcher --list

  # 指定输出目录
  python -m data.stock_code_fetcher --index csi300 --output ./stock_codes
        '''
    )

    parser.add_argument(
        '--index',
        type=str,
        help='指数代码（如 csi300, sse50, csi500等）'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='获取所有支持的指数成分股'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='列出所有支持的指数'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出目录路径（默认: stock_picker/stock_code/）'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细日志输出'
    )

    args = parser.parse_args()

    # 设置日志
    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = setup_logger(log_level)

    # 如果没有任何参数，显示帮助信息
    if not args.index and not args.all and not args.list:
        parser.print_help()
        return

    # 创建获取器
    fetcher = StockCodeFetcher(output_dir=args.output, logger=logger)

    # 执行相应操作
    if args.list:
        # 列出支持的指数
        fetcher.list_supported_indices()

    elif args.all:
        # 获取所有指数
        results = fetcher.fetch_all_and_save()

        # 返回状态码
        success = all(results.values())
        sys.exit(0 if success else 1)

    elif args.index:
        # 获取指定指数
        success = fetcher.fetch_and_save(args.index)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
