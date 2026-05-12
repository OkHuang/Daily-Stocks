"""
知行趋势策略测试脚本
Zhixing Trend Strategy Test Script

用法 (Usage):
    python test/test_zhixing_trend.py --stock 000001.SZ
    python test/test_zhixing_trend.py --stock 000001.SZ --days 120
    python test/test_zhixing_trend.py --test-all
"""

import sys
import argparse
from pathlib import Path

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pandas as pd
from data.local_store import LocalStore
from strategies.zhixing_trend_strategy import ZhixingTrendStrategy


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='知行趋势策略测试')
    parser.add_argument('--stock', type=str, help='股票代码，如 000001.SZ')
    parser.add_argument('--stocks', type=str, help='多个股票代码，逗号分隔')
    parser.add_argument('--test-all', action='store_true', help='测试数据库中所有股票')
    parser.add_argument('--days', type=int, default=120, help='显示最近N天的数据')
    parser.add_argument('--db', type=str, default='database/market_data.db', help='数据库路径')
    return parser.parse_args()


def run_strategy_test(stock_code: str, db_path: str, days: int = 120):
    """测试单只股票的策略"""
    print(f"\n{'='*100}")
    print(f"测试股票: {stock_code}")
    print(f"{'='*100}\n")

    # 初始化数据库连接
    local_store = LocalStore(db_path=db_path)

    # 获取股票数据
    df = local_store.get_stock_data(stock_code)

    if df is None or len(df) == 0:
        print(f"⚠️  股票 {stock_code} 没有数据")
        return

    print(f"📊 数据范围: {df['trade_date'].min()} 至 {df['trade_date'].max()}")
    print(f"📊 数据行数: {len(df)} 行\n")

    # 初始化策略
    strategy = ZhixingTrendStrategy()

    # 计算信号
    signals = strategy.calculate(df)

    # 获取最近N天的数据
    df_recent = df.tail(days).copy()

    # 计算指标用于显示
    from utils.indicators import calculate_zhixing_bull_bear, calculate_zhixing_short_trend, calculate_kdj

    zhixing_bb = calculate_zhixing_bull_bear(df, p1=14, p2=28, p3=57, p4=114)
    short_trend = calculate_zhixing_short_trend(df, period=10)
    k, d, j = calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)

    df_recent['知行多空线'] = zhixing_bb
    df_recent['短期趋势'] = short_trend
    df_recent['J值'] = j

    # 计算振幅
    df_recent['振幅%'] = (df_recent['high'] - df_recent['low']) / df_recent['low'] * 100

    # 计算成交量比例
    volume_ma = df['vol'].rolling(window=12).mean()
    df_recent['量比%'] = df_recent['vol'] / volume_ma * 100

    df_recent['Signal'] = signals.values

    # 显示信号统计
    signal_count = (signals > 0).sum()
    print(f"📈 历史信号次数: {signal_count} 次")

    if signal_count > 0:
        signal_dates = signals[signals > 0].index
        print(f"📅 最近信号日期:")
        for idx in signal_dates[-5:]:
            date = df.loc[idx, 'trade_date']
            price = df.loc[idx, 'close']
            print(f"   - {date} (收盘: {price:.2f})")
    else:
        print("📅 历史上未产生过信号")

    # 显示最近N天的详细数据
    print(f"\n📋 最近 {min(days, 20)} 天详细数据:")
    print("-" * 160)
    header = f"{'日期':<12} {'收盘':>8} {'知行多空':>10} {'短期趋势':>10} {'J值':>8} {'振幅%':>8} {'量比%':>8} {'信号':>8}"
    print(header)
    print("-" * 160)

    display_days = min(days, 20)
    for _, row in df_recent.tail(display_days).iterrows():
        signal_str = "🔥买入" if row['Signal'] > 0 else ""
        print(f"{row['trade_date']:<12} "
              f"{row['close']:>8.2f} "
              f"{row['知行多空线']:>10.2f} "
              f"{row['短期趋势']:>10.2f} "
              f"{row['J值']:>8.2f} "
              f"{row['振幅%']:>8.2f} "
              f"{row['量比%']:>8.1f} "
              f"{signal_str:>8}")

    # 检查最新日期是否满足各条件
    print(f"\n🔍 最新交易日条件分析 ({df_recent.iloc[-1]['trade_date']}):")
    latest = df_recent.iloc[-1]

    cond1 = latest['close'] > latest['知行多空线']
    print(f"  {'✅' if cond1 else '❌'} 条件1 - 股价 > 知行多空线: {latest['close']:.2f} > {latest['知行多空线']:.2f}")

    cond2 = latest['J值'] < 13
    print(f"  {'✅' if cond2 else '❌'} 条件2 - J值 < 13: {latest['J值']:.2f}")

    cond3 = latest['短期趋势'] > latest['知行多空线']
    print(f"  {'✅' if cond3 else '❌'} 条件3 - 短期趋势 > 知行多空线: {latest['短期趋势']:.2f} > {latest['知行多空线']:.2f}")

    cond4 = latest['振幅%'] < 4
    print(f"  {'✅' if cond4 else '❌'} 条件4 - 振幅 < 4%: {latest['振幅%']:.2f}%")

    cond5 = latest['量比%'] < 52
    print(f"  {'✅' if cond5 else '❌'} 条件5 - 量比 < 52%: {latest['量比%']:.1f}%")

    # 综合结果
    all_match = cond1 and cond2 and cond3 and cond4 and cond5
    print(f"\n  {'🎯 满足所有条件，建议关注!' if all_match else '⏸️  未满足所有条件'}")

    return all_match


def scan_stocks(db_path: str):
    """扫描数据库中所有股票，找出符合条件的"""
    print(f"\n{'='*100}")
    print("🔍 扫描数据库，寻找符合条件的股票...")
    print(f"{'='*100}\n")

    local_store = LocalStore(db_path=db_path)

    # 获取所有股票列表
    all_stocks = local_store.get_all_stocks()

    if not all_stocks:
        print("❌ 数据库中没有股票数据")
        return

    print(f"📊 共扫描 {len(all_stocks)} 只股票\n")

    strategy = ZhixingTrendStrategy()
    matched_stocks = []

    for i, stock_code in enumerate(all_stocks, 1):
        try:
            df = local_store.get_stock_data(stock_code)

            if df is None or len(df) < 114:
                continue

            # 计算信号
            signals = strategy.calculate(df)

            # 检查最新信号
            if len(signals) > 0 and signals.iloc[-1] > 0:
                matched_stocks.append(stock_code)
                print(f"  [{i:4d}] {stock_code} ✅")

            # 每100只股票显示进度
            if i % 100 == 0:
                print(f"  已扫描 {i} 只股票...")

        except Exception as e:
            continue

    print(f"\n{'='*100}")
    print(f"🎯 扫描完成！共找到 {len(matched_stocks)} 只符合条件的股票")
    print(f"{'='*100}\n")

    if matched_stocks:
        print("符合条件的股票列表:")
        for stock in matched_stocks:
            print(f"  - {stock}")


def main():
    """主函数"""
    args = parse_arguments()

    if args.test_all:
        # 扫描所有股票
        scan_stocks(args.db)
    elif args.stock:
        # 测试单只股票
        run_strategy_test(args.stock, args.db, args.days)
    elif args.stocks:
        # 测试多只股票
        stock_list = args.stocks.split(',')
        for stock in stock_list:
            run_strategy_test(stock.strip(), args.db, args.days)
    else:
        print("❌ 请指定 --stock 或 --test-all 参数")
        print("示例:")
        print("  python test/test_zhixing_trend.py --stock 000001.SZ")
        print("  python test/test_zhixing_trend.py --test-all")


if __name__ == '__main__':
    main()
