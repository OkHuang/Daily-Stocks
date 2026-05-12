# 数据收集系统使用指南
# Data Collection System User Guide

## 目录 (Table of Contents)

1. [系统概述](#系统概述)
2. [前置准备](#前置准备)
3. [快速开始](#快速开始)
4. [详细使用说明](#详细使用说明)
5. [核心模块说明](#核心模块说明)
6. [常见问题](#常见问题)

---

## 系统概述

### 功能介绍

本数据收集系统用于从 Tushare Pro API 获取A股历史行情数据，并存储到本地 SQLite 数据库中。

**核心特性：**
- 全量数据收集：从指定起始日期收集完整历史数据
- 增量数据更新：自动判断最新日期，只收集新增数据
- 指数成分股支持：支持沪深300、上证50、中证500等主流指数
- 失败重试机制：自动跟踪和重试失败的股票
- 数据完整性验证：自动验证数据的完整性和合理性

### 系统架构

```
股票代码获取 (stock_code_fetcher.py)
    │
    ├─ 使用 akshare 获取指数成分股
    └─ 保存到 stock_code/ 目录
            │
            ▼
股票池管理 (stock_pool.py)
    │
    ├─ 从文件读取成分股
    ├─ 从 Tushare API 获取全部A股
    └─ 支持失败股票列表
            │
            ▼
数据获取 (fetcher.py)
    │
    ├─ Tushare API 调用
    ├─ 频率限制控制
    └─ 自动重试机制
            │
            ▼
本地存储 (local_store.py)
    │
    ├─ SQLite 数据库
    ├─ 数据验证
    └─ 增量保存
            │
            ▼
收集控制 (collect.py)
    │
    ├─ 全量收集
    └─ 增量收集
```

---

## 前置准备

### 1. 环境要求

- Python 3.8+
- 依赖包：
  - tushare
  - pandas
  - pyyaml
  - akshare（用于获取指数成分股）

### 2. 安装依赖

```bash
pip install tushare pandas pyyaml akshare
```

### 3. 配置 Tushare Token

1. 访问 [Tushare Pro](https://tushare.pro) 注册账号
2. 获取 API Token
3. 编辑项目根目录下的 `settings.yaml` 文件：

```yaml
data_source:
  provider: "tushare"
  token: "你的Tushare Token"  # 替换为你的Token
```

### 4. 目录结构

确保以下目录存在（系统会自动创建）：

```
stock_picker/
├── database/          # 数据库文件目录
├── stock_code/        # 股票代码文件目录
├── logs/              # 日志文件目录
└── docs/              # 文档目录
```

---

## 快速开始

### 方式一：收集全部A股

```bash
# 全量收集（从2013-01-01开始）
python -m src.data.collect --mode full

# 增量更新（日常使用）
python -m src.data.collect --mode incremental
```

### 方式二：收集指数成分股

```bash
# 步骤1：先生成指数成分股文件
python -m src.data.stock_code_fetcher --index csi300

# 步骤2：收集沪深300成分股数据
python -m src.data.collect --mode full --source csi300 --start 20130101
```

---

## 详细使用说明

### 一、生成股票代码文件

在使用指数成分股功能之前，需要先生成股票代码文件。

#### 支持的指数

| 指数代码 | 指数名称 | 成分股数量 |
|---------|---------|-----------|
| csi300 | 沪深300 | 300 |
| sse50 | 上证50 | 50 |
| csi500 | 中证500 | 500 |
| csi1000 | 中证1000 | 1000 |
| sz50 | 深证50 | 100 |
| cyb50 | 创业板50 | 50 |
| star50 | 科创50 | 50 |

#### 生成命令

```bash
# 生成单个指数成分股文件
python -m src.data.stock_code_fetcher --index csi300

# 生成所有支持的指数成分股文件
python -m src.data.stock_code_fetcher --all

# 列出所有支持的指数
python -m src.data.stock_code_fetcher --list

# 指定输出目录
python -m src.data.stock_code_fetcher --index csi300 --output ./my_stock_codes
```

#### 生成的文件格式

生成的文件保存在 `stock_code/` 目录下，格式如下：

```
# 沪深300 成分股
# 总数: 300 只
# 更新时间: 2026-02-19 10:30:00
#==================================================

002625.SZ
300476.SZ
300251.SZ
...
```

### 二、数据收集命令

#### 基本语法

```bash
python -m src.data.collect --mode <模式> [选项]
```

#### 收集模式

**1. 全量收集 (full)**

从指定起始日期到当前时间收集所有数据。

```bash
# 基本用法（收集全部A股，从2013-01-01开始）
python -m src.data.collect --mode full

# 自定义起始日期
python -m src.data.collect --mode full --start 20200101

# 自定义结束日期
python -m src.data.collect --mode full --start 20200101 --end 20231231

# 收集指定指数成分股
python -m src.data.collect --mode full --source csi300 --start 20130101
python -m src.data.collect --mode full --source sse50 --start 20130101
python -m src.data.collect --mode full --source csi500 --start 20130101

# 收集失败的股票（从指定起始日期重新收集）
python -m src.data.collect --mode full --source failed --start 20130101

# 指定股票列表（会添加到现有股票列表中）
python -m src.data.collect --mode full --stocks 000001.SZ,000002.SZ,600519.SH

# 详细日志输出
python -m src.data.collect --mode full --verbose
```

**2. 增量收集 (incremental)**

自动判断数据库中每只股票的最新数据时间，只收集新增数据。

```bash
# 基本用法（更新数据库中所有股票）
python -m src.data.collect --mode incremental

# 指定指数成分股进行增量更新
python -m src.data.collect --mode incremental --source csi300

# 增量更新失败的股票（从数据库最新日期更新）
python -m src.data.collect --mode incremental --source failed

# 指定股票进行增量更新
python -m src.data.collect --mode incremental --stocks 000001.SZ,600519.SH

# 详细日志输出
python -m src.data.collect --mode incremental --verbose
```

#### 参数说明

| 参数 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| `--mode` | 收集模式：`full` 或 `incremental` | 是 | - |
| `--source` | 股票池来源：`csi300`/`sse50`/`csi500`/`csi1000`/`sz50`/`cyb50`/`star50`/`failed` | 否 | 全部A股 |
| `--start` | 起始日期（格式 YYYYMMDD），仅用于全量模式 | 否 | 20130101 |
| `--end` | 结束日期（格式 YYYYMMDD） | 否 | 最近交易日 |
| `--stocks` | 股票代码列表（逗号分隔） | 否 | 无 |
| `--config` | 配置文件路径 | 否 | settings.yaml |
| `--verbose` | 详细日志输出 | 否 | False |

**注意：**
- `--source` 为空时，默认收集全部A股
- `--source` 设置为 `failed` 时，从 `stock_code/failed_stocks.txt` 读取失败股票
  - 全量模式：从指定起始日期重新收集完整数据
  - 增量模式：从数据库最新日期开始收集增量数据
- `--stocks` 参数会添加到现有股票列表中，不会替换

---

## 核心模块说明

### 1. stock_code_fetcher.py - 股票代码获取器

**功能：** 使用 akshare 获取各类指数成分股代码并保存到文件。

**为什么需要这个工具？**
- Tushare Pro 的指数成分股接口需要付费权限
- akshare 提供免费的指数成分股数据
- 预先生成股票代码文件，避免每次都请求 API

**使用示例：**

```bash
# 获取沪深300成分股
python -m src.data.stock_code_fetcher --index csi300

# 获取所有支持的指数
python -m src.data.stock_code_fetcher --all

# 列出支持的指数
python -m src.data.stock_code_fetcher --list
```

### 2. stock_pool.py - 股票池管理

**功能：** 获取和管理待收集的股票列表。

**支持的股票来源：**
- `all_a`：全部A股（通过 Tushare API 获取）
- `csi300`、`sse50`、`csi500` 等：从 `stock_code/` 文件夹读取
- `failed`：从 `stock_code/failed_stocks.txt` 读取失败股票

### 3. fetcher.py - 数据获取器

**功能：** 从 Tushare Pro API 获取股票数据。

**核心特性：**
- 频率限制控制（默认0.3秒间隔）
- 自动重试机制（最多3次）
- 失败自动等待（频率限制错误时）

### 4. local_store.py - 本地存储管理

**功能：** 管理 SQLite 数据库，提供数据存储和查询接口。

**数据库结构：**

**表1：stock_daily（股票日线数据）**
```sql
CREATE TABLE stock_daily (
    ts_code TEXT NOT NULL,        -- 股票代码
    trade_date TEXT NOT NULL,     -- 交易日期
    open REAL,                    -- 开盘价
    high REAL,                     -- 最高价
    low REAL,                      -- 最低价
    close REAL,                    -- 收盘价
    vol REAL,                      -- 成交量
    amount REAL,                   -- 成交额
    PRIMARY KEY (ts_code, trade_date)  -- 联合主键（自动去重）
);
```

**表2：stock_list（股票基本信息）**
```sql
CREATE TABLE stock_list (
    ts_code TEXT PRIMARY KEY,     -- 股票代码
    name TEXT,                    -- 股票名称
    industry TEXT,                -- 所属行业
    list_date TEXT,               -- 上市日期
    update_time TEXT              -- 更新时间
);
```

### 5. collect.py - 数据收集控制

**功能：** 提供命令行接口，执行全量和增量数据收集。

**核心函数：**

**collect_full() - 全量收集**
```python
stats = collect_full(
    token=token,
    db_path=db_path,
    start_date="20130101",  # 默认起始日期
    end_date=None,           # 默认最近交易日
    stock_list=None,         # None表示全部A股
    logger=logger,
    update_failed_file=True  # 自动更新失败股票文件
)
```

**collect_incremental() - 增量收集**
```python
stats = collect_incremental(
    token=token,
    db_path=db_path,
    stock_list=None,         # None表示数据库中所有股票
    logger=logger,
    update_failed_file=True  # 自动更新失败股票文件
)
```

**增量收集的工作原理：**
1. 从数据库中获取所有股票列表
2. 查询每只股票的最新数据日期
3. 如果最新日期早于当前日期，则获取增量数据
4. 如果股票在数据库中没有数据，则跳过该股票
5. 收集完成后更新 `failed_stocks.txt`（如果有失败的股票）

**失败股票重试机制：**
- 失败的股票会被记录到 `stock_code/failed_stocks.txt`
- 失败股票在数据库中可能有旧数据，只是没有被成功更新到最新
- 可以使用 `--source failed` 重新收集这些股票
  - 全量模式：从指定起始日期重新收集
  - 增量模式：从数据库最新日期开始增量更新
- 如果全部成功，`failed_stocks.txt` 会被自动删除

---

## 常见问题

### Q1: 全量收集和增量收集有什么区别？

| 特性 | 全量收集 | 增量收集 |
|------|----------|----------|
| **时间范围** | 指定起始日期到当前 | 数据库最新日期到当前 |
| **数据量** | 大（每只股票约800-3000条记录） | 小（通常1-5条记录） |
| **运行时间** | 长（数小时） | 短（数分钟） |
| **使用场景** | 首次使用、扩展历史 | 日常更新 |

### Q2: 如何选择收集模式？

```
空数据库（首次使用）
  → 使用全量收集: --mode full

有数据但需要扩展历史
  → 使用全量收集: --mode full --start 20200101

有数据且需要保持最新
  → 使用增量收集: --mode incremental

收集失败的股票
  → 全量模式: --mode full --source failed --start 20130101
  → 增量模式: --mode incremental --source failed

只想更新部分股票
  → 使用增量收集 + --stocks 参数
```

### Q3: 失败股票是什么意思？如何处理？

**失败股票的含义：**
- 这些股票在之前的收集中失败了（API 限制、网络错误等）
- 它们在数据库中**可能有旧数据**，只是没有被更新到最新日期
- 失败股票会被记录到 `stock_code/failed_stocks.txt`

**处理方式：**

```bash
# 方式1：全量重新收集（从指定起始日期）
python -m src.data.collect --mode full --source failed --start 20130101

# 方式2：增量更新（从数据库最新日期）
python -m src.data.collect --mode incremental --source failed
```

**建议：**
- 如果失败股票在数据库中数据较旧，使用全量模式
- 如果失败股票在数据库中数据较新，使用增量模式
- 收集成功后，`failed_stocks.txt` 会被自动删除或更新

### Q4: 程序中断了怎么办？

重新运行相同的命令即可。系统采用增量保存机制，每只股票处理完后立即保存到数据库，已保存的数据不会丢失。

### Q5: 如何只收集特定的股票？

使用 `--stocks` 参数：

```bash
python -m src.data.collect --mode full --stocks 000001.SZ,000002.SZ,600519.SH
```

注意：`--stocks` 参数会**添加**到现有股票列表中，而不是替换。

### Q6: 如何处理API频率限制？

系统已自动处理：
- 请求间隔控制（0.3秒）
- 自动重试机制（最多3次）
- 频率限制错误时自动等待更长时间

如果仍遇到限制，可以：
1. 升级 Tushare 账户等级
2. 修改 `settings.yaml` 中的 `request_delay` 参数
3. 避开高峰时段（开盘、收盘时间）

### Q7: 数据库文件在哪里？

默认位置：`database/market_data.db`

可以在 `settings.yaml` 中修改：

```yaml
storage:
  path: "database/market_data.db"  # 修改这里
```

### Q8: 如何查看数据库中的数据？

**方式1：使用SQLite命令行**

```bash
sqlite3 database/market_data.db

# 查看表结构
.schema

# 查看某只股票的数据
SELECT * FROM stock_daily
WHERE ts_code='000001.SZ'
ORDER BY trade_date DESC
LIMIT 10;

# 退出
.quit
```

**方式2：使用Python**

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('database/market_data.db')
df = pd.read_sql_query("""
    SELECT ts_code, trade_date, close, vol
    FROM stock_daily
    WHERE ts_code = '000001.SZ'
    ORDER BY trade_date DESC
    LIMIT 10
""", conn)
print(df)
conn.close()
```

### Q9: 如何更新股票代码文件？

指数成分股会定期调整，建议定期更新：

```bash
# 更新单个指数
python -m src.data.stock_code_fetcher --index csi300

# 更新所有指数
python -m src.data.stock_code_fetcher --all
```

### Q10: 如何备份数据库？

```bash
# 直接复制
cp database/market_data.db database/backup/market_data_$(date +%Y%m%d).db

# 或使用SQLite备份命令
sqlite3 database/market_data.db ".backup database/backup/market_data_$(date +%Y%m%d).db"
```

### Q11: 增量收集会更新 failed_stocks.txt 吗？

会。增量收集过程中如果发生失败，也会更新 `failed_stocks.txt` 文件。

**两种情况：**
1. 股票在数据库中有数据，但增量获取失败 → 会被记录到 `failed_stocks.txt`
2. 股票在数据库中没有数据 → 会被跳过（增量收集不处理没有数据的股票）

**建议：**
- 如果数据库中可能没有某些股票的数据，使用全量模式配合 `--source failed`
- 如果数据库中所有股票都有数据，可以使用增量模式配合 `--source failed`

---

## 推荐使用流程

### 首次使用

```bash
# 1. 生成指数成分股文件（可选）
python -m src.data.stock_code_fetcher --index csi300

# 2. 全量收集沪深300成分股
python -m src.data.collect --mode full --source csi300 --start 20130101
```

### 日常更新

```bash
# 每天收盘后运行增量更新
python -m src.data.collect --mode incremental --source csi300
```

### 失败重试

```bash
# 如果有失败的股票，根据情况选择模式

# 情况1：失败股票数据较旧，全量重新收集
python -m src.data.collect --mode full --source failed --start 20130101

# 情况2：失败股票数据较新，增量更新
python -m src.data.collect --mode incremental --source failed
```

### 定期维护

```bash
# 每周更新一次指数成分股文件
python -m src.data.stock_code_fetcher --all

# 每月全量更新一次数据（确保数据完整）
python -m src.data.collect --mode full --source csi300 --start 20130101
```

---

## 命令速查表

| 场景 | 命令 |
|------|------|
| 收集全部A股 | `python -m src.data.collect --mode full` |
| 收集沪深300 | `python -m src.data.collect --mode full --source csi300 --start 20130101` |
| 增量更新全部 | `python -m src.data.collect --mode incremental` |
| 增量更新沪深300 | `python -m src.data.collect --mode incremental --source csi300` |
| 全量收集失败股票 | `python -m src.data.collect --mode full --source failed --start 20130101` |
| 增量更新失败股票 | `python -m src.data.collect --mode incremental --source failed` |
| 指定股票更新 | `python -m src.data.collect --mode incremental --stocks 000001.SZ,600519.SH` |
| 生成成分股文件 | `python -m src.data.stock_code_fetcher --index csi300` |
| 生成所有成分股文件 | `python -m src.data.stock_code_fetcher --all` |

---

**文档版本：** v2.0
**最后更新：** 2026-02-19
**维护者：** Stock Picker System Team
