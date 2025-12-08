"""
Client for Compliance Service integration.
"""

import logging
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)


class ComplianceClient:
    """Client for interacting with Compliance Service."""

    def __init__(self, base_url: str):
        """
        Initialize Compliance client.

        Args:
            base_url: Base URL of Compliance Service
        """
        self.base_url = base_url.rstrip("/")
        self.logger = logging.getLogger(__name__)

    async def update_kyc_claim(self, case_id: str, claim_id: str, claim_tx_hash: str) -> Dict[str, Any]:
        """
        Update KYC case with identity claim information.

        Args:
            case_id: KYC case ID
            claim_id: On-chain claim ID
            claim_tx_hash: Blockchain transaction hash

        Returns:
            Updated KYC case data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/compliance/kyc/{case_id}/claim",
                    json={"case_id": case_id, "claim_id": claim_id, "claim_tx_hash": claim_tx_hash},
                    timeout=30.0,
                )

                response.raise_for_status()
                result = response.json()

                self.logger.info(f"Updated KYC case {case_id} with claim {claim_id}")
                return result

        except httpx.HTTPError as e:
            self.logger.error(f"Error updating KYC case {case_id}: {e}")
            raise

    async def get_kyc_status(self, case_id: str) -> Dict[str, Any]:
        """
        Get KYC case status from Compliance Service.

        Args:
            case_id: KYC case ID

        Returns:
            KYC case data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/compliance/kyc/{case_id}", timeout=30.0
                )

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            self.logger.error(f"Error getting KYC status for {case_id}: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Compliance Service health.

        Returns:
            Health status
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=10.0)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            self.logger.error(f"Compliance Service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
