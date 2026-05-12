# Spec 4: 代码清理 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将所有注释统一为中文，精简冗余 docstring，清理 LLM 模块死代码，删除重复方法和空构造函数，为各包添加基本导出。

**Architecture:** 本 plan 是整个优化链的最后一环。不涉及任何逻辑变更，只做注释/docstring 清理和死代码删除。

**Tech Stack:** 无新依赖

**前置依赖:** Plan 1（Spec 1）、Plan 2（Spec 2）、Plan 3（Spec 3）全部完成

---

## 文件结构

| 文件 | 操作 |
|------|------|
| 所有 `src/**/*.py` + `run.py` | 注释统一 + docstring 精简 |
| `src/llm_integration/prompt_templates.py` | 删除死方法 |
| `src/llm_integration/report_analyzer.py` | 删除死方法 |
| `src/outputs/formatter.py` | 删除空 __init__ |
| `src/strategies/base.py` | 删除重复方法 |
| 各 `__init__.py` | 添加导出 |

---

### Task 1: LLM 模块清理 — prompt_templates.py

**Files:**
- Modify: `src/llm_integration/prompt_templates.py`

- [ ] **Step 1: 删除 format_stocks_for_prompt 方法**

删除 `format_stocks_for_prompt` 方法（整个方法体是 `pass` + TODO）。

- [ ] **Step 2: 删除 generate_analysis_prompt 方法**

删除 `generate_analysis_prompt` 方法（整个方法体是 `pass` + TODO）。

- [ ] **Step 3: 提交**

```bash
git add src/llm_integration/prompt_templates.py
git commit -m "chore: 删除 PromptTemplates 中的空壳方法"
```

---

### Task 2: LLM 模块清理 — report_analyzer.py

**Files:**
- Modify: `src/llm_integration/report_analyzer.py`

- [ ] **Step 1: 删除所有空壳方法**

删除以下方法（全部是 pass/TODO 或 NotImplementedError）:
- `analyze_results`
- `_call_llm_api`
- `save_analysis_report`
- `batch_analyze`

只保留 `__init__` 方法。

- [ ] **Step 2: 提交**

```bash
git add src/llm_integration/report_analyzer.py
git commit -m "chore: 删除 ReportAnalyzer 中的空壳方法"
```

---

### Task 3: 删除死代码

**Files:**
- Modify: `src/outputs/formatter.py`
- Modify: `src/strategies/base.py`

- [ ] **Step 1: 删除 Formatter 的空 __init__**

在 `src/outputs/formatter.py` 中，删除整个 `__init__` 方法:
```python
    def __init__(self):
        """ """
        pass
```

- [ ] **Step 2: 删除 StrategyMixin 重复的 validate_signal**

在 `src/strategies/base.py` 中，删除 `StrategyMixin` 类中的 `validate_signal` 方法（行 144-157），因为基类 `Strategy` 已有完全相同的实现。

- [ ] **Step 3: 提交**

```bash
git add src/outputs/formatter.py src/strategies/base.py
git commit -m "chore: 删除 Formatter 空 __init__ 和 StrategyMixin 重复方法"
```

---

### Task 4: 各包 __init__.py 添加导出

**Files:**
- Modify: `src/engine/__init__.py`
- Modify: `src/data/__init__.py`
- Modify: `src/strategies/__init__.py`
- Modify: `src/utils/__init__.py`
- Modify: `src/outputs/__init__.py`
- Modify: `src/llm_integration/__init__.py`
- Modify: `src/config/__init__.py`

- [ ] **Step 1: 为每个 __init__.py 添加基本导出**

`src/engine/__init__.py`:
```python
from .pipeline import Pipeline
from .strategy_runner import StrategyRunner
from .signal_aggregator import SignalAggregator
```

`src/data/__init__.py`:
```python
from .fetcher import BaseFetcher, TushareFetcher
from .local_store import LocalStore
from .stock_pool import StockPool
```

`src/strategies/__init__.py`:
```python
from .base import Strategy, StrategyMixin
from .ma_cross import MACrossStrategy
from .rsi_oversold import RSIOversoldStrategy
from .multi_indicator_combo import MultiIndicatorComboStrategy, LowVolatilityBullishStrategy
from .zhixing_trend_strategy import ZhixingTrendStrategy
```

`src/utils/__init__.py`:
```python
from .logger import setup_logger, get_logger
```

`src/outputs/__init__.py`:
```python
from .formatter import Formatter
```

`src/llm_integration/__init__.py`:
```python
from .report_analyzer import ReportAnalyzer
from .prompt_templates import PromptTemplates
```

`src/config/__init__.py`:
```python
from .config_manager import ConfigManager
```

- [ ] **Step 2: 验证导出正常**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
from engine import Pipeline, StrategyRunner, SignalAggregator
from data import BaseFetcher, TushareFetcher, LocalStore, StockPool
from strategies import Strategy, MACrossStrategy, RSIOversoldStrategy, MultiIndicatorComboStrategy, ZhixingTrendStrategy
from utils import setup_logger, get_logger
from outputs import Formatter
from config import ConfigManager
print('所有包导出正常')
"
```
Expected: `所有包导出正常`

- [ ] **Step 3: 提交**

```bash
git add src/engine/__init__.py src/data/__init__.py src/strategies/__init__.py src/utils/__init__.py src/outputs/__init__.py src/llm_integration/__init__.py src/config/__init__.py
git commit -m "chore: 各包 __init__.py 添加基本导出"
```

---

### Task 5: 注释统一为中文 + 精简 docstring（逐文件处理）

**Files:**
- Modify: 所有 `src/**/*.py` + `run.py`（排除 `test/` 目录）

这是一个机械性操作，对每个文件执行以下规则:
1. 删除所有纯英文注释行（如 `# Get stock pool`）
2. 中英双语注释只保留中文部分（如 `# 获取股票池 / Get stock pool` → `# 获取股票池`）
3. 多行双语 docstring 只保留中文段落，删除 `Parameters`、`Returns`、`Raises` 等英文段落及其中文翻译
4. 模块级 docstring 精简为 1-2 句中文
5. 类级别 docstring 保留 1-2 句中文
6. 方法 docstring 只保留说明 WHY 或非显而易见行为的，删除从签名能看出的参数说明

由于文件较多，按模块分组处理，每组一次提交。

- [ ] **Step 1: 清理 run.py 注释和 docstring**

处理 `run.py`，按上述规则清理。

- [ ] **Step 2: 清理 src/config/ 模块**

处理:
- `src/config/__init__.py`
- `src/config/config_manager.py`

- [ ] **Step 3: 清理 src/data/ 模块**

处理:
- `src/data/__init__.py`
- `src/data/fetcher.py`
- `src/data/local_store.py`
- `src/data/stock_pool.py`
- `src/data/collect.py`
- `src/data/stock_code_fetcher.py`
- `src/data/exceptions.py`

- [ ] **Step 4: 清理 src/engine/ 模块**

处理:
- `src/engine/__init__.py`
- `src/engine/pipeline.py`
- `src/engine/strategy_runner.py`
- `src/engine/signal_aggregator.py`

- [ ] **Step 5: 清理 src/strategies/ 模块**

处理:
- `src/strategies/__init__.py`
- `src/strategies/base.py`
- `src/strategies/ma_cross.py`
- `src/strategies/rsi_oversold.py`
- `src/strategies/multi_indicator_combo.py`
- `src/strategies/zhixing_trend_strategy.py`

- [ ] **Step 6: 清理 src/utils/ 模块**

处理:
- `src/utils/__init__.py`
- `src/utils/indicators.py`
- `src/utils/logger.py`

- [ ] **Step 7: 清理 src/outputs/ 模块**

处理:
- `src/outputs/__init__.py`
- `src/outputs/formatter.py`

- [ ] **Step 8: 清理 src/llm_integration/ 模块**

处理:
- `src/llm_integration/__init__.py`
- `src/llm_integration/report_analyzer.py`
- `src/llm_integration/prompt_templates.py`

- [ ] **Step 9: 提交（每步或合并提交）**

```bash
git add -A
git commit -m "chore: 注释统一为中文，精简冗余 docstring"
```

---

### Task 6: 最终验证

- [ ] **Step 1: 验证所有模块可正常 import**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys; sys.path.insert(0, 'src')
from config import ConfigManager
from engine import Pipeline, StrategyRunner, SignalAggregator
from data import TushareFetcher, LocalStore, StockPool
from strategies import MACrossStrategy, RSIOversoldStrategy, MultiIndicatorComboStrategy, ZhixingTrendStrategy
from utils import setup_logger
from outputs import Formatter
from llm_integration import ReportAnalyzer, PromptTemplates
print('所有模块 import 正常')
"
```
Expected: `所有模块 import 正常`

- [ ] **Step 2: 验证主入口正常**

Run:
```bash
cd d:/DeepLearning/stock_picker
python run.py --help
```
Expected: 显示帮助信息，无错误

- [ ] **Step 3: 最终提交**

```bash
git status
git add -A
git commit -m "chore: Spec 4 完成 — 代码清理"
```
