"""
自定义异常类 - Custom Exception Classes

定义项目中使用的自定义异常类型。
Defines custom exception types used in the project.
"""


class DataFetchError(Exception):
    """
    数据获取异常 - Data Fetch Exception

    当从数据源获取数据失败时抛出。
    Raised when fetching data from data source fails.

    属性 (Attributes):
        message: 错误消息 (Error message)
        stock_code: 股票代码（可选）(Stock code, optional)
    """

    def __init__(self, message: str, stock_code: str = None):
        self.message = message
        self.stock_code = stock_code
        super().__init__(self.message)

    def __str__(self):
        if self.stock_code:
            return f"DataFetchError[{self.stock_code}]: {self.message}"
        return f"DataFetchError: {self.message}"


class DataValidationError(Exception):
    """
    数据验证异常 - Data Validation Exception

    当数据验证失败时抛出。
    Raised when data validation fails.

    属性 (Attributes):
        message: 错误消息 (Error message)
        errors: 错误列表 (List of errors)
    """

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
    """
    存储异常 - Storage Exception

    当数据库操作失败时抛出。
    Raised when database operation fails.

    属性 (Attributes):
        message: 错误消息 (Error message)
        operation: 操作类型（可选）(Operation type, optional)
    """

    def __init__(self, message: str, operation: str = None):
        self.message = message
        self.operation = operation
        super().__init__(self.message)

    def __str__(self):
        if self.operation:
            return f"StorageError[{self.operation}]: {self.message}"
        return f"StorageError: {self.message}"


class StrategyExecutionError(Exception):
    """
    策略执行异常 - Strategy Execution Exception

    当策略执行失败时抛出。
    Raised when strategy execution fails.

    属性 (Attributes):
        message: 错误消息 (Error message)
        strategy_name: 策略名称（可选）(Strategy name, optional)
        stock_code: 股票代码（可选）(Stock code, optional)
    """

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
    """
    配置异常 - Configuration Exception

    当配置文件错误或缺少必要配置时抛出。
    Raised when configuration file is invalid or missing required config.

    属性 (Attributes):
        message: 错误消息 (Error message)
        config_key: 配置键（可选）(Config key, optional)
    """

    def __init__(self, message: str, config_key: str = None):
        self.message = message
        self.config_key = config_key
        super().__init__(self.message)

    def __str__(self):
        if self.config_key:
            return f"ConfigurationError[{self.config_key}]: {self.message}"
        return f"ConfigurationError: {self.message}"
