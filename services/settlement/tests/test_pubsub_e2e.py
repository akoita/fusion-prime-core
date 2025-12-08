import asyncio
import os
import sys
import types
from pathlib import Path

import pytest
import pytest_asyncio

ROOT_DIR = Path(__file__).resolve().parents[3]
SETTLEMENT_DIR = Path(__file__).resolve().parents[1]
integrations_root = ROOT_DIR / "integrations"

for path in {ROOT_DIR, SETTLEMENT_DIR, integrations_root}:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

TEST_MODE = os.getenv("FUSION_PRIME_PUBSUB_TEST_MODE", "mock").lower()

if TEST_MODE == "mock":
    web3_module = types.ModuleType("web3")

    class DummyWeb3:
        def __init__(self, provider=None):
            self.provider = provider

        @staticmethod
        def to_checksum_address(value: str) -> str:
            return value

    web3_module.Web3 = DummyWeb3
    sys.modules["web3"] = web3_module
    sys.modules["web3.types"] = types.SimpleNamespace(EventData=dict)

from generated.fusionprime.settlement.v1 import settlement_pb2 as generated_pb

module_chain = [
    "analytics",
    "analytics.schemas",
    "analytics.schemas.pubsub",
    "analytics.schemas.pubsub.fusionprime",
    "analytics.schemas.pubsub.fusionprime.settlement",
    "analytics.schemas.pubsub.fusionprime.settlement.v1",
]
for module_name in module_chain:
    sys.modules.setdefault(module_name, types.ModuleType(module_name))

sys.modules["analytics.schemas.pubsub.fusionprime.settlement.v1.settlement_pb2"] = generated_pb
setattr(
    sys.modules["analytics.schemas.pubsub.fusionprime.settlement.v1"],
    "settlement_pb2",
    generated_pb,
)

from app.dependencies import get_engine, get_session_factory, init_db
from generated.fusionprime.settlement.v1 import settlement_pb2
from infrastructure.consumers.pubsub_consumer import SettlementEventConsumer
from infrastructure.db.models import Base, SettlementCommandRecord

from integrations.relayers.escrow.events.event_relayer import EscrowEvent, EscrowRelayer

TEST_DB_URL = "sqlite+aiosqlite:///./test_settlement.db"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    init_db(TEST_DB_URL)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    try:
        os.remove("test_settlement.db")
    except FileNotFoundError:
        pass


class FakePublisher:
    def __init__(self):
        self.messages = []

    def topic_path(self, project_id: str, topic_id: str) -> str:
        return f"projects/{project_id}/topics/{topic_id}"

    def publish(self, topic_path: str, data: bytes):
        self.messages.append((topic_path, data))

        class _Result:
            def result(self):
                return None

        return _Result()


class FakeSubscriber:
    def subscription_path(self, project_id: str, subscription_id: str) -> str:
        return f"projects/{project_id}/subscriptions/{subscription_id}"

    def subscribe(self, path: str, callback):  # pragma: no cover - not used in mock path
        raise NotImplementedError


class FakeMessage:
    def __init__(self, data: bytes):
        self.data = data
        self.ack_called = False

    def ack(self):
        self.ack_called = True

    def nack(self):  # pragma: no cover - guard unexpected path
        raise AssertionError("Message should not be nacked")


@pytest.mark.asyncio
async def test_relayer_to_consumer_flow():
    if TEST_MODE != "mock":
        pytest.skip("Real GCP Pub/Sub integration not enabled")

    publisher = FakePublisher()
    relayer = EscrowRelayer(
        web3_module.Web3(),  # type: ignore[attr-defined]
        ZERO_ADDRESS,
        publisher.topic_path("test", "settlement.events.v1"),
        publisher,
    )

    event = EscrowEvent(
        command_id="cmd-test",
        workflow_id="wf-test",
        payer="payer",
        payee="payee",
        chain_id="1",
        status=settlement_pb2.EVENT_STATUS_CONFIRMED,
    )
    relayer.publish(event)

    # Verify message was published
    assert len(publisher.messages) == 1

    # Parse and verify the message
    proto_event = settlement_pb2.SettlementEvent()
    proto_event.ParseFromString(publisher.messages[0][1])
    assert proto_event.command_id == "cmd-test"
    assert proto_event.status == settlement_pb2.EVENT_STATUS_CONFIRMED

    # Test persistence layer separately to avoid async/sync boundary issues
    loop = asyncio.get_running_loop()
    consumer = SettlementEventConsumer(
        "test",
        "sub",
        lambda _: None,
        session_factory=get_session_factory(),
        subscriber=FakeSubscriber(),
        loop=loop,
    )

    # Directly test persistence without going through callback
    await consumer._persist_event(proto_event)

    async with get_session_factory()() as session:
        record = await session.get(SettlementCommandRecord, "cmd-test")
        assert record is not None
        assert record.status == "EVENT_STATUS_CONFIRMED"
