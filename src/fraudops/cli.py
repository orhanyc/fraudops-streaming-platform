import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from fraudops.data import generate_transactions, temporal_split
from fraudops.drift import drift_report
from fraudops.evaluation import evaluate_scores
from fraudops.features import MODEL_FEATURES
from fraudops.model import fit_models, save_bundle
from fraudops.streaming import publish_transactions


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _latency_report(bundle: Any, sample: Any, runs: int = 500) -> dict[str, float]:
    timings: list[float] = []
    for _ in range(runs):
        started = time.perf_counter_ns()
        bundle.predict_proba(sample)
        timings.append((time.perf_counter_ns() - started) / 1_000_000)
    values = np.asarray(timings)
    return {
        "runs": runs,
        "p50_ms": float(np.quantile(values, 0.5)),
        "p95_ms": float(np.quantile(values, 0.95)),
        "p99_ms": float(np.quantile(values, 0.99)),
    }


def run_pipeline(args: argparse.Namespace) -> None:
    frame = generate_transactions(events=args.events, accounts=args.accounts, seed=args.seed)
    train, validation, test = temporal_split(frame)
    baseline, bundle = fit_models(
        train,
        validation,
        alert_budget=args.alert_budget,
        seed=args.seed,
    )
    validation_labels = np.asarray(validation["label"], dtype=int)
    test_labels = np.asarray(test["label"], dtype=int)
    baseline_validation_scores = np.asarray(
        baseline.predict_proba(validation[MODEL_FEATURES])[:, 1], dtype=float
    )
    baseline_test_scores = np.asarray(
        baseline.predict_proba(test[MODEL_FEATURES])[:, 1], dtype=float
    )
    challenger_validation_scores = bundle.predict_proba(validation)
    challenger_test_scores = bundle.predict_proba(test)

    metrics = {
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": args.seed,
        "dataset": {
            "rows": len(frame),
            "train_rows": len(train),
            "validation_rows": len(validation),
            "test_rows": len(test),
            "positive_rate": float(frame["label"].mean()),
        },
        "baseline": {
            "validation": evaluate_scores(
                validation_labels, baseline_validation_scores, args.alert_budget
            ),
            "test": evaluate_scores(test_labels, baseline_test_scores, args.alert_budget),
        },
        "challenger": {
            "name": bundle.model_name,
            "validation": evaluate_scores(
                validation_labels, challenger_validation_scores, args.alert_budget
            ),
            "test": evaluate_scores(test_labels, challenger_test_scores, args.alert_budget),
        },
        "latency": _latency_report(bundle, test.iloc[[0]][MODEL_FEATURES]),
    }
    metrics["comparison"] = {
        "test_pr_auc_lift": (
            metrics["challenger"]["test"]["pr_auc"] - metrics["baseline"]["test"]["pr_auc"]
        ),
        "challenger_wins": (
            metrics["challenger"]["test"]["pr_auc"] > metrics["baseline"]["test"]["pr_auc"]
        ),
    }

    amount_shift = generate_transactions(
        events=3_000,
        accounts=80,
        seed=args.seed + 1,
        drift="amount_shift",
    )
    device_shift = generate_transactions(
        events=3_000,
        accounts=80,
        seed=args.seed + 2,
        drift="device_shift",
    )
    drift = {
        "amount_shift": drift_report(bundle.reference, amount_shift),
        "device_shift": drift_report(bundle.reference, device_shift),
    }

    artifact_path = Path(args.artifact)
    save_bundle(bundle, artifact_path)
    _write_json(Path(args.metrics), metrics)
    _write_json(Path(args.drift_report), drift)
    print(json.dumps(metrics, indent=2))
    print(json.dumps(drift, indent=2))


def publish(args: argparse.Namespace) -> None:
    frame = generate_transactions(events=args.events, accounts=args.accounts, seed=args.seed)
    count = publish_transactions(frame, args.bootstrap_servers, args.topic)
    print(f"Published {count} events to {args.topic}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fraudops")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pipeline = subparsers.add_parser("run-pipeline")
    pipeline.add_argument("--events", type=int, default=12_000)
    pipeline.add_argument("--accounts", type=int, default=180)
    pipeline.add_argument("--seed", type=int, default=42)
    pipeline.add_argument("--alert-budget", type=float, default=0.01)
    pipeline.add_argument("--artifact", default="artifacts/model.joblib")
    pipeline.add_argument("--metrics", default="reports/metrics.json")
    pipeline.add_argument("--drift-report", default="reports/drift.json")
    pipeline.set_defaults(handler=run_pipeline)

    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--events", type=int, default=5_000)
    publish_parser.add_argument("--accounts", type=int, default=100)
    publish_parser.add_argument("--seed", type=int, default=84)
    publish_parser.add_argument("--bootstrap-servers", default="localhost:19092")
    publish_parser.add_argument("--topic", default="payment-events")
    publish_parser.set_defaults(handler=publish)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
