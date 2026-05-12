# Stock Picker - A 股量化选股系统

基于技术指标的 A 股量化选股系统，从 Tushare Pro 获取数据，通过多种选股策略筛选潜力股票。

## 功能特性

- **多数据源支持**: Tushare Pro API，支持全量/增量数据更新
- **丰富的技术指标**: MA、EMA、RSI、MACD、布林带、KDJ、ATR、BBI 等
- **多种选股策略**: 均线交叉、RSI 超卖、多指标组合、知行趋势等
- **信号聚合引擎**: 多策略信号加权综合判断
- **灵活配置**: YAML 配置文件，策略参数可调
- **多种输出格式**: CSV、Excel、Markdown 报告

## 目录结构

```
stock_picker/
├── run.py                     # 主入口
├── settings.yaml               # 全局配置
├── strategies.yaml             # 策略配置
├── requirements.txt             # Python 依赖
│
├── src/                        # 源代码
│   ├── engine/                 # 核心引擎
│   │   ├── pipeline.py         # 工作流编排
│   │   ├── strategy_runner.py   # 策略批量执行
│   │   └── signal_aggregator.py # 信号聚合
│   │
│   ├── data/                   # 数据管理
│   │   ├── fetcher.py          # Tushare API 获取
│   │   ├── local_store.py      # SQLite 存储
│   │   ├── stock_pool.py       # 股票池管理
│   │   ├── collect.py          # 数据收集脚本
│   │   └── stock_code_fetcher.py # 指数成分股获取
│   │
│   ├── strategies/             # 选股策略
│   │   ├── base.py             # 策略基类
│   │   ├── ma_cross.py         # 均线交叉策略
│   │   ├── rsi_oversold.py     # RSI 超卖策略
│   │   ├── multi_indicator_combo.py # 多指标组合策略
│   │   └── zhixing_trend_strategy.py # 知行趋势策略
│   │
│   ├── utils/                  # 工具模块
│   │   ├── indicators.py       # 技术指标计算
│   │   └── logger.py           # 日志模块
│   │
│   ├── outputs/                # 输出格式化
│   │   └── formatter.py        # CSV/Excel/Markdown 输出
│   │
│   └── llm_integration/        # LLM 集成（预留）
│
├── test/                       # 单元测试
│   ├── test_strategies.py
│   └── test_data.py
│
├── docs/                       # 详细文档
│   ├── data_collection_guide.md  # 数据收集指南
│   ├── technical_indicators.md    # 技术指标说明
│   └── strategies/               # 策略说明文档
│
├── stock_code/                 # 指数成分股文件
│   ├── csi300.txt              # 沪深 300
│   ├── csi500.txt              # 中证 500
│   └── ...
│
├── database/                    # SQLite 数据库
├── logs/                        # 日志文件
└── reports/                     # 输出报告
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Tushare Token

在 `settings.yaml` 中填入你的 Tushare Pro Token：

```yaml
data_source:
  token: "你的Tushare Token"  # 在 https://tushare.pro 注册获取
```

### 3. 收集数据

```bash
# 全量收集（首次使用，从2013年开始）
python -m src.data.collect --mode full

# 增量更新（日常使用）
python -m src.data.collect --mode incremental

# 收集特定指数成分股
python -m src.data.collect --mode full --source csi300 --start 20130101

### 收集失败的股票

数据收集过程中可能因 API 频率限制等原因导致部分股票获取失败。失败股票会记录在 `stock_code/failed_stocks.txt` 文件中，后续可使用以下命令重试：

```bash
# 增量更新失败股票的数据库记录
python -m src.data.collect --mode incremental --source failed

# 全量重新收集失败股票（从2013年开始）
python -m src.data.collect --mode full --source failed --start 20130101
```

收集完成后，如果全部成功，该文件会自动删除；如仍有失败股票，文件会更新并保留失败列表。
```

### 4. 运行选股

```bash
# 默认运行（使用 settings.yaml 中的配置）
python run.py

# 指定日期和数量
python run.py --date 20240217 --top-n 20

# 指定启用哪些策略
python run.py --strategies ma_cross,rsi_oversold --top-n 30

# 显示详细日志
python run.py --verbose
```

## 配置说明

### 全局配置 (settings.yaml)

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `data_source.token` | Tushare Pro Token | 必填 |
| `storage.path` | SQLite 数据库路径 | `database/market_data.db` |
| `stock_pool.source` | 股票池来源 | `all_a` (全部A股) |
| `output.formats` | 输出格式 | `csv`, `excel` |
| `output.top_n` | 输出前N只股票 | 20 |

### 策略配置 (strategies.yaml)

支持的策略及默认参数：

| 策略 | 说明 | 默认状态 |
|------|------|----------|
| `ma_cross` | 均线交叉策略 | 启用 |
| `rsi_oversold` | RSI 超卖策略 | 启用 |
| `multi_indicator_combo` | 多指标组合策略 | 启用 |
| `zhixing_trend` | 知行趋势策略 | 启用 |
| `macd_cross` | MACD 金叉策略 | 禁用 |
| `bollinger_breakout` | 布林带突破策略 | 禁用 |

## 策略说明

### 均线交叉策略 (ma_cross)
短期均线上穿长期均线时产生买入信号，适合趋势跟踪。

### RSI 超卖策略 (rsi_oversold)
RSI 低于设定阈值（默认30）时视为超卖，产生买入信号。

### 多指标组合策略 (multi_indicator_combo)
四个条件同时满足时产生信号：
- 波动幅度 ≤ 100%（60日）
- BBI 持续上升（默认3天）
- KDJ 的 J 值 < -1（超卖）
- MACD 的 DIF > 0（多头市场）

### 知行趋势策略 (zhixing_trend)
综合多重条件判断：
- 知行多空线上升
- 知行短期趋势线上行
- KDJ 的 J 值高于阈值
- 振幅和成交量满足条件

## 输出示例

运行后在 `reports/` 目录生成报告文件：

```
reports/
├── 20240217_result.csv
├── 20240217_result.xlsx
└── 20240217_result.md
```

报告包含股票代码、名称、各策略信号、综合评分等信息。

## 依赖说明

| 依赖包 | 用途 |
|--------|------|
| pandas, numpy | 数据处理 |
| tushare | 行情数据 API |
| akshare | 指数成分股数据 |
| sqlalchemy | 数据库 |
| pyyaml | 配置文件 |
| openpyxl | Excel 输出 |
| tabulate | 终端表格显示 |
| pytest | 单元测试 |

## 详细文档

- [数据收集指南](docs/data_collection_guide.md)
- [技术指标说明](docs/technical_indicators.md)
- [多指标组合策略详解](docs/strategies/multi_indicator_combo.md)

## 免责声明

本系统仅供学习研究参考，不构成任何投资建议。股票投资有风险，入市需谨慎！