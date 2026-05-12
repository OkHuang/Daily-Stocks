# Spec 4: 代码清理

日期: 2026-05-12
父文档: [2026-05-12-deep-optimization-design.md](2026-05-12-deep-optimization-design.md) 第五部分

## 依赖关系

- **前置依赖**: Spec 3（所有功能性和性能改动必须先完成，避免在即将被大幅修改的代码上做注释清理）
- **后续影响**: 无（本 spec 是整个优化链的最后一环）

## 范围

注释统一为中文、docstring 精简、LLM 模块清理、死代码删除。

## 变更清单

### 4.1 注释风格统一为中文

- **范围**: 所有 `.py` 文件（排除 `test/` 目录）
- **操作**:
  - 删除所有 `# English comment` 格式的英文注释行
  - 删除中英双语注释中的英文部分，如 `# 数据源配置 / Data Source Configuration` → `# 数据源配置`
  - 多行注释中只保留中文段

### 4.2 精简 docstring

- **范围**: 所有 `.py` 文件（排除 `test/` 目录）
- **操作**:
  - 删除从函数签名就能看出的参数类型说明（如 `参数: period: int - RSI 计算周期`）
  - 删除双语 `Parameters` / `Returns` / `Raises` 段落
  - 类级别 docstring 保留简要中文说明（1-2 句）
  - 只保留说明 WHY、非显而易见行为、特殊约束的 docstring
  - 过于冗长的模块级 docstring 精简为 1-2 句

### 4.3 LLM 模块清理

- **文件**: `src/llm_integration/prompt_templates.py`
  - 保留: `__init__`、`_get_analysis_template`、`_get_summary_template`、`_get_risk_alert_template`、`fill_template`（这些是实际模板字符串，不是死代码）
  - 删除: `format_stocks_for_prompt`（行 137-149，pass/TODO）、`generate_analysis_prompt`（行 151-164，pass/TODO）
- **文件**: `src/llm_integration/report_analyzer.py`
  - 保留: `__init__`（行 25-36）
  - 删除: `analyze_results`（行 38-63）、`_call_llm_api`（行 65-79）、`save_analysis_report`（行 81-97）、`batch_analyze`（行 99-116）— 全部是 pass/TODO 或 NotImplementedError

### 4.4 其他清理

- `src/outputs/formatter.py`: 删除 `__init__` 方法（行 23-28），类无需构造函数
- `src/strategies/base.py`: 删除 `StrategyMixin.validate_signal`（行 144-157），与基类 `Strategy.validate_signal` 完全重复
- 各包 `src/engine/__init__.py`、`src/data/__init__.py`、`src/strategies/__init__.py`、`src/utils/__init__.py`、`src/outputs/__init__.py`、`src/llm_integration/__init__.py`、`src/config/__init__.py`: 添加基本导出

## 涉及文件

| 文件 | 操作 |
|------|------|
| 所有 `.py`（排除 `test/`） | 4.1 注释统一, 4.2 docstring 精简 |
| `src/llm_integration/prompt_templates.py` | 4.3 删除死方法 |
| `src/llm_integration/report_analyzer.py` | 4.3 删除死方法 |
| `src/outputs/formatter.py` | 4.4 删除空 __init__ |
| `src/strategies/base.py` | 4.4 删除重复方法 |
| 各 `__init__.py` | 4.4 添加导出 |

## 与其他 Spec 的交叉文件

- 本 spec 修改所有 `.py` 文件，但仅涉及注释和 docstring（不改变任何逻辑），因此不会与 Spec 1-3 的功能变更冲突
- 4.3 和 4.4 的逻辑删除（LLM 死方法、重复方法）是独立的，不影响其他 spec
