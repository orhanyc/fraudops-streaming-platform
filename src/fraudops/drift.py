from typing import Any

import numpy as np
import pandas as pd


def population_stability_index(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        minimum = min(float(reference.min()), float(current.min())) - 0.5
        maximum = max(float(reference.max()), float(current.max())) + 0.5
        edges = np.linspace(minimum, maximum, min(bins, 4) + 1)
    edges[0] = -np.inf
    edges[-1] = np.inf
    reference_counts, _ = np.histogram(reference, bins=edges)
    current_counts, _ = np.histogram(current, bins=edges)
    reference_rate = np.clip(reference_counts / len(reference), 1e-6, None)
    current_rate = np.clip(current_counts / len(current), 1e-6, None)
    return float(np.sum((current_rate - reference_rate) * np.log(current_rate / reference_rate)))


def drift_report(
    reference: dict[str, list[float]],
    current: pd.DataFrame,
    threshold: float = 0.2,
) -> dict[str, Any]:
    features: dict[str, Any] = {}
    for feature, values in reference.items():
        psi = population_stability_index(np.asarray(values), current[feature].to_numpy())
        features[feature] = {"psi": psi, "drifted": psi >= threshold}
    return {
        "threshold": threshold,
        "drift_detected": any(item["drifted"] for item in features.values()),
        "features": features,
    }
