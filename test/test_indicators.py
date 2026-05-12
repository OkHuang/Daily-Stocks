#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技术指标分析测试脚本 - Technical Indicators Analysis Test Script

该脚本用于从数据库读取股票数据并计算各种技术指标，验证数据收集的成果
和技术指标计算的正确性。

This script reads stock data from database and calculates various technical indicators,
validating the data collection results and indicator calculations.

使用方法 (Usage):
    # 测试单只股票
    python test/test_indicators.py --stock 000001.SZ

    # 测试多只股票
    python test/test_indicators.py --stock 000001.SZ,000002.SZ

    # 显示最近N天的数据
    python test/test_indicators.py --stock 000001.SZ --days 30

    # 导出为CSV
    python test/test_indicators.py --stock 000001.SZ --export indicators.csv

    # 生成统计报告
    python test/test_indicators.py --stats
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.local_store import LocalStore
from src.utils.indicators import (
    calculate_ma,
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_kdj,
    calculate_atr,
    calculate_bbi,
    calculate_zhixing_short_trend,
    calculate_zhixing_bull_bear
)
from src.utils.logger import setup_logger
import pandas as pd
import yaml


def load_config(config_path: str = "settings.yaml") -> dict:
    """加载配置文件"""
    config_file = project_root / config_path
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def analyze_single_stock(
    stock_code: str,
    db_path: str,
    days: int = 10,
    export_path: str = None,
    start_date: str = None,
    end_date: str = None
) -> pd.DataFrame:
    """
    分析单只股票的技术指标

    参数:
        stock_code: 股票代码
        db_path: 数据库路径
        days: 显示最近N天的数据（用于控制显示，不影响计算）
        export_path: 导出文件路径
        start_date: 分析起始日期，格式 YYYYMMDD（可选）
        end_date: 分析结束日期，格式 YYYYMMDD（可选）

    返回:
        包含所有技术指标的DataFrame（包含所有历史数据）
    """
    print(f"\n{'='*80}")
    print(f"分析股票 (Analyzing stock): {stock_code}")
    print(f"{'='*80}\n")

    # 1. 从数据库读取数据
    print(f"正在从数据库读取数据...")
    print(f"Loading data from database: {db_path}")
    local_store = LocalStore(db_path=db_path)

    # 如果指定了日期范围，按范围读取；否则读取全部数据
    if start_date or end_date:
        df = local_store.load_daily_data(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date
        )
    else:
        df = local_store.load_daily_data(stock_code)

    if df is None or len(df) == 0:
        print(f"[!] 未找到股票 {stock_code} 的数据")
        print(f"[!] No data found for stock {stock_code}")
        return None

    print(f"[OK] 成功读取 {len(df)} 条记录")
    print(f"[OK] Successfully loaded {len(df)} records")
    print(f"  日期范围 (Date range): {df['trade_date'].iloc[0]} - {df['trade_date'].iloc[-1]}")

    # 2. 计算技术指标（对全部历史数据计算）
    print(f"\n正在计算技术指标（全部历史数据）...")
    print(f"Calculating technical indicators for all historical data...\n")

    # 移动平均线
    df['ma5'] = calculate_ma(df, 5)
    df['ma10'] = calculate_ma(df, 10)
    df['ma20'] = calculate_ma(df, 20)
    df['ma60'] = calculate_ma(df, 60)
    print("  [OK] MA (5, 10, 20, 60) 计算完成")

    # 指数移动平均线
    df['ema12'] = calculate_ema(df, 12)
    df['ema26'] = calculate_ema(df, 26)
    print("  [OK] EMA (12, 26) 计算完成")

    # RSI
    df['rsi6'] = calculate_rsi(df, 6)
    df['rsi14'] = calculate_rsi(df, 14)
    df['rsi24'] = calculate_rsi(df, 24)
    print("  [OK] RSI (6, 14, 24) 计算完成")

    # MACD
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df)
    print("  [OK] MACD (12, 26, 9) 计算完成")

    # 布林带
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = calculate_bollinger_bands(df)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100
    print("  [OK] Bollinger Bands (20, 2) 计算完成")

    # KDJ
    df['kdj_k'], df['kdj_d'], df['kdj_j'] = calculate_kdj(df)
    print("  [OK] KDJ (9, 3, 3) 计算完成")

    # ATR
    df['atr'] = calculate_atr(df)
    print("  [OK] ATR (14) 计算完成")

    # BBI 多空指标
    df['bbi'] = calculate_bbi(df)
    print("  [OK] BBI (3, 6, 12, 24) 计算完成")

    # 知行短期趋势线
    df['zhixing_trend'] = calculate_zhixing_short_trend(df)
    print("  [OK] 知行短期趋势线 EMA(EMA,10) 计算完成")

    # 知行多空线
    df['zhixing_bb'] = calculate_zhixing_bull_bear(df)
    print("  [OK] 知行多空线 (14, 28, 57, 114) 计算完成")

    # 3. 显示最近N天的数据（但所有指标都已计算完毕）
    print(f"\n{'='*80}")
    print(f"显示最近 {days} 天的计算结果（全部 {len(df)} 条记录的指标已计算）")
    print(f"Displaying latest {days} days (indicators calculated for all {len(df)} records)")
    print(f"{'='*80}\n")

    # 选择要显示的列
    display_cols = [
        'trade_date', 'close', 'vol',
        'ma5', 'ma20', 'ma60',
        'rsi14', 'kdj_k', 'kdj_d', 'kdj_j',
        'macd', 'macd_hist',
        'bb_upper', 'bb_lower', 'atr',
        'bbi', 'zhixing_trend', 'zhixing_bb'
    ]

    # 只显示最近N天，且只显示有效数据
    recent_df = df[display_cols].tail(days).copy()

    # 格式化显示
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.float_format', lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A')

    print(recent_df.to_string(index=False))

    # 4. 显示最新指标摘要
    print(f"\n{'='*80}")
    print("最新指标摘要 (Latest Indicators Summary)")
    print(f"{'='*80}\n")

    latest = df.iloc[-1]
    print(f"交易日期 (Trade Date): {latest['trade_date']}")
    print(f"收盘价 (Close Price): {latest['close']:.2f}")
    print(f"成交量 (Volume): {latest['vol']:,.0f}")
    print()
    print(f"MA5:   {latest['ma5']:.2f}  |  MA20:  {latest['ma20']:.2f}  |  MA60:  {latest['ma60']:.2f}")
    print(f"RSI14: {latest['rsi14']:.2f}  |  KDJ_K: {latest['kdj_k']:.2f}  |  KDJ_D: {latest['kdj_d']:.2f}")
    print(f"MACD:  {latest['macd']:.2f}  |  Signal: {latest['macd_signal']:.2f}  |  Histogram: {latest['macd_hist']:.2f}")
    print(f"布林上轨: {latest['bb_upper']:.2f}  |  布林下轨: {latest['bb_lower']:.2f}  |  带宽: {latest['bb_width']:.2f}%")
    print(f"ATR: {latest['atr']:.2f}")
    print(f"\nBBI多空指标: {latest['bbi']:.2f}")
    print(f"知行短期趋势线: {latest['zhixing_trend']:.2f}")
    print(f"知行多空线: {latest['zhixing_bb']:.2f}")

    # 5. 技术分析提示
    print(f"\n{'='*80}")
    print("技术分析提示 (Technical Analysis Insights)")
    print(f"{'='*80}\n")

    # 均线分析
    if latest['ma5'] > latest['ma20'] > latest['ma60']:
        print("  [均线] 多头排列，短期均线在中期均线上方")
    elif latest['ma5'] < latest['ma20'] < latest['ma60']:
        print("  [均线] 空头排列，短期均线在中期均线下方")
    else:
        print("  [均线] 均线交织，趋势不明")

    # RSI分析
    if latest['rsi14'] > 70:
        print(f"  [RSI] 超买区域 ({latest['rsi14']:.2f} > 70)")
    elif latest['rsi14'] < 30:
        print(f"  [RSI] 超卖区域 ({latest['rsi14']:.2f} < 30)")
    else:
        print(f"  [RSI] 正常区域 ({latest['rsi14']:.2f})")

    # KDJ分析
    if latest['kdj_k'] > 80:
        print(f"  [KDJ] 超买 (K={latest['kdj_k']:.2f} > 80)")
    elif latest['kdj_k'] < 20:
        print(f"  [KDJ] 超卖 (K={latest['kdj_k']:.2f} < 20)")

    # MACD分析
    if latest['macd_hist'] > 0:
        prev_hist = df['macd_hist'].iloc[-2]
        if prev_hist <= 0:
            print("  [MACD] 金叉！MACD柱状图由负转正")
        else:
            print("  [MACD] 多头，MACD柱状图为正")
    else:
        prev_hist = df['macd_hist'].iloc[-2]
        if prev_hist >= 0:
            print("  [MACD] 死叉！MACD柱状图由正转负")
        else:
            print("  [MACD] 空头，MACD柱状图为负")

    # 布林带分析
    bb_position = (latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower']) * 100
    if bb_position > 80:
        print(f"  [布林带] 接近上轨 ({bb_position:.1f}%)")
    elif bb_position < 20:
        print(f"  [布林带] 接近下轨 ({bb_position:.1f}%)")
    else:
        print(f"  [布林带] 中性区域 ({bb_position:.1f}%)")

    # BBI 分析
    if latest['close'] > latest['bbi']:
        print(f"  [BBI] 价格在多空线上方 ({latest['close']:.2f} > {latest['bbi']:.2f})，多头市场")
    else:
        print(f"  [BBI] 价格在多空线下方 ({latest['close']:.2f} < {latest['bbi']:.2f})，空头市场")

    # 知行指标分析
    if latest['close'] > latest['zhixing_trend']:
        print(f"  [知行短期] 价格在趋势线上方，短期看涨")
    else:
        print(f"  [知行短期] 价格在趋势线下方，短期看跌")

    if latest['close'] > latest['zhixing_bb']:
        print(f"  [知行多空] 价格在多空线上方，中长期多头")
    else:
        print(f"  [知行多空] 价格在多空线下方，中长期空头")

    # 6. 导出数据
    if export_path:
        export_file = project_root / export_path
        df.to_csv(export_file, index=False, encoding='utf-8-sig')
        print(f"\n[OK] 数据已导出到: {export_file}")
        print(f"[OK] Data exported to: {export_file}")

    return df


def analyze_database_stats(db_path: str) -> dict:
    """
    分析数据库统计信息

    参数:
        db_path: 数据库路径

    返回:
        统计信息字典
    """
    print(f"\n{'='*80}")
    print("数据库统计信息 (Database Statistics)")
    print(f"{'='*80}\n")

    local_store = LocalStore(db_path=db_path)
    local_store._init_tables()

    conn = local_store._get_connection()

    # 统计股票数量
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT ts_code) FROM stock_daily")
    stock_count = cursor.fetchone()[0]

    # 统计总记录数
    cursor.execute("SELECT COUNT(*) FROM stock_daily")
    total_records = cursor.fetchone()[0]

    # 统计日期范围
    cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_daily")
    min_date, max_date = cursor.fetchone()

    # 统计每只股票的记录数
    cursor.execute("""
        SELECT ts_code, COUNT(*) as cnt
        FROM stock_daily
        GROUP BY ts_code
        ORDER BY cnt DESC
        LIMIT 10
    """)
    top_stocks = cursor.fetchall()

    # 统计最新交易日期
    cursor.execute("""
        SELECT trade_date, COUNT(*) as cnt
        FROM stock_daily
        WHERE trade_date = (SELECT MAX(trade_date) FROM stock_daily)
        GROUP BY trade_date
    """)
    latest_date_info = cursor.fetchone()

    print(f"股票总数 (Total stocks): {stock_count}")
    print(f"总记录数 (Total records): {total_records:,}")
    print(f"日期范围 (Date range): {min_date} - {max_date}")
    print(f"最新交易日 (Latest trading day): {latest_date_info[0]} ({latest_date_info[1]:,} 只股票有数据)")

    print(f"\n数据最多的前10只股票 (Top 10 stocks with most data):")
    for i, (stock_code, count) in enumerate(top_stocks, 1):
        print(f"  {i:2d}. {stock_code}: {count:,} 条记录")

    stats = {
        'stock_count': stock_count,
        'total_records': total_records,
        'min_date': min_date,
        'max_date': max_date,
        'latest_date': latest_date_info[0],
        'latest_date_count': latest_date_info[1]
    }

    local_store.close()
    return stats


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='技术指标分析测试脚本 - Technical Indicators Analysis Test Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例 (Examples):
  # 分析单只股票（计算全部历史数据）
  python test/test_indicators.py --stock 000001.SZ

  # 分析指定日期范围
  python test/test_indicators.py --stock 000001.SZ --start 20240101 --end 20241231

  # 分析多只股票
  python test/test_indicators.py --stock 000001.SZ,000002.SZ,600000.SH

  # 显示最近30天的计算结果（不影响计算范围）
  python test/test_indicators.py --stock 000001.SZ --days 30

  # 导出全部历史数据为CSV
  python test/test_indicators.py --stock 000001.SZ --export indicators.csv

  # 查看数据库统计信息
  python test/test_indicators.py --stats
        '''
    )

    parser.add_argument(
        '--stock',
        type=str,
        help='股票代码，支持多个代码用逗号分隔 (Stock codes, comma-separated)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='settings.yaml',
        help='配置文件路径 (Config file path)'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default=None,
        help='数据库文件路径 (Database file path)'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=10,
        help='显示最近N天的数据 (Show latest N days, default: 10)'
    )

    parser.add_argument(
        '--export',
        type=str,
        default=None,
        help='导出文件路径 (Export file path)'
    )

    parser.add_argument(
        '--start',
        type=str,
        default=None,
        help='分析起始日期，格式 YYYYMMDD (Analysis start date in YYYYMMDD format)'
    )

    parser.add_argument(
        '--end',
        type=str,
        default=None,
        help='分析结束日期，格式 YYYYMMDD (Analysis end date in YYYYMMDD format)'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='显示数据库统计信息 (Show database statistics)'
    )

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)
    db_path = args.db_path or config['storage']['path']

    # 设置日志
    logger = setup_logger(
        level='INFO',
        log_file='logs/indicators_test.log',
        console=True
    )

    if args.stats:
        # 显示统计信息
        analyze_database_stats(db_path)
    elif args.stock:
        # 分析指定股票
        stock_list = [s.strip() for s in args.stock.split(',')]

        for stock_code in stock_list:
            analyze_single_stock(
                stock_code=stock_code,
                db_path=db_path,
                days=args.days,
                export_path=args.export if len(stock_list) == 1 else None,
                start_date=args.start,
                end_date=args.end
            )
            print()
    else:
        # 默认：显示统计信息
        analyze_database_stats(db_path)
        print("\n提示: 使用 --stock 参数分析具体股票，例如:")
        print("      python test/test_indicators.py --stock 000001.SZ")
        print("\n      指定日期范围:")
        print("      python test/test_indicators.py --stock 000001.SZ --start 20240101 --end 20241231")


if __name__ == '__main__':
    main()
