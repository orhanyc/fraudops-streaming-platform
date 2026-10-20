from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import average_precision_score, brier_score_loss, precision_score


def recall_at_budget(
    labels: NDArray[np.int_], scores: NDArray[np.float64], budget: float
) -> tuple[float, float, float]:
    threshold = float(np.quantile(scores, 1 - budget))
    alerts = scores >= threshold
    positives = int(labels.sum())
    recall = float(labels[alerts].sum() / positives) if positives else 0.0
    precision = float(precision_score(labels, alerts, zero_division=0))
    return recall, precision, threshold


def bootstrap_recall_interval(
    labels: NDArray[np.int_],
    scores: NDArray[np.float64],
    budget: float,
    samples: int = 300,
    seed: int = 42,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    recalls: list[float] = []
    for _ in range(samples):
        indices = rng.integers(0, len(labels), len(labels))
        sampled_labels = labels[indices]
        sampled_scores = scores[indices]
        recall, _, _ = recall_at_budget(sampled_labels, sampled_scores, budget)
        recalls.append(recall)
    low, high = np.quantile(recalls, [0.025, 0.975])
    return float(low), float(high)


def evaluate_scores(
    labels: NDArray[np.int_],
    scores: NDArray[np.float64],
    budget: float = 0.01,
) -> dict[str, Any]:
    recall, precision, threshold = recall_at_budget(labels, scores, budget)
    low, high = bootstrap_recall_interval(labels, scores, budget)
    return {
        "pr_auc": float(average_precision_score(labels, scores)),
        "brier_score": float(brier_score_loss(labels, scores)),
        "alert_budget": budget,
        "alert_threshold": threshold,
        "recall_at_budget": recall,
        "recall_ci_95": [low, high],
        "precision_at_budget": precision,
        "positive_rate": float(labels.mean()),
        "rows": int(len(labels)),
    }
