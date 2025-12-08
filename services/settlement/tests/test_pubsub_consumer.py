import asyncio
import unittest
from unittest.mock import MagicMock

from generated.fusionprime.settlement.v1 import settlement_pb2
from infrastructure.consumers.pubsub_consumer import SettlementEventConsumer
from sqlalchemy.ext.asyncio import AsyncSession


class FakeMessage:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.message_id = "test-message-id"
        self.ack_called = False
        self.nack_called = False

    def ack(self) -> None:
        self.ack_called = True

    def nack(self) -> None:
        self.nack_called = True


class SettlementEventConsumerTest(unittest.TestCase):
    def test_callback_acknowledges_valid_message(self) -> None:
        handler = MagicMock()
        consumer = SettlementEventConsumer.__new__(SettlementEventConsumer)
        consumer._subscriber = MagicMock()
        consumer._subscription_path = "projects/test/subscriptions/test"
        consumer._handler = handler
        consumer._session_factory = None

        event = settlement_pb2.SettlementEvent(event_id="evt-1")
        message = FakeMessage(event.SerializeToString())

        SettlementEventConsumer._callback(consumer, message)  # type: ignore[arg-type]

        handler.assert_called_once()
        assert message.ack_called
        assert not message.nack_called


if __name__ == "__main__":
    unittest.main()
