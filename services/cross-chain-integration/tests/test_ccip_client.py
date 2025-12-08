"""
Tests for CCIPClient.

Validates CCIP message status checking via Web3 contract queries.
"""

import sys
from pathlib import Path

# Add service directory to path
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.integrations.ccip_client import CCIPClient


@pytest.fixture
def ccip_client():
    """Create CCIP client instance."""
    return CCIPClient()


class TestCCIPClient:
    """Tests for CCIPClient."""

    @pytest.mark.asyncio
    async def test_get_ccip_chain_selector(self, ccip_client):
        """Test getting chain selector for known chains."""
        # Test Sepolia
        selector = await ccip_client.get_ccip_chain_selector("sepolia")
        assert selector == 16015286601757825753

        # Test Amoy
        selector = await ccip_client.get_ccip_chain_selector("amoy")
        assert selector == 16281711391670634445  # Updated correct value

        # Test unknown chain
        selector = await ccip_client.get_ccip_chain_selector("unknown")
        assert selector is None

    @pytest.mark.asyncio
    async def test_get_message_status_with_rpc(self, ccip_client):
        """Test getting message status via Web3 contract query."""
        # Only run if RPC URL is available, otherwise mock the test
        rpc_url = os.getenv("POLYGON_RPC_URL") or os.getenv("ETH_RPC_URL")
        if not rpc_url:
            # Test that it handles missing RPC gracefully
            status = await ccip_client.get_message_status(
                message_id="0x" + "0" * 64,
                source_chain="ethereum",
                destination_chain="polygon",
            )
            assert status is None  # Should return None when RPC unavailable
            return

        # Test with a dummy message ID (will likely return None as message doesn't exist)
        message_id = "0x" + "0" * 64  # Dummy message ID

        status = await ccip_client.get_message_status(
            message_id=message_id,
            source_chain="ethereum",
            destination_chain="polygon",
        )

        # Status might be None if message doesn't exist, or dict if Router supports query
        assert status is None or isinstance(status, dict)

    @pytest.mark.asyncio
    async def test_get_message_status_no_rpc(self, ccip_client):
        """Test getting message status when RPC is unavailable."""
        with patch.dict(os.environ, {}, clear=True):
            status = await ccip_client.get_message_status(
                message_id="0x123",
                source_chain="ethereum",
                destination_chain="polygon",
            )

            assert status is None

    @pytest.mark.asyncio
    async def test_get_message_status_invalid_chain(self, ccip_client):
        """Test getting message status for unsupported chain."""
        status = await ccip_client.get_message_status(
            message_id="0x123",
            source_chain="ethereum",
            destination_chain="unsupported",
        )

        assert status is None

    @pytest.mark.asyncio
    async def test_close(self, ccip_client):
        """Test closing HTTP client."""
        await ccip_client.close()
        # Should not raise exception
        assert True
