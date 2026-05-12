#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增量更新测试脚本
Incremental Update Test Script

该脚本演示如何进行增量数据更新，只获取数据库中不存在的最新数据。
This script demonstrates how to perform incremental data updates, only fetching new data.
"""

import sys
import yaml
from pathlib import Path

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.date_utils import get_incremental_update_range, get_last_trading_day
from data.local_store import LocalStore
from data.fetcher import TushareFetcher
from utils.logger import setup_logger


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "settings.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("增量数据更新测试")
    print("Incremental Data Update Test")
    print("=" * 60 + "\n")

    # 1. 加载配置
    print("步骤 1: 加载配置 (Step 1: Load configuration)")
    config = load_config()
    token = config['data_source']['token']
    db_path = config['storage']['path']

    # 初始化日志
    logger = setup_logger(
        level=config['logging']['level'],
        log_file=config['logging']['file'],
        console=config['logging']['console']
    )

    print(f"数据库路径 (Database path): {db_path}\n")

    # 2. 初始化本地存储
    print("步骤 2: 初始化本地存储 (Step 2: Initialize local storage)")
    local_store = LocalStore(db_path=db_path, logger=logger)
    print("[成功] 本地存储初始化成功\n")

    # 3. 获取数据库中所有股票
    print("步骤 3: 获取股票列表 (Step 3: Get stock list)")
    stock_list = local_store.get_all_stocks()

    if not stock_list:
        print("[警告] 数据库中没有股票，请先运行 test_data_collection.py 收集初始数据")
        print("[Warning] No stocks in database, please run test_data_collection.py first")
        return

    print(f"数据库中共有 {len(stock_list)} 只股票\n")

    # 4. 显示各股票的最新数据日期
    print("步骤 4: 检查各股票最新数据日期 (Step 4: Check latest data date for each stock)")
    print("-" * 60)

    stocks_to_update = []
    latest_trading = get_last_trading_day()

    for stock_code in stock_list[:10]:  # 只显示前10只股票
        latest_date = local_store.get_latest_date(stock_code)
        status = "✓ 最新" if latest_date == latest_trading else "→ 需更新"
        print(f"  {stock_code}: 最新数据 {latest_date} {status}")

        if latest_date != latest_trading:
            stocks_to_update.append(stock_code)

    print("-" * 60)

    if not stocks_to_update:
        print("\n[完成] 所有股票数据都是最新的，无需更新")
        print("[Complete] All stocks are up-to-date, no update needed")
        return

    print(f"\n需要更新 {len(stocks_to_update)} 只股票\n")

    # 5. 初始化数据获取器
    print("步骤 5: 初始化数据获取器 (Step 5: Initialize data fetcher)")
    fetcher = TushareFetcher(token=token, logger=logger)
    print("[成功] 数据获取器初始化成功\n")

    # 6. 执行增量更新
    print("步骤 6: 执行增量更新 (Step 6: Perform incremental update)")
    print("=" * 60)

    # 演示单只股票的增量更新
    if stocks_to_update:
        test_stock = stocks_to_update[0]
        print(f"\n示例：更新 {test_stock}")
        print(f"Example: Update {test_stock}")
        print("-" * 60)

        # 获取该股票的最新日期
        last_date = local_store.get_latest_date(test_stock)
        print(f"数据库最新日期 (Latest in DB): {last_date}")

        # 计算增量更新范围
        start_date, end_date = get_incremental_update_range(last_date)
        print(f"更新范围 (Update range): {start_date} - {end_date}")

        # 获取增量数据
        df = fetcher.fetch_daily(test_stock, start_date, end_date)

        if df is not None and len(df) > 0:
            print(f"获取到 {len(df)} 条新记录")

            # 保存到数据库
            saved_count = local_store.save_daily_data(df)
            print(f"成功保存 {saved_count} 条记录")
            print(f"Successfully saved {saved_count} records")

            # 显示新数据
            print("\n新增数据 (New data):")
            for idx, row in df.head(5).iterrows():
                print(f"  {row['trade_date']} | 收盘: {row['close']:.2f} | 成交量: {row['vol']:.0f}")
        else:
            print("未获取到新数据")

    print("\n" + "=" * 60)
    print("[完成] 增量更新测试完成")
    print("[Complete] Incremental update test completed")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[错误] 发生异常: {e}")
        print(f"[Error] Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
