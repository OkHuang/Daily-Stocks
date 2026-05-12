"""SQLite 本地存储管理，支持增量更新"""

from typing import Optional, List, Sequence
import pandas as pd
from pathlib import Path
import logging
import sqlite3
import threading


class LocalStore:
    """SQLite 数据库存储历史行情数据，每只股票立即保存避免崩溃丢失"""

    def __init__(self, db_path: str = "database/market_data.db", logger: Optional[logging.Logger] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)
        self._local = threading.local()
        self._lock = threading.Lock()

    def _get_connection(self):
        """获取线程安全的数据库连接，每个线程使用独立连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            with self._lock:
                # 双重检查锁
                if not hasattr(self._local, 'conn') or self._local.conn is None:
                    self._local.conn = sqlite3.connect(
                        self.db_path,
                        check_same_thread=False
                    )
                    self._local.conn.execute("PRAGMA journal_mode=WAL")
                    self._local.conn.execute("PRAGMA synchronous=NORMAL")
                    self.logger.debug(f"Created new database connection for thread {threading.current_thread().name}")
        return self._local.conn

    def _init_tables(self):
        """创建必要的数据库表（如不存在）"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建股票日线数据表
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
        """使用 INSERT OR REPLACE 批量保存日线数据"""
        if df is None or len(df) == 0:
            self.logger.warning("Empty dataframe, nothing to save")
            return 0

        self._init_tables()

        conn = self._get_connection()

        try:
            # 使用 executemany 批量插入，提升性能
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
        """从数据库加载日线数据"""
        self._init_tables()

        conn = self._get_connection()

        sql = "SELECT * FROM stock_daily WHERE ts_code = ?"
        params = [stock_code]

        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)

        sql += " ORDER BY trade_date ASC"

        try:
            df = pd.read_sql_query(sql, conn, params=params)
            if len(df) > 0:
                self.logger.debug(f"Loaded {len(df)} records for {stock_code}")
            return df
        except Exception as e:
            self.logger.error(f"Failed to load data for {stock_code}: {e}")
            return None

    def get_latest_date(self, stock_code: str) -> Optional[str]:
        """获取指定股票的最新数据日期"""
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
        """获取股票基本信息"""
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
        """获取数据库中所有股票代码（从 stock_list 表）"""
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
        """从 stock_daily 表获取所有股票代码（用于增量收集）"""
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
        """获取数据库统计信息"""
        self._init_tables()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(DISTINCT ts_code) FROM stock_list")
            total_stocks = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM stock_daily")
            total_records = cursor.fetchone()[0]

            cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_daily")
            date_range = cursor.fetchone()

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
        """批量更新多只股票的日线数据，每只股票处理完立即保存"""
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

                df = fetcher.fetch_daily(stock_code, start_date, end_date)

                if df is not None and len(df) > 0:
                    # 验证数据完整性
                    validation_result = self.validate_daily_data(df, stock_code)

                    if not validation_result['is_valid']:
                        stats['failed'] += 1
                        stats['failed_stocks'].append(stock_code)
                        self.logger.error(f"  ✗ Data validation failed: {validation_result['errors'][:3]}")
                        continue

                    # 立即保存到数据库
                    saved_count = self.save_daily_data(df)
                    stats['total_records'] += saved_count
                    stats['success'] += 1

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
        """验证日线数据的完整性和合理性"""
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
            result['errors'].append("DataFrame 为空")
            return result

        # 检查必要的列是否存在
        required_columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            result['is_valid'] = False
            result['errors'].append(f"缺少必要的列: {missing_columns}")
            return result

        # 检查数据类型
        try:
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['vol'] = pd.to_numeric(df['vol'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"数据类型转换失败: {e}")
            return result

        # 向量化数据验证
        price_cols = ['open', 'high', 'low', 'close']
        volume_cols = ['vol', 'amount']
        all_cols = price_cols + volume_cols

        # 负数检查
        neg_mask = df[all_cols] < 0
        for col in all_cols:
            neg_count = neg_mask[col].sum()
            if neg_count > 0:
                result['errors'].append(f"{col} 存在 {neg_count} 行负数值")
                result['stats']['invalid_records'] += neg_count

        if result['errors']:
            result['is_valid'] = False

        # 价格逻辑检查（排除含 NaN 的行）
        valid_mask = df[price_cols].notna().all(axis=1)
        df_valid = df[valid_mask]

        logic_checks = [
            (df_valid['high'] < df_valid['low'], "high < low"),
            (df_valid['high'] < df_valid['open'], "high < open"),
            (df_valid['high'] < df_valid['close'], "high < close"),
            (df_valid['low'] > df_valid['open'], "low > open"),
            (df_valid['low'] > df_valid['close'], "low > close"),
        ]
        for mask, desc in logic_checks:
            error_count = mask.sum()
            if error_count > 0:
                result['is_valid'] = False
                result['errors'].append(f"{error_count} 行价格逻辑错误: {desc}")
                result['stats']['invalid_records'] += error_count

        # 缺失值统计
        missing_per_row = df[all_cols].isna().sum(axis=1)
        all_nan_count = (missing_per_row == len(all_cols)).sum()
        partial_nan_count = ((missing_per_row > 0) & (missing_per_row < len(all_cols))).sum()
        result['stats']['missing_values'] = int(missing_per_row.sum())

        if all_nan_count > 0:
            result['warnings'].append(f"{all_nan_count} 行所有字段为空（可能停牌）")
        if partial_nan_count > 0:
            result['warnings'].append(f"{partial_nan_count} 行部分字段为空")

        # 检查是否有重复记录（同一股票同一日期）
        if 'ts_code' in df.columns and 'trade_date' in df.columns:
            duplicates = df.duplicated(subset=['ts_code', 'trade_date'], keep='first')
            dup_count = duplicates.sum()
            if dup_count > 0:
                result['warnings'].append(f"发现 {dup_count} 条重复记录")

        # 生成验证日志
        prefix = f"[{stock_code}] " if stock_code else ""
        if result['is_valid']:
            self.logger.debug(f"{prefix}数据验证通过: {result['stats']['total_records']} 条记录")
        else:
            self.logger.warning(f"{prefix}数据验证失败: {len(result['errors'])} 个错误")

        if result['warnings']:
            for warning in result['warnings']:
                self.logger.warning(f"{prefix}{warning}")

        return result

    def close(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
            self.logger.debug(f"Closed database connection for thread {threading.current_thread().name}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
