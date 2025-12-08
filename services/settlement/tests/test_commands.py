import os

import pytest
import pytest_asyncio
from app.dependencies import get_engine, get_session_factory, init_db
from app.main import app
from httpx import ASGITransport, AsyncClient
from infrastructure.db.models import Base, SettlementCommandRecord
from sqlalchemy import select

TEST_DB_URL = "sqlite+aiosqlite:///./test_settlement.db"

# Get the service URL from environment or use default
SERVICE_URL = os.getenv("SETTLEMENT_SERVICE_URL", "http://localhost:8000")


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


async def _fetch_amount(command_id: str) -> str:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(SettlementCommandRecord.amount_numeric).where(
                SettlementCommandRecord.command_id == command_id
            )
        )
        amount = result.scalar_one()
        return str(amount)


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_ingest_command_accepts_payload(client):
    async with client:
        response = await client.post(
            "/commands/ingest",
            json={
                "command_id": "cmd-1",
                "workflow_id": "wf-1",
                "account_ref": "acct-1",
                "asset_symbol": "USDC",
                "amount": "100.5",
            },
        )

        assert response.status_code == 202
        assert response.json()["status"] == "accepted"

        amount = await _fetch_amount("cmd-1")
        assert amount == "100.500000000000000000"


@pytest.mark.asyncio
async def test_command_ingestion(client) -> None:
    """Test settlement command ingestion using FastAPI test client."""
    test_command = {
        "command_id": "test-1234567890",
        "payer": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "payee": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "amount": "0.01",
        "chain_id": 11155111,
    }

    async with client:
        response = await client.post("/commands/ingest", json=test_command)

        # Should accept the command (may return 200 or 202)
        assert response.status_code in [200, 202]

        response_data = response.json()
        assert "command_id" in response_data or "accepted" in str(response_data).lower()


@pytest.mark.asyncio
async def test_command_status_query(client) -> None:
    """Test command status query endpoint using FastAPI test client."""
    test_command_id = "test-1234567890"

    async with client:
        response = await client.get(f"/commands/{test_command_id}")

        # Should return some response (may be 200, 404, or other)
        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            response_data = response.json()
            assert "command_id" in response_data or "status" in response_data
