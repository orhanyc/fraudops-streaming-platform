from datetime import UTC, datetime, timedelta
from typing import Any, cast

import numpy as np
import pandas as pd

from fraudops.features import enrich_transactions
from fraudops.schemas import Channel, RawTransaction

COUNTRIES = ("US", "CA", "GB", "DE", "TR", "MX")
CHANNELS: tuple[Channel, ...] = ("ach", "card", "wire", "instant")
SCENARIOS = ("account_takeover", "velocity_burst", "new_counterparty")


def generate_transactions(
    events: int = 12_000,
    accounts: int = 180,
    seed: int = 42,
    drift: str | None = None,
    fraud_rate: float = 0.009,
) -> pd.DataFrame:
    if not 0 < fraud_rate < 1:
        raise ValueError("Fraud rate must be between zero and one")
    rng = np.random.default_rng(seed)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    base_events = events // accounts
    extra_events = events % accounts
    rows: list[dict[str, Any]] = []
    transaction_number = 0

    for account_number in range(accounts):
        account_id = f"acct-{account_number:04d}"
        home_country = "US" if rng.random() < 0.9 else str(rng.choice(COUNTRIES))
        base_device = f"device-{account_number:04d}-0"
        typical_amount = float(rng.lognormal(mean=3.45, sigma=0.55))
        current = start + timedelta(hours=float(rng.uniform(0, 24)))

        account_events = base_events + int(account_number < extra_events)
        for event_number in range(account_events):
            is_fraud = rng.random() < fraud_rate
            scenario = str(rng.choice(SCENARIOS)) if is_fraud else "benign"
            gap_minutes = float(rng.exponential(7 * 60))
            if scenario == "velocity_burst":
                gap_minutes = float(rng.uniform(0.2, 2.0))
            current += timedelta(minutes=gap_minutes)

            amount = float(rng.lognormal(np.log(typical_amount), 0.45))
            new_device = rng.random() < 0.07
            international = rng.random() < 0.04
            counterparty_age = float(rng.exponential(180))
            channel = str(rng.choice(CHANNELS, p=[0.28, 0.42, 0.08, 0.22]))

            if scenario == "account_takeover":
                new_device = True
                international = True
                amount *= float(rng.uniform(4, 9))
                channel = str(rng.choice(("wire", "instant")))
            elif scenario == "velocity_burst":
                amount *= float(rng.uniform(2, 5))
                new_device = rng.random() < 0.65
            elif scenario == "new_counterparty":
                counterparty_age = float(rng.uniform(0, 2))
                amount *= float(rng.uniform(3, 7))
                channel = str(rng.choice(("ach", "wire", "instant")))

            if drift == "amount_shift":
                amount *= 2.4
            if drift == "device_shift":
                new_device = rng.random() < 0.6
                international = rng.random() < 0.35

            country = home_country
            if international:
                foreign = [candidate for candidate in COUNTRIES if candidate != home_country]
                country = str(rng.choice(foreign))
            device_id = (
                f"device-{account_number:04d}-{event_number + 1}" if new_device else base_device
            )

            transaction_number += 1
            row = RawTransaction(
                transaction_id=f"txn-{transaction_number:07d}",
                timestamp=current,
                account_id=account_id,
                counterparty_id=f"cp-{int(rng.integers(0, accounts * 4)):05d}",
                device_id=device_id,
                amount=round(amount, 2),
                channel=cast(Channel, channel),
                country=country,
                home_country=home_country,
                counterparty_age_days=round(counterparty_age, 2),
                label=int(is_fraud),
                scenario=scenario,
            )
            rows.append(row.model_dump())

    raw = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return enrich_transactions(raw)


def temporal_split(
    frame: pd.DataFrame,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must leave a test partition")
    ordered = frame.sort_values("timestamp").reset_index(drop=True)
    train_end = int(len(ordered) * train_fraction)
    validation_end = int(len(ordered) * (train_fraction + validation_fraction))
    return (
        ordered.iloc[:train_end].copy(),
        ordered.iloc[train_end:validation_end].copy(),
        ordered.iloc[validation_end:].copy(),
    )
