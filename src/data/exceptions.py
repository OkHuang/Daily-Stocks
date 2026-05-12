"""自定义异常类"""


class DataFetchError(Exception):
    """数据获取异常"""

    def __init__(self, message: str, stock_code: str = None):
        self.message = message
        self.stock_code = stock_code
        super().__init__(self.message)

    def __str__(self):
        if self.stock_code:
            return f"DataFetchError[{self.stock_code}]: {self.message}"
        return f"DataFetchError: {self.message}"


class DataValidationError(Exception):
    """数据验证异常"""

    def __init__(self, message: str, errors: list = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)

    def __str__(self):
        error_str = "; ".join(self.errors[:3])  # 只显示前3个错误
        if error_str:
            return f"DataValidationError: {self.message} - {error_str}"
        return f"DataValidationError: {self.message}"


class StorageError(Exception):
    """存储异常"""

    def __init__(self, message: str, operation: str = None):
        self.message = message
        self.operation = operation
        super().__init__(self.message)

    def __str__(self):
        if self.operation:
            return f"StorageError[{self.operation}]: {self.message}"
        return f"StorageError: {self.message}"


class StrategyExecutionError(Exception):
    """策略执行异常"""

    def __init__(self, message: str, strategy_name: str = None, stock_code: str = None):
        self.message = message
        self.strategy_name = strategy_name
        self.stock_code = stock_code
        super().__init__(self.message)

    def __str__(self):
        parts = ["StrategyExecutionError"]
        if self.strategy_name:
            parts.append(f"[{self.strategy_name}]")
        if self.stock_code:
            parts.append(f"[{self.stock_code}]")
        parts.append(f": {self.message}")
        return "".join(parts)


class ConfigurationError(Exception):
    """配置异常"""

    def __init__(self, message: str, config_key: str = None):
        self.message = message
        self.config_key = config_key
        super().__init__(self.message)

    def __str__(self):
        if self.config_key:
            return f"ConfigurationError[{self.config_key}]: {self.message}"
        return f"ConfigurationError: {self.message}"
