# Spec 1: 安全修复与配置统一

日期: 2026-05-12
父文档: [2026-05-12-deep-optimization-design.md](2026-05-12-deep-optimization-design.md) 第一部分 + 第三部分 3.1

## 依赖关系

- **前置依赖**: 无（本 spec 是整个优化链的起点）
- **后续影响**: Spec 2/3/4 中的配置加载和 token 验证都依赖本 spec 的 ConfigManager 统一

## 范围

Token 安全迁移 + 统一配置加载 + 日期验证修复。这是所有后续工作的基础。

## 变更清单

### 1.1 Token 安全迁移

- 创建 `.env` 文件：`TUSHARE_TOKEN=3a49fed93eac19b95afa00647181659b803b5679a2cde87c4ea92fe2`
- 创建或修改 `.gitignore`，确保包含 `.env`
- `settings.yaml` 中 token 字段改为 `null`
- `requirements.txt` 添加 `python-dotenv`

### 1.2 ConfigManager 增强

- `src/config/config_manager.py` 的 `load_config` 方法开头加入 `dotenv` 自动加载：
  ```python
  from dotenv import load_dotenv
  load_dotenv(Path(config_path).parent / ".env")
  ```
- 确保 `get_token()` 正确处理 yaml 中 token 为 `null` 的情况（当前已处理空字符串和 `YOUR_TOKEN_HERE`，需增加 `None` 判断）

### 1.3 统一配置加载

- `run.py`: 删除 `load_config` 函数（行 25-46），改用 `ConfigManager.load_and_validate()`；token 检查（行 139-143）替换为 `ConfigManager.get_token(config)`；import 路径统一
- `src/data/collect.py`: 删除 `load_config` 函数（行 42-50），改用 `ConfigManager.load_and_validate()`
- **注意 import 路径**: `run.py` 通过 `sys.path.insert(0, 'src')` 使用 `from engine.xxx` 风格；`collect.py` 通过 `sys.path.insert(0, project_root)` 使用 `from src.data.xxx` 风格。ConfigManager 内部使用 `from data.exceptions` 风格。三种路径风格需要统一：
  - `run.py` 已添加 `src` 到 path，可使用 `from config.config_manager import ConfigManager`
  - `collect.py` 添加 `src` 到 path 后，可使用 `from src.config.config_manager import ConfigManager`
  - ConfigManager 内部的 `from data.exceptions` 保持不变（因为它在 `src/config/` 下，且 `run.py` 已将 `src` 加入 path）

### 1.4 run.py 日期验证修复

- 删除行 158 的 `from utils.date_utils import validate_date_format`（模块不存在）
- 改为：
  ```python
  try:
      datetime.strptime(args.date, '%Y%m%d')
  except ValueError:
      logger.error(f"日期格式错误: {args.date}，请使用 YYYYMMDD 格式")
      sys.exit(1)
  ```

## 涉及文件

| 文件 | 操作 |
|------|------|
| `.env` | 新建 |
| `.gitignore` | 新建或修改 |
| `settings.yaml` | token 改 null |
| `requirements.txt` | 添加 python-dotenv |
| `src/config/config_manager.py` | 增加 dotenv 加载，增强 get_token |
| `run.py` | 删除 load_config，统一 ConfigManager，修复日期验证 |
| `src/data/collect.py` | 删除 load_config，统一 ConfigManager |

## 与其他 Spec 的交叉文件

- `run.py`: 仅本 spec 修改
- `src/data/collect.py`: 仅本 spec 修改
- `src/config/config_manager.py`: 仅本 spec 修改
