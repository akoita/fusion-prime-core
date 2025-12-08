# Sprint 03 Implementation Improvements & Recommendations

**Date**: 2025-10-27
**Scope**: Risk Engine, Compliance Service, and Infrastructure

---

## Executive Summary

The current implementation provides a solid foundation with real database connectivity and basic functionality. However, several improvements are recommended to meet Sprint 03 requirements and production-readiness standards.

**Priority Areas**:
1. 🔴 **Critical**: Replace parametric VaR with Historical Simulation
2. 🔴 **Critical**: Add real market price feeds (Chainlink/Pyth)
3. 🟡 **High**: Implement margin health monitoring and alerts
4. 🟡 **High**: Add KYC provider integration (Persona)
5. 🟢 **Medium**: Improve error handling and resilience
6. 🟢 **Medium**: Add comprehensive caching strategy
7. 🟢 **Medium**: Enhance observability and monitoring

---

## 1. Risk Engine Service Improvements

### 1.1 Critical: Replace Parametric VaR with Historical Simulation

**Current Implementation** (`services/risk-engine/app/core/risk_calculator.py:94-101`):
```python
# Using fixed volatility (parametric method)
volatility = 0.02  # 2% daily volatility (conservative for ETH)
z_score_95 = 1.645  # 95% confidence level

var_1d = total_value * volatility * z_score_95
var_7d = total_value * volatility * np.sqrt(7) * z_score_95
var_30d = total_value * volatility * np.sqrt(30) * z_score_95
```

**Issues**:
- Uses fixed 2% volatility (not market-responsive)
- Assumes normal distribution (crypto is fat-tailed)
- Doesn't account for actual price movements
- Sprint 03 requirement specifies Historical Simulation method

**Recommended Implementation**:
```python
async def calculate_historical_var(
    self,
    portfolio: Dict[str, float],  # {asset: amount}
    lookback_days: int = 252,     # 1 year
    confidence_level: float = 0.95
) -> Dict[str, float]:
    """
    Calculate VaR using Historical Simulation method.

    Steps:
    1. Fetch historical prices for all assets (252 days)
    2. Calculate daily returns for each asset
    3. Compute portfolio returns for each historical day
    4. Sort returns and find percentile for confidence level
    5. VaR = portfolio_value * (1 - percentile_return)
    """
    # Fetch from price oracle or cache
    historical_prices = await self.price_oracle.get_historical_prices(
        assets=list(portfolio.keys()),
        days=lookback_days
    )

    # Calculate daily returns
    returns = self._calculate_returns(historical_prices)

    # Compute portfolio returns
    portfolio_returns = self._calculate_portfolio_returns(
        returns, portfolio
    )

    # Sort and find VaR
    portfolio_returns.sort()
    var_index = int((1 - confidence_level) * len(portfolio_returns))
    var_return = portfolio_returns[var_index]

    portfolio_value = sum(portfolio.values())
    var_amount = portfolio_value * abs(var_return)

    return {
        "var_1d": var_amount,
        "var_7d": var_amount * np.sqrt(7),  # Scale with sqrt rule
        "var_30d": var_amount * np.sqrt(30),
        "method": "historical_simulation",
        "lookback_days": lookback_days,
        "confidence_level": confidence_level
    }
```

**Benefits**:
- Uses actual market behavior (no distribution assumptions)
- Captures fat tails and extreme events
- Updates automatically with new price data
- Meets Sprint 03 specification

**Implementation Priority**: 🔴 **CRITICAL** - Start immediately after price oracle

---

### 1.2 Critical: Add Margin Health Score Calculation

**Current State**: Basic margin ratio exists but doesn't match Sprint 03 spec

**Sprint 03 Requirement**:
```
margin_health_score = (total_collateral_usd - total_borrow_usd) / total_borrow_usd * 100
```

**Recommended Implementation**:
```python
async def calculate_margin_health(
    self, user_id: str
) -> Dict[str, Any]:
    """
    Calculate margin health score per Sprint 03 specification.

    Formula: (total_collateral_usd - total_borrow_usd) / total_borrow_usd * 100

    Thresholds:
    - health_score < 30: MARGIN_CALL
    - health_score < 15: LIQUIDATION
    - health_score >= 30: HEALTHY
    """
    async with self.session_factory() as session:
        # Get user's positions with real-time USD valuation
        positions = await self._get_user_positions(session, user_id)

        # Calculate totals using real-time prices from oracle
        total_collateral_usd = 0.0
        total_borrow_usd = 0.0

        for position in positions:
            # Get current USD price
            price = await self.price_oracle.get_price(
                position.asset_symbol
            )

            value_usd = position.amount * price

            if position.position_type == "collateral":
                total_collateral_usd += value_usd
            elif position.position_type == "borrow":
                total_borrow_usd += value_usd

        # Calculate health score
        if total_borrow_usd == 0:
            health_score = 100.0  # No borrows = max health
        else:
            health_score = (
                (total_collateral_usd - total_borrow_usd)
                / total_borrow_usd
                * 100
            )

        # Determine health status
        if health_score < 15:
            status = "LIQUIDATION"
            severity = "critical"
        elif health_score < 30:
            status = "MARGIN_CALL"
            severity = "high"
        elif health_score < 50:
            status = "WARNING"
            severity = "medium"
        else:
            status = "HEALTHY"
            severity = "low"

        # If margin call or liquidation, publish alert
        if health_score < 30:
            await self._publish_margin_alert(
                user_id, health_score, status, severity
            )

        return {
            "user_id": user_id,
            "health_score": round(health_score, 2),
            "status": status,
            "severity": severity,
            "total_collateral_usd": round(total_collateral_usd, 2),
            "total_borrow_usd": round(total_borrow_usd, 2),
            "net_position_usd": round(
                total_collateral_usd - total_borrow_usd, 2
            ),
            "liquidation_price": await self._calculate_liquidation_price(
                positions, total_collateral_usd, total_borrow_usd
            ),
            "calculated_at": datetime.utcnow().isoformat() + "Z"
        }

async def _publish_margin_alert(
    self, user_id: str, health_score: float,
    status: str, severity: str
):
    """Publish margin alert to Pub/Sub for alert service."""
    alert_message = {
        "alert_type": "margin_health",
        "user_id": user_id,
        "health_score": health_score,
        "status": status,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    await self.pubsub_publisher.publish(
        topic="alerts.margin.v1",
        message=json.dumps(alert_message)
    )
```

**Implementation Priority**: 🔴 **CRITICAL** - Required for Sprint 03

---

### 1.3 High: Add Price Oracle Integration

**Current State**: None - using fixed values

**Recommended Architecture**:

Create `services/risk-engine/app/integrations/price_oracle.py`:

```python
from typing import Dict, List, Optional
import httpx
from datetime import datetime, timedelta
import asyncio

class PriceOracleClient:
    """Client for fetching real-time and historical crypto prices."""

    def __init__(
        self,
        chainlink_endpoints: Dict[str, str],
        pyth_endpoint: str,
        cache_ttl: int = 60  # seconds
    ):
        self.chainlink_endpoints = chainlink_endpoints
        self.pyth_endpoint = pyth_endpoint
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, tuple[float, datetime]] = {}
        self.client = httpx.AsyncClient(timeout=5.0)

    async def get_price(
        self,
        asset_symbol: str,
        force_refresh: bool = False
    ) -> float:
        """
        Get current USD price for an asset.

        Priority:
        1. Cache (if fresh)
        2. Chainlink (primary)
        3. Pyth (fallback)
        4. Raise exception if all fail
        """
        # Check cache
        if not force_refresh and asset_symbol in self.cache:
            price, cached_at = self.cache[asset_symbol]
            age = (datetime.utcnow() - cached_at).total_seconds()
            if age < self.cache_ttl:
                return price

        # Try Chainlink first
        try:
            price = await self._fetch_chainlink_price(asset_symbol)
            self.cache[asset_symbol] = (price, datetime.utcnow())
            return price
        except Exception as e:
            logger.warning(
                f"Chainlink fetch failed for {asset_symbol}: {e}"
            )

        # Fallback to Pyth
        try:
            price = await self._fetch_pyth_price(asset_symbol)
            self.cache[asset_symbol] = (price, datetime.utcnow())
            return price
        except Exception as e:
            logger.error(
                f"Pyth fetch failed for {asset_symbol}: {e}"
            )
            raise PriceOracleException(
                f"Failed to fetch price for {asset_symbol}"
            )

    async def get_historical_prices(
        self,
        assets: List[str],
        days: int
    ) -> Dict[str, List[tuple[datetime, float]]]:
        """
        Fetch historical daily prices for multiple assets.

        Returns:
            {asset_symbol: [(timestamp, price), ...]}
        """
        # Fetch from price oracle service (deployed separately)
        # or from BigQuery cache
        tasks = [
            self._fetch_historical_asset_prices(asset, days)
            for asset in assets
        ]
        results = await asyncio.gather(*tasks)

        return dict(zip(assets, results))

    async def _fetch_chainlink_price(
        self, asset_symbol: str
    ) -> float:
        """Fetch from Chainlink data feed."""
        endpoint = self.chainlink_endpoints.get(asset_symbol)
        if not endpoint:
            raise ValueError(
                f"No Chainlink endpoint for {asset_symbol}"
            )

        response = await self.client.get(endpoint)
        response.raise_for_status()
        data = response.json()

        # Parse Chainlink response format
        return float(data["answer"]) / (10 ** data["decimals"])

    async def _fetch_pyth_price(self, asset_symbol: str) -> float:
        """Fetch from Pyth network."""
        # Implement Pyth integration
        # https://pyth.network/developers/price-feed-ids
        pass
```

**Integration with Risk Calculator**:

```python
class RiskCalculator:
    def __init__(self, database_url: str, price_oracle_url: str):
        self.database_url = database_url
        self.price_oracle = PriceOracleClient(
            chainlink_endpoints={
                "ETH": "https://sepolia.data.chain.link/eth-usd",
                "BTC": "https://sepolia.data.chain.link/btc-usd",
                "USDC": "https://sepolia.data.chain.link/usdc-usd",
            },
            pyth_endpoint="https://pyth.network/api/latest_price_feeds",
            cache_ttl=60
        )
```

**Implementation Priority**: 🔴 **CRITICAL** - Blocks historical VaR and margin health

---

### 1.4 Medium: Add Caching Layer

**Current State**: No caching - every request queries database

**Recommended Implementation**:

```python
from aiocache import Cache
from aiocache.serializers import JsonSerializer

class RiskCalculator:
    def __init__(self, database_url: str, price_oracle_url: str):
        # ... existing init ...
        self.cache = Cache(
            Cache.REDIS,  # Or MEMORY for simpler setup
            endpoint="redis://localhost",
            port=6379,
            serializer=JsonSerializer(),
            ttl=300  # 5 minutes
        )

    async def calculate_portfolio_risk(
        self, portfolio_id: Optional[str] = None
    ) -> Dict[str, Any]:
        # Check cache first
        cache_key = f"portfolio_risk:{portfolio_id}"
        cached_result = await self.cache.get(cache_key)

        if cached_result:
            # Add cache indicator
            cached_result["from_cache"] = True
            return cached_result

        # Calculate fresh
        result = await self._calculate_portfolio_risk_fresh(
            portfolio_id
        )

        # Cache result
        await self.cache.set(cache_key, result)
        result["from_cache"] = False

        return result
```

**Cache Invalidation Strategy**:
- Invalidate on new settlement events (Pub/Sub trigger)
- TTL-based expiration (5 minutes for risk metrics)
- Manual invalidation API for admin/testing

**Implementation Priority**: 🟢 **MEDIUM** - Performance optimization

---

## 2. Compliance Service Improvements

### 2.1 Critical: Add Persona KYC Integration

**Current State**: Basic KYC case management without external provider

**Recommended Implementation**:

Create `services/compliance/integrations/persona.py`:

```python
import httpx
from typing import Dict, Any
from datetime import datetime

class PersonaClient:
    """
    Integration with Persona identity verification.
    Docs: https://docs.withpersona.com/
    """

    def __init__(
        self,
        api_key: str,
        environment: str = "sandbox"
    ):
        self.api_key = api_key
        self.base_url = (
            "https://withpersona.com/api/v1"
            if environment == "production"
            else "https://api.sandbox.withpersona.com/api/v1"
        )
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Key-Inflection": "snake_case"
            },
            timeout=30.0
        )

    async def create_inquiry(
        self,
        inquiry_template_id: str,
        reference_id: str,
        fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new identity verification inquiry.

        Args:
            inquiry_template_id: Persona template ID
            reference_id: Your internal user ID
            fields: Pre-filled form fields

        Returns:
            Inquiry data with inquiry_id and session_token
        """
        payload = {
            "data": {
                "type": "inquiry",
                "attributes": {
                    "inquiry_template_id": inquiry_template_id,
                    "reference_id": reference_id,
                    "fields": fields
                }
            }
        }

        response = await self.client.post(
            f"{self.base_url}/inquiries",
            json=payload
        )
        response.raise_for_status()

        data = response.json()["data"]
        return {
            "inquiry_id": data["id"],
            "session_token": data["attributes"]["session_token"],
            "status": data["attributes"]["status"],
            "created_at": data["attributes"]["created_at"]
        }

    async def get_inquiry(self, inquiry_id: str) -> Dict[str, Any]:
        """Get inquiry status and results."""
        response = await self.client.get(
            f"{self.base_url}/inquiries/{inquiry_id}"
        )
        response.raise_for_status()

        data = response.json()["data"]
        return {
            "inquiry_id": data["id"],
            "status": data["attributes"]["status"],
            "fields": data["attributes"]["fields"],
            "verifications": data["attributes"]["verifications"],
            "created_at": data["attributes"]["created_at"],
            "completed_at": data["attributes"]["completed_at"]
        }

    async def webhook_verify_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """Verify Persona webhook signature."""
        import hmac
        import hashlib

        # Persona uses HMAC-SHA256
        expected = hmac.new(
            self.api_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
```

**Integration with Compliance Engine**:

```python
class ComplianceEngine:
    def __init__(
        self,
        database_url: str,
        persona_api_key: str
    ):
        # ... existing init ...
        self.persona = PersonaClient(
            api_key=persona_api_key,
            environment="sandbox"  # From config
        )

    async def initiate_kyc(
        self,
        user_id: str,
        document_type: str,
        document_data: Dict[str, Any],
        personal_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Create local KYC case
        case_id = f"kyc-{user_id}-{int(datetime.utcnow().timestamp())}"

        # Create Persona inquiry
        inquiry = await self.persona.create_inquiry(
            inquiry_template_id="itmpl_...",  # From config
            reference_id=case_id,
            fields={
                "name_first": personal_info.get("first_name"),
                "name_last": personal_info.get("last_name"),
                "email": personal_info.get("email"),
                # ... other fields
            }
        )

        # Store in database
        async with self.session_factory() as session:
            kyc_case = KYCCase(
                case_id=case_id,
                user_id=user_id,
                document_type=document_type,
                document_data=document_data,
                personal_info=personal_info,
                status="pending",
                persona_inquiry_id=inquiry["inquiry_id"],
                persona_session_token=inquiry["session_token"]
            )
            session.add(kyc_case)
            await session.commit()

        return {
            "case_id": case_id,
            "user_id": user_id,
            "status": "pending",
            "inquiry_id": inquiry["inquiry_id"],
            "session_token": inquiry["session_token"],
            # Frontend uses this to load Persona widget
            "verification_url": f"https://withpersona.com/verify?session-token={inquiry['session_token']}"
        }
```

**Implementation Priority**: 🟡 **HIGH** - Sprint 03 requirement

---

### 2.2 High: Implement AML Transaction Monitoring

**Current State**: Database models exist but no monitoring logic

**Recommended Implementation**:

Create `services/compliance/rules/aml_rules.py`:

```python
from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class AMLRule:
    """Base class for AML monitoring rules."""
    rule_id: str
    name: str
    severity: str  # "high", "medium", "low"
    enabled: bool = True

class VelocityRule(AMLRule):
    """
    Detect suspicious transaction velocity.

    Examples:
    - More than 10 transactions in 1 hour
    - More than $50k in 24 hours
    """

    def __init__(
        self,
        max_count: int,
        time_window_minutes: int,
        severity: str = "medium"
    ):
        super().__init__(
            rule_id="velocity_check",
            name="Transaction Velocity Check",
            severity=severity
        )
        self.max_count = max_count
        self.time_window_minutes = time_window_minutes

    async def evaluate(
        self,
        user_id: str,
        session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Check if user exceeds transaction velocity limits."""
        cutoff_time = datetime.utcnow() - timedelta(
            minutes=self.time_window_minutes
        )

        query = select(func.count(Transaction.id)).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.created_at >= cutoff_time
            )
        )

        result = await session.execute(query)
        count = result.scalar()

        if count > self.max_count:
            return {
                "rule_id": self.rule_id,
                "triggered": True,
                "severity": self.severity,
                "details": {
                    "transaction_count": count,
                    "time_window_minutes": self.time_window_minutes,
                    "threshold": self.max_count
                },
                "recommended_action": "manual_review"
            }

        return None

class GeoRestrictionRule(AMLRule):
    """Check for transactions from restricted countries."""

    def __init__(
        self,
        blocked_countries: List[str],
        severity: str = "high"
    ):
        super().__init__(
            rule_id="geo_restriction",
            name="Geographic Restriction Check",
            severity=severity
        )
        self.blocked_countries = set(blocked_countries)

    async def evaluate(
        self,
        user_id: str,
        transaction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if transaction originates from blocked country."""
        country_code = transaction.get("country_code")

        if country_code in self.blocked_countries:
            return {
                "rule_id": self.rule_id,
                "triggered": True,
                "severity": self.severity,
                "details": {
                    "country_code": country_code,
                    "blocked_countries": list(self.blocked_countries)
                },
                "recommended_action": "block_transaction"
            }

        return None

class AmountThresholdRule(AMLRule):
    """Flag transactions exceeding amount thresholds."""

    def __init__(
        self,
        threshold_usd: float,
        severity: str = "medium"
    ):
        super().__init__(
            rule_id="amount_threshold",
            name="Transaction Amount Threshold",
            severity=severity
        )
        self.threshold_usd = threshold_usd

    async def evaluate(
        self,
        transaction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if transaction exceeds threshold."""
        amount_usd = transaction.get("amount_usd", 0)

        if amount_usd > self.threshold_usd:
            return {
                "rule_id": self.rule_id,
                "triggered": True,
                "severity": self.severity,
                "details": {
                    "amount_usd": amount_usd,
                    "threshold_usd": self.threshold_usd
                },
                "recommended_action": "enhanced_due_diligence"
            }

        return None

class AMLMonitor:
    """Orchestrates AML rule evaluation."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.rules = [
            VelocityRule(max_count=10, time_window_minutes=60),
            GeoRestrictionRule(
                blocked_countries=[
                    "KP",  # North Korea
                    "IR",  # Iran
                    "SY",  # Syria
                    # ... OFAC sanctioned countries
                ]
            ),
            AmountThresholdRule(threshold_usd=10000)
        ]

    async def evaluate_transaction(
        self,
        user_id: str,
        transaction: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all AML rules for a transaction.

        Returns list of triggered alerts.
        """
        alerts = []

        async with self.session_factory() as session:
            for rule in self.rules:
                if not rule.enabled:
                    continue

                alert = await rule.evaluate(
                    user_id=user_id,
                    transaction=transaction,
                    session=session if hasattr(rule.evaluate, "session") else None
                )

                if alert:
                    # Store alert in database
                    aml_alert = AMLAlert(
                        alert_id=f"aml-{user_id}-{int(datetime.utcnow().timestamp())}",
                        user_id=user_id,
                        rule_id=alert["rule_id"],
                        severity=alert["severity"],
                        details=alert["details"],
                        status="new",
                        transaction_id=transaction.get("transaction_id")
                    )
                    session.add(aml_alert)
                    await session.commit()

                    alerts.append(alert)

        return alerts
```

**Implementation Priority**: 🟡 **HIGH** - Sprint 03 requirement

---

## 3. Infrastructure & Architecture Improvements

### 3.1 Add Circuit Breaker Pattern

**Current State**: Services will continuously retry failed external calls

**Recommended Implementation**:

```python
from circuitbreaker import circuit
from circuitbreaker import CircuitBreakerError

class PriceOracleClient:
    @circuit(failure_threshold=5, recovery_timeout=60)
    async def _fetch_chainlink_price(
        self, asset_symbol: str
    ) -> float:
        """
        Fetch with circuit breaker protection.

        If 5 consecutive failures, circuit opens for 60 seconds.
        """
        # ... existing implementation ...
```

**Benefits**:
- Prevents cascade failures
- Fast-fail when external service is down
- Automatic recovery detection

---

### 3.2 Add Request Deduplication (Idempotency)

**Current State**: Duplicate requests processed multiple times

**Recommended Implementation**:

```python
from functools import wraps
import hashlib

def idempotent(ttl: int = 3600):
    """Decorator for idempotent request handling."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate idempotency key
            key_data = f"{func.__name__}:{args}:{kwargs}"
            idempotency_key = hashlib.sha256(
                key_data.encode()
            ).hexdigest()

            # Check cache
            cached = await self.cache.get(
                f"idempotent:{idempotency_key}"
            )
            if cached:
                return cached

            # Execute
            result = await func(self, *args, **kwargs)

            # Cache result
            await self.cache.set(
                f"idempotent:{idempotency_key}",
                result,
                ttl=ttl
            )

            return result
        return wrapper
    return decorator

class RiskCalculator:
    @idempotent(ttl=300)  # 5 minutes
    async def calculate_portfolio_risk(
        self, portfolio_id: str
    ) -> Dict[str, Any]:
        # ... existing implementation ...
```

---

### 3.3 Add Structured Logging with Context

**Current State**: Basic logging without request context

**Recommended Implementation**:

```python
import structlog

logger = structlog.get_logger()

class RiskCalculator:
    async def calculate_portfolio_risk(
        self, portfolio_id: str
    ) -> Dict[str, Any]:
        log = logger.bind(
            portfolio_id=portfolio_id,
            operation="calculate_portfolio_risk"
        )

        log.info("starting_risk_calculation")

        try:
            result = await self._do_calculation()
            log.info(
                "risk_calculation_complete",
                var_1d=result["var_1d"],
                risk_score=result["risk_score"]
            )
            return result
        except Exception as e:
            log.error(
                "risk_calculation_failed",
                error=str(e),
                exc_info=True
            )
            raise
```

**Benefits**:
- Better debugging in Cloud Logging
- Request tracing
- Performance monitoring
- Error correlation

---

## 4. Testing Improvements

### 4.1 Add Property-Based Testing for VaR

**Recommended**: Use `hypothesis` for property-based testing

```python
from hypothesis import given, strategies as st
import pytest

@given(
    portfolio_value=st.floats(min_value=1000, max_value=1000000),
    volatility=st.floats(min_value=0.01, max_value=0.10),
    confidence=st.floats(min_value=0.90, max_value=0.99)
)
def test_var_properties(portfolio_value, volatility, confidence):
    """Test VaR calculation properties."""
    var = calculate_var(portfolio_value, volatility, confidence)

    # Property 1: VaR should be positive
    assert var > 0

    # Property 2: VaR should be less than portfolio value
    assert var < portfolio_value

    # Property 3: Higher confidence = higher VaR
    var_low = calculate_var(portfolio_value, volatility, 0.90)
    var_high = calculate_var(portfolio_value, volatility, 0.99)
    assert var_high > var_low
```

---

### 4.2 Add Integration Tests with Testcontainers

**Recommended**: Use real databases in tests

```python
from testcontainers.postgres import PostgresContainer
import pytest_asyncio

@pytest_asyncio.fixture
async def database():
    """Provide real PostgreSQL database for tests."""
    with PostgresContainer("postgres:15") as postgres:
        database_url = postgres.get_connection_url()
        # Run migrations
        await run_migrations(database_url)

        yield database_url

        # Cleanup handled by context manager

@pytest.mark.asyncio
async def test_risk_calculation_with_real_db(database):
    """Test against real database."""
    calculator = RiskCalculator(database)
    await calculator.initialize()

    # Test with real data
    result = await calculator.calculate_portfolio_risk("test-portfolio")

    assert result["risk_score"] > 0
    assert "var_1d" in result
```

---

## 5. Monitoring & Observability Improvements

### 5.1 Add Custom Metrics with OpenTelemetry

```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)

# Create metrics
risk_calculation_duration = meter.create_histogram(
    "risk_calculation_duration_seconds",
    description="Time to calculate portfolio risk",
    unit="seconds"
)

portfolio_value_gauge = meter.create_gauge(
    "portfolio_total_value_usd",
    description="Total portfolio value in USD",
    unit="USD"
)

class RiskCalculator:
    async def calculate_portfolio_risk(
        self, portfolio_id: str
    ) -> Dict[str, Any]:
        start_time = time.time()

        try:
            result = await self._do_calculation()

            # Record metrics
            duration = time.time() - start_time
            risk_calculation_duration.record(
                duration,
                {"portfolio_id": portfolio_id}
            )

            portfolio_value_gauge.set(
                result["total_value_usd"],
                {"portfolio_id": portfolio_id}
            )

            return result
        finally:
            pass
```

---

## 6. Security Improvements

### 6.1 Add Rate Limiting

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

app = FastAPI()

@app.on_event("startup")
async def startup():
    await FastAPILimiter.init(redis)

@app.get("/api/v1/risk/portfolio/{portfolio_id}")
@limiter(times=10, seconds=60)  # 10 requests per minute
async def get_portfolio_risk(portfolio_id: str):
    # ... implementation ...
```

---

### 6.2 Add API Key Rotation

```python
class APIKeyManager:
    """Manage API key rotation for external services."""

    def __init__(self, secret_manager_client):
        self.secret_manager = secret_manager_client
        self.keys_cache = {}
        self.cache_ttl = 300  # 5 minutes

    async def get_api_key(
        self, service_name: str
    ) -> str:
        """
        Get API key with automatic rotation support.

        Keys are cached for 5 minutes to reduce Secret Manager calls.
        """
        if service_name in self.keys_cache:
            key, cached_at = self.keys_cache[service_name]
            if (datetime.utcnow() - cached_at).seconds < self.cache_ttl:
                return key

        # Fetch from Secret Manager
        key = await self.secret_manager.access_secret_version(
            f"projects/fusion-prime/secrets/{service_name}-api-key/versions/latest"
        )

        self.keys_cache[service_name] = (key, datetime.utcnow())
        return key
```

---

## Implementation Roadmap

### Phase 1: Critical Path (Week 1)
1. ✅ Deploy Price Oracle Service with Chainlink integration
2. ✅ Implement Historical Simulation VaR
3. ✅ Add Margin Health Score calculation
4. ✅ Create Pub/Sub topic and margin event detection

### Phase 2: High Priority (Week 2)
5. Integrate Persona KYC provider
6. Implement AML transaction monitoring rules
7. Add circuit breaker and resilience patterns
8. Build Alert Notification Service

### Phase 3: Frontend & Monitoring (Week 2)
9. Bootstrap Risk Dashboard React app
10. Set up SLO dashboards and monitoring
11. Add comprehensive logging and metrics

### Phase 4: Optimization (Post-Sprint 03)
12. Add caching layer (Redis)
13. Implement request deduplication
14. Add property-based testing
15. Set up chaos engineering tests

---

## Conclusion

The current implementation provides a solid foundation, but Sprint 03 requirements demand:

1. **Historical Simulation VaR** (currently parametric)
2. **Real market price feeds** (currently fixed values)
3. **Margin health monitoring** (partially implemented)
4. **External KYC integration** (Persona)
5. **Production-grade resilience** (circuit breakers, caching, monitoring)

**Recommended Starting Point**: Build the Price Oracle Service first, as it unblocks both VaR improvements and margin health calculations.

**Estimated Effort**:
- Price Oracle Service: 1-2 days
- Historical VaR: 1 day
- Margin Health + Alerts: 1 day
- Persona Integration: 1-2 days
- AML Rules: 1 day
- Frontend Dashboard: 2-3 days
- Monitoring & SLOs: 1 day

**Total**: ~8-10 days of focused development
