"""
Standard API response utilities for indexers

Provides consistent response formats across all indexer APIs.
"""

from typing import Any, Dict, List

from flask import jsonify


def success_response(data: Any, status: int = 200):
    """
    Create a successful response.

    Args:
        data: Response data
        status: HTTP status code (default: 200)

    Returns:
        Flask JSON response
    """
    return jsonify({"success": True, **data}), status


def error_response(message: str, status: int = 500, details: Dict[str, Any] = None):
    """
    Create an error response.

    Args:
        message: Error message
        status: HTTP status code (default: 500)
        details: Optional additional error details

    Returns:
        Flask JSON response
    """
    response = {"success": False, "error": message}
    if details:
        response["details"] = details
    return jsonify(response), status


def list_response(items: List[Any], total: int = None, status: int = 200):
    """
    Create a list response.

    Args:
        items: List of items
        total: Optional total count (if different from len(items))
        status: HTTP status code (default: 200)

    Returns:
        Flask JSON response
    """
    return (
        jsonify(
            {
                "success": True,
                "count": len(items),
                "total": total if total is not None else len(items),
                "items": items,
            }
        ),
        status,
    )


def not_found_response(resource: str, identifier: str):
    """
    Create a 404 not found response.

    Args:
        resource: Resource type (e.g., "Escrow")
        identifier: Resource identifier

    Returns:
        Flask JSON response
    """
    return error_response(
        f"{resource} not found: {identifier}",
        status=404,
    )


def validation_error_response(errors: Dict[str, str]):
    """
    Create a 400 validation error response.

    Args:
        errors: Dictionary of field errors

    Returns:
        Flask JSON response
    """
    return error_response(
        "Validation error",
        status=400,
        details={"validation_errors": errors},
    )
