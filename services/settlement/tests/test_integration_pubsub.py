import asyncio
from unittest.mock import MagicMock

import pytest
from generated.fusionprime.settlement.v1 import settlement_pb2
from infrastructure.consumers.pubsub_consumer import SettlementEventConsumer


class FakeSubscriber:
    def __init__(self) -> None:
        self.callback = None

    def subscription_path(self, project_id, subscription_id):  # type: ignore[no-redef]
        return f"projects/{project_id}/subscriptions/{subscription_id}"

    def subscribe(self, path, callback):  # type: ignore[no-redef]
        self.callback = callback
        return MagicMock()


@pytest.mark.asyncio
async def test_consumer_persists_event(monkeypatch):
    fake_subscriber = FakeSubscriber()
    monkeypatch.setattr("google.cloud.pubsub_v1.SubscriberClient", lambda: fake_subscriber)

    handler = MagicMock()
    consumer = SettlementEventConsumer("project", "subscription", handler, session_factory=None)
    consumer.start()

    event = settlement_pb2.SettlementEvent(event_id="evt1")
    message = MagicMock()
    message.data = event.SerializeToString()

    fake_subscriber.callback(message)
    await asyncio.sleep(0)

    handler.assert_called_once()
    message.ack.assert_called_once()
