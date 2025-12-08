"""
Analytics endpoints for Risk Engine Service.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.dependencies import get_analytics_engine
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


class StressTestRequest(BaseModel):
    """Stress test request model."""

    portfolio_id: str = Field(..., description="Portfolio identifier")
    scenarios: List[str] = Field(..., description="Stress test scenarios")
    time_horizon: Optional[int] = Field(30, description="Time horizon in days")
    confidence_level: Optional[float] = Field(0.95, description="Confidence level")


class CorrelationRequest(BaseModel):
    """Correlation analysis request model."""

    assets: List[str] = Field(..., description="Asset symbols to analyze")
    time_range: Optional[str] = Field("30d", description="Time range for analysis")
    method: Optional[str] = Field("pearson", description="Correlation method")


@router.get("/portfolio/{portfolio_id}/history")
async def get_portfolio_history(
    portfolio_id: str,
    time_range: str = Query("30d", description="Time range for history"),
    analytics_engine=Depends(get_analytics_engine),
):
    """Get portfolio performance history."""
    try:
        history = await analytics_engine.get_portfolio_history(portfolio_id, time_range)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {str(e)}")


@router.post("/stress-test")
async def run_stress_test(
    request: StressTestRequest, analytics_engine=Depends(get_analytics_engine)
):
    """Run stress test scenarios for a portfolio."""
    try:
        results = await analytics_engine.run_stress_test(
            portfolio_id=request.portfolio_id,
            scenarios=request.scenarios,
            time_horizon=request.time_horizon,
            confidence_level=request.confidence_level,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stress test failed: {str(e)}")


@router.post("/correlation")
async def analyze_correlation(
    request: CorrelationRequest, analytics_engine=Depends(get_analytics_engine)
):
    """Analyze asset correlation."""
    try:
        correlation_data = await analytics_engine.analyze_correlation(
            assets=request.assets, time_range=request.time_range, method=request.method
        )
        return correlation_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Correlation analysis failed: {str(e)}")


@router.get("/performance/{portfolio_id}")
async def get_portfolio_performance(
    portfolio_id: str,
    benchmark: Optional[str] = Query(None, description="Benchmark for comparison"),
    time_range: str = Query("30d", description="Time range for performance"),
    analytics_engine=Depends(get_analytics_engine),
):
    """Get portfolio performance metrics."""
    try:
        performance = await analytics_engine.get_portfolio_performance(
            portfolio_id=portfolio_id, benchmark=benchmark, time_range=time_range
        )
        return performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance analysis failed: {str(e)}")


@router.get("/volatility/{portfolio_id}")
async def get_portfolio_volatility(
    portfolio_id: str,
    time_range: str = Query("30d", description="Time range for volatility"),
    analytics_engine=Depends(get_analytics_engine),
):
    """Get portfolio volatility analysis."""
    try:
        volatility = await analytics_engine.get_portfolio_volatility(
            portfolio_id=portfolio_id, time_range=time_range
        )
        return volatility
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Volatility analysis failed: {str(e)}")


@router.get("/drawdown/{portfolio_id}")
async def get_portfolio_drawdown(
    portfolio_id: str,
    time_range: str = Query("30d", description="Time range for drawdown"),
    analytics_engine=Depends(get_analytics_engine),
):
    """Get portfolio drawdown analysis."""
    try:
        drawdown = await analytics_engine.get_portfolio_drawdown(
            portfolio_id=portfolio_id, time_range=time_range
        )
        return drawdown
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drawdown analysis failed: {str(e)}")


@router.get("/sharpe/{portfolio_id}")
async def get_portfolio_sharpe(
    portfolio_id: str,
    risk_free_rate: Optional[float] = Query(0.02, description="Risk-free rate"),
    time_range: str = Query("30d", description="Time range for Sharpe ratio"),
    analytics_engine=Depends(get_analytics_engine),
):
    """Get portfolio Sharpe ratio."""
    try:
        sharpe = await analytics_engine.get_portfolio_sharpe(
            portfolio_id=portfolio_id,
            risk_free_rate=risk_free_rate,
            time_range=time_range,
        )
        return sharpe
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sharpe ratio calculation failed: {str(e)}")


@router.get("/beta/{portfolio_id}")
async def get_portfolio_beta(
    portfolio_id: str,
    benchmark: str = Query("SPY", description="Benchmark for beta calculation"),
    time_range: str = Query("30d", description="Time range for beta"),
    analytics_engine=Depends(get_analytics_engine),
):
    """Get portfolio beta relative to benchmark."""
    try:
        beta = await analytics_engine.get_portfolio_beta(
            portfolio_id=portfolio_id, benchmark=benchmark, time_range=time_range
        )
        return beta
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beta calculation failed: {str(e)}")
