import json
import os
from pathlib import Path

from kafka import KafkaConsumer

from fraudops.model import load_bundle
from fraudops.schemas import RawTransaction
from fraudops.service import ScoringEngine
from fraudops.storage import FraudRepository


def main() -> None:
    bootstrap = os.getenv("FRAUDOPS_KAFKA_BOOTSTRAP", "localhost:19092")
    topic = os.getenv("FRAUDOPS_KAFKA_TOPIC", "payment-events")
    database_url = os.getenv("FRAUDOPS_DATABASE_URL", "sqlite:///fraudops.db")
    model_path = Path(os.getenv("FRAUDOPS_MODEL_PATH", "artifacts/model.joblib"))
    repository = FraudRepository(database_url)
    repository.create_schema()
    engine = ScoringEngine(load_bundle(model_path), repository)
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id="fraudops-feature-workers",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    for message in consumer:
        raw = RawTransaction.model_validate(message.value)
        result = engine.score(raw)
        print(
            json.dumps(
                {
                    "transaction_id": result.transaction_id,
                    "risk_score": result.risk_score,
                    "alert": result.alert,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
