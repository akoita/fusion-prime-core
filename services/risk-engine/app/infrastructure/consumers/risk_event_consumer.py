"""Pub/Sub consumer for Risk Engine escrow events."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Callable
from decimal import Decimal
from typing import Optional

from google.cloud import pubsub_v1
from sqlalchemy.ext.asyncio import AsyncSession

# Import models from shared infrastructure directory
try:
    from infrastructure.db.models import EscrowRecord
except ImportError:
    EscrowRecord = None  # Fallback for testing

logger = logging.getLogger(__name__)

# Repository functions will be imported from escrow_repository
try:
    from app.infrastructure.db.escrow_repository import (
        increment_escrow_approvals,
        update_escrow_status,
        upsert_escrow,
    )
except ModuleNotFoundError:
    # Stubs for testing
    upsert_escrow = None
    increment_escrow_approvals = None
    update_escrow_status = None


class _MockSubscriber:
    def subscription_path(self, project_id: str, subscription_id: str) -> str:
        return f"projects/{project_id}/subscriptions/{subscription_id}"

    def subscribe(self, path: str, callback):  # pragma: no cover
        raise RuntimeError("Mock subscriber does not support streaming pulls")


class RiskEventConsumer:
    """Consumes escrow events from Pub/Sub and syncs to risk_db."""

    def __init__(
        self,
        project_id: str,
        subscription_id: str,
        handler: Callable[[dict], None],
        session_factory: Optional[Callable[[], AsyncSession]] = None,
        subscriber: Optional[pubsub_v1.SubscriberClient] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        mode = os.getenv("FUSION_PRIME_PUBSUB_TEST_MODE", "").lower()
        if subscriber is not None:
            self._subscriber = subscriber
        elif mode == "mock":
            self._subscriber = _MockSubscriber()
        else:
            self._subscriber = pubsub_v1.SubscriberClient()

        self._subscription_path = self._subscriber.subscription_path(project_id, subscription_id)
        self._handler = handler
        self._session_factory = session_factory
        self._loop = loop

    def _callback(self, message: pubsub_v1.subscriber.message.Message) -> None:
        """Process incoming Pub/Sub messages."""
        try:
            logger.info(
                "Received Pub/Sub message",
                extra={"message_id": message.message_id, "attributes": dict(message.attributes)},
            )

            # Check message attributes to determine event type
            event_type = message.attributes.get("event_type") or message.attributes.get(
                "event_name", ""
            )

            logger.info(f"Risk Engine processing event: {event_type}")

            # Handle blockchain events (JSON format)
            if event_type in [
                "EscrowDeployed",
                "Approved",
                "ApprovalGranted",  # Legacy name
                "EscrowReleased",
                "PaymentReleased",  # Legacy name
                "EscrowRefunded",
                "PaymentRefunded",  # Legacy name
            ]:
                logger.info(f"Processing blockchain event for risk_db: {event_type}")
                event_data = json.loads(message.data.decode("utf-8"))

                if self._session_factory is not None:
                    coroutine = self._persist_escrow_event(event_type, event_data)
                    if self._loop is not None and self._loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
                        future.result()
                    else:
                        asyncio.run(coroutine)
                    logger.info(f"Escrow event {event_type} synced to risk_db")

                # Call handler for additional processing (risk calculations, etc.)
                self._handler(event_data)

            message.ack()
            logger.info("Message acknowledged successfully")

        except Exception as e:
            logger.error(
                f"Failed to process Pub/Sub message: {e}",
                extra={"message_id": message.message_id},
            )
            message.nack()

    def start(self) -> pubsub_v1.subscriber.futures.StreamingPullFuture:
        """Start the subscriber."""
        if isinstance(self._subscriber, _MockSubscriber):  # pragma: no cover
            raise RuntimeError("Mock subscriber does not support start(); call _callback directly")
        return self._subscriber.subscribe(self._subscription_path, callback=self._callback)

    async def _persist_escrow_event(self, event_type: str, event_data: dict) -> None:
        """Persist blockchain events to risk_db escrows table."""
        if self._session_factory is None or EscrowRecord is None or upsert_escrow is None:
            logger.warning("Cannot persist escrow event - dependencies not available")
            return

        async with self._session_factory() as session:
            try:
                if event_type == "EscrowDeployed":
                    # Extract escrow data from blockchain event
                    args = event_data.get("args", {})
                    escrow_address = args.get("escrow", "").lower()
                    payer = args.get("payer", "").lower()
                    payee = args.get("payee", "").lower()
                    amount = args.get("amount", "0")

                    # Convert Wei to ETH for amount_numeric
                    try:
                        amount_numeric = Decimal(str(amount)) / Decimal("1000000000000000000")
                    except:
                        amount_numeric = Decimal("0")

                    escrow_record = EscrowRecord(
                        address=escrow_address,
                        payer=payer,
                        payee=payee,
                        amount=str(amount),
                        amount_numeric=amount_numeric,
                        asset_symbol="ETH",
                        chain_id=int(event_data.get("chain_id", 0)),
                        status="created",
                        release_delay=(
                            int(args.get("releaseDelay")) if args.get("releaseDelay") else None
                        ),
                        approvals_required=(
                            int(args.get("approvalsRequired"))
                            if args.get("approvalsRequired")
                            else None
                        ),
                        approvals_count=0,
                        arbiter=(args.get("arbiter", "").lower() if args.get("arbiter") else None),
                        transaction_hash=event_data.get("transaction_hash"),
                        block_number=event_data.get("block_number"),
                    )

                    await upsert_escrow(session, escrow_record)
                    logger.info(f"Escrow {escrow_address} synced to risk_db")

                elif event_type in ["Approved", "ApprovalGranted"]:
                    # Update escrow approval count
                    escrow_address = event_data.get("contract_address", "").lower()
                    logger.info(f"Incrementing approval count for escrow {escrow_address}")
                    await increment_escrow_approvals(session, escrow_address)

                elif event_type in ["EscrowReleased", "PaymentReleased"]:
                    # Update escrow status to released
                    escrow_address = event_data.get("contract_address", "").lower()
                    await update_escrow_status(session, escrow_address, "released")
                    logger.info(f"Escrow {escrow_address} marked as released in risk_db")

                elif event_type in ["EscrowRefunded", "PaymentRefunded"]:
                    # Update escrow status to refunded
                    escrow_address = event_data.get("contract_address", "").lower()
                    await update_escrow_status(session, escrow_address, "refunded")
                    logger.info(f"Escrow {escrow_address} marked as refunded in risk_db")

            except Exception as e:
                logger.error(
                    f"Failed to persist escrow event {event_type}: {e}",
                    exc_info=True,  # Include full traceback
                    extra={"event_type": event_type, "event_data": event_data},
                )
                raise


def escrow_event_handler(event_data: dict) -> None:
    """
    Handle escrow events for risk calculations.

    This is called after the event has been persisted to risk_db.
    Triggers risk recalculations and margin health checks for affected users.
    """
    event_type = event_data.get("event", "unknown")
    args = event_data.get("args", {})

    logger.info(
        "Processing escrow event for risk analysis",
        extra={
            "event_type": event_type,
            "escrow_address": args.get("escrow"),
            "payer": args.get("payer"),
            "payee": args.get("payee"),
        },
    )

    # Extract affected users from event
    affected_users = []

    if event_type == "EscrowDeployed":
        # New escrow affects both payer and payee
        payer = args.get("payer", "").lower()
        payee = args.get("payee", "").lower()
        if payer:
            affected_users.append(payer)
        if payee:
            affected_users.append(payee)
        logger.info(f"New escrow deployed - will recalculate risk for payer={payer}, payee={payee}")

    elif event_type in ["EscrowReleased", "PaymentReleased"]:
        # Released escrow affects payee (receives funds) and payer (freed up exposure)
        payer = event_data.get("payer", "").lower()  # From escrow record
        payee = event_data.get("payee", "").lower()
        if payer:
            affected_users.append(payer)
        if payee:
            affected_users.append(payee)
        logger.info(f"Escrow released - will recalculate risk for payer={payer}, payee={payee}")

    elif event_type in ["EscrowRefunded", "PaymentRefunded"]:
        # Refunded escrow affects payer (receives funds back)
        payer = event_data.get("payer", "").lower()
        if payer:
            affected_users.append(payer)
        logger.info(f"Escrow refunded - will recalculate risk for payer={payer}")

    # Log what risk recalculations would be triggered
    # In production, this would actually call the risk calculator
    if affected_users:
        logger.info(
            f"Risk recalculation triggered for {len(affected_users)} user(s)",
            extra={
                "affected_users": affected_users,
                "event_type": event_type,
                "trigger_reason": "escrow_state_change",
            },
        )

        # TODO: Implement actual risk recalculation
        # This requires access to the risk_calculator instance
        # Options:
        # 1. Pass risk_calculator as parameter to consumer
        # 2. Use a separate async task queue (Celery, Cloud Tasks)
        # 3. Publish to another Pub/Sub topic for risk recalculation worker
        #
        # Example implementation:
        # for user_id in affected_users:
        #     await risk_calculator.calculate_portfolio_risk_by_user(user_id)
        #     await risk_calculator.calculate_user_margin_health(
        #         user_id=user_id,
        #         collateral_positions=get_user_collateral(user_id),
        #         borrow_positions=get_user_borrows(user_id)
        #     )
    else:
        logger.warning(f"No affected users identified for event {event_type}")
