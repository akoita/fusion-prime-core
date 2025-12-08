"""Orchestrator service for cross-chain settlement."""

import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

import httpx
from app.services.bridge_executor import BridgeExecutor
from app.services.message_service import MessageService
from app.services.vault_client import VaultClient
from infrastructure.db.models import BridgeProtocol, CollateralSnapshot, SettlementRecord
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class OrchestratorService:
    """Service for orchestrating cross-chain settlements."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.vault_client = VaultClient()
        # Price Oracle service URL (defaults to service URL from env or default)
        self.price_oracle_url = os.getenv(
            "PRICE_ORACLE_SERVICE_URL",
            os.getenv("PRICE_ORACLE_URL", "https://price-oracle-service-ggats6pubq-uc.a.run.app"),
        )

    async def initiate_settlement(
        self,
        source_chain: str,
        destination_chain: str,
        amount: float,
        asset: str,
        source_address: str,
        destination_address: str,
        preferred_protocol: Optional[str] = None,
    ) -> Dict:
        """Initiate a cross-chain settlement."""
        settlement_id = f"settle-{uuid.uuid4().hex[:16]}"

        # Determine protocol (default to Axelar if not specified)
        protocol = (
            BridgeProtocol(preferred_protocol.lower())
            if preferred_protocol
            else BridgeProtocol.AXELAR
        )

        # Create settlement record using raw SQL to properly cast enum value
        # The database column is a PostgreSQL enum type, so we need to cast the string value
        # Using raw SQL INSERT with CAST to ensure proper enum type conversion
        await self.session.execute(
            text(
                """
                INSERT INTO settlement_records
                (settlement_id, source_chain, destination_chain, amount, asset,
                 source_address, destination_address, protocol, status, message_id, completed_at)
                VALUES
                (:settlement_id, :source_chain, :destination_chain, :amount, :asset,
                 :source_address, :destination_address, CAST(:protocol AS bridgeprotocol), :status, :message_id, :completed_at)
            """
            ),
            {
                "settlement_id": settlement_id,
                "source_chain": source_chain,
                "destination_chain": destination_chain,
                "amount": amount,
                "asset": asset,
                "source_address": source_address,
                "destination_address": destination_address,
                "protocol": protocol.value,  # Use enum value ("axelar" or "ccip")
                "status": "pending",
                "message_id": None,
                "completed_at": None,
            },
        )
        await self.session.commit()

        logger.info(f"Created settlement: {settlement_id}")

        # Execute cross-chain transaction via bridge protocol
        try:
            # Encode settlement payload
            # Format: settlement_id, amount, asset, source_chain, destination_chain
            from eth_abi import encode

            # Convert amount to wei (18 decimals for ETH/WETH, 6 for USDC)
            amount_multiplier = 1e18 if asset.upper() in ["ETH", "WETH"] else 1e6
            amount_wei = int(amount * amount_multiplier)

            payload = encode(
                ["string", "uint256", "string", "string", "string"],
                [
                    settlement_id,
                    amount_wei,
                    asset,
                    source_chain,
                    destination_chain,
                ],
            )

            # Get destination address (default to source_address for now, or use vault address)
            # In production, this would be the CrossChainVault address on destination chain
            dest_address = destination_address or source_address

            # Execute bridge transaction
            executor = BridgeExecutor(source_chain=source_chain)
            tx_hash = await executor.execute_settlement(
                protocol=protocol,
                destination_chain=destination_chain,
                destination_address=dest_address,
                payload=payload,
                gas_value=1000000000000000,  # 0.001 ETH in wei
            )

            logger.info(f"Bridge transaction executed: {tx_hash}")

            # Create message record
            message_service = MessageService(self.session)
            message = await message_service.create_message(
                source_chain=source_chain,
                destination_chain=destination_chain,
                source_address=source_address,
                destination_address=dest_address,
                payload={
                    "settlement_id": settlement_id,
                    "amount": amount,
                    "asset": asset,
                    "protocol": protocol.value,
                },
                protocol=protocol,
                transaction_hash=tx_hash,
            )

            # Link settlement to message
            await self.session.execute(
                text(
                    "UPDATE settlement_records SET message_id = :message_id WHERE settlement_id = :settlement_id"
                ),
                {"message_id": message.message_id, "settlement_id": settlement_id},
            )
            await self.session.commit()

            logger.info(f"Settlement {settlement_id} linked to message {message.message_id}")

        except Exception as e:
            logger.error(f"Failed to execute bridge transaction: {e}", exc_info=True)
            # Rollback the failed transaction first
            try:
                await self.session.rollback()
            except:
                pass  # Ignore rollback errors

            # Start a new transaction to update settlement status
            try:
                await self.session.execute(
                    text(
                        "UPDATE settlement_records SET status = 'failed' WHERE settlement_id = :settlement_id"
                    ),
                    {"settlement_id": settlement_id},
                )
                await self.session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update settlement status: {update_error}", exc_info=True)
                await self.session.rollback()

            raise

        return {
            "settlement_id": settlement_id,
            "status": "pending",
            "protocol": protocol.value,
            "transaction_hash": tx_hash,
            "message_id": message.message_id,
            "estimated_completion": "5-10 minutes",
        }

    async def get_settlement_status(self, settlement_id: str) -> Dict:
        """Get settlement status."""
        result = await self.session.execute(
            select(SettlementRecord).where(SettlementRecord.settlement_id == settlement_id)
        )
        settlement = result.scalar_one_or_none()

        if not settlement:
            return {"error": "Settlement not found"}

        return {
            "settlement_id": settlement.settlement_id,
            "status": settlement.status,
            "source_chain": settlement.source_chain,
            "destination_chain": settlement.destination_chain,
            "amount": float(settlement.amount),
            "asset": settlement.asset,
            "protocol": str(settlement.protocol),  # Protocol is stored as string
            "message_id": settlement.message_id,
            "completed_at": (
                settlement.completed_at.isoformat() if settlement.completed_at else None
            ),
            "created_at": settlement.created_at.isoformat() if settlement.created_at else None,
            "updated_at": settlement.updated_at.isoformat() if settlement.updated_at else None,
        }

    async def get_collateral_snapshot(self, user_id: str) -> Dict:
        """
        Get aggregated collateral snapshot across all chains.

        Queries CrossChainVault contracts on each deployed chain and aggregates
        collateral amounts, converting to USD using the Price Oracle service.
        """
        snapshot_id = f"snapshot-{uuid.uuid4().hex[:16]}"

        # Assume user_id is an Ethereum address (could be enhanced to support other formats)
        user_address = user_id
        if not user_address.startswith("0x"):
            # If not an address, assume it's a user ID and we'd need a mapping
            # For now, return empty snapshot
            logger.warning(f"User ID {user_id} doesn't appear to be an Ethereum address")
            return {
                "user_id": user_id,
                "total_collateral_usd": 0.0,
                "chains": {},
                "snapshot_id": snapshot_id,
                "error": "User ID must be an Ethereum address",
            }

        # Query collateral from all available chains
        collateral_by_chain = self.vault_client.get_collateral_all_chains(user_address)

        # Get ETH price in USD (assumes collateral is in ETH/wei)
        eth_price_usd = await self._get_eth_price_usd()

        # Aggregate collateral and convert to USD
        total_collateral_wei = sum(collateral_by_chain.values())
        total_collateral_eth = total_collateral_wei / Decimal(10**18)
        total_collateral_usd = float(total_collateral_eth * eth_price_usd)

        # Build chains data with amounts in ETH and USD
        chains_data = {}
        for chain_name, collateral_wei in collateral_by_chain.items():
            collateral_eth = collateral_wei / Decimal(10**18)
            collateral_usd = float(collateral_eth * eth_price_usd)
            chains_data[chain_name] = {
                "collateral_wei": str(collateral_wei),
                "collateral_eth": float(collateral_eth),
                "collateral_usd": collateral_usd,
            }

        # Store snapshot in database
        snapshot = CollateralSnapshot(
            snapshot_id=snapshot_id,
            user_id=user_id,
            total_collateral_usd=total_collateral_usd,
            chains_data=chains_data,
        )

        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)

        return {
            "user_id": user_id,
            "total_collateral_usd": total_collateral_usd,
            "total_collateral_eth": float(total_collateral_eth),
            "total_collateral_wei": str(total_collateral_wei),
            "chains": chains_data,
            "snapshot_id": snapshot_id,
            "eth_price_usd": float(eth_price_usd),
            "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        }

    async def _get_eth_price_usd(self) -> Decimal:
        """
        Get ETH price in USD from Price Oracle service.

        Returns:
            ETH price in USD as Decimal

        Raises:
            Exception: If price fetch fails
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.price_oracle_url}/api/v1/prices/ETH")
                response.raise_for_status()
                data = response.json()
                return Decimal(str(data["price_usd"]))
        except Exception as e:
            logger.error(f"Failed to fetch ETH price from Price Oracle: {e}")
            # Fallback to a default price (could use cached value or Chainlink directly)
            logger.warning("Using fallback ETH price: $2000")
            return Decimal("2000.0")
