"""
结果格式化模块 - Output Formatter Module

该模块负责将选股结果格式化为各种输出格式。
This module is responsible for formatting stock selection results into various output formats.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from tabulate import tabulate


class Formatter:
    """
    结果格式化器
    Result formatter

    提供多种格式的结果输出功能，包括 CSV、Excel、Markdown 和终端表格。
    Provides result output functionality in various formats including CSV, Excel, Markdown, and terminal tables.
    """

    def _prepare_export_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        准备导出的数据框（统一的列筛选逻辑）
        Prepare DataFrame for export (unified column filtering logic)

        参数 (Parameters):
            df: 原始数据框 (Original DataFrame)

        返回 (Returns):
            pd.DataFrame: 筛选后的数据框 (Filtered DataFrame)
        """
        # 保留必要的列
        # Keep necessary columns
        columns_to_export = ['ts_code', 'score', 'signal_count']
        # 添加策略信号列（如果有）
        # Add strategy signal columns (if any)
        strategy_columns = [col for col in df.columns if col not in ['ts_code', 'score', 'signal_count']]
        columns_to_export.extend(strategy_columns)

        # 筛选存在的列
        # Filter existing columns
        existing_columns = [col for col in columns_to_export if col in df.columns]
        return df[existing_columns]

    def to_csv(self, df: pd.DataFrame, file_path: str):
        """
        导出为 CSV 文件
        Export to CSV file

        参数 (Parameters):
            df: 结果数据 (Result data)
            file_path: 输出文件路径 (Output file path)
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用统一的列筛选逻辑
        # Use unified column filtering logic
        df_export = self._prepare_export_columns(df)

        # 保存为 CSV
        # Save as CSV
        df_export.to_csv(file_path, index=False, encoding='utf-8-sig')

    def to_excel(self, df: pd.DataFrame, file_path: str, max_rows: int = 100000):
        """
        导出为 Excel 文件（支持大数据集分批处理）
        Export to Excel file (supports batch processing for large datasets)

        参数 (Parameters):
            df: 结果数据 (Result data)
            file_path: 输出文件路径 (Output file path)
            max_rows: 每个 sheet 的最大行数 (Maximum rows per sheet), default: 100000
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用统一的列筛选逻辑
        # Use unified column filtering logic
        df_export = self._prepare_export_columns(df)

        # 如果数据量超过 max_rows，分多个 sheet 写入
        # If data exceeds max_rows, write to multiple sheets
        if len(df_export) > max_rows:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for i in range(0, len(df_export), max_rows):
                    chunk = df_export.iloc[i:i + max_rows]
                    sheet_name = f'选股结果_{i // max_rows + 1}'
                    chunk.to_excel(writer, index=False, sheet_name=sheet_name)
        else:
            # 数据量不大，直接写入单个 sheet
            # Data size is small, write to single sheet directly
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='选股结果')

    def to_markdown(self, df: pd.DataFrame, file_path: str):
        """
        导出为 Markdown 文件
        Export to Markdown file

        参数 (Parameters):
            df: 结果数据 (Result data)
            file_path: 输出文件路径 (Output file path)
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用统一的列筛选逻辑
        # Use unified column filtering logic
        df_export = self._prepare_export_columns(df)

        # 生成 Markdown 表格
        # Generate Markdown table
        markdown_content = "# 选股结果\n\n"
        markdown_content += f"生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        markdown_content += df_export.to_markdown(index=False)

        # 保存为 Markdown
        # Save as Markdown
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

    def print_summary(self, df: pd.DataFrame, max_rows: int = 20):
        """
        在终端打印结果摘要
        Print result summary in terminal

        参数 (Parameters):
            df: 结果数据 (Result data)
            max_rows: 最大显示行数 (Maximum rows to display)
        """
        if df is None or len(df) == 0:
            print("\n没有符合条件的股票")
            print("No stocks matching the criteria")
            return

        # 使用统一的列筛选逻辑
        # Use unified column filtering logic
        df_export = self._prepare_export_columns(df)
        df_display = df_export.head(max_rows)

        # 打印标题
        # Print title
        print("\n" + "=" * 80)
        print("股票选股结果")
        print("Stock Selection Results")
        print(f"生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Generation Time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"候选股票数量: {len(df)}")
        print(f"Number of Candidates: {len(df)}")
        print("=" * 80)

        # 打印表格
        # Print table
        print(tabulate(df_display, headers='keys', tablefmt='grid', showindex=False))

        print("=" * 80 + "\n")

    def format_signal_details(self, signals: dict) -> str:
        """
        格式化信号详情
        Format signal details

        参数 (Parameters):
            signals: 策略信号字典 (Strategy signal dictionary)

        返回 (Returns):
            str: 格式化的信号详情字符串 (Formatted signal details string)
        """
        if not signals:
            return "无信号 (No signals)"

        details = []
        for strategy, signal in signals.items():
            details.append(f"{strategy}: {signal:.2f}")

        return ", ".join(details)
