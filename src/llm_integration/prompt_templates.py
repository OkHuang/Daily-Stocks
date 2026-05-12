"""LLM 提示词模板模块（预留扩展，暂未实现）"""

from typing import Dict, Any
import pandas as pd


class PromptTemplates:
    """提示词模板管理类"""

    def __init__(self):
        self.templates = {
            'analysis': self._get_analysis_template(),
            'summary': self._get_summary_template(),
            'risk_alert': self._get_risk_alert_template()
        }

    def _get_analysis_template(self) -> str:
        """获取选股分析提示词模板"""
        template = """
# 股票选股结果分析

你是一位专业的证券分析师，请对以下选股结果进行分析。

## 选股结果概览
日期: {date}
候选股票数量: {stock_count}
使用的策略: {strategies}

## 候选股票列表
{stocks}

## 分析要求
1. 分析整体选股特征（行业分布、市值分布等）
2. 指出值得关注的前3-5只股票
3. 提示潜在风险
4. 给出投资建议

请以专业、客观的语调进行分析。
"""
        return template

    def _get_summary_template(self) -> str:
        """获取选股摘要提示词模板"""
        template = """
# 选股摘要

请为以下选股结果生成一份简明摘要（不超过200字）。

## 选股结果
{summary_info}

## 要求
- 突出重点
- 语言简洁
- 适合快速阅读
"""
        return template

    def _get_risk_alert_template(self) -> str:
        """获取风险提示提示词模板"""
        template = """
# 投资风险提示

请分析以下选股结果，并提示可能的投资风险。

## 候选股票
{stocks}

## 风险分析维度
1. 行业集中度风险
2. 市场整体风险
3. 个股特有风险
4. 技术面风险

请提供具体、可操作的风险提示。
"""
        return template

    def fill_template(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """填充提示词模板"""
        template = self.templates.get(template_name)
        if template is None:
            raise ValueError(f"Template not found: {template_name}")

        return template.format(**kwargs)
