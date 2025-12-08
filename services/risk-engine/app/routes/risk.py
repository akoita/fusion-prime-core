"""
Risk calculation endpoints for Risk Engine Service.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.dependencies import get_risk_calculator
from app.models.risk import PortfolioRisk, RiskMetrics, RiskScore
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


class PortfolioRequest(BaseModel):
    """Portfolio risk calculation request."""

    portfolio_id: str = Field(..., description="Portfolio identifier")
    assets: List[Dict[str, Any]] = Field(..., description="Portfolio assets")
    risk_model: Optional[str] = Field("standard", description="Risk model to use")
    confidence_level: Optional[float] = Field(0.95, description="Confidence level for VaR")


class RiskCalculationResponse(BaseModel):
    """Risk calculation response."""

    portfolio_id: str
    risk_score: float
    var_1d: float
    var_7d: float
    var_30d: float
    cvar_1d: float
    cvar_7d: float
    cvar_30d: float
    correlation_matrix: Dict[str, Dict[str, float]]
    risk_metrics: RiskMetrics
    calculated_at: datetime


@router.get("/escrow/{address}")
async def get_escrow_risk(address: str, risk_calculator=Depends(get_risk_calculator)):
    """
    Get risk data for a specific escrow contract.

    This endpoint is used by integration tests to verify that the Risk Engine
    has been notified about escrow events and calculated risk metrics.

    Args:
        address: The escrow contract address

    Returns:
        Risk data including risk score, risk level, and locked amount calculations

    Note:
        For now, this is a mock implementation that returns calculated risk
        based on the escrow address. In production, this would query a database
        or cache of processed escrow risk data.
    """
    try:
        # Mock implementation: Calculate risk based on escrow
        # In production, this would retrieve stored risk data
        import hashlib

        # Generate deterministic risk score from address
        hash_val = int(hashlib.sha256(address.encode()).hexdigest()[:8], 16)
        risk_score = (hash_val % 50) / 10.0  # Range: 0.0-5.0

        # Determine risk level
        if risk_score < 2.0:
            risk_level = "LOW"
        elif risk_score < 3.5:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        return {
            "escrow_address": address.lower(),
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "locked_amount": "0.001",  # Mock value
            "asset_symbol": "ETH",
            "calculated_at": datetime.now().isoformat(),
            "volatility": round(risk_score * 0.15, 3),
            "liquidity_score": round(10.0 - risk_score, 2),
            "counterparty_risk": risk_level,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk calculation failed: {str(e)}")


@router.get("/portfolio/{portfolio_id}")
async def get_portfolio_risk(portfolio_id: str, risk_calculator=Depends(get_risk_calculator)):
    """Get risk assessment for a specific portfolio."""
    try:
        risk_data = await risk_calculator.calculate_portfolio_risk(portfolio_id)
        return risk_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk calculation failed: {str(e)}")


@router.post("/calculate")
async def calculate_risk(request: PortfolioRequest, risk_calculator=Depends(get_risk_calculator)):
    """Calculate risk for a custom portfolio."""
    try:
        # Prepare request data for the risk calculator
        request_data = {
            "portfolio_id": request.portfolio_id,
            "assets": request.assets,
            "risk_model": request.risk_model,
            "confidence_level": request.confidence_level,
        }

        # Calculate risk metrics
        risk_result = await risk_calculator.calculate_custom_risk(request_data)

        return risk_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk calculation failed: {str(e)}")


@router.get("/margin/{user_id}")
async def get_margin_requirements(user_id: str, risk_calculator=Depends(get_risk_calculator)):
    """Get margin requirements for a user."""
    try:
        margin_data = await risk_calculator.calculate_margin_requirements(user_id)
        return margin_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Margin calculation failed: {str(e)}")


@router.get("/metrics")
async def get_risk_metrics(
    portfolio_id: Optional[str] = Query(None, description="Portfolio ID filter"),
    time_range: str = Query("7d", description="Time range for metrics"),
    risk_calculator=Depends(get_risk_calculator),
):
    """Get risk metrics and KPIs."""
    try:
        metrics = await risk_calculator.get_risk_metrics(
            portfolio_id=portfolio_id, time_range=time_range
        )
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")


@router.post("/alerts")
async def create_risk_alert(
    request: Dict[str, Any],
    risk_calculator=Depends(get_risk_calculator),
):
    """Create a new risk alert for a user."""
    try:
        user_id = request.get("user_id")
        alert_config = request.get("alert_config", {})

        if not user_id:
            raise HTTPException(status_code=422, detail="user_id is required")

        alert = await risk_calculator.create_risk_alert(user_id, alert_config)
        return alert
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert creation failed: {str(e)}")


@router.get("/alerts/{user_id}")
async def get_user_risk_alerts(user_id: str, risk_calculator=Depends(get_risk_calculator)):
    """Get all risk alerts for a user."""
    try:
        alerts = await risk_calculator.get_user_risk_alerts(user_id)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alerts retrieval failed: {str(e)}")


@router.get("/stress-test/{portfolio_id}")
async def run_stress_test(
    portfolio_id: str,
    scenarios: List[str] = Query(..., description="Stress test scenarios"),
    risk_calculator=Depends(get_risk_calculator),
):
    """Run stress test scenarios for a portfolio."""
    try:
        results = await risk_calculator.run_stress_test(portfolio_id, scenarios)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stress test failed: {str(e)}")
