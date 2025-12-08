"""
Tests for OrchestratorService collateral snapshot functionality.

Validates collateral aggregation across chains and USD conversion.
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

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.orchestrator_service import OrchestratorService
from infrastructure.db.models import CollateralSnapshot


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def orchestrator_service(mock_session):
    """Create OrchestratorService instance."""
    return OrchestratorService(mock_session)


class TestOrchestratorCollateral:
    """Tests for collateral snapshot functionality."""

    @pytest.mark.asyncio
    async def test_get_collateral_snapshot_invalid_user_id(self, orchestrator_service):
        """Test getting collateral snapshot with invalid user ID."""
        result = await orchestrator_service.get_collateral_snapshot(user_id="invalid")

        assert result["total_collateral_usd"] == 0.0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_collateral_snapshot_valid_address(self, orchestrator_service, mock_session):
        """Test getting collateral snapshot with valid Ethereum address."""
        user_address = "0x1234567890123456789012345678901234567890"

        # Mock VaultClient
        with patch.object(
            orchestrator_service.vault_client, "get_collateral_all_chains"
        ) as mock_get:
            mock_get.return_value = {
                "ethereum": 1000000000000000000,  # 1 ETH in wei
                "polygon": 500000000000000000,  # 0.5 ETH in wei
            }

            # Mock price oracle
            with patch.object(
                orchestrator_service, "_get_eth_price_usd", return_value=Decimal("2000")
            ):
                result = await orchestrator_service.get_collateral_snapshot(user_id=user_address)

                assert result["user_id"] == user_address
                assert result["total_collateral_usd"] > 0
                assert "chains" in result
                assert "ethereum" in result["chains"]
                assert "polygon" in result["chains"]
                assert result["chains"]["ethereum"]["collateral_eth"] == 1.0
                assert result["chains"]["polygon"]["collateral_eth"] == 0.5
                mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collateral_snapshot_no_collateral(self, orchestrator_service, mock_session):
        """Test getting collateral snapshot when user has no collateral."""
        user_address = "0x1234567890123456789012345678901234567890"

        # Mock VaultClient to return zero collateral
        with patch.object(
            orchestrator_service.vault_client, "get_collateral_all_chains"
        ) as mock_get:
            mock_get.return_value = {
                "ethereum": 0,
                "polygon": 0,
            }

            # Mock price oracle
            with patch.object(
                orchestrator_service, "_get_eth_price_usd", return_value=Decimal("2000")
            ):
                result = await orchestrator_service.get_collateral_snapshot(user_id=user_address)

                assert result["total_collateral_usd"] == 0.0
                assert result["total_collateral_eth"] == 0.0

    @pytest.mark.asyncio
    async def test_get_eth_price_usd_success(self, orchestrator_service):
        """Test getting ETH price from Price Oracle service."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"price_usd": "2500.50"}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            price = await orchestrator_service._get_eth_price_usd()

            assert price == Decimal("2500.50")

    @pytest.mark.asyncio
    async def test_get_eth_price_usd_fallback(self, orchestrator_service):
        """Test ETH price fallback when Price Oracle fails."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=Exception("Connection error"))
            mock_client_class.return_value = mock_client

            price = await orchestrator_service._get_eth_price_usd()

            # Should fallback to default price
            assert price == Decimal("2000.0")
