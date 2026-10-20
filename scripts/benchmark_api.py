import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

import numpy as np


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "benchmark.db"
        os.environ["FRAUDOPS_DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ.setdefault("FRAUDOPS_MODEL_PATH", "artifacts/model.joblib")

        from fastapi.testclient import TestClient

        from fraudops.api import app, repository
        from fraudops.data import generate_transactions
        from fraudops.schemas import RawTransaction

        frame = generate_transactions(events=250, accounts=25, seed=91)
        timings: list[float] = []
        failures = 0
        started_all = time.perf_counter()
        with TestClient(app) as client:
            for record in frame.to_dict(orient="records"):
                raw = RawTransaction.model_validate(record)
                started = time.perf_counter_ns()
                response = client.post("/score", json=raw.model_dump(mode="json"))
                timings.append((time.perf_counter_ns() - started) / 1_000_000)
                failures += int(response.status_code != 200)
        elapsed = time.perf_counter() - started_all
        values = np.asarray(timings)
        report = {
            "requests": len(timings),
            "failures": failures,
            "transport": "FastAPI TestClient, sequential requests",
            "throughput_requests_per_second": len(timings) / elapsed,
            "p50_ms": float(np.quantile(values, 0.5)),
            "p95_ms": float(np.quantile(values, 0.95)),
            "p99_ms": float(np.quantile(values, 0.99)),
            "environment": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "processor": platform.processor(),
            },
        }
        output = Path("reports/api_benchmark.json")
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        repository.engine.dispose()
        if failures:
            raise SystemExit("API benchmark encountered failed requests")


if __name__ == "__main__":
    main()
