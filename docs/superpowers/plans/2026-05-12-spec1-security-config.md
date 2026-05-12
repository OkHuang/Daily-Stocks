# Spec 1: 安全修复与配置统一 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Tushare Token 从 settings.yaml 迁移到 .env 文件，统一所有入口使用 ConfigManager 加载配置，修复 run.py 中不存在的模块引用。

**Architecture:** ConfigManager 作为唯一配置加载入口，支持 python-dotenv 自动加载 .env 文件，优先从环境变量读取敏感信息。run.py 和 collect.py 删除各自的 load_config 函数，统一调用 ConfigManager.load_and_validate()。

**Tech Stack:** python-dotenv, PyYAML

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `.env` | 新建 | 存放 Tushare Token |
| `.gitignore` | 新建 | 排除 .env 等敏感文件 |
| `settings.yaml` | 修改 | token 字段改为 null |
| `requirements.txt` | 修改 | 添加 python-dotenv |
| `src/config/config_manager.py` | 修改 | 增加 dotenv 加载，增强 get_token |
| `run.py` | 修改 | 删除 load_config，统一 ConfigManager，修复日期验证 |
| `src/data/collect.py` | 修改 | 删除 load_config，统一 ConfigManager |

---

### Task 1: 创建 .env 和 .gitignore

**Files:**
- Create: `.env`
- Create: `.gitignore`

- [ ] **Step 1: 创建 .env 文件，存放 Token**

```ini
TUSHARE_TOKEN=3a49fed93eac19b95afa00647181659b803b5679a2cde87c4ea92fe2
```

- [ ] **Step 2: 创建 .gitignore，排除敏感文件和常见忽略项**

```
# 敏感配置
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
*.egg

# 虚拟环境
venv/
.venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 数据和日志
database/
logs/
reports/

# 系统文件
.DS_Store
Thumbs.db
```

- [ ] **Step 3: 修改 settings.yaml，将 token 改为 null**

将行 7:
```yaml
  token: "3a49fed93eac19b95afa00647181659b803b5679a2cde87c4ea92fe2"
```
改为:
```yaml
  token: null  # 从 .env 文件或环境变量 TUSHARE_TOKEN 读取
```

- [ ] **Step 4: 修改 requirements.txt，添加 python-dotenv**

在 `pyyaml>=5.4.0` 之后添加:
```
python-dotenv>=1.0.0
```

- [ ] **Step 5: 安装 python-dotenv**

Run: `pip install python-dotenv>=1.0.0`
Expected: `Successfully installed python-dotenv-x.x.x`

- [ ] **Step 6: 提交**

```bash
git add .env .gitignore settings.yaml requirements.txt
git commit -m "chore: 将 Tushare Token 迁移到 .env 文件，添加 .gitignore"
```

---

### Task 2: 增强 ConfigManager

**Files:**
- Modify: `src/config/config_manager.py`

- [ ] **Step 1: 在 load_config 方法中添加 dotenv 加载**

在 `src/config/config_manager.py` 文件顶部 import 区添加:
```python
from dotenv import load_dotenv
```

在 `load_config` 方法中，`config_path = Path(config_path)` 之后、`if not config_path.exists()` 之前，添加:
```python
        # 加载 .env 文件中的环境变量
        env_path = Path(config_path).parent / ".env"
        load_dotenv(env_path)
```

完整的 `load_config` 方法变为:
```python
    @staticmethod
    def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
        # 确定配置文件路径
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "settings.yaml"

        config_path = Path(config_path)

        # 加载 .env 文件中的环境变量
        env_path = config_path.parent / ".env"
        load_dotenv(env_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML format: {e}")

        # 从环境变量获取敏感配置
        if 'TUSHARE_TOKEN' in os.environ:
            config['data_source']['token'] = os.environ['TUSHARE_TOKEN']

        return config
```

- [ ] **Step 2: 增强 get_token 方法，处理 null 值**

将 `get_token` 方法中从配置文件获取 token 的 try 块修改为:
```python
        try:
            token = config['data_source']['token']
        except (KeyError, TypeError):
            raise ConfigurationError(
                "Tushare Token 未配置。请设置 TUSHARE_TOKEN 环境变量或在 .env 文件中配置",
                'data_source.token'
            )

        if not token or token == 'YOUR_TOKEN_HERE':
            raise ConfigurationError(
                "Tushare Token 未配置。请设置 TUSHARE_TOKEN 环境变量或在 .env 文件中配置",
                'data_source.token'
            )
```

关键变化: `token` 为 `None` 时 `not token` 为 `True`，自然被捕获，无需单独判断。

- [ ] **Step 3: 验证 ConfigManager 能正确加载配置**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "import sys; sys.path.insert(0, 'src'); from config.config_manager import ConfigManager; c = ConfigManager.load_and_validate(); print('Token loaded:', c['data_source']['token'][:8] + '...')"
```
Expected: `Token loaded: 3a49fed93...`

- [ ] **Step 4: 提交**

```bash
git add src/config/config_manager.py
git commit -m "feat: ConfigManager 增加 dotenv 加载和 null token 处理"
```

---

### Task 3: 更新 run.py

**Files:**
- Modify: `run.py`

- [ ] **Step 1: 删除 load_config 函数，替换为 ConfigManager import**

删除 `run.py` 行 25-46 的 `load_config` 函数。

在文件顶部 import 区（行 13-16 之后）添加:
```python
from config.config_manager import ConfigManager
```

注意: `run.py` 行 19 已将 `src` 加入 `sys.path`，所以 `from config.config_manager` 可以正确找到。

- [ ] **Step 2: 修改 main() 中的配置加载逻辑**

将行 126-127:
```python
        config = load_config(args.config)
```
改为:
```python
        config = ConfigManager.load_and_validate(args.config)
```

- [ ] **Step 3: 用 ConfigManager.get_token 替换手动 token 检查**

将行 138-144:
```python
        # 验证 Tushare Token
        token = config['data_source'].get('token', '')
        if token == 'YOUR_TOKEN_HERE' or not token:
            print("错误 (Error): 请在 settings.yaml 中配置有效的 Tushare Token")
            print("Error: Please configure a valid Tushare Token in settings.yaml")
            print("\n获取 Token (Get Token): https://tushare.pro")
            sys.exit(1)
```
改为:
```python
        # 验证 Tushare Token
        try:
            ConfigManager.get_token(config)
        except ConfigurationError as e:
            print(f"错误: {e}")
            print("请在 .env 文件中设置 TUSHARE_TOKEN 或设置环境变量")
            sys.exit(1)
```

并在文件顶部 import 区添加:
```python
from data.exceptions import ConfigurationError
```

- [ ] **Step 4: 修复日期验证（删除不存在的模块引用）**

将行 157-161:
```python
        if args.date:
            from utils.date_utils import validate_date_format
            if not validate_date_format(args.date):
                logger.error(f"日期格式错误 (Invalid date format): {args.date}")
                logger.error("请使用 YYYYMMDD 格式 (Please use YYYYMMDD format)")
                sys.exit(1)
```
改为:
```python
        if args.date:
            try:
                datetime.strptime(args.date, '%Y%m%d')
            except ValueError:
                logger.error(f"日期格式错误: {args.date}，请使用 YYYYMMDD 格式")
                sys.exit(1)
```

`datetime` 已在文件顶部行 16 import，无需额外添加。

- [ ] **Step 5: 验证 run.py 帮助信息正常**

Run:
```bash
cd d:/DeepLearning/stock_picker
python run.py --help
```
Expected: 显示帮助信息，无 import 错误

- [ ] **Step 6: 验证 run.py 的日期验证**

Run:
```bash
python run.py --date invalid
```
Expected: `日期格式错误: invalid，请使用 YYYYMMDD 格式`

Run:
```bash
python run.py --date 20240101
```
Expected: 正常启动（可能在后续步骤因数据库为空而退出，但不应有 import 或配置错误）

- [ ] **Step 7: 提交**

```bash
git add run.py
git commit -m "refactor: run.py 统一使用 ConfigManager，修复日期验证"
```

---

### Task 4: 更新 collect.py

**Files:**
- Modify: `src/data/collect.py`

- [ ] **Step 1: 删除 load_config 函数，替换为 ConfigManager import**

删除 `src/data/collect.py` 行 42-50 的 `load_config` 函数。

在文件顶部 import 区（行 28-29 之后，`from pathlib import Path` 之后可能已有）添加:
```python
from src.config.config_manager import ConfigManager
```

注意: `collect.py` 通过 `sys.path.insert(0, str(project_root))`（行 34）将项目根目录加入 path，所以使用 `from src.config.config_manager` 路径。

- [ ] **Step 2: 修改 main() 中的配置加载**

在 `main()` 函数中，将行 449:
```python
    config = load_config(args.config)
```
改为:
```python
    config = ConfigManager.load_and_validate(args.config)
```

如果 `args.config` 为 `None`，`ConfigManager.load_and_validate()` 会使用默认路径，与原 `load_config` 行为一致。

- [ ] **Step 3: 验证 collect.py 帮助信息正常**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -m src.data.collect --help
```
Expected: 显示帮助信息，无 import 错误

- [ ] **Step 4: 提交**

```bash
git add src/data/collect.py
git commit -m "refactor: collect.py 统一使用 ConfigManager"
```

---

### Task 5: 端到端验证

- [ ] **Step 1: 验证 ConfigManager 完整流程**

Run:
```bash
cd d:/DeepLearning/stock_picker
python -c "
import sys
sys.path.insert(0, 'src')
from config.config_manager import ConfigManager

# 测试加载和验证
config = ConfigManager.load_and_validate()
print('Config loaded OK')

# 测试 token 获取
token = ConfigManager.get_token(config)
print(f'Token OK: {token[:8]}...')

# 测试 null token 场景
test_config = {'data_source': {'token': None}}
try:
    ConfigManager.get_token(test_config)
    print('ERROR: should have raised')
except Exception as e:
    print(f'Null token correctly rejected: {type(e).__name__}')

print('All checks passed')
"
```
Expected:
```
Config loaded OK
Token OK: 3a49fed9...
Null token correctly rejected: ConfigurationError
All checks passed
```

- [ ] **Step 2: 验证 .gitignore 排除 .env**

Run:
```bash
cd d:/DeepLearning/stock_picker
cat .gitignore | grep "\.env"
```
Expected: 显示 `.env`

- [ ] **Step 3: 最终提交（如有遗漏的改动）**

```bash
git status
git add -A
git commit -m "chore: Spec 1 完成 — 安全修复与配置统一"
```
