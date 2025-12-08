"""
Service Query Utilities

Provides utilities for querying services to verify event processing.
Includes retry logic and proper error handling.
"""

from typing import Any, Dict, Optional

import requests

from tests.common.polling_utils import poll_until, retry_on_failure


def query_settlement_escrow(
    base_url: str, escrow_address: str, timeout: int = 180, poll_interval: int = 2
) -> Optional[Dict[str, Any]]:
    """
    Query Settlement service for escrow data with polling.

    Args:
        base_url: Settlement service base URL
        escrow_address: Escrow contract address
        timeout: Maximum wait time
        poll_interval: Time between polls

    Returns:
        Escrow data dict or None if not found/timeout

    Example:
        escrow_data = query_settlement_escrow(
            "http://localhost:8000",
            "0x123...",
            timeout=30
        )
        if escrow_data:
            assert escrow_data['status'] == 'created'
    """

    def check_escrow():
        try:
            response = requests.get(f"{base_url}/escrows/{escrow_address}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    print(f"🔍 Polling Settlement service for escrow {escrow_address}...")

    result = poll_until(
        check_escrow,
        timeout=timeout,
        interval=poll_interval,
        description=f"Settlement escrow {escrow_address}",
    )

    return result


def query_settlement_commands(
    base_url: str,
    escrow_address: Optional[str] = None,
    workflow_id: Optional[str] = None,
    timeout: int = 30,
) -> Optional[list]:
    """
    Query Settlement service for commands.

    Args:
        base_url: Settlement service base URL
        escrow_address: Filter by escrow address
        workflow_id: Filter by workflow ID
        timeout: Request timeout

    Returns:
        List of commands or None
    """
    params = {}
    if escrow_address:
        params["escrow_address"] = escrow_address
    if workflow_id:
        params["workflow_id"] = workflow_id

    def query():
        response = requests.get(f"{base_url}/commands", params=params, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        return None

    return retry_on_failure(query, max_attempts=3, description=f"GET /commands")


def query_risk_engine_escrow(
    base_url: str, escrow_address: str, timeout: int = 180, poll_interval: int = 2
) -> Optional[Dict[str, Any]]:
    """
    Query Risk Engine for escrow risk data with polling.

    Args:
        base_url: Risk Engine base URL
        escrow_address: Escrow address
        timeout: Maximum wait time
        poll_interval: Time between polls

    Returns:
        Risk data dict or None

    Example:
        risk_data = query_risk_engine_escrow(
            "http://localhost:8001",
            "0x123...",
            timeout=30
        )
        if risk_data:
            assert 'risk_score' in risk_data
    """

    def check_risk():
        try:
            response = requests.get(f"{base_url}/risk/escrow/{escrow_address}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    print(f"🔍 Polling Risk Engine for escrow {escrow_address}...")

    result = poll_until(
        check_risk,
        timeout=timeout,
        interval=poll_interval,
        description=f"Risk Engine escrow {escrow_address}",
    )

    return result


def query_compliance_checks(
    base_url: str, escrow_address: str, timeout: int = 180, poll_interval: int = 2
) -> Optional[list]:
    """
    Query Compliance service for checks related to an escrow.

    Args:
        base_url: Compliance service base URL
        escrow_address: Escrow address
        timeout: Maximum wait time
        poll_interval: Time between polls

    Returns:
        List of compliance checks or None

    Example:
        checks = query_compliance_checks(
            "http://localhost:8002",
            "0x123...",
            timeout=30
        )
        if checks:
            assert any(c['status'] == 'approved' for c in checks)
    """

    def check_compliance():
        try:
            response = requests.get(
                f"{base_url}/compliance/checks",
                params={"escrow_address": escrow_address},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data
            return None
        except Exception:
            return None

    print(f"🔍 Polling Compliance service for escrow {escrow_address}...")

    result = poll_until(
        check_compliance,
        timeout=timeout,
        interval=poll_interval,
        description=f"Compliance checks for {escrow_address}",
    )

    return result


def verify_database_update(
    base_url: str,
    resource_type: str,
    resource_id: str,
    expected_fields: Dict[str, Any],
    timeout: int = 180,
    poll_interval: int = 2,
) -> bool:
    """
    Verify that a resource was updated in the database with expected values.

    Args:
        base_url: Service base URL
        resource_type: Type of resource (e.g., 'escrows', 'commands')
        resource_id: Resource ID
        expected_fields: Dict of field:value pairs to verify
        timeout: Maximum wait time
        poll_interval: Time between polls

    Returns:
        True if all fields match, False if timeout

    Example:
        success = verify_database_update(
            "http://localhost:8000",
            "escrows",
            "0x123...",
            {"status": "created", "payer": "0xabc..."},
            timeout=30
        )
    """

    def check_fields():
        try:
            response = requests.get(f"{base_url}/{resource_type}/{resource_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Check all expected fields
                for field, expected_value in expected_fields.items():
                    if data.get(field) != expected_value:
                        return None
                return data
            return None
        except Exception:
            return None

    print(f"🔍 Verifying database update for {resource_type}/{resource_id}...")

    result = poll_until(
        check_fields,
        timeout=timeout,
        interval=poll_interval,
        description=f"Database update for {resource_type}/{resource_id}",
    )

    if result:
        print(f"✅ Database fields verified: {expected_fields}")
        return True
    else:
        print(f"❌ Database fields not updated within {timeout}s")
        return False


def check_service_health(base_url: str, timeout: int = 10) -> bool:
    """
    Check if a service is healthy.

    Args:
        base_url: Service base URL
        timeout: Request timeout

    Returns:
        True if healthy, False otherwise
    """
    try:
        response = requests.get(f"{base_url}/health", timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False
