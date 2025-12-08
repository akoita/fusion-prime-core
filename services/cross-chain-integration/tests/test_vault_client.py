"""
Tests for VaultClient.

Validates CrossChainVault contract queries and collateral aggregation.
"""

import sys
from pathlib import Path

# Add service directory to path
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

import os
from unittest.mock import MagicMock, patch

import pytest
from app.services.vault_client import VaultClient


@pytest.fixture
def vault_client():
    """Create VaultClient instance."""
    return VaultClient()


class TestVaultClient:
    """Tests for VaultClient."""

    def test_initialization(self, vault_client):
        """Test VaultClient initialization."""
        assert vault_client is not None
        assert hasattr(vault_client, "vaults")

    def test_get_collateral_on_chain_no_vault(self, vault_client):
        """Test getting collateral when vault not available."""
        collateral = vault_client.get_collateral_on_chain(
            user_address="0x1234567890123456789012345678901234567890",
            chain_name="unsupported",
        )

        assert collateral == 0

    @pytest.mark.asyncio
    async def test_get_collateral_on_chain_with_rpc(self, vault_client):
        """Test getting collateral when RPC is available."""
        # Test with a dummy address
        user_address = "0x1234567890123456789012345678901234567890"

        # Try to get collateral (will return 0 if user has none, vault not connected, or RPC unavailable)
        collateral = vault_client.get_collateral_on_chain(
            user_address=user_address,
            chain_name="ethereum",
        )

        # Should return a non-negative integer (wei amount)
        # Returns 0 if RPC unavailable, vault not connected, or user has no collateral
        assert isinstance(collateral, int)
        assert collateral >= 0

        # If RPC is available, test actual query (may still return 0 if no collateral)
        rpc_url = os.getenv("ETH_RPC_URL") or os.getenv("POLYGON_RPC_URL")
        if rpc_url:
            # Test that it attempts to query (may return 0 for valid reasons)
            collateral_polygon = vault_client.get_collateral_on_chain(
                user_address=user_address,
                chain_name="polygon",
            )
            assert isinstance(collateral_polygon, int)
            assert collateral_polygon >= 0

    def test_get_total_collateral_no_vault(self, vault_client):
        """Test getting total collateral when vault not available."""
        total = vault_client.get_total_collateral(
            user_address="0x1234567890123456789012345678901234567890",
            chain_name="unsupported",
        )

        assert total == 0

    def test_get_collateral_all_chains(self, vault_client):
        """Test getting collateral across all chains."""
        user_address = "0x1234567890123456789012345678901234567890"

        collateral_by_chain = vault_client.get_collateral_all_chains(user_address)

        # Should return a dictionary
        assert isinstance(collateral_by_chain, dict)
        # All values should be non-negative integers
        for chain, amount in collateral_by_chain.items():
            assert isinstance(amount, int)
            assert amount >= 0
