"""
策略可视化分析脚本
Strategy Visualization Script

用图表展示策略信号和各项指标
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from data.local_store import LocalStore
from strategies.multi_indicator_combo import MultiIndicatorComboStrategy
from utils.indicators import calculate_bbi, calculate_kdj, calculate_macd


def plot_strategy_analysis(stock_code: str, db_path: str = 'database/market_data.db', days: int = 120):
    """
    绘制策略分析图表

    参数:
        stock_code: 股票代码
        db_path: 数据库路径
        days: 显示最近N天
    """
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    # 获取数据
    local_store = LocalStore(db_path=db_path)
    df = local_store.get_stock_data(stock_code)

    if df is None or len(df) == 0:
        print(f"❌ 股票 {stock_code} 没有数据")
        return

    # 只取最近N天
    df = df.tail(days).copy()

    # 计算指标
    bbi = calculate_bbi(df, p1=3, p2=6, p3=12, p4=24)
    k, d, j = calculate_kdj(df, n_period=9, m1_period=3, m2_period=3)
    dif, dea, macd = calculate_macd(df, fast_period=12, slow_period=26, signal_period=9)

    # 计算策略信号
    strategy = MultiIndicatorComboStrategy()
    signals = strategy.calculate(df)

    # 计算波动率
    rolling_high = df['high'].rolling(window=60).max()
    rolling_low = df['low'].rolling(window=60).min()
    volatility = (rolling_high - rolling_low) / rolling_low * 100

    # 创建图表
    fig, axes = plt.subplots(5, 1, figsize=(14, 12))
    fig.suptitle(f'{stock_code} 多指标组合策略分析', fontsize=16, fontweight='bold')

    # 转换日期
    df['date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

    # 子图1: 价格与BBI
    ax1 = axes[0]
    ax1.plot(df['date'], df['close'], label='收盘价', linewidth=1.5, color='black')
    ax1.plot(df['date'], bbi, label='BBI', linewidth=1.2, color='blue', alpha=0.7)

    # 标记买入信号
    signal_dates = df[signals > 0]['date']
    signal_prices = df[signals > 0]['close']
    ax1.scatter(signal_dates, signal_prices, color='red', s=100, marker='^',
                label='买入信号', zorder=5)

    ax1.set_ylabel('价格', fontsize=10)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('价格与BBI', fontsize=12)

    # 子图2: KDJ指标
    ax2 = axes[1]
    ax2.plot(df['date'], k, label='K', linewidth=1, color='orange')
    ax2.plot(df['date'], d, label='D', linewidth=1, color='blue')
    ax2.plot(df['date'], j, label='J', linewidth=1, color='purple')
    ax2.axhline(y=-1, color='red', linestyle='--', alpha=0.5, label='J阈值(-1)')
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax2.set_ylabel('KDJ值', fontsize=10)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('KDJ指标', fontsize=12)

    # 子图3: MACD指标
    ax3 = axes[2]
    colors = ['red' if x > 0 else 'green' for x in macd]
    ax3.bar(df['date'], macd, color=colors, alpha=0.6, label='MACD柱')
    ax3.plot(df['date'], dif, label='DIF', linewidth=1, color='white')
    ax3.plot(df['date'], dea, label='DEA', linewidth=1, color='yellow')
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax3.set_ylabel('MACD', fontsize=10)
    ax3.legend(loc='upper left', fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_title('MACD指标', fontsize=12)

    # 子图4: 波动率
    ax4 = axes[3]
    ax4.fill_between(df['date'], 0, volatility, alpha=0.5, color='lightblue')
    ax4.plot(df['date'], volatility, linewidth=1.5, color='blue', label='60日波动率')
    ax4.axhline(y=100, color='red', linestyle='--', alpha=0.7, label='阈值(100%)')
    ax4.set_ylabel('波动率 (%)', fontsize=10)
    ax4.legend(loc='upper left', fontsize=9)
    ax4.grid(True, alpha=0.3)
    ax4.set_title('波动率', fontsize=12)

    # 子图5: 策略信号
    ax5 = axes[4]
    signal_strength = pd.Series(0, index=df.index)
    signal_strength[signals > 0] = 1
    ax5.plot(df['date'], signal_strength, drawstyle='steps-pre', linewidth=2, color='red')
    ax5.fill_between(df['date'], 0, signal_strength, alpha=0.3, color='red')
    ax5.set_ylabel('信号', fontsize=10)
    ax5.set_xlabel('日期', fontsize=10)
    ax5.set_yticks([0, 1])
    ax5.set_yticklabels(['无信号', '买入'])
    ax5.grid(True, alpha=0.3, axis='x')
    ax5.set_title('策略信号', fontsize=12)

    # 格式化x轴日期
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    # 保存图片
    output_dir = Path('reports/charts')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'{stock_code}_strategy_analysis.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ 图表已保存: {output_file}")

    # 打印最新状态
    print(f"\n📊 {stock_code} 最新状态:")
    print(f"  日期: {df.iloc[-1]['trade_date']}")
    print(f"  收盘价: {df.iloc[-1]['close']:.2f}")
    print(f"  BBI: {bbi.iloc[-1]:.2f}")
    print(f"  J值: {j.iloc[-1]:.2f}")
    print(f"  DIF: {dif.iloc[-1]:.2f}")
    print(f"  60日波动率: {volatility.iloc[-1]:.2f}%")
    print(f"  信号: {'🔥 买入' if signals.iloc[-1] > 0 else '⏸️  无信号'}")

    plt.show()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='策略可视化分析')
    parser.add_argument('--stock', type=str, required=True, help='股票代码，如 000001.SZ')
    parser.add_argument('--days', type=int, default=120, help='显示最近N天')
    parser.add_argument('--db', type=str, default='database/market_data.db', help='数据库路径')

    args = parser.parse_args()

    plot_strategy_analysis(args.stock, args.db, args.days)
