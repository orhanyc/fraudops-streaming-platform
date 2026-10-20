# FraudOps Streaming Platform

Production-style reference implementation for detecting suspicious synthetic payment events under a strict analyst alert budget.

The first release will demonstrate streaming ingestion, online feature computation, calibrated fraud scoring, alert prioritization, evidence-linked case summaries, drift monitoring and end-to-end performance measurement. All data and code are independent portfolio work; no employer data, schemas, rules, prompts or source code are used.

## Planned proof points

- PR-AUC and calibration against a transparent baseline
- Recall at a 1% alert budget
- p50, p95 and p99 scoring latency under a documented load test
- Sustained event throughput and failure recovery
- Data and score drift detection
- Citation correctness for generated case summaries

The complete implementation specification is in [`docs/SPEC.md`](docs/SPEC.md).

## Status

Architecture and acceptance criteria are defined. Implementation has not started.
