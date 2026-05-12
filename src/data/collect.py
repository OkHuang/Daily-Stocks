#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据收集脚本 - Data Collection Script

提供全量收集和增量收集功能：
- 全量收集：从2013-01-01到当前时间收集所有股票数据
- 增量收集：自动判断数据库最新时间，收集新增数据

使用方法:
    # 全量收集
    python -m data.collect --mode full

    # 增量收集
    python -m data.collect --mode incremental

    # 指定股票列表
    python -m data.collect --mode full --stocks 000001.SZ,000002.SZ

    # 自定义起始日期
    python -m data.collect --mode full --start 20200101
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.fetcher import TushareFetcher
from src.data.local_store import LocalStore
from src.data.stock_pool import StockPool
from src.utils.logger import setup_logger
from src.config.config_manager import ConfigManager


def collect_full(
    token: str,
    db_path: str,
    start_date: str = "20130101",
    end_date: str = None,
    stock_list: list = None,
    logger=None,
    update_failed_file: bool = False
) -> dict:
    """
    全量数据收集

    从固定起始日期（默认2013-01-01）到当前时间收集所有股票数据。
    收集后覆盖数据库中的全部数据。

    参数:
        token: Tushare API Token
        db_path: 数据库文件路径
        start_date: 开始日期，格式 YYYYMMDD，默认 20130101
        end_date: 结束日期，格式 YYYYMMDD，默认最近交易日
        stock_list: 股票代码列表，为 None 时获取全部A股
        logger: 日志记录器
        update_failed_file: 是否更新 failed_stocks.txt 文件（当收集失败的股票时）

    返回:
        dict: 收集统计信息
    """
    logger.info("=" * 60)
    logger.info("开始全量数据收集")
    logger.info("Starting Full Data Collection")
    logger.info("=" * 60)

    # 1. 确定时间范围
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
        logger.info(f"结束日期 (End date): {end_date}")

    logger.info(f"时间范围 (Date range): {start_date} - {end_date}")
    logger.info(f"说明 (Note): 将覆盖数据库中的全部历史数据\n")

    # 2. 初始化组件
    fetcher = TushareFetcher(token=token, logger=logger)
    local_store = LocalStore(db_path=db_path, logger=logger)

    # 3. 获取股票列表
    if stock_list is None:
        logger.info("正在获取全部A股列表...")
        stock_pool = StockPool(source="all_a", token=token, logger=logger)
        stock_list = stock_pool.get_all_a_stocks()

        if stock_list and len(stock_list) > 0:
            logger.info(f"获取到 {len(stock_list)} 只股票\n")
        else:
            logger.error("获取股票列表失败")
            return {
                'total_stocks': 0,
                'success': 0,
                'failed': 0,
                'total_records': 0
            }

    # 4. 批量收集数据
    stats = local_store.update_daily_data(
        stock_list=stock_list,
        fetcher=fetcher,
        start_date=start_date,
        end_date=end_date
    )

    # 5. 打印统计信息
    logger.info("\n" + "=" * 60)
    logger.info("全量数据收集完成")
    logger.info("Full Data Collection Completed")
    logger.info(f"总股票数 (Total): {stats['total']}")
    logger.info(f"成功 (Success): {stats['success']}")
    logger.info(f"失败 (Failed): {stats['failed']}")
    logger.info(f"总记录数 (Total records): {stats['total_records']}")
    logger.info("=" * 60)

    # 6. 更新 failed_stocks.txt 文件（如果需要）
    if update_failed_file:
        _update_failed_stocks_file(stats, logger)

    # 7. 关闭数据库
    local_store.close()

    return stats


def _update_failed_stocks_file(stats: dict, logger):
    """
    更新 failed_stocks.txt 文件

    如果有失败的股票，更新文件内容；如果全部成功，删除文件。

    参数:
        stats: 收集统计信息
        logger: 日志记录器
    """
    if not stats.get('failed_stocks'):
        # 没有失败的股票，删除文件
        project_root = Path(__file__).parent.parent.parent
        failed_file = project_root / "stock_code" / "failed_stocks.txt"

        if failed_file.exists():
            failed_file.unlink()
            logger.info(f"已删除失败股票文件: {failed_file}")
        return

    # 有失败的股票，更新文件
    project_root = Path(__file__).parent.parent.parent
    failed_file = project_root / "stock_code" / "failed_stocks.txt"

    with open(failed_file, 'w', encoding='utf-8') as f:
        # 写入文件头
        f.write("# 获取失败的股票列表\n")
        f.write("# 这些股票在数据收集过程中因API频率限制等原因未能成功获取\n")
        f.write(f"# 总数: {len(stats['failed_stocks'])} 只\n")
        f.write(f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("#" + "=" * 50 + "\n\n")

        # 写入股票代码
        for stock in stats['failed_stocks']:
            f.write(f"{stock}\n")

    logger.info(f"已更新失败股票文件: {failed_file}")
    logger.info(f"仍需重试的股票: {len(stats['failed_stocks'])} 只")


def _get_next_day(date: str) -> str:
    """
    获取指定日期之后的一天（用于增量收集的起始日期）

    直接返回日期+1，让 Tushare API 自动处理非交易日。
    Returns date + 1 directly, letting Tushare API handle non-trading days automatically.

    参数 (Parameters):
        date: 指定日期，格式 YYYYMMDD

    返回 (Returns):
        str: 下一天日期，格式 YYYYMMDD

    示例 (Examples):
        20260212 (周五) -> 20260213 (周六) -> Tushare 从下周一开始获取
        20260214 (周日) -> 20260215 (周一) -> Tushare 从周一开始获取
    """
    from datetime import datetime, timedelta

    date_obj = datetime.strptime(date, '%Y%m%d')
    next_date = date_obj + timedelta(days=1)
    return next_date.strftime('%Y%m%d')


def collect_incremental(
    token: str,
    db_path: str,
    stock_list: list = None,
    logger: Optional[logging.Logger] = None,
    update_failed_file: bool = True
) -> dict:
    """
    增量数据收集

    自动判断数据库中每只股票的最新数据时间，收集从最新时间到当前时间的新增数据。

    参数:
        token: Tushare API Token
        db_path: 数据库文件路径
        stock_list: 股票代码列表，为 None 时更新数据库中所有股票
        logger: 日志记录器
        update_failed_file: 是否更新 failed_stocks.txt 文件

    返回:
        dict: 收集统计信息
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("开始增量数据收集")
    logger.info("Starting Incremental Data Collection")
    logger.info("=" * 60)

    # 1. 获取当前日期
    end_date = datetime.now().strftime('%Y%m%d')
    logger.info(f"目标日期 (Target date): {end_date}\n")

    # 2. 初始化组件
    fetcher = TushareFetcher(token=token, logger=logger)
    local_store = LocalStore(db_path=db_path, logger=logger)

    # 3. 确定股票列表
    if stock_list is None:
        # 获取数据库中所有股票（从 stock_daily 表获取唯一股票代码）
        stock_list = local_store.get_all_stocks_from_daily()
        logger.info(f"数据库中共有 {len(stock_list)} 只股票\n")

        if not stock_list:
            logger.warning("数据库为空，请先运行全量收集 (collect --mode full)")
            logger.warning("Database is empty, please run full collection first")
            return {
                'total_stocks': 0,
                'need_update': 0,
                'success': 0,
                'failed': 0,
                'total_records': 0,
                'skipped': 0
            }

    # 4. 为每只股票计算增量更新的起始日期，并分类
    stocks_need_update = []  # 需要更新的股票列表（包含起始日期信息）
    skipped_count = 0

    for stock_code in stock_list:
        last_date = local_store.get_latest_date(stock_code)
        if last_date is None:
            logger.debug(f"{stock_code}: 无数据，跳过")
            skipped_count += 1
            continue

        if last_date >= end_date:
            logger.debug(f"{stock_code}: 已是最新 ({last_date})，跳过")
            skipped_count += 1
            continue

        # 计算增量范围（从数据库最新日期的下一天开始）
        start_date = _get_next_day(last_date)
        stocks_need_update.append((stock_code, start_date, last_date))

    logger.info(f"需要更新: {len(stocks_need_update)} 只，已是最新: {skipped_count} 只\n")

    if not stocks_need_update:
        logger.info("所有股票都已是最新，无需更新")
        local_store.close()
        return {
            'total_stocks': len(stock_list),
            'need_update': 0,
            'success': 0,
            'failed': 0,
            'total_records': 0,
            'skipped': skipped_count
        }

    # 5. 批量更新需要更新的股票（使用统一的代码风格）
    stats = {
        'total': len(stocks_need_update),
        'success': 0,
        'failed': 0,
        'total_records': 0,
        'failed_stocks': []
    }

    for idx, (stock_code, start_date, last_date) in enumerate(stocks_need_update, 1):
        try:
            logger.info(f"[{idx}/{len(stocks_need_update)}] {stock_code}: {last_date} -> {end_date}")

            # 获取增量数据
            df = fetcher.fetch_daily(stock_code, start_date, end_date)

            if df is not None and len(df) > 0:
                # 验证数据完整性
                validation_result = local_store.validate_daily_data(df, stock_code)

                if not validation_result['is_valid']:
                    stats['failed'] += 1
                    stats['failed_stocks'].append(stock_code)
                    logger.error(f"  ✗ 数据验证失败 (Data validation failed): {validation_result['errors'][:3]}")
                    continue

                # 显示验证警告（如果有）
                if validation_result['warnings']:
                    for warning in validation_result['warnings']:
                        logger.warning(f"  ⚠ {warning}")

                # 保存到数据库
                saved_count = local_store.save_daily_data(df)
                stats['total_records'] += saved_count
                stats['success'] += 1
                logger.info(f"  ✓ 新增 {saved_count} 条记录")
            else:
                logger.warning(f"  ✗ 未获取到新数据")

        except Exception as e:
            stats['failed'] += 1
            stats['failed_stocks'].append(stock_code)
            logger.error(f"  ✗ 错误: {e}")

    # 6. 添加 skipped 计数
    stats['skipped'] = skipped_count
    stats['need_update'] = stats['success'] + stats['failed']

    # 7. 打印统计信息
    logger.info("\n" + "=" * 60)
    logger.info("增量数据收集完成")
    logger.info("Incremental Data Collection Completed")
    logger.info(f"总股票数 (Total): {len(stock_list)}")
    logger.info(f"需要更新 (Need update): {stats['need_update']}")
    logger.info(f"已是最新 (Skipped): {stats['skipped']}")
    logger.info(f"成功 (Success): {stats['success']}")
    logger.info(f"失败 (Failed): {stats['failed']}")
    logger.info(f"新增记录 (New records): {stats['total_records']}")
    logger.info("=" * 60)

    # 8. 更新 failed_stocks.txt 文件（如果需要）
    if update_failed_file:
        _update_failed_stocks_file(stats, logger)

    # 9. 关闭数据库
    local_store.close()

    return stats


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='数据收集脚本 - Data Collection Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例 (Examples):
  # 全量收集（从2013-01-01开始，收集全部A股）
  python -m data.collect --mode full

  # 收集沪深300成分股
  python -m data.collect --mode full --source csi300 --start 20130101

  # 收集中证500成分股
  python -m data.collect --mode full --source csi500

  # 收集失败的股票
  python -m data.collect --mode full --source failed --start 20130101

  # 增量收集（自动判断最新日期）
  python -m data.collect --mode incremental

  # 指定股票
  python -m data.collect --mode full --stocks 000001.SZ,000002.SZ

  # 自定义起始日期
  python -m data.collect --mode full --start 20200101
        '''
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'incremental'],
        required=True,
        help='收集模式 (Collection mode): full=全量收集, incremental=增量收集'
    )

    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='配置文件路径 (Config file path)'
    )

    parser.add_argument(
        '--stocks',
        type=str,
        default=None,
        help='股票代码列表，逗号分隔 (Stock codes, comma-separated)'
    )

    parser.add_argument(
        '--start',
        type=str,
        default=None,
        help='起始日期，格式 YYYYMMDD (Start date in YYYYMMDD format), 仅用于全量收集'
    )

    parser.add_argument(
        '--end',
        type=str,
        default=None,
        help='结束日期，格式 YYYYMMDD (End date in YYYYMMDD format)'
    )


    parser.add_argument(
        '--source',
        type=str,
        default=None,
        help='股票池来源 (Stock pool source): csi300/sse50/csi500/csi1000/sz50/cyb50/star50'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细日志输出 (Verbose logging)'
    )

    args = parser.parse_args()

    # 加载配置
    config = ConfigManager.load_and_validate(args.config)
    token = config['data_source']['token']
    db_path = config['storage']['path']

    # 设置日志
    log_level = 'DEBUG' if args.verbose else config['logging']['level']
    logger = setup_logger(
        level=log_level,
        log_file=config['logging']['file'],
        console=config['logging']['console']
    )

    # 处理股票列表
    stock_list = None
    update_failed_file = True  # 默认启用失败股票自动保存功能

    if args.source:
        # 从指定的指数成分股文件读取
        source_map = {
            'csi300': '沪深300',
            'sse50': '上证50',
            'csi500': '中证500',
            'csi1000': '中证1000',
            'sz50': '深证50',
            'cyb50': '创业板50',
            'star50': '科创50',
            'failed': '失败的股票'
        }
        source_name = source_map.get(args.source, args.source)
        logger.info(f"从 stock_code/{args.source}.txt 读取{source_name}...")
        stock_pool = StockPool(source=args.source, token=token, logger=logger)
        stock_list = stock_pool.get_stock_list()

        if not stock_list:
            if args.source == 'failed':
                logger.info("没有需要重试的股票")
            else:
                logger.error(f"未找到{source_name}，请先运行: python -m src.data.stock_code_fetcher --index {args.source}")
            sys.exit(0)

        logger.info(f"找到 {len(stock_list)} 只{source_name}\n")
    else:
        # source 为空，收集全部A股
        logger.info("正在获取全部A股列表...")
        stock_pool = StockPool(source="all_a", token=token, logger=logger)
        stock_list = stock_pool.get_stock_list()

        if stock_list and len(stock_list) > 0:
            logger.info(f"获取到 {len(stock_list)} 只A股\n")
        else:
            logger.error("获取股票列表失败")
            sys.exit(1)

    # 如果用户指定了股票列表，则添加到现有的 stock_list 中
    if args.stocks:
        additional_stocks = [s.strip() for s in args.stocks.split(',')]
        stock_list.extend(additional_stocks)
        logger.info(f"添加 {len(additional_stocks)} 只指定股票，当前共 {len(stock_list)} 只股票\n")

    # 执行收集
    try:
        if args.mode == 'full':
            stats = collect_full(
                token=token,
                db_path=db_path,
                start_date=args.start or "20130101",
                end_date=args.end,
                stock_list=stock_list,
                logger=logger,
                update_failed_file=update_failed_file
            )
        else:  # incremental
            stats = collect_incremental(
                token=token,
                db_path=db_path,
                stock_list=stock_list,
                logger=logger,
                update_failed_file=update_failed_file
            )

        # 返回状态码
        sys.exit(0 if stats['failed'] == 0 else 1)

    except Exception as e:
        logger.error(f"发生错误 (Error): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
