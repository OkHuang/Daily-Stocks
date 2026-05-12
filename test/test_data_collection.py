#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据收集测试脚本（简化版）
Data Collection Test Script (Simplified)

该脚本使用固定的股票代码测试从 Tushare 获取数据。
This script tests fetching data from Tushare using fixed stock codes.
"""

import sys
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.date_utils import get_data_collection_period, get_incremental_update_range

import tushare as ts


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "settings.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def init_database(db_path):
    """初始化数据库表结构"""
    import sqlite3
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建股票日线数据表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_daily (
            ts_code TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            amount REAL,
            PRIMARY KEY (ts_code, trade_date)
        )
    """)

    # 创建股票基本信息表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_list (
            ts_code TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            list_date TEXT,
            update_time TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"[成功] 数据库初始化完成: {db_path}")
    print(f"[Success] Database initialized: {db_path}")


def save_stock_info(db_path, stock_code, stock_name):
    """保存单只股票信息"""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        INSERT OR REPLACE INTO stock_list (ts_code, name, industry, list_date, update_time)
        VALUES (?, ?, ?, ?, ?)
    """, (stock_code, stock_name, '未知', '19900101', update_time))

    conn.commit()
    conn.close()


def save_daily_data(db_path, df):
    """保存日线数据到数据库"""
    import sqlite3

    if df is None or len(df) == 0:
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    records_saved = 0
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO stock_daily
                (ts_code, trade_date, open, high, low, close, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['ts_code'],
                row['trade_date'],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['vol'],
                row['amount']
            ))
            records_saved += 1
        except Exception as e:
            print(f"    [警告] 保存记录失败: {e}")

    conn.commit()
    conn.close()
    return records_saved


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Tushare 数据收集测试（10只股票）")
    print("Tushare Data Collection Test (10 stocks)")
    print("=" * 60 + "\n")

    # 1. 加载配置
    print("步骤 1: 加载配置 (Step 1: Load configuration)")
    config = load_config()
    token = config['data_source']['token']
    db_path = config['storage']['path']

    print(f"数据库路径 (Database path): {db_path}")
    print(f"Token: {token[:20]}...{token[-10:]}\n")

    # 2. 初始化 Tushare API
    print("步骤 2: 初始化 Tushare API (Step 2: Initialize Tushare API)")
    ts.set_token(token)
    pro = ts.pro_api()
    print("[成功] Tushare API 初始化成功\n")

    # 3. 初始化数据库
    print("步骤 3: 初始化数据库 (Step 3: Initialize database)")
    init_database(db_path)
    print()

    # 4. 定义10只测试股票（知名股票）
    print("步骤 4: 准备测试股票列表 (Step 4: Prepare test stock list)")
    test_stocks = [
        ('000001.SZ', '平安银行'),
        ('000002.SZ', '万科A'),
        ('600000.SH', '浦发银行'),
        ('600036.SH', '招商银行'),
        ('600519.SH', '贵州茅台'),
        ('000858.SZ', '五粮液'),
        ('002594.SZ', '比亚迪'),
        ('600900.SH', '长江电力'),
        ('601318.SH', '中国平安'),
        ('000001.SH', '上证指数')
    ]

    print("测试股票列表 (Test stocks):")
    for idx, (code, name) in enumerate(test_stocks, 1):
        print(f"  {idx}. {code} - {name}")
    print()

    # 5. 获取并保存数据
    print("步骤 5: 获取日线数据 (Step 5: Fetch daily data)")
    print("=" * 60)

    # 使用配置的策略类型确定日期范围
    # Use configured strategy type to determine date range
    strategy_type = config.get('data_collection', {}).get('initial', {}).get('strategy_type', 'medium')
    print(f"策略类型 (Strategy type): {strategy_type}")

    start_date, end_date = get_data_collection_period(strategy_type)

    print(f"日期范围 (Date range): {start_date} - {end_date}")
    print(f"说明 (Note): 使用最近已完成交易日作为结束日期，避免未完成数据\n")

    total_records = 0
    success_count = 0
    failed_stocks = []

    for idx, (stock_code, stock_name) in enumerate(test_stocks, 1):
        try:
            print(f"[{idx}/10] 正在获取 {stock_code} - {stock_name}...")

            # 保存股票基本信息
            save_stock_info(db_path, stock_code, stock_name)

            # 获取日线数据
            df_daily = pro.daily(
                ts_code=stock_code,
                start_date=start_date,
                end_date=end_date
            )

            if df_daily is not None and len(df_daily) > 0:
                # 保存到数据库
                records = save_daily_data(db_path, df_daily)
                total_records += records
                success_count += 1
                print(f"    [成功] 获取 {len(df_daily)} 条记录，保存 {records} 条")
                print(f"    [Success] Retrieved {len(df_daily)} records, saved {records} records")

                # 显示最新数据
                latest = df_daily.iloc[0]
                print(f"    最新交易 (Latest): {latest['trade_date']} | "
                      f"收盘: {latest['close']:.2f} | "
                      f"成交量: {latest['vol']:.0f}")
            else:
                print(f"    [警告] 未获取到数据")
                print(f"    [Warning] No data retrieved")
                failed_stocks.append((stock_code, stock_name, "无数据"))

        except Exception as e:
            print(f"    [错误] 获取失败: {str(e)[:50]}")
            print(f"    [Error] Failed: {str(e)[:50]}")
            failed_stocks.append((stock_code, stock_name, str(e)[:50]))

    print("\n" + "=" * 60)
    print(f"[完成] 数据收集完成！")
    print(f"[Complete] Data collection completed!")
    print(f"成功股票 (Success): {success_count}/10")
    print(f"总记录数 (Total records): {total_records}")

    if failed_stocks:
        print(f"\n失败股票 (Failed stocks):")
        for code, name, reason in failed_stocks:
            print(f"  - {code} {name}: {reason}")

    print(f"数据库位置 (Database): {db_path}")
    print("=" * 60 + "\n")

    # 6. 验证数据
    print("步骤 6: 验证数据 (Step 6: Verify data)")
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查询统计信息
    cursor.execute("SELECT COUNT(DISTINCT ts_code) FROM stock_list")
    stock_count = cursor.fetchone()[0]
    print(f"数据库中的股票数 (Stocks in DB): {stock_count}")

    cursor.execute("SELECT COUNT(*) FROM stock_daily")
    daily_count = cursor.fetchone()[0]
    print(f"数据库中的日线记录数 (Daily records): {daily_count}")

    # 查询每个股票的记录数
    cursor.execute("""
        SELECT ts_code, COUNT(*) as count
        FROM stock_daily
        GROUP BY ts_code
        ORDER BY count DESC
    """)
    print("\n各股票记录数 (Records per stock):")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 条")

    # 查询最近的数据
    cursor.execute("""
        SELECT ts_code, trade_date, close, volume
        FROM stock_daily
        ORDER BY trade_date DESC, ts_code
        LIMIT 10
    """)
    recent_data = cursor.fetchall()
    print("\n最近10条记录 (Recent 10 records):")
    for row in recent_data:
        print(f"  {row[0]} | {row[1]} | 收盘: {row[2]:.2f} | 成交量: {row[3]:.0f}")

    conn.close()
    print("\n" + "=" * 60)
    print("[成功] 测试完成！所有数据已保存到数据库")
    print("[Success] Test completed! All data saved to database")
    print(f"\n您可以使用以下命令查看数据库:")
    print(f"You can view the database with:")
    print(f"  sqlite3 {db_path}")
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
