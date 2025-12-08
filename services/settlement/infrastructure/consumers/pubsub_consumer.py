"""Pub/Sub consumer skeleton for settlement events."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import Optional

from generated.fusionprime.settlement.v1 import settlement_pb2
from google.cloud import pubsub_v1
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from infrastructure.db.escrow_repository import upsert_escrow  # type: ignore
    from infrastructure.db.models import EscrowRecord, SettlementCommandRecord  # type: ignore
    from infrastructure.db.repository import upsert_command  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional during test stubs
    SettlementCommandRecord = None  # type: ignore
    EscrowRecord = None  # type: ignore
    upsert_command = None  # type: ignore
    upsert_escrow = None  # type: ignore


class _MockSubscriber:
    def subscription_path(self, project_id: str, subscription_id: str) -> str:
        return f"projects/{project_id}/subscriptions/{subscription_id}"

    def subscribe(self, path: str, callback):  # pragma: no cover
        raise RuntimeError("Mock subscriber does not support streaming pulls")


class SettlementEventConsumer:
    """Consumes settlement events from Pub/Sub and updates command state."""

    def __init__(
        self,
        project_id: str,
        subscription_id: str,
        handler: Callable[[settlement_pb2.SettlementEvent], None],
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
        import json
        import logging

        logger = logging.getLogger(__name__)

        try:
            logger.info(
                "Received Pub/Sub message",
                extra={"message_id": message.message_id, "attributes": dict(message.attributes)},
            )

            # Check message attributes to determine event type
            # Support both event_type (new) and event_name (legacy) attributes
            event_type = message.attributes.get("event_type") or message.attributes.get(
                "event_name", ""
            )

            logger.info(
                f"Detected event_type: '{event_type}' (from attributes: {dict(message.attributes)})"
            )

            # Handle blockchain events (JSON format)
            # Note: Contract emits "Approved", "EscrowReleased", "EscrowRefunded"
            # but we also support legacy names for backwards compatibility
            if event_type in [
                "EscrowDeployed",
                "Approved",  # Actual event from contract
                "ApprovalGranted",  # Legacy name (backwards compat)
                "EscrowReleased",  # Actual event from contract
                "PaymentReleased",  # Legacy name (backwards compat)
                "EscrowRefunded",  # Actual event from contract
                "PaymentRefunded",  # Legacy name (backwards compat)
            ]:
                logger.info(f"Processing blockchain event: {event_type}")
                logger.info(
                    f"Session factory available: {self._session_factory is not None}, Event loop running: {self._loop is not None and self._loop.is_running()}"
                )
                event_data = json.loads(message.data.decode("utf-8"))

                if self._session_factory is not None:
                    coroutine = self._persist_blockchain_event(event_type, event_data)
                    if self._loop is not None and self._loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
                        future.result()
                    else:
                        asyncio.run(coroutine)
                    logger.info(f"Blockchain event {event_type} persisted successfully")

            # Handle protobuf settlement events (legacy format)
            else:
                event = settlement_pb2.SettlementEvent()
                event.ParseFromString(message.data)

                logger.info(
                    "Parsed settlement event from Pub/Sub",
                    extra={
                        "command_id": event.command_id,
                        "workflow_id": event.workflow_id,
                        "message_id": message.message_id,
                    },
                )

                if self._session_factory is not None and SettlementCommandRecord is not None:
                    logger.info("Persisting event to database")
                    coroutine = self._persist_event(event)
                    if self._loop is not None and self._loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
                        future.result()
                    else:
                        asyncio.run(coroutine)
                    logger.info("Event persisted to database successfully")

                self._handler(event)

            message.ack()
            logger.info("Message acknowledged successfully")

        except Exception as e:
            logger.error(
                f"Failed to process Pub/Sub message: {e}",
                extra={"message_id": message.message_id},
            )
            message.nack()

    def start(self) -> pubsub_v1.subscriber.futures.StreamingPullFuture:
        if isinstance(self._subscriber, _MockSubscriber):  # pragma: no cover
            raise RuntimeError("Mock subscriber does not support start(); call _callback directly")
        return self._subscriber.subscribe(self._subscription_path, callback=self._callback)

    async def _persist_event(self, event: settlement_pb2.SettlementEvent) -> None:
        if (
            self._session_factory is None
            or upsert_command is None
            or SettlementCommandRecord is None
        ):  # pragma: no cover
            return
        async with self._session_factory() as session:
            record = SettlementCommandRecord(
                command_id=event.command_id,
                workflow_id=event.workflow_id,
                account_ref="unknown",
                payer=event.payer,
                payee=event.payee,
                status=settlement_pb2.EventStatus.Name(event.status),
            )
            await upsert_command(session, record)

    async def _persist_blockchain_event(self, event_type: str, event_data: dict) -> None:
        """Persist blockchain events to appropriate database tables."""
        import logging
        from decimal import Decimal

        logger = logging.getLogger(__name__)

        if self._session_factory is None or EscrowRecord is None or upsert_escrow is None:
            logger.warning(
                f"Cannot persist blockchain event - session_factory: {self._session_factory is not None}, EscrowRecord: {EscrowRecord is not None}, upsert_escrow: {upsert_escrow is not None}"
            )
            return

        async with self._session_factory() as session:
            try:
                if event_type == "EscrowDeployed":
                    # Log raw event data for debugging
                    logger.info(f"Raw event_data keys: {list(event_data.keys())}")
                    logger.info(f"Raw event_data: {str(event_data)[:500]}")

                    # Extract escrow data from blockchain event
                    # Relayer sends fields at top level (NOT nested under "args")
                    escrow_address = event_data.get("escrow", "").lower()
                    payer = event_data.get("payer", "").lower()
                    payee = event_data.get("payee", "").lower()
                    amount = event_data.get("amount", "0")

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
                            int(event_data.get("releaseDelay"))
                            if event_data.get("releaseDelay")
                            else None
                        ),
                        approvals_required=(
                            int(event_data.get("approvalsRequired"))
                            if event_data.get("approvalsRequired")
                            else None
                        ),
                        approvals_count=0,
                        arbiter=(
                            event_data.get("arbiter", "").lower()
                            if event_data.get("arbiter")
                            else None
                        ),
                        transaction_hash=event_data.get("transaction_hash"),
                        block_number=event_data.get("block_number"),
                    )

                    await upsert_escrow(session, escrow_record)
                    logger.info(f"Escrow {escrow_address} stored in database")

                elif event_type in ["Approved", "ApprovalGranted"]:
                    # Update escrow approval count
                    # Note: For escrow contract events, the escrow address is the contract_address field
                    # (the contract that emitted the event), NOT in args
                    from infrastructure.db.escrow_repository import increment_escrow_approvals

                    escrow_address = event_data.get("contract_address", "").lower()
                    logger.info(
                        f"Processing approval for escrow {escrow_address} (from contract_address field)"
                    )
                    await increment_escrow_approvals(session, escrow_address)
                    logger.info(f"Approval count incremented for escrow {escrow_address}")

                elif event_type in ["EscrowReleased", "PaymentReleased"]:
                    # Update escrow status to released
                    # Note: For escrow contract events, the escrow address is the contract_address field
                    from infrastructure.db.escrow_repository import update_escrow_status

                    escrow_address = event_data.get("contract_address", "").lower()
                    await update_escrow_status(session, escrow_address, "released")
                    logger.info(f"Escrow {escrow_address} marked as released")

                elif event_type in ["EscrowRefunded", "PaymentRefunded"]:
                    # Update escrow status to refunded
                    # Note: For escrow contract events, the escrow address is the contract_address field
                    from infrastructure.db.escrow_repository import update_escrow_status

                    escrow_address = event_data.get("contract_address", "").lower()
                    await update_escrow_status(session, escrow_address, "refunded")
                    logger.info(f"Escrow {escrow_address} marked as refunded")

            except Exception as e:
                logger.error(f"Failed to persist blockchain event {event_type}: {e}")
                raise


def settlement_event_handler(event: settlement_pb2.SettlementEvent) -> None:
    """Process settlement events from Pub/Sub."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        logger.info(
            "Processing settlement event",
            extra={
                "command_id": event.command_id,
                "workflow_id": event.workflow_id,
                "payer": event.payer,
                "payee": event.payee,
                "status": settlement_pb2.EventStatus.Name(event.status),
            },
        )

        # TODO: Implement actual business logic for settlement processing
        # For now, just log that we received the event
        logger.info(f"Settlement event processed: {event.command_id}")

    except Exception as e:
        logger.error(f"Failed to process settlement event {event.command_id}: {e}")
        raise
