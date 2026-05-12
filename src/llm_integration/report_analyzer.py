"""LLM 报告分析模块（预留扩展，暂未实现）"""

from typing import Dict, Any, Optional
import pandas as pd
from .prompt_templates import PromptTemplates


class ReportAnalyzer:
    """LLM 报告分析器（预留扩展）"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.prompt_templates = PromptTemplates()
