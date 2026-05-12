"""
配置管理器 - Configuration Manager

提供配置加载、验证和环境变量支持。
Provides configuration loading, validation, and environment variable support.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from dotenv import load_dotenv
from data.exceptions import ConfigurationError


class ConfigManager:
    """
    配置管理器
    Configuration Manager

    负责加载配置文件，支持环境变量覆盖，并提供配置验证功能。
    Responsible for loading config files, supporting environment variable override,
    and providing configuration validation.
    """

    @staticmethod
    def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置文件并支持环境变量覆盖
        Load configuration file with environment variable override support

        参数 (Parameters):
            config_path: 配置文件路径 (Configuration file path)
                       如果为 None，使用默认路径 (If None, use default path)

        返回 (Returns):
            Dict[str, Any]: 配置字典 (Configuration dictionary)

        异常 (Raises):
            FileNotFoundError: 配置文件不存在 (Configuration file not found)
            ConfigurationError: 配置格式错误 (Configuration format error)
        """
        # 确定配置文件路径
        # Determine configuration file path
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "settings.yaml"

        config_path = Path(config_path)

        # 加载 .env 文件中的环境变量
        env_path = config_path.parent / ".env"
        load_dotenv(env_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # 加载 YAML 配置
        # Load YAML configuration
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML format: {e}")

        # 从环境变量获取敏感配置
        # Get sensitive configuration from environment variables
        if 'TUSHARE_TOKEN' in os.environ:
            config['data_source']['token'] = os.environ['TUSHARE_TOKEN']

        return config

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        验证配置完整性
        Validate configuration integrity

        参数 (Parameters):
            config: 配置字典 (Configuration dictionary)

        返回 (Returns):
            bool: 验证是否通过 (Whether validation passed)

        异常 (Raises):
            ConfigurationError: 配置验证失败 (Configuration validation failed)
        """
        required_keys = [
            'data_source.token',
            'data_source.provider',
            'storage.path',
            'stock_pool.source',
            'output.path'
        ]

        for key in required_keys:
            keys = key.split('.')
            value = config

            try:
                for k in keys:
                    value = value[k]
            except (KeyError, TypeError):
                raise ConfigurationError(f"Missing required configuration: {key}", key)

            # 验证配置值不为空
            # Validate configuration value is not empty
            if value is None or value == '':
                raise ConfigurationError(f"Configuration value cannot be empty: {key}", key)

        # 验证数据源提供商
        # Validate data source provider
        valid_providers = ['tushare']
        if config['data_source']['provider'] not in valid_providers:
            raise ConfigurationError(
                f"Unsupported data provider: {config['data_source']['provider']}. "
                f"Supported providers: {', '.join(valid_providers)}",
                'data_source.provider'
            )

        return True

    @staticmethod
    def get_token(config: Dict[str, Any]) -> str:
        """
        获取 API Token（优先从环境变量）
        Get API Token (prefer from environment variable)

        参数 (Parameters):
            config: 配置字典 (Configuration dictionary)

        返回 (Returns):
            str: API Token

        异常 (Raises):
            ConfigurationError: Token 未配置或为空 (Token not configured or empty)
        """
        # 优先从环境变量获取
        # Prefer environment variable
        token = os.environ.get('TUSHARE_TOKEN')

        if token:
            return token

        # 从配置文件获取
        # Get from configuration file
        try:
            token = config['data_source']['token']
        except (KeyError, TypeError):
            raise ConfigurationError(
                "Tushare Token 未配置。请设置 TUSHARE_TOKEN 环境变量或在 .env 文件中配置",
                'data_source.token'
            )

        if not token or token == 'YOUR_TOKEN_HERE':
            raise ConfigurationError(
                "Tushare Token 未配置。请设置 TUSHARE_TOKEN 环境变量或在 .env 文件中配置",
                'data_source.token'
            )

        return token

    @staticmethod
    def load_and_validate(config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载并验证配置（便捷方法）
        Load and validate configuration (convenience method)

        参数 (Parameters):
            config_path: 配置文件路径 (Configuration file path)

        返回 (Returns):
            Dict[str, Any]: 验证后的配置字典 (Validated configuration dictionary)
        """
        config = ConfigManager.load_config(config_path)
        ConfigManager.validate_config(config)
        return config
