"""Axelar API client for monitoring cross-chain messages."""

import logging
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class AxelarClient:
    """Client for interacting with Axelar APIs (AxelarScan, Gateway API)."""

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or "https://api-axelarscan-4ae3bd1a8ade.herokuapp.com"
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    async def get_gmp_transaction_status(self, tx_hash: str) -> Optional[Dict]:
        """
        Get status of a GMP (General Message Passing) transaction.

        Args:
            tx_hash: Transaction hash on source chain

        Returns:
            Transaction status information or None if not found
        """
        try:
            # AxelarScan API endpoint for GMP transactions
            # Format: GET /axelar/evm/v1beta1/gmp/tx/{tx_hash}
            response = await self.client.get(f"/axelar/evm/v1beta1/gmp/tx/{tx_hash}")

            if response.status_code == 200:
                data = response.json()
                return {
                    "tx_hash": tx_hash,
                    "status": data.get("status", "unknown"),
                    "source_chain": data.get("source_chain"),
                    "destination_chain": data.get("destination_chain"),
                    "confirmed_at": data.get("confirmed_at"),
                    "delivered_at": data.get("delivered_at"),
                    "executed_at": data.get("executed_at"),
                    "gas_used": data.get("gas_used"),
                }
            elif response.status_code == 404:
                logger.debug(f"GMP transaction not found: {tx_hash}")
                return None
            else:
                logger.warning(f"Axelar API error: {response.status_code} - {response.text}")
                return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error querying Axelar: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get Axelar GMP status: {e}", exc_info=True)
            return None

    async def get_gmp_transactions_by_address(self, address: str, limit: int = 50) -> List[Dict]:
        """
        Get GMP transactions for a specific address.

        Args:
            address: Wallet or contract address
            limit: Maximum number of transactions to return

        Returns:
            List of transaction information
        """
        try:
            # Try multiple possible API endpoints for AxelarScan
            endpoints = [
                f"/axelar/evm/v1beta1/gmp/tx",
                f"/gmp/tx",
                f"/transactions",
            ]

            for endpoint in endpoints:
                try:
                    response = await self.client.get(
                        endpoint,
                        params={"address": address, "limit": limit},
                    )

                    if response.status_code == 200:
                        data = response.json()
                        # Handle different response formats
                        if isinstance(data, dict):
                            transactions = data.get(
                                "transactions", data.get("data", data.get("result", []))
                            )
                        elif isinstance(data, list):
                            transactions = data
                        else:
                            transactions = []

                        if transactions:
                            logger.debug(
                                f"Found {len(transactions)} transactions for address {address}"
                            )
                            return transactions[:limit]
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        # Endpoint doesn't exist, try next one
                        continue
                    raise
                except Exception as e:
                    logger.debug(f"Failed to query endpoint {endpoint}: {e}")
                    continue

            # If all endpoints fail, return empty list
            logger.warning(f"No transactions found for address {address} via any endpoint")
            return []

        except Exception as e:
            logger.error(f"Failed to get Axelar transactions for address: {e}", exc_info=True)
            return []

    async def get_chain_status(self, chain_name: str) -> Optional[Dict]:
        """Get status of an Axelar-connected chain."""
        try:
            response = await self.client.get(f"/chains/{chain_name}/status")

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"Failed to get chain status: {e}")

        return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
