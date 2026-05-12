# Stock Picker - A 股量化选股系统

基于技术指标的 A 股量化选股系统，从 Tushare Pro 获取数据，通过多种选股策略筛选潜力股票。

## 功能特性

- **多数据源支持**: Tushare Pro API，支持全量/增量数据更新
- **丰富的技术指标**: MA、EMA、RSI、MACD、布林带、KDJ、ATR、BBI 等
- **多种选股策略**: 均线交叉、RSI 超卖、多指标组合、知行趋势等
- **信号聚合引擎**: 多策略信号加权综合判断
- **多进程并行**: ProcessPoolExecutor 多核并行执行策略，全 A 股约 5 秒完成
- **灵活配置**: YAML 配置文件 + .env 敏感信息管理，策略参数可调
- **多种输出格式**: CSV、Excel、Markdown 报告

## 目录结构

```
stock_picker/
├── run.py                     # 主入口
├── settings.yaml               # 全局配置
├── strategies.yaml             # 策略配置
├── .env                        # Tushare Token（不提交 Git）
├── requirements.txt            # Python 依赖
│
├── src/                        # 源代码
│   ├── engine/                 # 核心引擎
│   │   ├── pipeline.py         # 工作流编排
│   │   ├── strategy_runner.py  # 策略批量执行（多进程）
│   │   └── signal_aggregator.py # 信号聚合
│   │
│   ├── data/                   # 数据管理
│   │   ├── fetcher.py          # Tushare API 获取
│   │   ├── local_store.py      # SQLite 存储（WAL 模式）
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
│
├── docs/                       # 详细文档
│   ├── data_collection_guide.md
│   ├── technical_indicators.md
│   └── strategies/
│
├── stock_code/                 # 指数成分股文件
├── database/                   # SQLite 数据库
├── logs/                       # 日志文件
└── reports/                    # 输出报告
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Tushare Token

在项目根目录创建 `.env` 文件：

```
TUSHARE_TOKEN=你的Token
```

Token 在 [Tushare Pro](https://tushare.pro) 注册获取。也可通过环境变量 `TUSHARE_TOKEN` 或在 `settings.yaml` 中直接设置（不推荐）。

### 3. 收集数据

```bash
# 全量收集（首次使用）
python -m src.data.collect --mode full

# 增量更新（日常使用）
python -m src.data.collect --mode incremental

# 收集特定指数成分股
python -m src.data.collect --mode full --source csi300 --start 20130101

# 重试失败股票
python -m src.data.collect --mode incremental --source failed
```

### 4. 运行选股

```bash
# 默认运行（使用 settings.yaml 配置）
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
| `data_source.token` | Tushare Pro Token | 从 .env 读取 |
| `storage.path` | SQLite 数据库路径 | `database/market_data.db` |
| `stock_pool.source` | 股票池来源 | `all_a`（全部 A 股） |
| `output.formats` | 输出格式 | `csv`, `excel` |
| `output.top_n` | 输出前 N 只股票 | 20 |
| `logging.level` | 日志级别 | `INFO` |

### 策略配置 (strategies.yaml)

| 策略 | 说明 | 默认状态 |
|------|------|----------|
| `ma_cross` | 均线交叉策略 | 启用 |
| `rsi_oversold` | RSI 超卖策略 | 启用 |
| `multi_indicator_combo` | 多指标组合策略 | 启用 |
| `zhixing_trend` | 知行趋势策略 | 启用 |
| `macd_cross` | MACD 金叉策略 | 禁用 |
| `bollinger_breakout` | 布林带突破策略 | 禁用 |
| `low_volatility_bullish` | 低波动多头策略 | 禁用 |

## 策略说明

### 均线交叉策略 (ma_cross)
短期均线上穿长期均线时产生买入信号，适合趋势跟踪。

### RSI 超卖策略 (rsi_oversold)
RSI 低于设定阈值（默认 30）时视为超卖，产生买入信号。

### 多指标组合策略 (multi_indicator_combo)
四个条件同时满足时产生信号：
- 波动幅度 <= 100%（60 日）
- BBI 持续上升（默认 3 天）
- KDJ 的 J 值 < -1（超卖）
- MACD 的 DIF > 0（多头市场）

### 知行趋势策略 (zhixing_trend)
综合多重条件判断：
- 知行多空线上升
- 知行短期趋势线上行
- KDJ 的 J 值高于阈值
- 振幅和成交量满足条件

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
| python-dotenv | 环境变量管理 |
| pytest | 单元测试 |

## 详细文档

- [数据收集指南](docs/data_collection_guide.md)
- [技术指标说明](docs/technical_indicators.md)
- [多指标组合策略详解](docs/strategies/multi_indicator_combo.md)

## 免责声明

本系统仅供学习研究参考，不构成任何投资建议。股票投资有风险，入市需谨慎！
