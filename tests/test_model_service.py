from datetime import UTC, datetime, timedelta
from pathlib import Path

from fraudops.data import generate_transactions, temporal_split
from fraudops.model import ModelBundle, fit_models, load_bundle, save_bundle
from fraudops.schemas import RawTransaction
from fraudops.service import ScoringEngine
from fraudops.storage import FraudRepository
from fraudops.summary import summary_has_complete_citations


def train_bundle() -> ModelBundle:
    frame = generate_transactions(events=2_400, accounts=60, seed=15)
    train, validation, _ = temporal_split(frame)
    _, bundle = fit_models(train, validation, seed=15)
    return bundle


def raw_event(number: int, amount: float, country: str = "US") -> RawTransaction:
    return RawTransaction(
        transaction_id=f"service-{number}",
        timestamp=datetime(2026, 5, 1, tzinfo=UTC) + timedelta(minutes=number),
        account_id="acct-service",
        counterparty_id="cp-new",
        device_id="device-main" if number < 4 else "device-new",
        amount=amount,
        channel="instant",
        country=country,
        home_country="US",
        counterparty_age_days=1 if number >= 4 else 90,
        scenario="new_counterparty" if number >= 4 else "benign",
    )


def test_model_round_trip_and_scoring_service(tmp_path: Path) -> None:
    bundle = train_bundle()
    artifact = tmp_path / "model.joblib"
    save_bundle(bundle, artifact)
    loaded = load_bundle(artifact)
    repository = FraudRepository(f"sqlite:///{tmp_path / 'scores.db'}")
    repository.create_schema()
    engine = ScoringEngine(loaded, repository)

    for number in range(4):
        engine.score(raw_event(number, 50 + number))
    result = engine.score(raw_event(4, 1_000, country="GB"))
    assert 0 <= result.risk_score <= 1
    assert summary_has_complete_citations(result.summary)
    assert result.summary.risk_signals
