#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票收盘选股系统 - 主入口文件
Stock Picker System - Main Entry Point

该文件是系统的主入口，负责解析命令行参数并启动选股流程。
This file is the main entry point of the system, responsible for parsing command-line arguments and starting the stock selection workflow.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# 添加 src 到 Python 路径
# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.config_manager import ConfigManager
from data.exceptions import ConfigurationError
from engine.pipeline import Pipeline
from utils.logger import setup_logger


def parse_arguments():
    """
    解析命令行参数
    Parse command-line arguments

    返回 (Returns):
        argparse.Namespace: 解析后的参数 (Parsed arguments)
    """
    parser = argparse.ArgumentParser(
        description='股票收盘选股系统 - Stock Picker System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例 (Examples):
  python run.py                          # 使用默认配置运行
  python run.py --date 20240217          # 指定日期运行
  python run.py --config custom.yaml    # 使用自定义配置
  python run.py --version               # 显示版本信息
        '''
    )

    parser.add_argument(
        '--config',
        type=str,
        default='settings.yaml',
        help='配置文件路径 (Configuration file path), 默认: settings.yaml'
    )

    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='交易日期，格式 YYYYMMDD (Trading date in YYYYMMDD format), 默认: 当前日期'
    )

    parser.add_argument(
        '--strategies',
        type=str,
        default=None,
        help='启用的策略列表，逗号分隔 (Enabled strategies, comma-separated), 例如: ma_cross,rsi_oversold'
    )

    parser.add_argument(
        '--top-n',
        type=int,
        default=None,
        help='输出前 N 只股票 (Output top N stocks), 覆盖配置文件设置'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='启用详细日志输出 (Enable verbose logging)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    return parser.parse_args()


def main():
    """
    主函数
    Main function

    解析参数、加载配置、启动选股流程。
    Parses arguments, loads configuration, and starts the stock selection workflow.
    """
    # 解析命令行参数
    # Parse command-line arguments
    args = parse_arguments()

    try:
        # 加载配置文件
        # Load configuration file
        config = ConfigManager.load_and_validate(args.config)

        # 覆盖配置（如果指定了命令行参数）
        # Override configuration if command-line arguments are specified
        if args.verbose:
            config['logging']['level'] = 'DEBUG'

        if args.top_n:
            config['output']['top_n'] = args.top_n

        # 验证 Tushare Token
        try:
            ConfigManager.get_token(config)
        except ConfigurationError as e:
            print(f"错误: {e}")
            print("请在 .env 文件中设置 TUSHARE_TOKEN 或设置环境变量")
            sys.exit(1)

        # 初始化日志
        # Initialize logger
        logger = setup_logger(
            level=config['logging']['level'],
            log_file=config['logging']['file'],
            console=config['logging']['console']
        )

        # 验证日期格式
        # Validate date format
        if args.date:
            try:
                datetime.strptime(args.date, '%Y%m%d')
            except ValueError:
                logger.error(f"日期格式错误: {args.date}，请使用 YYYYMMDD 格式")
                sys.exit(1)

        # 打印启动信息
        # Print startup information
        logger.info("=" * 60)
        logger.info("股票收盘选股系统启动")
        logger.info("Stock Picker System Starting")
        logger.info("=" * 60)
        logger.info(f"配置文件 (Config): {args.config}")
        logger.info(f"运行日期 (Date): {args.date or '最新交易日 (Latest trading day)'}")
        logger.info(f"日志级别 (Log Level): {config['logging']['level']}")
        logger.info("=" * 60)

        # 初始化流程控制器
        # Initialize pipeline controller
        pipeline = Pipeline(config)

        # 执行选股流程
        # Execute stock selection workflow
        results = pipeline.run(date=args.date)

        # 打印完成信息
        # Print completion information
        logger.info("=" * 60)
        logger.info("选股流程完成")
        logger.info("Stock Selection Completed")
        logger.info(f"候选股票数量 (Candidates): {len(results)}")
        logger.info("=" * 60)

    except FileNotFoundError as e:
        print(f"错误 (Error): {e}")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误 (Error occurred): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
