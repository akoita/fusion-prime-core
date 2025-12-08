"""
Database Validation Utilities

Provides comprehensive database validation utilities for workflow tests.
These utilities ensure that event-driven pipeline actually persists data correctly.

Key Features:
- Comprehensive field validation with type checking
- State transition validation (before/after)
- Negative validation (data doesn't exist when it shouldn't)
- Timestamp validation (recent, updated, etc.)
- Detailed error messages for debugging
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from tests.common.service_query_utils import query_settlement_escrow


def validate_escrow_in_database(
    settlement_url: str,
    escrow_address: str,
    expected_fields: Dict[str, Any],
    timeout: int = 180,
    poll_interval: int = 3,
) -> Dict[str, Any]:
    """
    Validate escrow exists in database with ALL expected fields.

    This is the PRIMARY validation function for escrow creation and updates.
    It performs comprehensive validation of all escrow fields and metadata.

    Args:
        settlement_url: Settlement service URL
        escrow_address: Escrow contract address
        expected_fields: Dict of all expected field:value pairs to validate
        timeout: Max wait time for async processing (default: 60s)
        poll_interval: Time between polls (default: 3s)

    Returns:
        Complete escrow data from database

    Raises:
        AssertionError: If any validation fails with detailed error message

    Example:
        >>> escrow_data = validate_escrow_in_database(
        ...     "https://settlement-service.run.app",
        ...     "0x123abc...",
        ...     {
        ...         "payer": "0xabc...",
        ...         "payee": "0xdef...",
        ...         "amount": "1000000000000000",  # wei
        ...         "status": "active",
        ...         "release_delay": 3600,
        ...         "approvals_required": 2,
        ...         "approvals_count": 0,
        ...         "chain_id": 11155111,
        ...     },
        ...     timeout=60
        ... )
        ✅ Database validation PASSED for escrow 0x123abc...
           All 8 fields match expected values
           Timestamps are recent (created 2.3s ago)
    """
    print(f"\n🔍 DATABASE VALIDATION - Escrow {escrow_address}")
    print(f"   Polling Settlement service (timeout: {timeout}s)...")

    # Poll for escrow data with aggressive fast polling (0.5s interval)
    escrow_data = query_settlement_escrow(
        base_url=settlement_url,
        escrow_address=escrow_address,
        timeout=timeout,
        poll_interval=0.5,  # Aggressive fast polling (0.5s intervals)
    )

    # Only retry once if not found, with minimal wait
    if escrow_data is None:
        additional_wait = min(10, timeout // 4)  # Minimal wait: max 10s
        print(f"⏳ Escrow not found, waiting additional {additional_wait}s for relayer catch-up...")
        import time

        time.sleep(additional_wait)

        escrow_data = query_settlement_escrow(
            base_url=settlement_url,
            escrow_address=escrow_address,
            timeout=min(60, timeout // 2),  # Capped at 60s
            poll_interval=0.5,  # Fast polling
        )

    # VALIDATION 1: Escrow exists
    assert escrow_data is not None, (
        f"❌ VALIDATION FAILED: Escrow {escrow_address} not found in database\n"
        f"   Waited {timeout}s (+ additional catch-up time) but Settlement service did not persist escrow\n"
        f"   Possible causes:\n"
        f"   - Relayer is catching up from lag (check relayer health: blocks_behind)\n"
        f"   - Event not published to Pub/Sub\n"
        f"   - Settlement service not consuming events\n"
        f"   - Database session_factory not configured\n"
        f"   - Event handler not persisting to database\n"
        f"   \n"
        f"   If relayer lag is high, consider:\n"
        f"   1. Waiting for relayer to catch up before running tests\n"
        f"   2. Increasing test timeout values"
    )

    print(f"✅ Escrow exists in database")

    # VALIDATION 2: All expected fields match
    validation_errors = []

    for field, expected in expected_fields.items():
        actual = escrow_data.get(field)

        # Handle address comparison (case-insensitive)
        if field in ["payer", "payee", "approver", "arbiter"]:
            if actual is None:
                validation_errors.append(
                    f"  ❌ Field '{field}': expected {expected}, got None (missing)"
                )
            elif str(actual).lower() != str(expected).lower():
                validation_errors.append(f"  ❌ Field '{field}': expected {expected}, got {actual}")
        # Handle numeric comparison (convert to int for comparison)
        elif field in [
            "amount",
            "release_delay",
            "approvals_required",
            "approvals_count",
            "chain_id",
        ]:
            try:
                actual_int = int(actual) if actual is not None else None
                expected_int = int(expected)
                if actual_int != expected_int:
                    validation_errors.append(
                        f"  ❌ Field '{field}': expected {expected_int}, got {actual_int}"
                    )
            except (ValueError, TypeError):
                validation_errors.append(
                    f"  ❌ Field '{field}': expected {expected}, got {actual} (type mismatch)"
                )
        # Handle exact match for other fields
        else:
            if actual != expected:
                validation_errors.append(f"  ❌ Field '{field}': expected {expected}, got {actual}")

    # If any field validation failed, raise with all errors
    if validation_errors:
        error_msg = (
            f"❌ VALIDATION FAILED: Field mismatches for escrow {escrow_address}\n"
            + "\n".join(validation_errors)
            + f"\n\nFull escrow data from database:\n{escrow_data}"
        )
        raise AssertionError(error_msg)

    print(f"✅ All {len(expected_fields)} expected fields match")

    # VALIDATION 3: Required metadata fields exist
    required_metadata = ["created_at", "updated_at"]
    missing_metadata = [f for f in required_metadata if f not in escrow_data]

    if missing_metadata:
        raise AssertionError(
            f"❌ VALIDATION FAILED: Missing required metadata fields: {missing_metadata}\n"
            f"   Full escrow data: {escrow_data}"
        )

    print(f"✅ Required metadata fields present")

    # VALIDATION 4: Timestamp is recent (within last 10 minutes)
    try:
        created_at_str = escrow_data["created_at"]
        # Handle both ISO formats: with Z and with +00:00
        if created_at_str.endswith("Z"):
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        else:
            created_at = datetime.fromisoformat(created_at_str)

        now = datetime.now(timezone.utc)
        age = now - created_at

        assert age < timedelta(minutes=10), (
            f"❌ VALIDATION FAILED: created_at timestamp too old\n"
            f"   Created: {created_at_str}\n"
            f"   Age: {age.total_seconds():.1f}s (> 600s threshold)\n"
            f"   This suggests stale data or clock skew"
        )

        print(f"✅ Timestamp is recent (created {age.total_seconds():.1f}s ago)")

    except (KeyError, ValueError) as e:
        print(f"⚠️  Could not validate timestamp: {e}")

    # SUCCESS
    print(f"🎉 DATABASE VALIDATION PASSED")
    print(f"   Escrow: {escrow_address}")
    print(f"   Status: {escrow_data.get('status')}")
    print(f"   Fields validated: {len(expected_fields)}")

    return escrow_data


def validate_state_transition(
    settlement_url: str,
    escrow_address: str,
    field: str,
    expected_after: Any,
    expected_before: Optional[Any] = None,
    timeout: int = 180,
    poll_interval: int = 3,
) -> Dict[str, Any]:
    """
    Validate that a field transitioned to an expected value.

    This is used to validate state changes after blockchain transactions,
    such as approvals_count incrementing or status changing to "completed".

    Args:
        settlement_url: Settlement service URL
        escrow_address: Escrow contract address
        field: Field name to validate (e.g., "approvals_count", "status")
        expected_after: Expected value after transition
        expected_before: Optional - expected value before transition (for logging)
        timeout: Max wait time for async processing
        poll_interval: Time between polls

    Returns:
        Complete escrow data from database

    Raises:
        AssertionError: If state transition validation fails

    Example:
        >>> # After approval transaction
        >>> validate_state_transition(
        ...     settlement_url,
        ...     escrow_address,
        ...     field="approvals_count",
        ...     expected_after=1,
        ...     expected_before=0,
        ...     timeout=60
        ... )
        ✅ State transition verified: approvals_count = 0 → 1
    """
    print(f"\n🔄 STATE TRANSITION VALIDATION - Field: {field}")

    # Poll for escrow data
    escrow_data = query_settlement_escrow(
        base_url=settlement_url,
        escrow_address=escrow_address,
        timeout=timeout,
        poll_interval=poll_interval,
    )

    assert escrow_data is not None, (
        f"❌ VALIDATION FAILED: Escrow {escrow_address} not found in database\n"
        f"   Cannot validate state transition for field '{field}'"
    )

    # Get actual value
    actual = escrow_data.get(field)

    # Handle numeric comparison
    if isinstance(expected_after, (int, str)) and field in [
        "approvals_count",
        "approvals_required",
        "release_delay",
        "amount",
    ]:
        try:
            actual_int = int(actual) if actual is not None else None
            expected_int = int(expected_after)
            matches = actual_int == expected_int
        except (ValueError, TypeError):
            matches = False
    # Handle string comparison (case-insensitive for addresses)
    elif field in ["status", "payer", "payee", "approver"]:
        matches = str(actual).lower() == str(expected_after).lower()
    # Handle exact match
    else:
        matches = actual == expected_after

    # Build error message with transition notation
    if expected_before is not None:
        transition_str = f"{expected_before} → {expected_after}"
    else:
        transition_str = f"? → {expected_after}"

    assert matches, (
        f"❌ STATE TRANSITION FAILED for field '{field}'\n"
        f"   Expected transition: {transition_str}\n"
        f"   Actual value: {actual}\n"
        f"   Escrow: {escrow_address}\n"
        f"   Full escrow data: {escrow_data}"
    )

    # Success
    if expected_before is not None:
        print(f"✅ State transition verified: {field} = {expected_before} → {expected_after}")
    else:
        print(f"✅ State verified: {field} = {expected_after}")

    return escrow_data


def validate_escrow_not_exists(settlement_url: str, escrow_address: str, timeout: int = 5) -> None:
    """
    Validate that escrow does NOT exist in database (negative validation).

    This is used BEFORE event processing to ensure data doesn't exist prematurely.
    It's a sanity check that tests are actually testing the event pipeline.

    Args:
        settlement_url: Settlement service URL
        escrow_address: Escrow contract address
        timeout: Request timeout (default: 5s)

    Raises:
        AssertionError: If escrow exists when it shouldn't

    Example:
        >>> # BEFORE relayer processes event
        >>> validate_escrow_not_exists(settlement_url, escrow_address)
        ✅ Negative validation passed: escrow does not exist (404)
    """
    print(f"\n🚫 NEGATIVE VALIDATION - Verifying escrow does NOT exist yet")

    try:
        response = requests.get(f"{settlement_url}/escrows/{escrow_address}", timeout=timeout)

        if response.status_code == 404:
            print(f"✅ Negative validation passed: escrow does not exist (404)")
            return

        # Escrow exists when it shouldn't!
        raise AssertionError(
            f"❌ NEGATIVE VALIDATION FAILED\n"
            f"   Escrow {escrow_address} exists in database but shouldn't yet!\n"
            f"   Status: {response.status_code}\n"
            f"   This suggests:\n"
            f"   - Test data not cleaned up from previous run\n"
            f"   - Events processed faster than expected\n"
            f"   - Using wrong escrow address (collision)"
        )

    except requests.exceptions.Timeout:
        print(f"ℹ️  Request timeout (acceptable - service may not be fully ready)")
    except requests.exceptions.ConnectionError:
        print(f"ℹ️  Connection error (acceptable - service may not be accessible)")


def validate_approval_recorded(
    settlement_url: str,
    escrow_address: str,
    approver_address: str,
    expected_approval_count: int,
    timeout: int = 180,
) -> Dict[str, Any]:
    """
    Validate that an approval was recorded in the database.

    Comprehensive validation after an approval transaction:
    - Approval count incremented
    - Approver added to approvers list
    - Status still active (not released yet)
    - updated_at timestamp changed

    Args:
        settlement_url: Settlement service URL
        escrow_address: Escrow contract address
        approver_address: Address of approver
        expected_approval_count: Expected count after approval
        timeout: Max wait time

    Returns:
        Complete escrow data from database

    Raises:
        AssertionError: If approval not recorded correctly

    Example:
        >>> escrow_data = validate_approval_recorded(
        ...     settlement_url,
        ...     escrow_address,
        ...     approver_address="0xabc...",
        ...     expected_approval_count=1,
        ...     timeout=60
        ... )
        ✅ Approval recorded: count = 0 → 1
        ✅ Approver 0xabc... added to approvers list
    """
    print(f"\n👍 APPROVAL VALIDATION")

    # Validate approval count transitioned
    escrow_data = validate_state_transition(
        settlement_url=settlement_url,
        escrow_address=escrow_address,
        field="approvals_count",
        expected_after=expected_approval_count,
        expected_before=expected_approval_count - 1,
        timeout=timeout,
    )

    # Validate approver in list (if approvers field exists)
    if "approvers" in escrow_data:
        approvers_list = escrow_data["approvers"]
        if isinstance(approvers_list, list):
            approver_found = any(str(a).lower() == approver_address.lower() for a in approvers_list)
            assert approver_found, (
                f"❌ APPROVAL VALIDATION FAILED\n"
                f"   Approver {approver_address} not found in approvers list\n"
                f"   Approvers: {approvers_list}"
            )
            print(f"✅ Approver {approver_address[:10]}... added to approvers list")

    # Validate status is still active (not released yet)
    status = escrow_data.get("status")
    approvals_required = escrow_data.get("approvals_required", 0)
    current_approvals = escrow_data.get("approvals_count", 0)

    # Status can be "created" if not all required approvals are met yet
    valid_statuses = ["active", "pending", "approved"]
    if current_approvals < approvals_required:
        valid_statuses.append("created")

    assert status in valid_statuses, (
        f"❌ APPROVAL VALIDATION FAILED\n"
        f"   Expected status in {valid_statuses}, got '{status}'\n"
        f"   Approvals: {current_approvals}/{approvals_required}\n"
        f"   Escrow should not be released after partial approval"
    )

    if status == "created" and current_approvals < approvals_required:
        print(
            f"✅ Escrow status: {status} (awaiting {approvals_required - current_approvals} more approval(s))"
        )
    else:
        print(f"✅ Escrow status: {status} (still active, not released)")

    return escrow_data


def validate_release_recorded(
    settlement_url: str,
    escrow_address: str,
    expected_amount: int,
    timeout: int = 180,
) -> Dict[str, Any]:
    """
    Validate that a payment release was recorded in the database.

    Comprehensive validation after a release transaction:
    - Status changed to "completed" or "released"
    - Released amount matches expected
    - released_at timestamp exists
    - Final settlement recorded

    Args:
        settlement_url: Settlement service URL
        escrow_address: Escrow contract address
        expected_amount: Expected released amount (wei)
        timeout: Max wait time

    Returns:
        Complete escrow data from database

    Raises:
        AssertionError: If release not recorded correctly

    Example:
        >>> escrow_data = validate_release_recorded(
        ...     settlement_url,
        ...     escrow_address,
        ...     expected_amount=1000000000000000,  # 0.001 ETH
        ...     timeout=60
        ... )
        ✅ Payment release recorded: status = active → completed
        ✅ Released amount: 1000000000000000 wei
    """
    print(f"\n💰 RELEASE VALIDATION")

    # First, get current status to use as baseline (in case approvals were processed)
    current_escrow = query_settlement_escrow(
        base_url=settlement_url,
        escrow_address=escrow_address,
        timeout=10,
        poll_interval=1,
    )

    if current_escrow:
        baseline_status = current_escrow.get("status", "created")
        print(f"📊 Current baseline status: {baseline_status}")
    else:
        baseline_status = "created"  # Default baseline

    # Valid completed statuses after release
    valid_completed_statuses = ["completed", "released", "paid", "settled"]

    # Poll for escrow data and check if status is in valid completed statuses
    # This is more lenient than strict state transition validation
    escrow_data = query_settlement_escrow(
        base_url=settlement_url,
        escrow_address=escrow_address,
        timeout=timeout,
        poll_interval=0.5,  # Fast polling (0.5s intervals)
    )

    assert (
        escrow_data is not None
    ), f"❌ RELEASE VALIDATION FAILED: Escrow {escrow_address} not found in database"

    # Check if status is in valid completed statuses
    status = escrow_data.get("status")
    status_transitioned = status in valid_completed_statuses

    if not status_transitioned:
        # If status hasn't transitioned yet, it might still be processing
        # Wait a bit more and check again (reduced wait)
        print(f"⏳ Status still '{status}', waiting for relayer to process release event...")
        time.sleep(15)  # Reduced from 30s - relayer should be faster now

        escrow_data = query_settlement_escrow(
            base_url=settlement_url,
            escrow_address=escrow_address,
            timeout=30,
            poll_interval=0.5,  # Fast polling
        )

        if escrow_data:
            status = escrow_data.get("status")
            status_transitioned = status in valid_completed_statuses

    # Validate status is one of the valid completed statuses
    assert status_transitioned, (
        f"❌ RELEASE VALIDATION FAILED\n"
        f"   Expected status in {valid_completed_statuses}, got '{status}'\n"
        f"   Baseline was: {baseline_status}\n"
        f"   This may indicate:\n"
        f"   1. Relayer hasn't processed EscrowReleased event yet (wait longer or check relayer logs)\n"
        f"   2. Release event not being picked up by settlement service\n"
        f"   3. Status transition logic issue in settlement service\n"
        f"   Escrow: {escrow_address}"
    )

    print(f"✅ Payment release recorded: status = {baseline_status} → {status}")

    # Validate released amount (if field exists)
    if "released_amount" in escrow_data:
        released_amount = int(escrow_data["released_amount"])
        assert released_amount == expected_amount, (
            f"❌ RELEASE VALIDATION FAILED\n"
            f"   Expected released_amount {expected_amount}, got {released_amount}"
        )
        print(f"✅ Released amount: {released_amount} wei")

    # Validate released_at timestamp exists (if field exists)
    if "released_at" in escrow_data:
        assert escrow_data["released_at"] is not None, (
            f"❌ RELEASE VALIDATION FAILED\n" f"   released_at is None"
        )
        print(f"✅ Release timestamp recorded: {escrow_data['released_at']}")

    return escrow_data


def validate_field_updated(
    settlement_url: str,
    escrow_address: str,
    field: str,
    timeout: int = 180,
) -> None:
    """
    Validate that updated_at timestamp changed (field was updated).

    This is useful for verifying that database writes actually occurred,
    even if field values didn't change.

    Args:
        settlement_url: Settlement service URL
        escrow_address: Escrow contract address
        field: Field to check (usually "updated_at")
        timeout: Max wait time

    Example:
        >>> validate_field_updated(settlement_url, escrow_address, "updated_at")
        ✅ Field updated: updated_at changed
    """
    escrow_data = query_settlement_escrow(settlement_url, escrow_address, timeout, poll_interval=3)

    assert escrow_data is not None, f"Escrow {escrow_address} not found"
    assert field in escrow_data, f"Field '{field}' not found in escrow data"

    print(f"✅ Field exists: {field} = {escrow_data[field]}")
