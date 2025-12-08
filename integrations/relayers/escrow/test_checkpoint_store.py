"""
Tests for checkpoint store
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from checkpoint_store import Checkpoint, ProcessedEvent, SQLiteCheckpointStore


@pytest.fixture
async def checkpoint_store():
    """Create a temporary SQLite checkpoint store for testing"""
    store = SQLiteCheckpointStore(":memory:")
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_save_and_retrieve_checkpoint(checkpoint_store):
    """Test saving and retrieving checkpoints"""
    checkpoint = Checkpoint(
        chain_id="31337",
        contract_address="0x1234567890123456789012345678901234567890",
        last_processed_block=1000,
        last_processed_timestamp=datetime.now(timezone.utc),
        total_events_processed=42,
        event_metadata={"test": "data"},
    )

    # Save checkpoint
    await checkpoint_store.save_checkpoint(checkpoint)

    # Retrieve checkpoint
    retrieved = await checkpoint_store.get_checkpoint(
        checkpoint.chain_id, checkpoint.contract_address
    )

    assert retrieved is not None
    assert retrieved.chain_id == checkpoint.chain_id
    assert retrieved.contract_address == checkpoint.contract_address
    assert retrieved.last_processed_block == checkpoint.last_processed_block
    assert retrieved.total_events_processed == checkpoint.total_events_processed
    assert retrieved.metadata == checkpoint.metadata


@pytest.mark.asyncio
async def test_update_checkpoint(checkpoint_store):
    """Test updating an existing checkpoint"""
    checkpoint1 = Checkpoint(
        chain_id="31337",
        contract_address="0x1234567890123456789012345678901234567890",
        last_processed_block=1000,
        last_processed_timestamp=datetime.now(timezone.utc),
        total_events_processed=42,
    )

    checkpoint2 = Checkpoint(
        chain_id="31337",
        contract_address="0x1234567890123456789012345678901234567890",
        last_processed_block=2000,
        last_processed_timestamp=datetime.now(timezone.utc),
        total_events_processed=100,
    )

    # Save first checkpoint
    await checkpoint_store.save_checkpoint(checkpoint1)

    # Update with second checkpoint
    await checkpoint_store.save_checkpoint(checkpoint2)

    # Retrieve should get the updated values
    retrieved = await checkpoint_store.get_checkpoint(
        checkpoint1.chain_id, checkpoint1.contract_address
    )

    assert retrieved is not None
    assert retrieved.last_processed_block == 2000
    assert retrieved.total_events_processed == 100


@pytest.mark.asyncio
async def test_checkpoint_not_found(checkpoint_store):
    """Test retrieving non-existent checkpoint"""
    retrieved = await checkpoint_store.get_checkpoint("999", "0xnonexistent")
    assert retrieved is None


@pytest.mark.asyncio
async def test_mark_event_processed(checkpoint_store):
    """Test marking events as processed"""
    event = ProcessedEvent(
        event_id="31337:0xtxhash:0",
        chain_id="31337",
        contract_address="0x1234567890123456789012345678901234567890",
        block_number=1000,
        transaction_hash="0xtxhash",
        log_index=0,
        event_name="EscrowReleased",
        processed_at=datetime.now(timezone.utc),
        published=True,
        event_metadata={
            "payer": "0xpayer",
            "payee": "0xpayee",
            "amount": "1000000000000000000",
        },
    )

    # Mark as processed (should return True - newly marked)
    result = await checkpoint_store.mark_event_processed(event)
    assert result is True

    # Try to mark again (should return False - already processed)
    result = await checkpoint_store.mark_event_processed(event)
    assert result is False


@pytest.mark.asyncio
async def test_is_event_processed(checkpoint_store):
    """Test checking if event is processed"""
    event = ProcessedEvent(
        event_id="31337:0xtxhash:0",
        chain_id="31337",
        contract_address="0x1234567890123456789012345678901234567890",
        block_number=1000,
        transaction_hash="0xtxhash",
        log_index=0,
        event_name="EscrowReleased",
        processed_at=datetime.now(timezone.utc),
        published=True,
    )

    # Should not be processed initially
    is_processed = await checkpoint_store.is_event_processed(event.event_id)
    assert is_processed is False

    # Mark as processed
    await checkpoint_store.mark_event_processed(event)

    # Should be processed now
    is_processed = await checkpoint_store.is_event_processed(event.event_id)
    assert is_processed is True


@pytest.mark.asyncio
async def test_get_processed_events(checkpoint_store):
    """Test retrieving processed events in a block range"""
    events = [
        ProcessedEvent(
            event_id=f"31337:0xtxhash{i}:0",
            chain_id="31337",
            contract_address="0x1234567890123456789012345678901234567890",
            block_number=1000 + i,
            transaction_hash=f"0xtxhash{i}",
            log_index=0,
            event_name="EscrowReleased",
            processed_at=datetime.now(timezone.utc),
            published=True,
        )
        for i in range(10)
    ]

    # Mark all as processed
    for event in events:
        await checkpoint_store.mark_event_processed(event)

    # Get events in range
    retrieved = await checkpoint_store.get_processed_events("31337", 1002, 1007)

    assert len(retrieved) == 6  # Blocks 1002-1007 (inclusive)
    assert all(1002 <= e.block_number <= 1007 for e in retrieved)


@pytest.mark.asyncio
async def test_cleanup_old_events(checkpoint_store):
    """Test cleaning up old processed events"""
    now = datetime.now(timezone.utc)

    # Create old and recent events
    old_event = ProcessedEvent(
        event_id="31337:0xold:0",
        chain_id="31337",
        contract_address="0x1234567890123456789012345678901234567890",
        block_number=1000,
        transaction_hash="0xold",
        log_index=0,
        event_name="EscrowReleased",
        processed_at=now - timedelta(days=10),
        published=True,
    )

    recent_event = ProcessedEvent(
        event_id="31337:0xrecent:0",
        chain_id="31337",
        contract_address="0x1234567890123456789012345678901234567890",
        block_number=2000,
        transaction_hash="0xrecent",
        log_index=0,
        event_name="EscrowReleased",
        processed_at=now - timedelta(days=1),
        published=True,
    )

    # Mark both as processed
    await checkpoint_store.mark_event_processed(old_event)
    await checkpoint_store.mark_event_processed(recent_event)

    # Clean up events older than 7 days
    cutoff = now - timedelta(days=7)
    removed = await checkpoint_store.cleanup_old_events(cutoff)

    assert removed == 1

    # Old event should be gone
    is_old_processed = await checkpoint_store.is_event_processed(old_event.event_id)
    assert is_old_processed is False

    # Recent event should still exist
    is_recent_processed = await checkpoint_store.is_event_processed(recent_event.event_id)
    assert is_recent_processed is True


@pytest.mark.asyncio
async def test_multiple_chains(checkpoint_store):
    """Test handling multiple chains"""
    checkpoint1 = Checkpoint(
        chain_id="31337",
        contract_address="0x1234567890123456789012345678901234567890",
        last_processed_block=1000,
        last_processed_timestamp=datetime.now(timezone.utc),
        total_events_processed=42,
    )

    checkpoint2 = Checkpoint(
        chain_id="11155111",  # Sepolia
        contract_address="0x1234567890123456789012345678901234567890",
        last_processed_block=5000,
        last_processed_timestamp=datetime.now(timezone.utc),
        total_events_processed=100,
    )

    # Save both checkpoints
    await checkpoint_store.save_checkpoint(checkpoint1)
    await checkpoint_store.save_checkpoint(checkpoint2)

    # Retrieve each independently
    retrieved1 = await checkpoint_store.get_checkpoint("31337", checkpoint1.contract_address)
    retrieved2 = await checkpoint_store.get_checkpoint("11155111", checkpoint2.contract_address)

    assert retrieved1 is not None
    assert retrieved1.last_processed_block == 1000

    assert retrieved2 is not None
    assert retrieved2.last_processed_block == 5000
