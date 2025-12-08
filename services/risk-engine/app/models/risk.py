"""
Risk models and data structures for Risk Engine Service.
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskScore(BaseModel):
    """Risk score model."""

    score: float = Field(..., ge=0, le=100, description="Risk score (0-100)")
    level: RiskLevel = Field(..., description="Risk level")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in score")
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PortfolioRisk(BaseModel):
    """Portfolio risk assessment model."""

    portfolio_id: str = Field(..., description="Portfolio identifier")
    risk_score: RiskScore = Field(..., description="Overall risk score")
    var_1d: float = Field(..., description="1-day Value at Risk")
    var_7d: float = Field(..., description="7-day Value at Risk")
    var_30d: float = Field(..., description="30-day Value at Risk")
    cvar_1d: float = Field(..., description="1-day Conditional VaR")
    cvar_7d: float = Field(..., description="7-day Conditional VaR")
    cvar_30d: float = Field(..., description="30-day Conditional VaR")
    correlation_matrix: Dict[str, Dict[str, float]] = Field(
        ..., description="Asset correlation matrix"
    )
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RiskMetrics(BaseModel):
    """Risk metrics model."""

    volatility: float = Field(..., description="Portfolio volatility")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    beta: float = Field(..., description="Portfolio beta")
    alpha: float = Field(..., description="Portfolio alpha")
    tracking_error: float = Field(..., description="Tracking error")
    information_ratio: float = Field(..., description="Information ratio")


class AssetRisk(BaseModel):
    """Individual asset risk model."""

    asset_id: str = Field(..., description="Asset identifier")
    symbol: str = Field(..., description="Asset symbol")
    risk_score: RiskScore = Field(..., description="Asset risk score")
    weight: float = Field(..., ge=0, le=1, description="Asset weight in portfolio")
    contribution_to_risk: float = Field(..., description="Contribution to portfolio risk")
    beta: float = Field(..., description="Asset beta")
    volatility: float = Field(..., description="Asset volatility")


class MarginRequirement(BaseModel):
    """Margin requirement model."""

    user_id: str = Field(..., description="User identifier")
    total_margin: float = Field(..., description="Total margin requirement")
    initial_margin: float = Field(..., description="Initial margin requirement")
    maintenance_margin: float = Field(..., description="Maintenance margin requirement")
    available_margin: float = Field(..., description="Available margin")
    margin_ratio: float = Field(..., description="Margin ratio")
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RiskAlert(BaseModel):
    """Risk alert model."""

    alert_id: str = Field(..., description="Alert identifier")
    user_id: str = Field(..., description="User identifier")
    alert_type: str = Field(..., description="Alert type")
    threshold: float = Field(..., description="Alert threshold")
    current_value: float = Field(..., description="Current value")
    status: str = Field(..., description="Alert status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    triggered_at: Optional[datetime] = Field(None, description="When alert was triggered")


class StressTestScenario(BaseModel):
    """Stress test scenario model."""

    scenario_id: str = Field(..., description="Scenario identifier")
    name: str = Field(..., description="Scenario name")
    description: str = Field(..., description="Scenario description")
    market_shock: Dict[str, float] = Field(..., description="Market shock parameters")
    time_horizon: int = Field(..., description="Time horizon in days")


class StressTestResult(BaseModel):
    """Stress test result model."""

    portfolio_id: str = Field(..., description="Portfolio identifier")
    scenario: StressTestScenario = Field(..., description="Test scenario")
    portfolio_value_before: float = Field(..., description="Portfolio value before shock")
    portfolio_value_after: float = Field(..., description="Portfolio value after shock")
    loss_amount: float = Field(..., description="Loss amount")
    loss_percentage: float = Field(..., description="Loss percentage")
    var_impact: float = Field(..., description="VaR impact")
    cvar_impact: float = Field(..., description="CVaR impact")
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorrelationAnalysis(BaseModel):
    """Correlation analysis model."""

    assets: List[str] = Field(..., description="Asset symbols")
    correlation_matrix: Dict[str, Dict[str, float]] = Field(..., description="Correlation matrix")
    average_correlation: float = Field(..., description="Average correlation")
    max_correlation: float = Field(..., description="Maximum correlation")
    min_correlation: float = Field(..., description="Minimum correlation")
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PerformanceMetrics(BaseModel):
    """Performance metrics model."""

    portfolio_id: str = Field(..., description="Portfolio identifier")
    total_return: float = Field(..., description="Total return")
    annualized_return: float = Field(..., description="Annualized return")
    volatility: float = Field(..., description="Volatility")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    calmar_ratio: float = Field(..., description="Calmar ratio")
    sortino_ratio: float = Field(..., description="Sortino ratio")
    information_ratio: float = Field(..., description="Information ratio")
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
