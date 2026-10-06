"""Evaluation framework (PRD s.47-49).

Retrieval and answer quality are measured against a hand-labelled golden
dataset. Every number the platform reports comes from a stored evaluation run:
nothing here invents a metric, and an experiment that cannot run on this
deployment is reported as unavailable rather than skipped silently.
"""

from app.evaluation.dataset import GoldenDataset, GoldenQuestion, load_golden_dataset
from app.evaluation.metrics import (
    answer_keywords,
    citation_validity,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    refusal_correct,
)
from app.evaluation.runner import EXPERIMENTS, EvaluationRunner

__all__ = [
    "EXPERIMENTS",
    "EvaluationRunner",
    "GoldenDataset",
    "GoldenQuestion",
    "answer_keywords",
    "citation_validity",
    "load_golden_dataset",
    "ndcg_at_k",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
    "refusal_correct",
]
