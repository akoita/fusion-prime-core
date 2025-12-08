"""Circle USDC integration for fiat on/off-ramps."""

import logging
import os
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class CircleClient:
    """Client for Circle API interactions."""

    def __init__(self):
        self.api_key = os.getenv("CIRCLE_API_KEY")
        self.base_url = os.getenv("CIRCLE_BASE_URL", "https://api-sandbox.circle.com")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def mint_usdc(self, amount: float, destination_address: str, chain: str = "ETH") -> Dict:
        """
        Mint USDC via Circle API.

        Args:
            amount: Amount in USD to mint
            destination_address: Wallet address to receive USDC
            chain: Blockchain network (ETH, POLYGON, etc.)

        Returns:
            Transaction response from Circle
        """
        if not self.api_key:
            logger.warning("Circle API key not configured, returning mock response")
            return {
                "id": f"circle-mint-{hash(str(amount))}",
                "status": "pending",
                "amount": amount,
                "destination": destination_address,
            }

        try:
            # Circle API: Create a transfer (on-ramp)
            # Documentation: https://developers.circle.com/stablecoins/docs/circle-payments-api
            payload = {
                "source": {"type": "wallet", "id": os.getenv("CIRCLE_WALLET_ID")},
                "destination": {
                    "type": "blockchain",
                    "address": destination_address,
                    "chain": chain,
                },
                "amount": {"amount": str(amount), "currency": "USD"},
                "idempotencyKey": f"mint-{hash(str(amount) + destination_address)}",
            }

            response = await self.client.post("/v1/m3/transactions/transfer", json=payload)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Circle mint initiated: {result.get('id')}")
            return {
                "id": result.get("id"),
                "status": result.get("status", "pending"),
                "amount": amount,
                "destination": destination_address,
                "fee": result.get("fee", {}),
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Circle API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to mint USDC via Circle: {e}", exc_info=True)
            raise

    async def burn_usdc(
        self,
        amount: float,
        source_address: str,
        destination_account: str,
        chain: str = "ETH",
    ) -> Dict:
        """
        Burn USDC and initiate fiat withdrawal via Circle API.

        Args:
            amount: Amount of USDC to burn (in USD value)
            source_address: Wallet address sending USDC
            destination_account: Bank account or payment method ID to receive fiat
            chain: Blockchain network (ETH, POLYGON, etc.)

        Returns:
            Transaction response from Circle
        """
        if not self.api_key:
            logger.warning("Circle API key not configured, returning mock response")
            return {
                "id": f"circle-burn-{hash(str(amount))}",
                "status": "pending",
                "amount": amount,
                "source": source_address,
            }

        try:
            # Circle API: Create a transfer (off-ramp)
            # Source is blockchain address, destination is wallet/bank account
            payload = {
                "source": {
                    "type": "blockchain",
                    "address": source_address,
                    "chain": chain,
                },
                "destination": {
                    "type": "wallet",
                    "id": os.getenv("CIRCLE_WALLET_ID"),
                },
                "amount": {"amount": str(amount), "currency": "USD"},
                "idempotencyKey": f"burn-{hash(str(amount) + source_address)}",
            }

            response = await self.client.post("/v1/m3/transactions/transfer", json=payload)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Circle burn initiated: {result.get('id')}")
            return {
                "id": result.get("id"),
                "status": result.get("status", "pending"),
                "amount": amount,
                "source": source_address,
                "fee": result.get("fee", {}),
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Circle API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to burn USDC via Circle: {e}", exc_info=True)
            raise

    async def get_transaction_status(self, transaction_id: str) -> Dict:
        """Get status of a Circle transaction."""
        if not self.api_key:
            return {"status": "pending", "transaction_id": transaction_id}

        try:
            response = await self.client.get(f"/v1/m3/transactions/{transaction_id}")
            response.raise_for_status()
            result = response.json()
            return {
                "transaction_id": transaction_id,
                "status": result.get("status"),
                "amount": result.get("amount", {}).get("amount"),
                "currency": result.get("amount", {}).get("currency"),
                "created_at": result.get("createDate"),
                "updated_at": result.get("updateDate"),
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Circle API error: {e.response.status_code} - {e.response.text}")
            return {"status": "error", "transaction_id": transaction_id}
        except Exception as e:
            logger.error(f"Failed to get Circle transaction status: {e}", exc_info=True)
            return {"status": "error", "transaction_id": transaction_id}

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
