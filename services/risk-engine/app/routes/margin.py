"""
Margin Health endpoints for Risk Engine Service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.dependencies import get_risk_calculator
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


class MarginHealthRequest(BaseModel):
    """Margin health calculation request."""

    user_id: str = Field(..., description="User identifier")
    collateral_positions: Dict[str, float] = Field(
        ..., description="Collateral positions {asset_symbol: amount}"
    )
    borrow_positions: Dict[str, float] = Field(
        ..., description="Borrow positions {asset_symbol: amount}"
    )
    previous_health_score: Optional[float] = Field(
        None, description="Previous health score (if available)"
    )


class MarginHealthResponse(BaseModel):
    """Margin health calculation response."""

    user_id: str
    health_score: float
    status: str  # HEALTHY, WARNING, MARGIN_CALL, LIQUIDATION
    total_collateral_usd: float
    total_borrow_usd: float
    liquidation_price_drop_percent: float
    collateral_breakdown: Dict[str, Dict[str, Any]]
    borrow_breakdown: Dict[str, Dict[str, Any]]
    margin_event: Optional[Dict[str, Any]] = None
    calculated_at: str


class BatchMarginHealthRequest(BaseModel):
    """Batch margin health calculation request."""

    user_positions: List[Dict[str, Any]] = Field(
        ..., description="List of user positions with user_id, collateral, and borrows"
    )


@router.post("/health", response_model=MarginHealthResponse)
async def calculate_margin_health(
    request: MarginHealthRequest, risk_calculator=Depends(get_risk_calculator)
):
    """
    Calculate margin health score for a user.

    This endpoint calculates the user's margin health based on their
    collateral and borrow positions, using real-time USD prices.

    **Health Score Formula**:
    ```
    health_score = (total_collateral_usd - total_borrow_usd) / total_borrow_usd * 100
    ```

    **Health Status**:
    - HEALTHY: >= 50%
    - WARNING: 30-50%
    - MARGIN_CALL: 15-30%
    - LIQUIDATION: < 15%

    Args:
        request: Margin health request with user_id, collateral, and borrow positions

    Returns:
        Margin health metrics including health score, status, and event (if detected)

    Example:
        ```json
        {
            "user_id": "0x1234...",
            "collateral_positions": {"ETH": 10.0, "BTC": 0.5},
            "borrow_positions": {"USDC": 15000.0}
        }
        ```
    """
    try:
        result = await risk_calculator.calculate_user_margin_health(
            user_id=request.user_id,
            collateral_positions=request.collateral_positions,
            borrow_positions=request.borrow_positions,
            previous_health_score=request.previous_health_score,
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate margin health: {str(e)}")


@router.get("/health/{user_id}")
async def get_margin_health(user_id: str, risk_calculator=Depends(get_risk_calculator)):
    """
    Get margin health score for a user (placeholder endpoint).

    **Note**: This endpoint currently returns a placeholder response.
    In production, it would query stored position data from the database.

    To calculate margin health with specific positions, use POST /api/v1/margin/health

    Args:
        user_id: User identifier

    Returns:
        Margin health metrics (placeholder)
    """
    # TODO: Query database for user's actual collateral and borrow positions
    # For now, return placeholder
    return {
        "user_id": user_id,
        "health_score": 0.0,
        "status": "UNKNOWN",
        "message": "Use POST /api/v1/margin/health with position data to calculate health score",
        "total_collateral_usd": 0.0,
        "total_borrow_usd": 0.0,
        "calculated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.post("/monitor")
async def monitor_all_margins(risk_calculator=Depends(get_risk_calculator)):
    """
    Monitor margin health for all users with active positions.

    This endpoint triggers a batch margin health check for all users
    and returns only users with margin events (warnings, calls, liquidations).

    **Use Case**: Called periodically (e.g., every 5 minutes) via Cloud Scheduler
    to detect margin events across all users.

    Returns:
        List of users with margin events

    Example Response:
        ```json
        {
            "total_users_checked": 100,
            "users_with_events": 3,
            "events": [
                {
                    "user_id": "0x1234...",
                    "health_score": 22.5,
                    "status": "MARGIN_CALL",
                    "margin_event": {...}
                }
            ]
        }
        ```
    """
    try:
        margin_events = await risk_calculator.monitor_all_user_margins()

        return {
            "total_users_checked": len(margin_events),  # Would be total users in production
            "users_with_events": len(margin_events),
            "events": margin_events,
            "monitored_at": datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to monitor margins: {str(e)}")


@router.post("/health/batch", response_model=List[MarginHealthResponse])
async def batch_calculate_margin_health(
    request: BatchMarginHealthRequest, risk_calculator=Depends(get_risk_calculator)
):
    """
    Calculate margin health for multiple users in batch.

    **Use Case**: Calculate health for a list of users efficiently
    by batching price fetches.

    Args:
        request: Batch request with list of user positions

    Returns:
        List of margin health results

    Example Request:
        ```json
        {
            "user_positions": [
                {
                    "user_id": "0x1234...",
                    "collateral": {"ETH": 10.0},
                    "borrows": {"USDC": 15000.0}
                },
                {
                    "user_id": "0x5678...",
                    "collateral": {"BTC": 1.0},
                    "borrows": {"USDT": 30000.0}
                }
            ]
        }
        ```
    """
    try:
        # Calculate health for each user
        results = []
        for position in request.user_positions:
            user_id = position.get("user_id")
            collateral = position.get("collateral", {})
            borrows = position.get("borrows", {})

            if not user_id:
                continue

            result = await risk_calculator.calculate_user_margin_health(
                user_id=user_id, collateral_positions=collateral, borrow_positions=borrows
            )

            if "error" not in result:
                results.append(result)

        return results

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to batch calculate margin health: {str(e)}"
        )


@router.get("/events")
async def get_margin_events(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    severity: Optional[str] = Query(
        None, description="Filter by severity (low, medium, high, critical)"
    ),
    limit: int = Query(100, description="Maximum number of events to return"),
):
    """
    Get recent margin events.

    **Note**: This endpoint currently returns a placeholder response.
    In production, it would query stored margin events from the database.

    Args:
        user_id: Optional user ID filter
        severity: Optional severity filter
        limit: Maximum number of events

    Returns:
        List of recent margin events (placeholder)
    """
    # TODO: Query database for margin events
    # For now, return placeholder
    return {
        "events": [],
        "total": 0,
        "user_id_filter": user_id,
        "severity_filter": severity,
        "message": "Margin event storage not yet implemented",
    }


@router.get("/stats")
async def get_margin_stats():
    """
    Get margin health statistics across all users.

    **Note**: This endpoint currently returns a placeholder response.
    In production, it would aggregate margin health data from the database.

    Returns:
        Margin health statistics (placeholder)

    Example Response:
        ```json
        {
            "total_users": 150,
            "healthy_users": 120,
            "warning_users": 20,
            "margin_call_users": 8,
            "liquidation_users": 2,
            "average_health_score": 65.4,
            "updated_at": "2025-10-27T12:00:00Z"
        }
        ```
    """
    # TODO: Aggregate margin health statistics from database
    return {
        "total_users": 0,
        "healthy_users": 0,
        "warning_users": 0,
        "margin_call_users": 0,
        "liquidation_users": 0,
        "average_health_score": 0.0,
        "message": "Margin stats aggregation not yet implemented",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
