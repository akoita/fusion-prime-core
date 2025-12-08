# x402 Payment Protocol Integration for Fusion Prime API Gateway

**Version**: 1.0.0
**Status**: 🚀 Proposed
**Created**: 2025-01-28
**Author**: Architecture Team
**Related Sprint**: Sprint 04 (Enhancement) / Sprint 05 (Full Implementation)

---

## Overview

This specification proposes integrating the [x402 Payment Protocol](https://www.x402.org/) into Fusion Prime's API Gateway to enable frictionless, pay-per-use API access. This allows institutional clients, developers, and automated systems to access Fusion Prime's APIs without traditional subscription models, registration requirements, or complex payment flows.

### Motivation

- **Eliminate Payment Friction**: Remove the need for credit cards, subscription management, and account creation for API access
- **Enable Micropayments**: Allow pay-per-request pricing models for expensive operations (risk calculations, cross-chain settlements)
- **AI Agent Support**: Enable autonomous agents and automated trading systems to pay for API access dynamically
- **Instant Settlement**: Blockchain-native payments settle in ~2 seconds vs traditional payment rails
- **Privacy-Preserving**: No email, OAuth, or personal information required

### Use Cases

1. **Institutional API Access**: Hedge funds pay for risk calculations and portfolio analytics on-demand
2. **Automated Trading Systems**: Trading bots pay per API call for real-time settlement status
3. **Developer Sandbox**: Developers test integrations with small payments instead of complex billing
4. **Cross-Chain Service Calls**: Pay for cross-chain message monitoring and settlement orchestration
5. **Compliance Checks**: Pay-per-check for AML screening and identity verification

---

## Specification: x402-Enhanced API Gateway

### Architecture Overview

```
┌─────────────┐
│ API Client  │
│ (Developer  │
│ / Agent /   │
│ Institution)│
└──────┬──────┘
       │
       │ HTTP Request + X-PAYMENT header
       │
┌──────▼──────────────────────────────────────────┐
│         API Gateway (Cloud Endpoints)            │
│  ┌────────────────────────────────────────────┐ │
│  │   x402 Payment Middleware                  │ │
│  │  - Verify X-PAYMENT header                 │ │
│  │  - Check payment requirements              │ │
│  │  - Validate payment payload                │ │
│  │  - Forward to Facilitator for settlement   │ │
│  └────────────────────────────────────────────┘ │
│                  │                              │
│                  │ Valid Payment?               │
│                  │                              │
┌──────────────────▼──────────────────────────────┐
│        Backend Services                         │
│  - Risk Engine                                  │
│  - Settlement Service                           │
│  - Compliance Service                           │
│  - Fiat Gateway                                 │
└─────────────────────────────────────────────────┘
```

### Payment Flow

1. **Client Request**: Client sends HTTP request with optional `X-PAYMENT` header containing base64-encoded payment payload
2. **Payment Check**: Middleware checks if endpoint requires payment
3. **Payment Required (402)**: If no valid payment, return `HTTP 402` with `Payment Required Response`
4. **Payment Verification**: Valid payment is verified via Facilitator service (or local verification)
5. **Payment Settlement**: Payment is settled on-chain via Facilitator
6. **Request Processing**: Validated request proceeds to backend service
7. **Response**: Backend response includes `X-PAYMENT-RESPONSE` header with settlement confirmation

---

## Enhanced x402 Protocol Features

### Feature 1: Multi-Tier Payment Requirements

**Problem**: Different API endpoints have different computational costs and should support different pricing tiers.

**Solution**: Extend `paymentRequirements` to support tiered pricing with usage-based tiers.

```typescript
interface EnhancedPaymentRequirements {
  // ... existing x402 fields ...

  // NEW: Tiered pricing structure
  pricingTiers?: {
    tier: "standard" | "premium" | "enterprise";
    amountRequired: string; // in atomic units
    features: string[]; // e.g., ["realtime", "bulk", "priority"]
  }[];

  // NEW: Usage-based pricing for expensive operations
  usageBasedPricing?: {
    baseAmount: string; // base fee per request
    perUnitFee?: {
      unit: "risk_calculation" | "settlement" | "compliance_check";
      amount: string;
    };
    maxAmountCap: string; // maximum charge per request
  };
}
```

### Feature 2: Payment Credits / Pre-Authorization

**Problem**: High-frequency clients shouldn't pay per-request to reduce blockchain transactions and latency.

**Solution**: Support payment credits that can be pre-authorized and consumed incrementally.

```typescript
interface PaymentCredits {
  creditId: string; // unique credit session identifier
  preAuthorizedAmount: string; // total credits authorized
  consumedAmount: string; // credits used so far
  expiresAt: number; // Unix timestamp
  perRequestDeduction: string; // amount deducted per API call
}

interface CreditPaymentPayload {
  x402Version: number;
  scheme: "credit" | "exact";
  network: string;
  payload: {
    creditId: string;
    signature: string; // signature proving credit ownership
  };
}
```

### Feature 3: Payment Receipt & Audit Trail

**Problem**: Enterprise clients need receipts and audit trails for compliance and accounting.

**Solution**: Enhanced response headers with payment receipts and transaction references.

```typescript
interface PaymentReceipt {
  paymentId: string; // unique payment identifier
  timestamp: number; // Unix timestamp
  amount: string; // amount paid
  asset: string; // token contract address
  network: string; // blockchain network
  txHash: string; // blockchain transaction hash
  apiEndpoint: string; // endpoint accessed
  requestId: string; // API request identifier
}

// Response header: X-PAYMENT-RECEIPT (base64 JSON)
```

### Feature 4: Dynamic Pricing Based on Load

**Problem**: During high-load periods, API calls should cost more to manage demand.

**Problem**: Support dynamic pricing that adjusts based on system load or time-of-day.

```typescript
interface DynamicPricing {
  baseAmount: string;
  loadMultiplier?: number; // e.g., 1.0 = normal, 2.0 = 2x during peak
  timeOfDayMultiplier?: {
    peakHours: number[]; // e.g., [9, 10, 11, 14, 15, 16] (9am-5pm UTC)
    multiplier: number;
  };
  currentAmount: string; // calculated current price
  priceUpdateInterval: number; // seconds between price updates
}
```

### Feature 5: Payment Aggregation / Batching

**Problem**: Multiple API calls in a short window should be batched into a single payment.

**Solution**: Support payment aggregation windows where multiple requests share one payment.

```typescript
interface PaymentAggregation {
  aggregationWindow: number; // seconds (e.g., 60 = 1 minute window)
  maxRequestsPerPayment: number; // max requests in one payment
  totalAmount: string; // aggregated amount for all requests
  requestIds: string[]; // IDs of requests included in payment
}
```

---

## Implementation Plan

### Phase 1: Core x402 Integration (Week 1-2)

**Deliverables**:
- x402 payment middleware for FastAPI/Cloud Endpoints
- Payment verification service
- Facilitator integration (self-hosted or use public facilitator)
- Basic payment flow end-to-end

**Tasks**:
1. Create `services/payment-gateway/` service
   - x402 middleware implementation
   - Payment verification logic
   - Facilitator client

2. Integrate with API Gateway
   - Add middleware to Cloud Endpoints configuration
   - Configure payment requirements per endpoint

3. Payment verification
   - Local verification for EVM chains (USDC on Base, Ethereum, Polygon)
   - Facilitator integration for verification

4. Settlement handling
   - On-chain settlement via Facilitator
   - Payment receipt generation

5. Testing
   - Unit tests for payment verification
   - Integration tests with testnet payments
   - E2E tests with mock clients

### Phase 2: Enhanced Features (Week 3-4)

**Deliverables**:
- Payment credits/pre-authorization
- Payment receipts and audit trail
- Dynamic pricing support

**Tasks**:
1. Payment Credits System
   - Smart contract for credit management (optional)
   - Credit session management
   - Credit consumption tracking

2. Payment Receipt System
   - Receipt generation service
   - Receipt storage (database)
   - Receipt retrieval API

3. Dynamic Pricing
   - Load-based pricing calculation
   - Price update mechanism
   - Client pricing transparency

### Phase 3: Advanced Features (Week 5-6)

**Deliverables**:
- Payment aggregation
- Multi-tier pricing
- Usage-based pricing

**Tasks**:
1. Payment Aggregation
   - Aggregation window management
   - Request batching logic
   - Aggregated payment settlement

2. Tiered Pricing
   - Pricing tier configuration
   - Tier selection logic
   - Feature gating based on tier

3. Usage-Based Pricing
   - Unit-based fee calculation
   - Cost estimation API
   - Usage tracking

---

## Technical Specifications

### API Gateway Middleware

```python
from fastapi import Request, HTTPException, Response
from typing import Optional, Dict, Any
import base64
import json

class X402PaymentMiddleware:
    """x402 payment middleware for API Gateway."""

    def __init__(
        self,
        facilitator_url: str,
        payment_config: Dict[str, Any],
        verify_locally: bool = True
    ):
        self.facilitator_url = facilitator_url
        self.payment_config = payment_config  # endpoint -> payment requirements
        self.verify_locally = verify_locally

    async def __call__(self, request: Request, call_next):
        """Middleware to verify x402 payments."""

        # Skip payment check for health/status endpoints
        if request.url.path in ["/health", "/status", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Get payment requirements for this endpoint
        endpoint_key = f"{request.method}:{request.url.path}"
        payment_req = self.payment_config.get(endpoint_key)

        if not payment_req:
            # Endpoint doesn't require payment
            return await call_next(request)

        # Extract X-PAYMENT header
        payment_header = request.headers.get("X-PAYMENT")

        if not payment_header:
            # Return 402 Payment Required
            return self._payment_required_response(payment_req, request.url.path)

        # Verify payment
        payment_payload = self._decode_payment_header(payment_header)
        is_valid = await self._verify_payment(payment_payload, payment_req)

        if not is_valid:
            return self._payment_required_response(payment_req, request.url.path, "Invalid payment")

        # Settle payment (async, non-blocking)
        settlement_task = self._settle_payment(payment_payload, payment_req)

        # Process request
        response = await call_next(request)

        # Add payment receipt to response
        settlement_result = await settlement_task
        if settlement_result:
            receipt = self._generate_receipt(payment_payload, payment_req, settlement_result)
            response.headers["X-PAYMENT-RECEIPT"] = base64.b64encode(
                json.dumps(receipt).encode()
            ).decode()

        return response

    def _payment_required_response(
        self,
        payment_req: Dict[str, Any],
        resource: str,
        error: Optional[str] = None
    ) -> Response:
        """Return HTTP 402 with payment requirements."""
        payment_required = {
            "x402Version": 1,
            "accepts": [payment_req],
            "error": error
        }
        return Response(
            status_code=402,
            content=json.dumps(payment_required),
            media_type="application/json",
            headers={
                "X-Payment-Required": "true",
                "Content-Type": "application/json"
            }
        )

    async def _verify_payment(
        self,
        payment_payload: Dict[str, Any],
        payment_req: Dict[str, Any]
    ) -> bool:
        """Verify payment via facilitator or locally."""
        if self.verify_locally and payment_payload["scheme"] == "exact":
            # Local verification for exact scheme on EVM
            return await self._verify_locally(payment_payload, payment_req)
        else:
            # Use facilitator
            return await self._verify_via_facilitator(payment_payload, payment_req)

    async def _settle_payment(
        self,
        payment_payload: Dict[str, Any],
        payment_req: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Settle payment via facilitator."""
        # Async settlement (don't block request)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.facilitator_url}/settle",
                json={
                    "x402Version": payment_payload["x402Version"],
                    "paymentHeader": base64.b64encode(
                        json.dumps(payment_payload).encode()
                    ).decode(),
                    "paymentRequirements": payment_req
                }
            )
            return response.json() if response.status_code == 200 else None
```

### Payment Configuration

```yaml
# config/x402-payment-config.yaml
payment_requirements:
  "POST:/api/v1/risk/calculate":
    scheme: "exact"
    network: "base-sepolia"
    maxAmountRequired: "1000000"  # $1.00 USDC (6 decimals)
    resource: "/api/v1/risk/calculate"
    description: "Risk calculation for portfolio"
    mimeType: "application/json"
    payTo: "0x..." # Fusion Prime treasury address
    maxTimeoutSeconds: 30
    asset: "0x036CbD53842c5426634e7929541eC2318f3dCF7e"  # USDC on Base Sepolia
    extra:
      name: "USD Coin"
      version: "2"

  "GET:/api/v1/settlement/status/{settlement_id}":
    scheme: "exact"
    network: "base-sepolia"
    maxAmountRequired: "100000"  # $0.10 USDC
    resource: "/api/v1/settlement/status/{settlement_id}"
    description: "Settlement status query"
    payTo: "0x..."
    asset: "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

  "POST:/api/v1/compliance/aml-check":
    scheme: "exact"
    network: "base-sepolia"
    maxAmountRequired: "500000"  # $0.50 USDC
    resource: "/api/v1/compliance/aml-check"
    description: "AML compliance screening"
    payTo: "0x..."
    asset: "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
```

### Database Schema

```sql
-- Payment receipts and audit trail
CREATE TABLE payment_receipts (
    receipt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id VARCHAR(255) UNIQUE NOT NULL,
    request_id VARCHAR(255),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    amount VARCHAR(78) NOT NULL, -- uint256 as string
    asset VARCHAR(255) NOT NULL,
    network VARCHAR(50) NOT NULL,
    tx_hash VARCHAR(255),
    payer_address VARCHAR(255),
    payee_address VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    x402_version INTEGER NOT NULL,
    scheme VARCHAR(50) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_payment_receipts_payment_id ON payment_receipts(payment_id);
CREATE INDEX idx_payment_receipts_payer ON payment_receipts(payer_address);
CREATE INDEX idx_payment_receipts_timestamp ON payment_receipts(timestamp);
CREATE INDEX idx_payment_receipts_endpoint ON payment_receipts(endpoint);

-- Payment credits (pre-authorization)
CREATE TABLE payment_credits (
    credit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_address VARCHAR(255) NOT NULL,
    pre_authorized_amount VARCHAR(78) NOT NULL,
    consumed_amount VARCHAR(78) DEFAULT '0',
    per_request_deduction VARCHAR(78) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- active, exhausted, expired
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_payment_credits_client ON payment_credits(client_address);
CREATE INDEX idx_payment_credits_status ON payment_credits(status);
CREATE INDEX idx_payment_credits_expires ON payment_credits(expires_at);
```

---

## Security Considerations

1. **Payment Verification**: Always verify payments before processing requests (never trust, always verify)
2. **Replay Protection**: Track processed payment IDs to prevent double-spending
3. **Amount Validation**: Verify payment amount matches or exceeds required amount
4. **Network Validation**: Ensure payment is on accepted network (prevent cross-network attacks)
5. **Signature Verification**: For local verification, verify EIP-712 signatures correctly
6. **Facilitator Security**: If using third-party facilitator, verify facilitator authenticity
7. **Rate Limiting**: Combine x402 with rate limiting to prevent payment spam

---

## Integration Points

### API Gateway (Sprint 04)
- Add x402 middleware to Cloud Endpoints configuration
- Configure payment requirements per API route
- Enable/disable x402 per endpoint via configuration

### Fiat Gateway (Sprint 04)
- Accept x402 payments for fiat on/off-ramp service fees
- Alternative payment method alongside Circle/Stripe

### Developer Portal (Sprint 04/05)
- x402 payment demonstration
- Payment testing tools
- Receipt lookup interface

### SDKs (Sprint 05)
- TypeScript SDK: x402 client integration
- Python SDK: x402 client integration
- Auto-handle 402 responses and payment flows

---

## Success Metrics

- **Payment Success Rate**: >99% payment verification success
- **Payment Latency**: <500ms payment verification overhead
- **API Adoption**: 30%+ of API calls use x402 within 3 months
- **Transaction Cost**: <$0.01 per payment (gas-efficient settlement)
- **Developer Experience**: <5 minutes to integrate x402 payments

---

## Dependencies

- x402 Python SDK (or implementation)
- x402 Facilitator service (self-hosted or public)
- Supported networks: Base, Ethereum, Polygon (at minimum)
- Supported assets: USDC (at minimum)

---

## Future Enhancements

1. **Multi-Asset Support**: Accept payments in ETH, DAI, other stablecoins
2. **Cross-Chain Payments**: Pay on one chain, access API on another
3. **Payment Subscriptions**: Monthly pre-paid credits
4. **Volume Discounts**: Lower per-request fees for high-volume clients
5. **Payment Analytics**: Dashboard for payment trends and revenue

---

## References

- [x402 Protocol Specification](https://github.com/coinbase/x402)
- [x402 Official Website](https://www.x402.org/)
- [x402Scan Explorer](https://github.com/Merit-Systems/x402scan)
- [EIP-712: Typed structured data hashing and signing](https://eips.ethereum.org/EIPS/eip-712)

---

## Appendix: Example Payment Flow

### Client Request (No Payment)

```bash
curl https://api.fusionprime.io/api/v1/risk/calculate \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id": "abc123"}'
```

**Response (402 Payment Required)**:
```json
HTTP/1.1 402 Payment Required
Content-Type: application/json
X-Payment-Required: true

{
  "x402Version": 1,
  "accepts": [
    {
      "scheme": "exact",
      "network": "base-sepolia",
      "maxAmountRequired": "1000000",
      "resource": "/api/v1/risk/calculate",
      "description": "Risk calculation for portfolio",
      "mimeType": "application/json",
      "payTo": "0xFusionPrimeTreasuryAddress",
      "maxTimeoutSeconds": 30,
      "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
      "extra": {
        "name": "USD Coin",
        "version": "2"
      }
    }
  ],
  "error": null
}
```

### Client Request (With Payment)

```bash
curl https://api.fusionprime.io/api/v1/risk/calculate \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: eyJ4NDAyVmVyc2lvbiI6MSwic2NoZW1lIjoiZXhhY3QiLCJuZXR3b3JrIjoiYmFzZS1zZXBvbGlhIiwicGF5bG9hZCI6e319" \
  -d '{"portfolio_id": "abc123"}'
```

**Response (200 OK with Receipt)**:
```json
HTTP/1.1 200 OK
Content-Type: application/json
X-PAYMENT-RECEIPT: eyJwYXltZW50SWQiOiIuLi4iLCJ0eEhhc2giOiIuLi4ifQ==

{
  "portfolio_id": "abc123",
  "total_value_usd": "1000000.00",
  "margin_health": 0.85,
  ...
}
```

---

**Status**: ✅ Specification Complete - Ready for Implementation
**Next Steps**: Add to Sprint 04/05 planning, begin Phase 1 implementation
