"""
日志配置模块 - Logger Configuration Module

该模块提供统一的日志配置功能。
This module provides unified logging configuration functionality.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "stock_picker",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    配置并返回日志记录器
    Configure and return a logger

    参数 (Parameters):
        name: 日志记录器名称 (Logger name)
        level: 日志级别 (Log level): DEBUG/INFO/WARNING/ERROR/CRITICAL
        log_file: 日志文件路径 (Log file path)
        console: 是否输出到控制台 (Whether to output to console)

    返回 (Returns):
        logging.Logger: 配置好的日志记录器 (Configured logger)
    """
    # 创建日志记录器
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 清除现有的处理器
    # Clear existing handlers
    logger.handlers.clear()

    # 创建格式化器
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 添加文件处理器
    # Add file handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 添加控制台处理器
    # Add console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "stock_picker") -> logging.Logger:
    """
    获取已配置的日志记录器
    Get an already configured logger

    参数 (Parameters):
        name: 日志记录器名称 (Logger name)

    返回 (Returns):
        logging.Logger: 日志记录器 (Logger)
    """
    return logging.getLogger(name)
