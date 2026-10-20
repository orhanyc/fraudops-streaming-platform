import numpy as np

from fraudops.data import generate_transactions
from fraudops.drift import drift_report, population_stability_index
from fraudops.evaluation import evaluate_scores, recall_at_budget


def test_recall_at_budget_selects_high_scores() -> None:
    labels = np.asarray([0, 0, 1, 0, 1], dtype=int)
    scores = np.asarray([0.01, 0.1, 0.9, 0.2, 0.8], dtype=float)
    recall, precision, threshold = recall_at_budget(labels, scores, budget=0.4)
    assert recall == 1
    assert precision == 1
    assert threshold >= 0.2
    metrics = evaluate_scores(labels, scores, budget=0.4)
    assert metrics["pr_auc"] == 1


def test_population_shift_has_high_psi() -> None:
    reference = np.linspace(1, 10, 1_000)
    shifted = np.linspace(20, 40, 1_000)
    assert population_stability_index(reference, shifted) > 0.2


def test_both_injected_drift_scenarios_trigger() -> None:
    reference_frame = generate_transactions(events=2_000, accounts=50, seed=10)
    reference = {
        feature: reference_frame[feature].astype(float).tolist()
        for feature in ("amount", "amount_to_avg", "is_new_device", "is_international")
    }
    amount_shift = generate_transactions(events=1_000, accounts=30, seed=11, drift="amount_shift")
    device_shift = generate_transactions(events=1_000, accounts=30, seed=12, drift="device_shift")
    assert drift_report(reference, amount_shift)["drift_detected"]
    assert drift_report(reference, device_shift)["drift_detected"]
