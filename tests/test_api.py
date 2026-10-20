from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

import fraudops.api as api
from fraudops.data import generate_transactions, temporal_split
from fraudops.model import fit_models
from fraudops.schemas import RawTransaction
from fraudops.service import ScoringEngine
from fraudops.storage import FraudRepository


def test_api_scores_and_exposes_metrics(tmp_path: Path) -> None:
    frame = generate_transactions(events=2_000, accounts=50, seed=21)
    train, validation, _ = temporal_split(frame)
    _, bundle = fit_models(train, validation, seed=21)
    repository = FraudRepository(f"sqlite:///{tmp_path / 'api.db'}")
    repository.create_schema()
    api.repository = repository
    api.model_bundle = bundle
    api.scoring_engine = ScoringEngine(bundle, repository)

    transaction = RawTransaction(
        transaction_id="api-1",
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
        account_id="acct-api",
        counterparty_id="cp-api",
        device_id="device-api",
        amount=800,
        channel="wire",
        country="GB",
        home_country="US",
        counterparty_age_days=1,
        scenario="account_takeover",
    )
    with TestClient(api.app) as client:
        health = client.get("/health")
        response = client.post("/score", json=transaction.model_dump(mode="json"))
        metrics = client.get("/metrics")
        page = client.get("/")
    assert health.status_code == 200
    assert health.json()["status"] == "ready"
    assert response.status_code == 200
    assert response.headers["x-trace-id"]
    assert 0 <= response.json()["risk_score"] <= 1
    assert "fraudops_scored_transactions_total" in metrics.text
    assert "FraudOps Analyst Queue" in page.text
