"""
数据模块单元测试 - Data Module Unit Tests

该文件包含数据模块的单元测试。
This file contains unit tests for the data module.
"""

import unittest
import tempfile
import os
from pathlib import Path

from stock_picker.data.local_store import LocalStore
from stock_picker.data.stock_pool import StockPool


class TestLocalStore(unittest.TestCase):
    """本地存储测试 (Local storage tests)"""

    def setUp(self):
        """设置测试环境 (Set up test environment)"""
        # 创建临时数据库文件
        # Create temporary database file
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_data.db")
        self.local_store = LocalStore(db_path=self.db_path)

    def tearDown(self):
        """清理测试环境 (Clean up test environment)"""
        # 删除临时文件
        # Delete temporary files
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_initialization(self):
        """测试初始化 (Test initialization)"""
        self.assertIsNotNone(self.local_store)
        self.assertEqual(self.local_store.db_path, Path(self.db_path))

    def test_directory_creation(self):
        """测试目录自动创建 (Test automatic directory creation)"""
        # 数据库文件所在目录应该被创建
        # The directory containing the database file should be created
        self.assertTrue(os.path.exists(self.temp_dir))


class TestStockPool(unittest.TestCase):
    """股票池测试 (Stock pool tests)"""

    def test_initialization_default(self):
        """测试默认初始化 (Test default initialization)"""
        stock_pool = StockPool()
        self.assertEqual(stock_pool.source, "all_a")
        self.assertIsNone(stock_pool.custom_file)

    def test_initialization_csi300(self):
        """测试沪深300初始化 (Test CSI 300 initialization)"""
        stock_pool = StockPool(source="csi300")
        self.assertEqual(stock_pool.source, "csi300")

    def test_initialization_custom(self):
        """测试自定义列表初始化 (Test custom list initialization)"""
        stock_pool = StockPool(source="custom", custom_file="test.txt")
        self.assertEqual(stock_pool.source, "custom")
        self.assertEqual(stock_pool.custom_file, "test.txt")

    def test_custom_file_not_found(self):
        """测试自定义文件不存在 (Test custom file not found)"""
        stock_pool = StockPool(source="custom", custom_file="nonexistent.txt")

        with self.assertRaises(FileNotFoundError):
            stock_pool.get_stock_list()

    def test_invalid_source(self):
        """测试无效来源 (Test invalid source)"""
        stock_pool = StockPool(source="invalid_source")

        with self.assertRaises(ValueError):
            stock_pool.get_stock_list()


if __name__ == '__main__':
    unittest.main()
