"""
REST API routes for querying escrow data.
"""

import logging
from typing import List, Optional

from flask import Blueprint, jsonify, request
from infrastructure.db import Approval, Escrow, EscrowEvent, get_db_session
from sqlalchemy import or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Create blueprint
escrows_bp = Blueprint("escrows", __name__, url_prefix="/api/v1/escrows")


def _escrow_to_dict(escrow: Escrow, include_approvals: bool = False) -> dict:
    """Convert Escrow model to dictionary."""
    result = {
        "escrow_address": escrow.escrow_address,
        "payer_address": escrow.payer_address,
        "payee_address": escrow.payee_address,
        "arbiter_address": escrow.arbiter_address,
        "amount": str(escrow.amount),  # Convert to string to avoid precision issues
        "release_delay": escrow.release_delay,
        "approvals_required": escrow.approvals_required,
        "status": escrow.status,
        "chain_id": escrow.chain_id,
        "created_block": escrow.created_block,
        "created_tx": escrow.created_tx,
        "created_at": escrow.created_at.isoformat(),
        "updated_at": escrow.updated_at.isoformat(),
    }

    if include_approvals:
        result["approvals"] = [
            {
                "approver_address": approval.approver_address,
                "block_number": approval.block_number,
                "tx_hash": approval.tx_hash,
                "created_at": approval.created_at.isoformat(),
            }
            for approval in escrow.approvals
        ]
        result["approvals_count"] = len(escrow.approvals)

    return result


@escrows_bp.route("/by-payer/<address>", methods=["GET"])
def get_escrows_by_payer(address: str):
    """
    Get all escrows where the address is the payer.

    Query params:
        - status: Filter by status (created, approved, released, refunded)
    """
    try:
        address = address.lower()
        status = request.args.get("status")

        with get_db_session() as db:
            query = db.query(Escrow).filter(Escrow.payer_address == address)

            if status:
                query = query.filter(Escrow.status == status)

            escrows = query.order_by(Escrow.created_block.desc()).all()

            return (
                jsonify(
                    {
                        "success": True,
                        "count": len(escrows),
                        "escrows": [_escrow_to_dict(e) for e in escrows],
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Error getting escrows by payer: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@escrows_bp.route("/by-payee/<address>", methods=["GET"])
def get_escrows_by_payee(address: str):
    """
    Get all escrows where the address is the payee.

    Query params:
        - status: Filter by status (created, approved, released, refunded)
    """
    try:
        address = address.lower()
        status = request.args.get("status")

        with get_db_session() as db:
            query = db.query(Escrow).filter(Escrow.payee_address == address)

            if status:
                query = query.filter(Escrow.status == status)

            escrows = query.order_by(Escrow.created_block.desc()).all()

            return (
                jsonify(
                    {
                        "success": True,
                        "count": len(escrows),
                        "escrows": [_escrow_to_dict(e) for e in escrows],
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Error getting escrows by payee: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@escrows_bp.route("/by-arbiter/<address>", methods=["GET"])
def get_escrows_by_arbiter(address: str):
    """
    Get all escrows where the address is the arbiter.

    Query params:
        - status: Filter by status (created, approved, released, refunded)
    """
    try:
        address = address.lower()
        status = request.args.get("status")

        with get_db_session() as db:
            query = db.query(Escrow).filter(Escrow.arbiter_address == address)

            if status:
                query = query.filter(Escrow.status == status)

            escrows = query.order_by(Escrow.created_block.desc()).all()

            return (
                jsonify(
                    {
                        "success": True,
                        "count": len(escrows),
                        "escrows": [_escrow_to_dict(e) for e in escrows],
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Error getting escrows by arbiter: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@escrows_bp.route("/by-role/<address>", methods=["GET"])
def get_escrows_by_role(address: str):
    """
    Get all escrows where the address is involved in any role.

    Returns escrows grouped by role.

    Query params:
        - status: Filter by status (created, approved, released, refunded)
    """
    try:
        address = address.lower()
        status = request.args.get("status")

        with get_db_session() as db:
            # Query escrows where address is payer, payee, or arbiter
            query = db.query(Escrow).filter(
                or_(
                    Escrow.payer_address == address,
                    Escrow.payee_address == address,
                    Escrow.arbiter_address == address,
                )
            )

            if status:
                query = query.filter(Escrow.status == status)

            all_escrows = query.order_by(Escrow.created_block.desc()).all()

            # Group by role
            result = {
                "asPayer": [],
                "asPayee": [],
                "asArbiter": [],
            }

            for escrow in all_escrows:
                escrow_dict = _escrow_to_dict(escrow)

                if escrow.payer_address == address:
                    result["asPayer"].append(escrow_dict)
                if escrow.payee_address == address:
                    result["asPayee"].append(escrow_dict)
                if escrow.arbiter_address == address:
                    result["asArbiter"].append(escrow_dict)

            return (
                jsonify(
                    {
                        "success": True,
                        "address": address,
                        "total": len(all_escrows),
                        "escrows": result,
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Error getting escrows by role: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@escrows_bp.route("/<escrow_address>", methods=["GET"])
def get_escrow(escrow_address: str):
    """Get details for a specific escrow."""
    try:
        escrow_address = escrow_address.lower()

        with get_db_session() as db:
            escrow = db.query(Escrow).filter(Escrow.escrow_address == escrow_address).first()

            if not escrow:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Escrow not found",
                        }
                    ),
                    404,
                )

            return (
                jsonify(
                    {
                        "success": True,
                        "escrow": _escrow_to_dict(escrow, include_approvals=True),
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Error getting escrow: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@escrows_bp.route("/<escrow_address>/approvals", methods=["GET"])
def get_escrow_approvals(escrow_address: str):
    """Get all approvals for a specific escrow."""
    try:
        escrow_address = escrow_address.lower()

        with get_db_session() as db:
            approvals = (
                db.query(Approval)
                .filter(Approval.escrow_address == escrow_address)
                .order_by(Approval.created_at.asc())
                .all()
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "count": len(approvals),
                        "approvals": [
                            {
                                "id": approval.id,
                                "approver_address": approval.approver_address,
                                "block_number": approval.block_number,
                                "tx_hash": approval.tx_hash,
                                "created_at": approval.created_at.isoformat(),
                            }
                            for approval in approvals
                        ],
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Error getting approvals: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@escrows_bp.route("/<escrow_address>/events", methods=["GET"])
def get_escrow_events(escrow_address: str):
    """Get all events for a specific escrow (audit trail)."""
    try:
        escrow_address = escrow_address.lower()

        with get_db_session() as db:
            events = (
                db.query(EscrowEvent)
                .filter(EscrowEvent.escrow_address == escrow_address)
                .order_by(EscrowEvent.block_number.asc())
                .all()
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "count": len(events),
                        "events": [
                            {
                                "id": event.id,
                                "event_type": event.event_type,
                                "block_number": event.block_number,
                                "tx_hash": event.tx_hash,
                                "chain_id": event.chain_id,
                                "created_at": event.created_at.isoformat(),
                            }
                            for event in events
                        ],
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Error getting events: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@escrows_bp.route("/stats", methods=["GET"])
def get_stats():
    """Get overall statistics."""
    try:
        with get_db_session() as db:
            total_escrows = db.query(Escrow).count()
            by_status = {
                "created": db.query(Escrow).filter(Escrow.status == "created").count(),
                "approved": db.query(Escrow).filter(Escrow.status == "approved").count(),
                "released": db.query(Escrow).filter(Escrow.status == "released").count(),
                "refunded": db.query(Escrow).filter(Escrow.status == "refunded").count(),
            }
            total_approvals = db.query(Approval).count()
            total_events = db.query(EscrowEvent).count()

            return (
                jsonify(
                    {
                        "success": True,
                        "stats": {
                            "total_escrows": total_escrows,
                            "by_status": by_status,
                            "total_approvals": total_approvals,
                            "total_events": total_events,
                        },
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
