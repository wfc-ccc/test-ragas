"""
Ragas AI 回答质量评估器。

基于项目现有的 RAG 系统与评估 LLM，针对高升AI接口返回的回答
进行 Faithfulness / Answer Relevancy / Context Recall 等多维度评估，
并将结果汇总成表格，用于报告层展示与断言。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import allure
import pandas as pd
from ragas import evaluate, EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRelevance, LLMContextRecall

from ..base import config, assertions, get_logger
from .allure_manager import AllureManager

log = get_logger(__name__)


@dataclass
class RagasEvalItem:
    """单个 ragas 评估条目。"""

    question: str
    response: str
    retrieved_contexts: list[str] = field(default_factory=list)
    reference: str = ""
    type: str = "general"


class GaoShengRagasEvaluator:
    """高升AI回答质量评估器。"""

    METRIC_MAP = {
        "faithfulness": Faithfulness,
        "answer_relevancy": AnswerRelevancy,
        "context_relevance": ContextRelevance,
        "context_recall": LLMContextRecall,
    }

    def __init__(
        self,
        evaluator_llm: Any = None,
        evaluator_embeddings: Any = None,
        metric_names: Optional[list[str]] = None,
    ):
        self._llm = evaluator_llm
        self._embeddings = evaluator_embeddings
        self._metric_names = metric_names or config.get("ragas.metrics") or [
            "faithfulness",
            "answer_relevancy",
            "context_recall",
        ]
        self._metrics: list = self._build_metrics()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    def _default_llm(self) -> Any:
        try:
            from src.llm import create_deepseek_llm
            from ragas.llms import LangchainLLMWrapper
            return LangchainLLMWrapper(create_deepseek_llm(temperature=0.0), bypass_n=True)
        except Exception as e:
            log.warning("加载默认 evaluator LLM 失败（请配置 DEEPSEEK_API_KEY）: %s", e)
            return None

    def _default_embeddings(self) -> Any:
        try:
            from src.embeddings import create_remote_embeddings
            from ragas.embeddings.base import LangchainEmbeddingsWrapper
            return LangchainEmbeddingsWrapper(create_remote_embeddings())
        except Exception as e:
            log.warning("加载默认 evaluator embeddings 失败: %s", e)
            return None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = self._default_llm()
        return self._llm

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = self._default_embeddings()
        return self._embeddings

    def _build_metrics(self) -> list:
        metrics = []
        for name in self._metric_names:
            cls = self.METRIC_MAP.get(name)
            if cls is None:
                log.warning("未知 ragas 指标: %s，跳过", name)
                continue
            kwargs: dict[str, Any] = {}
            if name != "faithfulness" and cls not in (Faithfulness,):
                # 需要 embeddings 的指标
                if self.embeddings is not None and name == "answer_relevancy":
                    kwargs["embeddings"] = self.embeddings
            if self.llm is not None:
                kwargs["llm"] = self.llm
            metrics.append(cls(**kwargs))
        return metrics

    # ------------------------------------------------------------------
    # 评估核心
    # ------------------------------------------------------------------

    def evaluate_items(
        self,
        items: list[RagasEvalItem],
        scenario_name: str = "高升AI问答质量评估",
        attach_to_allure: bool = True,
    ) -> pd.DataFrame:
        """批量评估多条回答。

        Returns:
            ragas evaluate 结果转换的 DataFrame，每行一个 question，
            每列一个指标分数，再加 question 列。
        """
        if not items:
            log.warning("ragas 评估条目为空，直接返回空 DataFrame")
            return pd.DataFrame()
        if not self._metrics:
            log.warning("ragas 指标列表为空，跳过评估")
            df = pd.DataFrame({
                "question": [i.question for i in items],
                "response": [i.response for i in items],
            })
            return df

        samples: list[SingleTurnSample] = []
        for it in items:
            samples.append(SingleTurnSample(
                user_input=it.question,
                response=it.response,
                retrieved_contexts=it.retrieved_contexts or ["（高升AI接口未返回检索上下文，使用空占位）"],
                reference=it.reference or "",
            ))

        dataset = EvaluationDataset(samples=samples)
        with allure.step(f"Ragas 评估 [{scenario_name}] 样本数={len(samples)} 指标={self._metric_names}"):
            result = evaluate(dataset=dataset, metrics=self._metrics)

        df = result.to_pandas() if hasattr(result, "to_pandas") else pd.DataFrame(result)
        # 确保 question 列存在
        if "user_input" in df.columns and "question" not in df.columns:
            df = df.rename(columns={"user_input": "question"})
        if "question" not in df.columns:
            df.insert(0, "question", [i.question for i in items])

        if attach_to_allure:
            AllureManager.attach_ragas_table(df, name=f"{scenario_name}-明细")
            summary = self.summarize(df)
            AllureManager.attach_ragas_summary(summary, name=f"{scenario_name}-汇总")
        return df

    # ------------------------------------------------------------------
    # 汇总 + 断言
    # ------------------------------------------------------------------

    def summarize(self, df: pd.DataFrame) -> dict[str, float]:
        """计算 DataFrame 中每个数值列的均值。"""
        summary: dict[str, float] = {"sample_count": int(len(df))}
        for col in df.columns:
            s = df[col]
            if pd.api.types.is_numeric_dtype(s):
                valid = s.dropna()
                summary[col] = float(valid.mean()) if len(valid) else 0.0
        return summary

    def assert_thresholds(
        self,
        df: pd.DataFrame,
        thresholds: Optional[dict[str, float]] = None,
        scenario_name: str = "Ragas",
    ) -> None:
        """对指标均值做阈值断言。"""
        if df.empty:
            return
        thresholds = thresholds or config.get("ragas.threshold") or {}
        summary = self.summarize(df)
        for metric_name, thr in thresholds.items():
            ragas_col = metric_name
            # 兼容 ragas 返回的列名（snake_case）
            if ragas_col not in summary:
                # 尝试找近似列
                matched = [c for c in summary if metric_name.lower() in str(c).lower()]
                if matched:
                    ragas_col = matched[0]
                else:
                    continue
            score = float(summary[ragas_col])
            assertions.assert_ragas_score(
                score, thr, metric_name=f"{scenario_name}.{ragas_col}"
            )

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------

    def evaluate_single(
        self,
        question: str,
        response: str,
        retrieved_contexts: Optional[list[str]] = None,
        reference: str = "",
        scenario_name: str = "单条回答Ragas评估",
    ) -> pd.DataFrame:
        """评估单条回答。"""
        item = RagasEvalItem(
            question=question,
            response=response,
            retrieved_contexts=retrieved_contexts or [],
            reference=reference,
        )
        return self.evaluate_items([item], scenario_name=scenario_name)
