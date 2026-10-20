from typing import Any

from fraudops.data import generate_transactions
from fraudops.streaming import publish_transactions


class FakeProducer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes, dict[str, Any]]] = []

    def send(self, topic: str, key: bytes, value: dict[str, Any]) -> None:
        self.messages.append((topic, key, value))

    def flush(self, timeout: int) -> None:
        assert timeout == 30

    def close(self, timeout: int) -> None:
        assert timeout == 10


def test_publisher_serializes_raw_events(monkeypatch: Any) -> None:
    producer = FakeProducer()
    monkeypatch.setattr("fraudops.streaming.create_producer", lambda _: producer)
    frame = generate_transactions(events=100, accounts=10, seed=30)
    count = publish_transactions(frame, "unused", "events")
    assert count == len(frame)
    assert len(producer.messages) == len(frame)
    assert producer.messages[0][0] == "events"
    assert producer.messages[0][2]["transaction_id"].startswith("txn-")
