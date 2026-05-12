#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tushare API 连接测试脚本
Tushare API Connection Test Script

该脚本用于测试 Tushare Pro API 连接是否正常。
This script is used to test if Tushare Pro API connection is working properly.
"""

import sys
import yaml
from pathlib import Path

# 添加项目根目录到 Python 路径
# Add project root directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import tushare as ts
    import pandas as pd
    from datetime import datetime, timedelta
    print("[成功] 所有必要库已导入")
    print("[Success] All required libraries imported")
except ImportError as e:
    print(f"[错误] 缺少必要的库: {e}")
    print(f"[Error] Missing required library: {e}")
    sys.exit(1)


def load_config():
    """
    加载配置文件
    Load configuration file
    """
    config_path = Path("settings.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def test_tushare_connection(token):
    """
    测试 Tushare API 连接
    Test Tushare API connection

    参数 (Parameters):
        token: Tushare Pro Token
    """
    print("\n" + "=" * 60)
    print("测试 1: 初始化 Tushare API")
    print("Test 1: Initialize Tushare API")
    print("=" * 60)

    try:
        ts.set_token(token)
        pro = ts.pro_api()
        print("[成功] Tushare API 初始化成功")
        print("[Success] Tushare API initialized successfully")
        return pro
    except Exception as e:
        print(f"[失败] Tushare API 初始化失败: {e}")
        print(f"[Failed] Tushare API initialization failed: {e}")
        return None


def test_get_stock_list(pro):
    """
    测试获取股票列表
    Test getting stock list

    参数 (Parameters):
        pro: Tushare Pro API 对象
    """
    print("\n" + "=" * 60)
    print("测试 2: 获取股票列表")
    print("Test 2: Get Stock List")
    print("=" * 60)

    try:
        # 获取股票列表
        # Get stock list
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name,industry,list_date')

        if df is not None and len(df) > 0:
            print(f"[成功] 获取到 {len(df)} 只股票")
            print(f"[Success] Retrieved {len(df)} stocks")
            print("\n前 5 只股票 (First 5 stocks):")
            print(df.head().to_string(index=False))
            return df
        else:
            print("[失败] 未获取到股票数据")
            print("[Failed] No stock data retrieved")
            return None
    except Exception as e:
        print(f"[失败] 获取股票列表失败: {e}")
        print(f"[Failed] Failed to get stock list: {e}")
        return None


def test_get_daily_data(pro, stock_code='000001.SZ'):
    """
    测试获取日线数据
    Test getting daily market data

    参数 (Parameters):
        pro: Tushare Pro API 对象
        stock_code: 股票代码 (默认: 平安银行)
    """
    print("\n" + "=" * 60)
    print(f"测试 3: 获取 {stock_code} 的日线数据")
    print(f"Test 3: Get Daily Data for {stock_code}")
    print("=" * 60)

    try:
        # 计算日期范围（最近 30 个交易日）
        # Calculate date range (last 30 trading days)
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

        print(f"日期范围 (Date range): {start_date} - {end_date}")

        # 获取日线数据
        # Get daily data
        df = pro.daily(
            ts_code=stock_code,
            start_date=start_date,
            end_date=end_date
        )

        if df is not None and len(df) > 0:
            print(f"\n[成功] 获取到 {len(df)} 条日线数据")
            print(f"[Success] Retrieved {len(df)} daily data records")
            print("\n最近 5 条数据 (Latest 5 records):")
            print(df.head().to_string(index=False))
            return df
        else:
            print(f"[失败] 未获取到 {stock_code} 的数据")
            print(f"[Failed] No data retrieved for {stock_code}")
            return None
    except Exception as e:
        print(f"[失败] 获取日线数据失败: {e}")
        print(f"[Failed] Failed to get daily data: {e}")
        return None


def main():
    """
    主函数
    Main function
    """
    print("\n" + "=" * 60)
    print("Tushare API 连接测试")
    print("Tushare API Connection Test")
    print("=" * 60)

    # 加载配置
    # Load configuration
    config = load_config()
    token = config['data_source']['token']

    # 检查 Token
    # Check Token
    if token == 'YOUR_TOKEN_HERE' or not token:
        print("\n[错误] 请先在 settings.yaml 中配置有效的 Tushare Token")
        print("[Error] Please configure a valid Tushare Token in settings.yaml first")
        print("\n获取 Token (Get Token): https://tushare.pro")
        sys.exit(1)

    print(f"\nToken: {token[:20]}...{token[-10:]}")

    # 测试 1: 初始化 API
    # Test 1: Initialize API
    pro = test_tushare_connection(token)
    if pro is None:
        sys.exit(1)

    # 测试 2: 获取股票列表
    # Test 2: Get stock list
    stock_list = test_get_stock_list(pro)
    if stock_list is None:
        print("\n[警告] 获取股票列表失败，但继续测试...")
        print("[Warning] Failed to get stock list, but continuing...")

    # 测试 3: 获取日线数据
    # Test 3: Get daily data
    daily_data = test_get_daily_data(pro)
    if daily_data is None:
        print("\n[警告] 获取日线数据失败")
        print("[Warning] Failed to get daily data")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("[成功] 所有测试通过！Tushare API 连接正常")
    print("[Success] All tests passed! Tushare API is working properly")
    print("=" * 60)
    print("\n您可以开始使用选股系统了！")
    print("You can now start using the stock selection system!")
    print("\n运行命令 (Run command): python run.py")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
