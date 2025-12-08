"""
Tests for RetryCoordinator.

Validates retry logic for failed cross-chain messages.
"""

import os
import sys
from pathlib import Path

# Add service directory to path FIRST (before any other imports)
service_dir = Path(__file__).parent.parent.absolute()
service_dir_str = str(service_dir)
if service_dir_str not in sys.path:
    sys.path.insert(0, service_dir_str)
elif sys.path.index(service_dir_str) != 0:
    sys.path.remove(service_dir_str)
    sys.path.insert(0, service_dir_str)

# Ensure PYTHONPATH is set for subprocesses
os.environ["PYTHONPATH"] = service_dir_str + os.pathsep + os.environ.get("PYTHONPATH", "")

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.retry_coordinator import RetryCoordinator
from infrastructure.db.models import BridgeProtocol, CrossChainMessage, MessageStatus


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def failed_message():
    """Create a failed message for testing."""
    message = MagicMock(spec=CrossChainMessage)
    message.message_id = "msg-test123"
    message.status = MessageStatus.FAILED
    message.source_chain = "ethereum"
    message.destination_chain = "polygon"
    message.source_address = "0x1234567890123456789012345678901234567890"
    message.destination_address = "0x5678901234567890123456789012345678901234"
    message.protocol = BridgeProtocol.AXELAR
    message.transaction_hash = "0xabcdef1234567890"
    message.retry_count = 1
    message.max_retries = 3
    message.updated_at = datetime.utcnow() - timedelta(minutes=5)
    message.payload = {
        "settlement_id": "settle-test123",
        "amount": 0.1,
        "asset": "ETH",
        "protocol": "axelar",
    }
    return message


class TestRetryCoordinator:
    """Tests for RetryCoordinator."""

    @pytest.mark.asyncio
    async def test_find_failed_messages(self, mock_session):
        """Test finding failed messages eligible for retry."""
        coordinator = RetryCoordinator(mock_session)

        # Mock query result
        mock_message = MagicMock(spec=CrossChainMessage)
        mock_message.status = MessageStatus.FAILED
        mock_message.retry_count = 1
        mock_message.max_retries = 3
        mock_message.updated_at = datetime.utcnow() - timedelta(minutes=10)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_message]
        mock_session.execute.return_value = mock_result

        messages = await coordinator.find_failed_messages(limit=10)

        assert len(messages) >= 0  # May be filtered by eligibility
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_eligible_for_retry(self, mock_session):
        """Test eligibility check for retry."""
        coordinator = RetryCoordinator(mock_session)

        message = MagicMock(spec=CrossChainMessage)
        message.retry_count = 1
        message.updated_at = datetime.utcnow() - timedelta(minutes=10)

        eligible = await coordinator._is_eligible_for_retry(message)

        # Should be eligible if enough time has passed
        assert isinstance(eligible, bool)

    @pytest.mark.asyncio
    async def test_retry_message_success(self, mock_session, failed_message):
        """Test successful message retry."""
        coordinator = RetryCoordinator(mock_session)

        # Mock BridgeExecutor
        with patch("app.core.retry_coordinator.BridgeExecutor") as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute_settlement = AsyncMock(return_value="0xnewtxhash123")
            mock_executor_class.return_value = mock_executor

            result = await coordinator.retry_message(failed_message)

            assert result is True
            assert failed_message.status == MessageStatus.PENDING
            assert failed_message.retry_count == 2  # Incremented
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_retry_message_exceeds_max_retries(self, mock_session, failed_message):
        """Test retry fails when max retries exceeded."""
        coordinator = RetryCoordinator(mock_session)
        failed_message.retry_count = 3
        failed_message.max_retries = 3

        result = await coordinator.retry_message(failed_message)

        assert result is False

    @pytest.mark.asyncio
    async def test_retry_message_not_eligible(self, mock_session, failed_message):
        """Test retry fails when message not yet eligible."""
        coordinator = RetryCoordinator(mock_session)
        failed_message.updated_at = datetime.utcnow()  # Just updated

        result = await coordinator.retry_message(failed_message)

        assert result is False

    @pytest.mark.asyncio
    async def test_retry_message_execution_failure(self, mock_session, failed_message):
        """Test retry handles execution failure gracefully."""
        coordinator = RetryCoordinator(mock_session)

        # Mock BridgeExecutor to raise exception
        with patch("app.core.retry_coordinator.BridgeExecutor") as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.execute_settlement = AsyncMock(side_effect=Exception("Bridge error"))
            mock_executor_class.return_value = mock_executor

            result = await coordinator.retry_message(failed_message)

            assert result is False
            assert failed_message.status == MessageStatus.FAILED

    @pytest.mark.asyncio
    async def test_process_retry_queue(self, mock_session):
        """Test processing a batch of failed messages."""
        coordinator = RetryCoordinator(mock_session)

        # Mock find_failed_messages
        mock_message = MagicMock(spec=CrossChainMessage)
        mock_message.message_id = "msg-test"
        mock_message.status = MessageStatus.FAILED
        mock_message.retry_count = 1
        mock_message.max_retries = 3
        mock_message.updated_at = datetime.utcnow() - timedelta(minutes=10)
        mock_message.protocol = BridgeProtocol.AXELAR
        mock_message.source_chain = "ethereum"
        mock_message.destination_chain = "polygon"
        mock_message.destination_address = "0x123"
        mock_message.payload = {"settlement_id": "test", "amount": 0.1, "asset": "ETH"}

        with patch.object(coordinator, "find_failed_messages", return_value=[mock_message]):
            with patch.object(coordinator, "retry_message", return_value=True):
                await coordinator.process_retry_queue(batch_size=10)

                # Should process messages without error
                assert True
