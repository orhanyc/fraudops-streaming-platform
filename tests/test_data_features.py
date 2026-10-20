from datetime import UTC, datetime, timedelta

from fraudops.data import generate_transactions, temporal_split
from fraudops.features import OnlineFeatureStore
from fraudops.schemas import RawTransaction


def make_transaction(
    transaction_id: str,
    timestamp: datetime,
    amount: float = 100.0,
    device_id: str = "device-a",
) -> RawTransaction:
    return RawTransaction(
        transaction_id=transaction_id,
        timestamp=timestamp,
        account_id="acct-test",
        counterparty_id="cp-test",
        device_id=device_id,
        amount=amount,
        channel="instant",
        country="US",
        home_country="US",
        counterparty_age_days=30,
    )


def test_generator_is_reproducible_and_contains_scenarios() -> None:
    first = generate_transactions(events=1_200, accounts=30, seed=7)
    second = generate_transactions(events=1_200, accounts=30, seed=7)
    assert first.equals(second)
    assert first["label"].sum() > 0
    assert set(first[first["label"] == 1]["scenario"]) >= {
        "account_takeover",
        "velocity_burst",
        "new_counterparty",
    }


def test_temporal_split_preserves_time_order() -> None:
    frame = generate_transactions(events=500, accounts=20, seed=8)
    train, validation, test = temporal_split(frame)
    assert train["timestamp"].max() <= validation["timestamp"].min()
    assert validation["timestamp"].max() <= test["timestamp"].min()
    assert len(train) + len(validation) + len(test) == len(frame)


def test_online_features_use_only_prior_events() -> None:
    store = OnlineFeatureStore()
    started = datetime(2026, 1, 1, tzinfo=UTC)
    first = store.enrich(make_transaction("one", started))
    second = store.enrich(
        make_transaction("two", started + timedelta(minutes=10), amount=400, device_id="device-b")
    )
    assert first.tx_count_1h == 0
    assert first.amount_to_avg == 1
    assert second.tx_count_1h == 1
    assert second.amount_to_avg == 4
    assert second.is_new_device == 1
    assert second.minutes_since_prev == 10
