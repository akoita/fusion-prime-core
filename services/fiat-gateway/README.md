# Fiat Gateway Service

Handles fiat on/off-ramps via Circle USDC and Stripe payment processing.

## Features

- **On-Ramp**: Convert fiat (USD, EUR) to stablecoins (USDC) via Circle or Stripe
- **Off-Ramp**: Convert stablecoins to fiat and withdraw to bank accounts
- **Transaction Management**: Track payment status and history
- **Webhook Integration**: Receive payment callbacks from providers

## API Endpoints

### Payments

- `POST /api/v1/payments/on-ramp` - Initiate fiat to stablecoin conversion
- `POST /api/v1/payments/off-ramp` - Initiate stablecoin to fiat conversion
- `GET /api/v1/payments/status/{transaction_id}` - Get transaction status

### Transactions

- `GET /api/v1/transactions/` - List transactions (with filters)
- `GET /api/v1/transactions/{transaction_id}` - Get transaction details

### Webhooks

- `POST /api/v1/webhooks/circle` - Circle payment callbacks
- `POST /api/v1/webhooks/stripe` - Stripe payment callbacks

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Circle API
CIRCLE_API_KEY=your_circle_api_key
CIRCLE_BASE_URL=https://api-sandbox.circle.com

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8080
```

## Deployment

See `cloudbuild.yaml` for Cloud Run deployment configuration.
