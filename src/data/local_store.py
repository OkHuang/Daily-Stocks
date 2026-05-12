"""
本地存储模块 - Local Storage Module

该模块负责管理本地历史数据的存储和读写。
This module manages local storage and read/write operations for historical data.

功能特性 (Features):
- 增量保存 (Incremental save)
- 数据查询接口 (Data query interface)
- 错误处理 (Error handling)
- 日志记录 (Logging)
"""

from typing import Optional, List, Sequence
import pandas as pd
from pathlib import Path
import logging
import sqlite3
import threading


class LocalStore:
    """
    本地数据存储管理类
    Local data storage manager

    使用 SQLite 数据库存储历史行情数据，支持增量更新。
    Uses SQLite database to store historical market data with incremental update support.

    功能特性 (Features):
    - 增量保存：每只股票立即保存，避免程序崩溃丢失数据 (Incremental save: save immediately per stock)
    - 数据查询：提供多种查询接口 (Data query: various query interfaces)
    - 事务处理：确保数据一致性 (Transaction processing: ensure data consistency)
    """

    def __init__(self, db_path: str = "database/market_data.db", logger: Optional[logging.Logger] = None):
        """
        初始化本地存储
        Initialize local storage

        参数 (Parameters):
            db_path: 数据库文件路径 (Database file path)
            logger: 日志记录器 (Logger instance)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)
        self._local = threading.local()  # 线程本地存储
        self._lock = threading.Lock()  # 用于初始化保护

    def _get_connection(self):
        """
        获取线程安全的数据库连接
        Get thread-safe database connection

        每个线程使用独立的数据库连接，避免并发问题。
        Each thread uses its own database connection to avoid concurrency issues.

        返回 (Returns):
            sqlite3.Connection: 数据库连接对象 (Database connection object)
        """
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            with self._lock:
                # 双重检查锁
                if not hasattr(self._local, 'conn') or self._local.conn is None:
                    self._local.conn = sqlite3.connect(
                        self.db_path,
                        check_same_thread=False
                    )
                    self._local.conn.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式，提高并发性能
                    self._local.conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全
                    self.logger.debug(f"Created new database connection for thread {threading.current_thread().name}")
        return self._local.conn

    def _init_tables(self):
        """
        初始化数据库表结构
        Initialize database table structure

        创建必要的数据库表，如果不存在。
        Creates necessary database tables if they don't exist.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建股票日线数据表
        # Create stock daily data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily (
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                vol REAL,
                amount REAL,
                PRIMARY KEY (ts_code, trade_date)
            )
        """)

        # 创建股票基本信息表
        # Create stock basic info table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_list (
                ts_code TEXT PRIMARY KEY,
                name TEXT,
                industry TEXT,
                list_date TEXT,
                update_time TEXT
            )
        """)

        # 创建索引以提高查询性能
        # Create indexes to improve query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_date
            ON stock_daily(trade_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ts_code
            ON stock_daily(ts_code)
        """)

        conn.commit()
        self.logger.info("Database tables initialized")

    def save_daily_data(self, df: pd.DataFrame) -> int:
        """
        保存日线数据到数据库（批量插入优化）
        Save daily data to database (optimized with batch insert)

        使用 INSERT OR REPLACE 策略将数据保存到 stock_daily 表：
        - 如果记录不存在（主键冲突），则插入新记录
        - 如果记录已存在，则替换旧记录
        - 使用批量插入和事务保证数据一致性

        参数 (Parameters):
            df: 包含日线数据的 DataFrame (DataFrame containing daily data)

        返回 (Returns):
            int: 保存的记录数 (Number of records saved)
        """
        if df is None or len(df) == 0:
            self.logger.warning("Empty dataframe, nothing to save")
            return 0

        # 确保表存在
        # Ensure tables exist
        self._init_tables()

        conn = self._get_connection()

        # 使用事务确保数据一致性
        # Use transaction to ensure data consistency
        try:
            # 使用 executemany 批量插入，提升性能
            # Use executemany for batch insert to improve performance
            data = df[['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount']].values.tolist()

            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO stock_daily
                (ts_code, trade_date, open, high, low, close, vol, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data)

            conn.commit()
            saved_count = len(data)
            self.logger.info(f"Batch saved {saved_count} records")
            return saved_count

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Batch save failed, rolled back: {e}")
            raise

    def load_daily_data(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        从数据库加载日线数据
        Load daily data from database

        参数 (Parameters):
            stock_code: 股票代码 (Stock code)
            start_date: 开始日期，格式 'YYYYMMDD' (Start date)
            end_date: 结束日期，格式 'YYYYMMDD' (End date)

        返回 (Returns):
            Optional[pd.DataFrame]: 日线数据 (Daily data)
        """
        self._init_tables()

        conn = self._get_connection()

        # 构建SQL查询
        # Build SQL query
        sql = "SELECT * FROM stock_daily WHERE ts_code = ?"
        params = [stock_code]

        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)

        sql += " ORDER BY trade_date ASC"

        # 执行查询
        # Execute query
        try:
            df = pd.read_sql_query(sql, conn, params=params)
            if len(df) > 0:
                self.logger.debug(f"Loaded {len(df)} records for {stock_code}")
            return df
        except Exception as e:
            self.logger.error(f"Failed to load data for {stock_code}: {e}")
            return None

    def get_latest_date(self, stock_code: str) -> Optional[str]:
        """
        获取指定股票的最新数据日期
        Get the latest data date for a specific stock

        参数 (Parameters):
            stock_code: 股票代码 (Stock code)

        返回 (Returns):
            Optional[str]: 最新日期，格式 'YYYYMMDD'，若无数据则返回 None
                          (Latest date in 'YYYYMMDD' format, or None if no data)
        """
        self._init_tables()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT MAX(trade_date) FROM stock_daily WHERE ts_code = ?
            """, (stock_code,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            self.logger.error(f"Failed to get latest date for {stock_code}: {e}")
            return None

    def get_stock_info(self, stock_code: str) -> Optional[dict]:
        """
        获取股票基本信息
        Get stock basic information

        参数 (Parameters):
            stock_code: 股票代码 (Stock code)

        返回 (Returns):
            Optional[dict]: 股票信息字典 (Stock info dictionary)
        """
        self._init_tables()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT ts_code, name, industry, list_date
                FROM stock_list
                WHERE ts_code = ?
            """, (stock_code,))
            result = cursor.fetchone()

            if result:
                return {
                    'ts_code': result[0],
                    'name': result[1],
                    'industry': result[2],
                    'list_date': result[3]
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get stock info for {stock_code}: {e}")
            return None

    def get_all_stocks(self) -> List[str]:
        """
        获取数据库中所有股票代码（从 stock_list 表）
        Get all stock codes in database (from stock_list table)

        返回 (Returns):
            List[str]: 股票代码列表 (List of stock codes)
        """
        self._init_tables()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT ts_code FROM stock_list ORDER BY ts_code")
            results = cursor.fetchall()
            return [row[0] for row in results]
        except Exception as e:
            self.logger.error(f"Failed to get all stocks: {e}")
            return []

    def get_all_stocks_from_daily(self) -> List[str]:
        """
        从 stock_daily 表获取所有股票代码（用于增量收集）
        Get all stock codes from stock_daily table (for incremental collection)

        返回 (Returns):
            List[str]: 股票代码列表 (List of stock codes)
        """
        self._init_tables()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT DISTINCT ts_code FROM stock_daily ORDER BY ts_code")
            results = cursor.fetchall()
            return [row[0] for row in results]
        except Exception as e:
            self.logger.error(f"Failed to get all stocks from daily table: {e}")
            return []

    def get_statistics(self) -> dict:
        """
        获取数据库统计信息
        Get database statistics

        返回 (Returns):
            dict: 统计信息 (Statistics):
                - total_stocks: 股票总数 (Total stocks)
                - total_records: 总记录数 (Total records)
                - date_range: 日期范围 (Date range)
                - db_size: 数据库大小 (Database size in MB)
        """
        self._init_tables()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 股票数量
            # Stock count
            cursor.execute("SELECT COUNT(DISTINCT ts_code) FROM stock_list")
            total_stocks = cursor.fetchone()[0]

            # 记录数量
            # Record count
            cursor.execute("SELECT COUNT(*) FROM stock_daily")
            total_records = cursor.fetchone()[0]

            # 日期范围
            # Date range
            cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_daily")
            date_range = cursor.fetchone()

            # 数据库大小
            # Database size
            db_size = self.db_path.stat().st_size / (1024 * 1024)  # MB

            stats = {
                'total_stocks': total_stocks,
                'total_records': total_records,
                'date_range': date_range,
                'db_size': round(db_size, 2)
            }

            self.logger.info(f"Database stats: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}

    def update_daily_data(
        self,
        stock_list: List[str],
        fetcher,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        批量更新多只股票的日线数据（带进度跟踪和立即保存）
        Batch update daily data for multiple stocks (with progress tracking and immediate save)

        对每只股票：
        1. 从数据源获取指定时间范围的全量数据
        2. 验证数据完整性
        3. 立即保存到数据库（避免程序崩溃丢失数据）

        注意 (Note):
            - 这是全量收集，会获取 start_date 到 end_date 之间的所有数据
            - "立即保存"指每处理完一只股票就保存，避免程序中断导致数据丢失

        参数 (Parameters):
            stock_list: 股票代码列表 (List of stock codes)
            fetcher: 数据获取器实例 (Data fetcher instance)
            start_date: 开始日期 (Start date)
            end_date: 结束日期 (End date)

        返回 (Returns):
            dict: 更新统计信息 (Update statistics):
                - total: 总数 (Total count)
                - success: 成功数 (Success count)
                - failed: 失败数 (Failed count)
                - total_records: 总记录数 (Total records saved)
                - failed_stocks: 失败股票列表 (List of failed stocks)
        """
        self.logger.info(f"Starting batch update for {len(stock_list)} stocks")

        stats = {
            'total': len(stock_list),
            'success': 0,
            'failed': 0,
            'total_records': 0,
            'failed_stocks': []
        }

        for idx, stock_code in enumerate(stock_list, 1):
            try:
                self.logger.info(f"[{idx}/{len(stock_list)}] Updating {stock_code}...")

                # 从数据源获取全量数据（指定时间范围）
                # Fetch full data from source (within specified date range)
                df = fetcher.fetch_daily(stock_code, start_date, end_date)

                if df is not None and len(df) > 0:
                    # 验证数据完整性
                    # Validate data integrity
                    validation_result = self.validate_daily_data(df, stock_code)

                    if not validation_result['is_valid']:
                        stats['failed'] += 1
                        stats['failed_stocks'].append(stock_code)
                        self.logger.error(f"  ✗ Data validation failed: {validation_result['errors'][:3]}")  # 只显示前3个错误
                        continue

                    # 立即保存到数据库（每处理完一只股票就保存，避免程序中断导致数据丢失）
                    # Save to database immediately (save after each stock to prevent data loss on interruption)
                    saved_count = self.save_daily_data(df)
                    stats['total_records'] += saved_count
                    stats['success'] += 1

                    # 显示验证警告（如果有）
                    # Show validation warnings (if any)
                    if validation_result['warnings']:
                        for warning in validation_result['warnings']:
                            self.logger.warning(f"  ⚠ {warning}")

                    self.logger.info(f"  ✓ Saved {saved_count} records")
                else:
                    stats['failed'] += 1
                    stats['failed_stocks'].append(stock_code)
                    self.logger.warning(f"  ✗ No data retrieved")

            except Exception as e:
                stats['failed'] += 1
                stats['failed_stocks'].append(stock_code)
                self.logger.error(f"  ✗ Error: {e}")

        self.logger.info(f"Batch update completed: {stats}")
        return stats

    def validate_daily_data(self, df: pd.DataFrame, stock_code: Optional[str] = None) -> dict:
        """
        验证日线数据的完整性和合理性
        Validate daily data integrity and validity

        参数 (Parameters):
            df: 包含日线数据的 DataFrame
            stock_code: 股票代码（用于日志记录）

        返回 (Returns):
            dict: 验证结果 (Validation results):
                - is_valid: 是否通过验证 (Whether passed validation)
                - errors: 错误列表 (Error list)
                - warnings: 警告列表 (Warning list)
                - stats: 统计信息 (Statistics)
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {
                'total_records': len(df) if df is not None else 0,
                'invalid_records': 0,
                'missing_values': 0
            }
        }

        if df is None or len(df) == 0:
            result['is_valid'] = False
            result['errors'].append("DataFrame 为空 (DataFrame is empty)")
            return result

        # 检查必要的列是否存在
        # Check if required columns exist
        required_columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            result['is_valid'] = False
            result['errors'].append(f"缺少必要的列 (Missing required columns): {missing_columns}")
            return result

        # 检查数据类型
        # Check data types
        try:
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['vol'] = pd.to_numeric(df['vol'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"数据类型转换失败 (Data type conversion failed): {e}")
            return result

        # 逐行验证数据
        # Validate data row by row
        for idx, row in df.iterrows():
            record_errors = []

            # 检查价格是否为负数（只检查负数，NaN 值在后续单独处理）
            # Check if prices are negative (NaN values are handled separately)
            if not pd.isna(row['open']) and row['open'] < 0:
                record_errors.append(f"第 {idx} 行: open 价格为负数 (Negative open price)")
            if not pd.isna(row['high']) and row['high'] < 0:
                record_errors.append(f"第 {idx} 行: high 价格为负数 (Negative high price)")
            if not pd.isna(row['low']) and row['low'] < 0:
                record_errors.append(f"第 {idx} 行: low 价格为负数 (Negative low price)")
            if not pd.isna(row['close']) and row['close'] < 0:
                record_errors.append(f"第 {idx} 行: close 价格为负数 (Negative close price)")

            # 检查成交量和成交额是否为负数（只检查负数，NaN 值在后续单独处理）
            # Check if volume and amount are negative (NaN values are handled separately)
            if not pd.isna(row['vol']) and row['vol'] < 0:
                record_errors.append(f"第 {idx} 行: vol 成交量为负数 (Negative volume)")
            if not pd.isna(row['amount']) and row['amount'] < 0:
                record_errors.append(f"第 {idx} 行: amount 成交额为负数 (Negative amount)")

            # 检查价格逻辑关系：high >= low, high >= open, high >= close, low <= open, low <= close
            # Check price logic: high >= low, high >= open, high >= close, low <= open, low <= close
            try:
                if not pd.isna(row['high']) and not pd.isna(row['low']):
                    if row['high'] < row['low']:
                        record_errors.append(f"第 {idx} 行: high < low，价格逻辑错误 (Price logic error: high < low)")
                if not pd.isna(row['high']) and not pd.isna(row['open']):
                    if row['high'] < row['open']:
                        record_errors.append(f"第 {idx} 行: high < open，价格逻辑错误 (Price logic error: high < open)")
                if not pd.isna(row['high']) and not pd.isna(row['close']):
                    if row['high'] < row['close']:
                        record_errors.append(f"第 {idx} 行: high < close，价格逻辑错误 (Price logic error: high < close)")
                if not pd.isna(row['low']) and not pd.isna(row['open']):
                    if row['low'] > row['open']:
                        record_errors.append(f"第 {idx} 行: low > open，价格逻辑错误 (Price logic error: low > open)")
                if not pd.isna(row['low']) and not pd.isna(row['close']):
                    if row['low'] > row['close']:
                        record_errors.append(f"第 {idx} 行: low > close，价格逻辑错误 (Price logic error: low > close)")
            except Exception as e:
                record_errors.append(f"第 {idx} 行: 价格逻辑检查失败 (Price logic check failed): {e}")

            # 检查缺失值（可能是停牌期间的正常现象）
            # Check missing values (normal during suspension periods)
            missing_count = sum(1 for col in ['open', 'high', 'low', 'close', 'vol', 'amount'] if pd.isna(row[col]))
            if missing_count > 0:
                result['stats']['missing_values'] += missing_count
                # 对于 NaN 值，只记录警告（可能是停牌）
                # For NaN values, only record warning (possibly suspended)
                if missing_count == 6:  # 所有字段都是 NaN
                    result['warnings'].append(f"第 {idx} 行 (日期: {row.get('trade_date', 'N/A')}): 所有字段为空（可能停牌，Suspended trading）")
                elif missing_count > 0:
                    result['warnings'].append(f"第 {idx} 行 (日期: {row.get('trade_date', 'N/A')}): 有 {missing_count} 个字段为空")

            if record_errors:
                result['is_valid'] = False
                result['errors'].extend(record_errors)
                result['stats']['invalid_records'] += 1

        # 检查是否有重复记录（同一股票同一日期）
        # Check for duplicate records (same stock same date)
        if 'ts_code' in df.columns and 'trade_date' in df.columns:
            duplicates = df.duplicated(subset=['ts_code', 'trade_date'], keep='first')
            dup_count = duplicates.sum()
            if dup_count > 0:
                result['warnings'].append(f"发现 {dup_count} 条重复记录 (Found {dup_count} duplicate records)")

        # 生成验证日志
        # Generate validation log
        prefix = f"[{stock_code}] " if stock_code else ""
        if result['is_valid']:
            self.logger.debug(f"{prefix}数据验证通过 (Data validation passed): {result['stats']['total_records']} 条记录")
        else:
            self.logger.warning(f"{prefix}数据验证失败 (Data validation failed): {len(result['errors'])} 个错误")

        if result['warnings']:
            for warning in result['warnings']:
                self.logger.warning(f"{prefix}{warning}")

        return result

    def close(self):
        """
        关闭当前线程的数据库连接
        Close database connection for current thread
        """
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
            self.logger.debug(f"Closed database connection for thread {threading.current_thread().name}")

    def __enter__(self):
        """
        上下文管理器入口
        Context manager entry
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器退出，自动关闭连接
        Context manager exit, automatically close connection
        """
        self.close()
        return False
