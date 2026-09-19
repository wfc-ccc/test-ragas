"""
report 层：报告与 AI 质量评估。

- AllureManager   负责 Allure 结果目录、环境、分类、HTML 报告生成
- GaoShengRagasEvaluator  负责对高升AI回答做 Faithfulness / 相关性等多维度评估
- RagasEvalItem / evaluate_items / assert_thresholds 用于快速集成 ragas
"""

from .allure_manager import AllureManager, ALLURE_RESULTS, ALLURE_HTML
from .ragas_evaluator import GaoShengRagasEvaluator, RagasEvalItem

__all__ = [
    "AllureManager",
    "ALLURE_RESULTS",
    "ALLURE_HTML",
    "GaoShengRagasEvaluator",
    "RagasEvalItem",
]
