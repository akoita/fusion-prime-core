"""
Identity Service - Business logic for identity and claim management.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from infrastructure.blockchain.web3_client import Web3Client
from web3 import Web3

logger = logging.getLogger(__name__)


class IdentityService:
    """Service for managing identities and claims."""

    # Claim topic constants
    KYC_VERIFIED = 1
    AML_CLEARED = 2
    ACCREDITED_INVESTOR = 3
    SANCTIONS_CLEARED = 4
    COUNTRY_ALLOWED = 5

    def __init__(self, web3_client: Web3Client):
        """
        Initialize identity service.

        Args:
            web3_client: Web3 client for blockchain interactions
        """
        self.web3_client = web3_client
        self.logger = logging.getLogger(__name__)

    async def create_identity_for_user(self, user_id: str, wallet_address: str) -> Dict[str, Any]:
        """
        Create a new identity for a user.

        Args:
            user_id: Internal user ID
            wallet_address: User's wallet address

        Returns:
            Dict with identity creation details
        """
        try:
            self.logger.info(f"Creating identity for user {user_id}, wallet {wallet_address}")

            # Validate address
            if not Web3.is_address(wallet_address):
                raise ValueError(f"Invalid wallet address: {wallet_address}")

            # Create identity on blockchain
            result = await self.web3_client.create_identity(wallet_address)

            return {
                "user_id": user_id,
                "wallet_address": wallet_address,
                "identity_address": result["identity_address"],
                "tx_hash": result["tx_hash"],
                "already_exists": result.get("already_exists", False),
                "block_number": result.get("block_number"),
                "created_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error creating identity for user {user_id}: {e}")
            raise

    async def issue_kyc_claim(
        self,
        user_id: str,
        wallet_address: str,
        kyc_case_id: str,
        kyc_inquiry_id: str,
    ) -> Dict[str, Any]:
        """
        Issue KYC verification claim to a user's identity.

        Args:
            user_id: Internal user ID
            wallet_address: User's wallet address
            kyc_case_id: KYC case ID from Compliance Service
            kyc_inquiry_id: Persona inquiry ID

        Returns:
            Dict with claim issuance details
        """
        try:
            self.logger.info(f"Issuing KYC claim for user {user_id}")

            # Get identity address
            identity_address = self.web3_client.get_identity(wallet_address)
            if not identity_address:
                raise ValueError(f"No identity found for wallet {wallet_address}")

            # Prepare claim data
            claim_data = Web3.keccak(
                text=f"KYC_VERIFIED:{user_id}:{kyc_inquiry_id}:{datetime.utcnow().isoformat()}"
            )

            # Issue claim on blockchain
            result = await self.web3_client.issue_claim(
                identity_address=identity_address,
                topic=self.KYC_VERIFIED,
                data=claim_data,
                uri=f"fusion-prime://kyc/{kyc_case_id}",
            )

            return {
                "user_id": user_id,
                "wallet_address": wallet_address,
                "identity_address": identity_address,
                "claim_topic": self.KYC_VERIFIED,
                "claim_topic_name": "KYC_VERIFIED",
                "claim_id": result["claim_id"],
                "tx_hash": result["tx_hash"],
                "block_number": result["block_number"],
                "kyc_case_id": kyc_case_id,
                "kyc_inquiry_id": kyc_inquiry_id,
                "issued_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error issuing KYC claim for user {user_id}: {e}")
            raise

    async def issue_aml_claim(
        self, user_id: str, wallet_address: str, aml_check_id: str
    ) -> Dict[str, Any]:
        """
        Issue AML cleared claim to a user's identity.

        Args:
            user_id: Internal user ID
            wallet_address: User's wallet address
            aml_check_id: AML check ID from Compliance Service

        Returns:
            Dict with claim issuance details
        """
        try:
            self.logger.info(f"Issuing AML claim for user {user_id}")

            identity_address = self.web3_client.get_identity(wallet_address)
            if not identity_address:
                raise ValueError(f"No identity found for wallet {wallet_address}")

            # Prepare claim data
            claim_data = Web3.keccak(
                text=f"AML_CLEARED:{user_id}:{aml_check_id}:{datetime.utcnow().isoformat()}"
            )

            # Issue claim on blockchain
            result = await self.web3_client.issue_claim(
                identity_address=identity_address,
                topic=self.AML_CLEARED,
                data=claim_data,
                uri=f"fusion-prime://aml/{aml_check_id}",
            )

            return {
                "user_id": user_id,
                "wallet_address": wallet_address,
                "identity_address": identity_address,
                "claim_topic": self.AML_CLEARED,
                "claim_topic_name": "AML_CLEARED",
                "claim_id": result["claim_id"],
                "tx_hash": result["tx_hash"],
                "block_number": result["block_number"],
                "aml_check_id": aml_check_id,
                "issued_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error issuing AML claim for user {user_id}: {e}")
            raise

    async def get_user_identity(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """
        Get identity information for a user.

        Args:
            wallet_address: User's wallet address

        Returns:
            Dict with identity info or None
        """
        try:
            identity_address = self.web3_client.get_identity(wallet_address)

            if not identity_address:
                return None

            return {
                "wallet_address": wallet_address,
                "identity_address": identity_address,
                "has_identity": True,
            }

        except Exception as e:
            self.logger.error(f"Error getting identity for {wallet_address}: {e}")
            return None

    def get_claim_topic_name(self, topic: int) -> str:
        """Get human-readable name for claim topic."""
        topic_names = {
            self.KYC_VERIFIED: "KYC_VERIFIED",
            self.AML_CLEARED: "AML_CLEARED",
            self.ACCREDITED_INVESTOR: "ACCREDITED_INVESTOR",
            self.SANCTIONS_CLEARED: "SANCTIONS_CLEARED",
            self.COUNTRY_ALLOWED: "COUNTRY_ALLOWED",
        }
        return topic_names.get(topic, f"UNKNOWN_{topic}")
