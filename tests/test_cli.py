import argparse
import json
from pathlib import Path

from fraudops.cli import run_pipeline


def test_pipeline_writes_reproducible_release_artifacts(tmp_path: Path) -> None:
    artifact = tmp_path / "model.joblib"
    metrics = tmp_path / "metrics.json"
    drift = tmp_path / "drift.json"
    args = argparse.Namespace(
        events=1_800,
        accounts=45,
        seed=42,
        alert_budget=0.01,
        artifact=str(artifact),
        metrics=str(metrics),
        drift_report=str(drift),
    )
    run_pipeline(args)
    report = json.loads(metrics.read_text(encoding="utf-8"))
    drift_report = json.loads(drift.read_text(encoding="utf-8"))
    assert artifact.exists()
    assert report["dataset"]["rows"] == 1_800
    assert 0 <= report["challenger"]["test"]["pr_auc"] <= 1
    assert drift_report["amount_shift"]["drift_detected"]
    assert drift_report["device_shift"]["drift_detected"]
