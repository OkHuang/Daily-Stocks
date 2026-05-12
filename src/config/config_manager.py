"""配置加载、验证和环境变量支持"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from dotenv import load_dotenv
from src.data.exceptions import ConfigurationError


class ConfigManager:
    """配置管理器，支持环境变量覆盖和配置验证"""

    @staticmethod
    def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载配置文件并支持环境变量覆盖"""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "settings.yaml"

        config_path = Path(config_path)

        # 加载 .env 文件中的环境变量
        env_path = config_path.parent / ".env"
        load_dotenv(env_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML format: {e}")

        # 从环境变量获取敏感配置
        if 'TUSHARE_TOKEN' in os.environ:
            config['data_source']['token'] = os.environ['TUSHARE_TOKEN']

        return config

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """验证配置完整性"""
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
            if value is None or value == '':
                raise ConfigurationError(f"Configuration value cannot be empty: {key}", key)

        # 验证数据源提供商
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
        """获取 API Token，优先从环境变量读取"""
        # 优先从环境变量获取
        token = os.environ.get('TUSHARE_TOKEN')

        if token:
            return token

        # 从配置文件获取
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
        """加载并验证配置（便捷方法）"""
        config = ConfigManager.load_config(config_path)
        ConfigManager.validate_config(config)
        return config
