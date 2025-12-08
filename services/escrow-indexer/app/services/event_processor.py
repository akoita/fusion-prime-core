"""
Event Processor for Escrow Indexer.
Processes blockchain events from Pub/Sub and updates database.
"""

import json
import logging
from decimal import Decimal
from typing import Any, Dict

from infrastructure.db.models import Approval, Escrow, EscrowEvent
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EscrowEventProcessor:
    """Processes escrow-related blockchain events."""

    def __init__(self, db: Session):
        """Initialize processor with database session."""
        self.db = db

    def process_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Process an event based on its type.

        Args:
            event_type: Type of event (EscrowDeployed, Approved, etc.)
            event_data: Event data dictionary

        Returns:
            True if successfully processed, False otherwise
        """
        try:
            logger.info(f"Processing {event_type} event")

            if event_type == "EscrowDeployed":
                return self._process_escrow_deployed(event_data)
            elif event_type == "EscrowCreated":
                return self._process_escrow_created(event_data)
            elif event_type == "Approved":
                return self._process_approved(event_data)
            elif event_type == "EscrowReleased":
                return self._process_escrow_released(event_data)
            elif event_type == "EscrowRefunded":
                return self._process_escrow_refunded(event_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Error processing {event_type}: {e}", exc_info=True)
            return False

    def _process_escrow_deployed(self, data: Dict[str, Any]) -> bool:
        """Process EscrowDeployed event - creates new escrow record."""
        try:
            escrow_address = data["escrow"].lower()

            # Check if escrow already exists
            existing = self.db.query(Escrow).filter(Escrow.escrow_address == escrow_address).first()
            if existing:
                logger.info(f"Escrow {escrow_address} already exists, skipping")
                return True

            # Create new escrow record
            escrow = Escrow(
                escrow_address=escrow_address,
                payer_address=data["payer"].lower(),
                payee_address=data["payee"].lower(),
                arbiter_address=data.get("arbiter", "0x" + "0" * 40).lower(),
                amount=Decimal(data["amount"]),
                release_delay=int(data["releaseDelay"]),
                approvals_required=int(data["approvalsRequired"]),
                status="created",
                chain_id=int(data["chain_id"]),
                created_block=int(data["block_number"]),
                created_tx=data["transaction_hash"],
            )

            self.db.add(escrow)

            # Create event log
            event = EscrowEvent(
                escrow_address=escrow_address,
                event_type="EscrowDeployed",
                event_data=json.dumps(data),
                block_number=int(data["block_number"]),
                tx_hash=data["transaction_hash"],
                chain_id=int(data["chain_id"]),
            )
            self.db.add(event)

            self.db.commit()
            logger.info(f"✅ Created escrow {escrow_address}")
            return True

        except Exception as e:
            logger.error(f"Error processing EscrowDeployed: {e}", exc_info=True)
            self.db.rollback()
            return False

    def _process_escrow_created(self, data: Dict[str, Any]) -> bool:
        """Process EscrowCreated event - updates escrow with additional details."""
        try:
            escrow_address = data["contract_address"].lower()

            # Find escrow
            escrow = self.db.query(Escrow).filter(Escrow.escrow_address == escrow_address).first()
            if not escrow:
                logger.warning(f"Escrow {escrow_address} not found for EscrowCreated event")
                # Create placeholder escrow from this event
                escrow = Escrow(
                    escrow_address=escrow_address,
                    payer_address=data["payer"].lower(),
                    payee_address=data["payee"].lower(),
                    arbiter_address="0x" + "0" * 40,  # Unknown from this event
                    amount=Decimal(data["amount"]),
                    release_delay=0,  # Unknown from this event
                    approvals_required=int(data["approvals_required"]),
                    status="created",
                    chain_id=int(data["chain_id"]),
                    created_block=int(data["block_number"]),
                    created_tx=data["transaction_hash"],
                )
                self.db.add(escrow)

            # Create event log
            event = EscrowEvent(
                escrow_address=escrow_address,
                event_type="EscrowCreated",
                event_data=json.dumps(data),
                block_number=int(data["block_number"]),
                tx_hash=data["transaction_hash"],
                chain_id=int(data["chain_id"]),
            )
            self.db.add(event)

            self.db.commit()
            logger.info(f"✅ Processed EscrowCreated for {escrow_address}")
            return True

        except Exception as e:
            logger.error(f"Error processing EscrowCreated: {e}", exc_info=True)
            self.db.rollback()
            return False

    def _process_approved(self, data: Dict[str, Any]) -> bool:
        """Process Approved event - adds approval and checks if fully approved."""
        try:
            escrow_address = data["contract_address"].lower()
            approver_address = data["approver"].lower()
            tx_hash = data["transaction_hash"]

            # Check if approval already exists
            existing = self.db.query(Approval).filter(Approval.tx_hash == tx_hash).first()
            if existing:
                logger.info(f"Approval {tx_hash} already exists, skipping")
                return True

            # Add approval
            approval = Approval(
                escrow_address=escrow_address,
                approver_address=approver_address,
                block_number=int(data["block_number"]),
                tx_hash=tx_hash,
            )
            self.db.add(approval)

            # Create event log
            event = EscrowEvent(
                escrow_address=escrow_address,
                event_type="Approved",
                event_data=json.dumps(data),
                block_number=int(data["block_number"]),
                tx_hash=tx_hash,
                chain_id=int(data["chain_id"]),
            )
            self.db.add(event)

            # Check if escrow is now fully approved
            escrow = self.db.query(Escrow).filter(Escrow.escrow_address == escrow_address).first()
            if escrow:
                approval_count = (
                    self.db.query(Approval)
                    .filter(Approval.escrow_address == escrow_address)
                    .count()
                )

                if approval_count >= escrow.approvals_required and escrow.status == "created":
                    escrow.status = "approved"
                    logger.info(
                        f"🎉 Escrow {escrow_address} is now fully approved ({approval_count}/{escrow.approvals_required})"
                    )

            self.db.commit()
            logger.info(f"✅ Added approval from {approver_address} for {escrow_address}")
            return True

        except Exception as e:
            logger.error(f"Error processing Approved: {e}", exc_info=True)
            self.db.rollback()
            return False

    def _process_escrow_released(self, data: Dict[str, Any]) -> bool:
        """Process EscrowReleased event - marks escrow as released."""
        try:
            escrow_address = data["contract_address"].lower()

            # Update escrow status
            escrow = self.db.query(Escrow).filter(Escrow.escrow_address == escrow_address).first()
            if escrow:
                escrow.status = "released"
            else:
                logger.warning(f"Escrow {escrow_address} not found for EscrowReleased event")

            # Create event log
            event = EscrowEvent(
                escrow_address=escrow_address,
                event_type="EscrowReleased",
                event_data=json.dumps(data),
                block_number=int(data["block_number"]),
                tx_hash=data["transaction_hash"],
                chain_id=int(data["chain_id"]),
            )
            self.db.add(event)

            self.db.commit()
            logger.info(f"✅ Escrow {escrow_address} marked as released")
            return True

        except Exception as e:
            logger.error(f"Error processing EscrowReleased: {e}", exc_info=True)
            self.db.rollback()
            return False

    def _process_escrow_refunded(self, data: Dict[str, Any]) -> bool:
        """Process EscrowRefunded event - marks escrow as refunded."""
        try:
            escrow_address = data["contract_address"].lower()

            # Update escrow status
            escrow = self.db.query(Escrow).filter(Escrow.escrow_address == escrow_address).first()
            if escrow:
                escrow.status = "refunded"
            else:
                logger.warning(f"Escrow {escrow_address} not found for EscrowRefunded event")

            # Create event log
            event = EscrowEvent(
                escrow_address=escrow_address,
                event_type="EscrowRefunded",
                event_data=json.dumps(data),
                block_number=int(data["block_number"]),
                tx_hash=data["transaction_hash"],
                chain_id=int(data["chain_id"]),
            )
            self.db.add(event)

            self.db.commit()
            logger.info(f"✅ Escrow {escrow_address} marked as refunded")
            return True

        except Exception as e:
            logger.error(f"Error processing EscrowRefunded: {e}", exc_info=True)
            self.db.rollback()
            return False
