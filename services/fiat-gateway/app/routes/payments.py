"""Payment routes for fiat gateway."""

import logging
from typing import Optional

from app.integrations.circle import CircleClient
from app.integrations.stripe import StripeClient
from app.services.transaction_service import TransactionService
from fastapi import APIRouter, Depends, HTTPException
from infrastructure.db.models import PaymentProvider, TransactionStatus, TransactionType
from infrastructure.db.session import get_session
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


class OnRampRequest(BaseModel):
    """Request to convert fiat to stablecoin."""

    user_id: str
    amount: float
    currency: str  # USD, EUR, etc.
    destination_address: str  # Wallet address to receive stablecoin
    payment_method: str  # "circle" or "stripe"
    chain: Optional[str] = "ETH"  # Blockchain network


class OnRampResponse(BaseModel):
    """Response for on-ramp request."""

    transaction_id: str
    status: str
    payment_url: Optional[str] = None
    estimated_completion: Optional[str] = None


class OffRampRequest(BaseModel):
    """Request to convert stablecoin to fiat."""

    user_id: str
    amount: float
    stablecoin_address: str  # USDC contract address
    source_address: str  # Wallet address sending stablecoin
    destination_account: str  # Bank account or payment method
    payment_method: str  # "circle" or "stripe"
    chain: Optional[str] = "ETH"  # Blockchain network


class OffRampResponse(BaseModel):
    """Response for off-ramp request."""

    transaction_id: str
    status: str
    estimated_completion: Optional[str] = None


@router.post("/on-ramp", response_model=OnRampResponse)
async def initiate_on_ramp(request: OnRampRequest, session: AsyncSession = Depends(get_session)):
    """
    Initiate fiat to stablecoin conversion.

    Creates a payment request that user can complete via Circle or Stripe.
    """
    logger.info(
        f"On-ramp request: {request.amount} {request.currency} -> {request.destination_address}"
    )

    # Determine provider
    provider = (
        PaymentProvider.CIRCLE
        if request.payment_method.lower() == "circle"
        else PaymentProvider.STRIPE
    )

    # Create transaction record
    transaction_service = TransactionService(session)
    transaction = await transaction_service.create_transaction(
        user_id=request.user_id,
        transaction_type=TransactionType.ON_RAMP,
        amount=request.amount,
        currency=request.currency,
        provider=provider,
        destination_address=request.destination_address,
    )

    try:
        if provider == PaymentProvider.CIRCLE:
            # Circle: Mint USDC directly
            circle_client = CircleClient()
            circle_result = await circle_client.mint_usdc(
                amount=request.amount,
                destination_address=request.destination_address,
                chain=request.chain,
            )

            # Update transaction with provider info
            await transaction_service.update_transaction(
                transaction_id=transaction.transaction_id,
                provider_transaction_id=circle_result.get("id"),
                status=(
                    TransactionStatus.PROCESSING
                    if circle_result.get("status") == "pending"
                    else TransactionStatus.COMPLETED
                ),
            )

            return OnRampResponse(
                transaction_id=transaction.transaction_id,
                status="processing",
                estimated_completion="5-10 minutes",
            )
        else:
            # Stripe: Create Payment Intent
            stripe_client = StripeClient()
            stripe_result = await stripe_client.create_payment_intent(
                amount=request.amount,
                currency=request.currency,
                metadata={
                    "user_id": request.user_id,
                    "destination_address": request.destination_address,
                    "transaction_id": transaction.transaction_id,
                },
            )

            # Update transaction with provider info
            await transaction_service.update_transaction(
                transaction_id=transaction.transaction_id,
                provider_transaction_id=stripe_result.get("id"),
                provider_response=str(stripe_result),
            )

            return OnRampResponse(
                transaction_id=transaction.transaction_id,
                status="pending",
                payment_url=stripe_result.get("payment_url"),
                estimated_completion="5-10 minutes",
            )
    except Exception as e:
        logger.error(f"Failed to process on-ramp: {e}", exc_info=True)
        await transaction_service.update_transaction(
            transaction_id=transaction.transaction_id,
            status=TransactionStatus.FAILED,
        )
        raise HTTPException(status_code=500, detail=f"Failed to initiate on-ramp: {str(e)}")


@router.post("/off-ramp", response_model=OffRampResponse)
async def initiate_off_ramp(request: OffRampRequest, session: AsyncSession = Depends(get_session)):
    """
    Initiate stablecoin to fiat conversion.

    Burns stablecoin and initiates fiat withdrawal to bank account.
    """
    logger.info(f"Off-ramp request: {request.amount} from {request.source_address}")

    # Determine provider
    provider = (
        PaymentProvider.CIRCLE
        if request.payment_method.lower() == "circle"
        else PaymentProvider.STRIPE
    )

    # Create transaction record
    transaction_service = TransactionService(session)
    transaction = await transaction_service.create_transaction(
        user_id=request.user_id,
        transaction_type=TransactionType.OFF_RAMP,
        amount=request.amount,
        currency="USD",  # Assume USD for stablecoin
        provider=provider,
        source_address=request.source_address,
        destination_account=request.destination_account,
    )

    try:
        if provider == PaymentProvider.CIRCLE:
            # Circle: Burn USDC
            circle_client = CircleClient()
            circle_result = await circle_client.burn_usdc(
                amount=request.amount,
                source_address=request.source_address,
                destination_account=request.destination_account,
                chain=request.chain,
            )

            # Update transaction with provider info
            await transaction_service.update_transaction(
                transaction_id=transaction.transaction_id,
                provider_transaction_id=circle_result.get("id"),
                status=(
                    TransactionStatus.PROCESSING
                    if circle_result.get("status") == "pending"
                    else TransactionStatus.COMPLETED
                ),
            )

            return OffRampResponse(
                transaction_id=transaction.transaction_id,
                status="processing",
                estimated_completion="1-3 business days",
            )
        else:
            # Stripe: Create Payout
            stripe_client = StripeClient()
            stripe_result = await stripe_client.create_payout(
                amount=request.amount,
                destination_account=request.destination_account,
                metadata={
                    "user_id": request.user_id,
                    "source_address": request.source_address,
                    "transaction_id": transaction.transaction_id,
                    "currency": "usd",
                },
            )

            # Update transaction with provider info
            await transaction_service.update_transaction(
                transaction_id=transaction.transaction_id,
                provider_transaction_id=stripe_result.get("id"),
                provider_response=str(stripe_result),
            )

            return OffRampResponse(
                transaction_id=transaction.transaction_id,
                status="pending",
                estimated_completion="1-3 business days",
            )
    except Exception as e:
        logger.error(f"Failed to process off-ramp: {e}", exc_info=True)
        await transaction_service.update_transaction(
            transaction_id=transaction.transaction_id,
            status=TransactionStatus.FAILED,
        )
        raise HTTPException(status_code=500, detail=f"Failed to initiate off-ramp: {str(e)}")


@router.get("/status/{transaction_id}")
async def get_transaction_status(transaction_id: str, session: AsyncSession = Depends(get_session)):
    """Get status of a payment transaction."""
    transaction_service = TransactionService(session)
    transaction = await transaction_service.get_transaction(transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Optionally refresh status from provider
    if transaction.provider_transaction_id:
        try:
            if transaction.provider == PaymentProvider.CIRCLE:
                circle_client = CircleClient()
                provider_status = await circle_client.get_transaction_status(
                    transaction.provider_transaction_id
                )
                if provider_status.get("status") != transaction.status.value:
                    # Update if status changed
                    new_status = (
                        TransactionStatus.COMPLETED
                        if provider_status.get("status") == "complete"
                        else TransactionStatus.PROCESSING
                    )
                    await transaction_service.update_transaction(
                        transaction_id=transaction_id,
                        status=new_status,
                    )
                    transaction.status = new_status
            elif transaction.provider == PaymentProvider.STRIPE:
                stripe_client = StripeClient()
                provider_status = await stripe_client.get_payment_intent_status(
                    transaction.provider_transaction_id
                )
                if provider_status.get("status") != transaction.status.value:
                    # Map Stripe status to our status
                    stripe_status = provider_status.get("status")
                    if stripe_status == "succeeded":
                        new_status = TransactionStatus.COMPLETED
                    elif stripe_status in ["requires_action", "processing"]:
                        new_status = TransactionStatus.PROCESSING
                    else:
                        new_status = TransactionStatus.FAILED

                    await transaction_service.update_transaction(
                        transaction_id=transaction_id,
                        status=new_status,
                    )
                    transaction.status = new_status
        except Exception as e:
            logger.warning(f"Failed to refresh status from provider: {e}")

    return {
        "transaction_id": transaction.transaction_id,
        "status": transaction.status.value,
        "amount": float(transaction.amount),
        "currency": transaction.currency,
        "type": transaction.type.value,
        "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
        "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
    }
