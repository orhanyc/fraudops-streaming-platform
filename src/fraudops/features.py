from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from fraudops.schemas import EnrichedTransaction, RawTransaction

NUMERIC_FEATURES = [
    "amount",
    "counterparty_age_days",
    "tx_count_1h",
    "minutes_since_prev",
    "amount_to_avg",
    "is_new_device",
    "is_international",
]
CATEGORICAL_FEATURES = ["channel"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


@dataclass
class AccountState:
    recent_timestamps: deque[datetime] = field(default_factory=deque)
    seen_devices: set[str] = field(default_factory=set)
    amount_total: float = 0.0
    amount_count: int = 0
    last_timestamp: datetime | None = None


class OnlineFeatureStore:
    def __init__(self) -> None:
        self._accounts: defaultdict[str, AccountState] = defaultdict(AccountState)

    def enrich(self, raw: RawTransaction) -> EnrichedTransaction:
        state = self._accounts[raw.account_id]
        cutoff = raw.timestamp - timedelta(hours=1)
        while state.recent_timestamps and state.recent_timestamps[0] < cutoff:
            state.recent_timestamps.popleft()

        prior_average = (
            state.amount_total / state.amount_count if state.amount_count else raw.amount
        )
        if state.last_timestamp is None:
            minutes_since_prev = 24 * 60.0
        else:
            minutes_since_prev = max(
                0.0, (raw.timestamp - state.last_timestamp).total_seconds() / 60.0
            )

        enriched = EnrichedTransaction(
            **raw.model_dump(),
            tx_count_1h=len(state.recent_timestamps),
            minutes_since_prev=minutes_since_prev,
            amount_to_avg=max(raw.amount / max(prior_average, 0.01), 0.01),
            is_new_device=int(raw.device_id not in state.seen_devices),
            is_international=int(raw.country != raw.home_country),
        )

        state.recent_timestamps.append(raw.timestamp)
        state.seen_devices.add(raw.device_id)
        state.amount_total += raw.amount
        state.amount_count += 1
        state.last_timestamp = raw.timestamp
        return enriched


def enrich_transactions(frame: pd.DataFrame) -> pd.DataFrame:
    store = OnlineFeatureStore()
    enriched: list[dict[str, Any]] = []
    for record in frame.sort_values("timestamp").to_dict(orient="records"):
        raw = RawTransaction.model_validate(record)
        enriched.append(store.enrich(raw).model_dump())
    return pd.DataFrame(enriched)
