"""Stripe integration for payment processing."""

import logging
import os
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class StripeClient:
    """Client for Stripe API interactions."""

    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self.base_url = "https://api.stripe.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30.0,
        )

    async def create_payment_intent(
        self, amount: float, currency: str, metadata: Dict, return_url: Optional[str] = None
    ) -> Dict:
        """
        Create a Stripe Payment Intent for on-ramp.

        Args:
            amount: Amount in fiat currency
            currency: Currency code (USD, EUR, etc.)
            metadata: Additional metadata (user_id, destination_address, etc.)
            return_url: Return URL for checkout completion

        Returns:
            Payment Intent response from Stripe
        """
        if not self.api_key:
            logger.warning("Stripe API key not configured, returning mock response")
            return {
                "id": f"pi_mock_{hash(str(amount))}",
                "status": "requires_payment_method",
                "amount": int(amount * 100),
                "currency": currency.lower(),
                "client_secret": f"pi_mock_{hash(str(amount))}_secret",
            }

        try:
            # Stripe API: Create Payment Intent
            # Documentation: https://stripe.com/docs/api/payment_intents/create
            data = {
                "amount": int(amount * 100),  # Stripe uses cents
                "currency": currency.lower(),
                "automatic_payment_methods[enabled]": "true",
                "metadata[user_id]": str(metadata.get("user_id", "")),
                "metadata[destination_address]": str(metadata.get("destination_address", "")),
            }

            if return_url:
                data["return_url"] = return_url

            # Add other metadata fields
            for key, value in metadata.items():
                if key not in ["user_id", "destination_address"]:
                    data[f"metadata[{key}]"] = str(value)

            response = await self.client.post("/payment_intents", data=data)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Stripe Payment Intent created: {result.get('id')}")
            return {
                "id": result.get("id"),
                "status": result.get("status"),
                "amount": result.get("amount"),
                "currency": result.get("currency"),
                "client_secret": result.get("client_secret"),
                "payment_url": f"https://checkout.stripe.com/pay/{result.get('id')}",
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Stripe API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Stripe Payment Intent: {e}", exc_info=True)
            raise

    async def create_payout(self, amount: float, destination_account: str, metadata: Dict) -> Dict:
        """
        Create a Stripe Payout for off-ramp.

        Args:
            amount: Amount in fiat currency
            destination_account: Bank account or payment method ID (stripe account)
            metadata: Additional metadata

        Returns:
            Payout response from Stripe
        """
        if not self.api_key:
            logger.warning("Stripe API key not configured, returning mock response")
            return {
                "id": f"po_mock_{hash(str(amount))}",
                "status": "pending",
                "amount": int(amount * 100),
            }

        try:
            # Stripe API: Create Payout
            # Documentation: https://stripe.com/docs/api/payouts/create
            data = {
                "amount": int(amount * 100),  # Stripe uses cents
                "currency": metadata.get("currency", "usd").lower(),
                "destination": destination_account,
                "metadata[user_id]": str(metadata.get("user_id", "")),
                "metadata[source_address]": str(metadata.get("source_address", "")),
            }

            # Add other metadata fields
            for key, value in metadata.items():
                if key not in ["user_id", "source_address", "currency"]:
                    data[f"metadata[{key}]"] = str(value)

            response = await self.client.post("/payouts", data=data)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Stripe Payout created: {result.get('id')}")
            return {
                "id": result.get("id"),
                "status": result.get("status"),
                "amount": result.get("amount"),
                "currency": result.get("currency"),
                "arrival_date": result.get("arrival_date"),
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Stripe API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Stripe Payout: {e}", exc_info=True)
            raise

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature."""
        if not self.webhook_secret:
            logger.warning("Stripe webhook secret not configured")
            return False

        try:
            # Stripe webhook signature verification
            # Documentation: https://stripe.com/docs/webhooks/signatures
            import hashlib
            import hmac

            timestamp, signatures = signature.split(",", 1)
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                (timestamp.split("=")[1] + "." + payload.decode()).encode(),
                hashlib.sha256,
            ).hexdigest()

            # Check if any of the signatures match
            for sig_pair in signatures.split(" "):
                if "=" in sig_pair:
                    _, sig = sig_pair.split("=", 1)
                    if hmac.compare_digest(expected_signature, sig):
                        return True

            logger.warning("Stripe webhook signature verification failed")
            return False
        except Exception as e:
            logger.error(f"Failed to verify Stripe webhook signature: {e}", exc_info=True)
            return False

    async def get_payment_intent_status(self, payment_intent_id: str) -> Dict:
        """Get status of a Stripe Payment Intent."""
        if not self.api_key:
            return {"status": "unknown", "id": payment_intent_id}

        try:
            response = await self.client.get(f"/payment_intents/{payment_intent_id}")
            response.raise_for_status()
            result = response.json()
            return {
                "id": result.get("id"),
                "status": result.get("status"),
                "amount": result.get("amount"),
                "currency": result.get("currency"),
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Stripe API error: {e.response.status_code} - {e.response.text}")
            return {"status": "error", "id": payment_intent_id}
        except Exception as e:
            logger.error(f"Failed to get Stripe Payment Intent status: {e}", exc_info=True)
            return {"status": "error", "id": payment_intent_id}

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
