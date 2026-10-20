import json
import time
from typing import Any

import pandas as pd
from kafka import KafkaProducer

from fraudops.schemas import RawTransaction


def create_producer(bootstrap_servers: str, retries: int = 12) -> KafkaProducer:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                acks="all",
                retries=5,
            )
        except Exception as error:
            last_error = error
            time.sleep(min(1 + attempt, 5))
    raise RuntimeError("Kafka broker did not become available") from last_error


def publish_transactions(
    frame: pd.DataFrame,
    bootstrap_servers: str,
    topic: str = "payment-events",
) -> int:
    producer = create_producer(bootstrap_servers)
    published = 0
    try:
        for record in frame.to_dict(orient="records"):
            raw = RawTransaction.model_validate(record)
            payload: dict[str, Any] = raw.model_dump(mode="json")
            producer.send(topic, key=raw.account_id.encode("utf-8"), value=payload)
            published += 1
        producer.flush(timeout=30)
    finally:
        producer.close(timeout=10)
    return published
