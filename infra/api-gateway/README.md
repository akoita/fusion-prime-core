# API Gateway

Unified API Gateway for Fusion Prime services with rate limiting, authentication, and developer portal.

## Architecture

- **GCP API Gateway**: API Gateway service using OpenAPI 3.0 specification
- **Cloud Armor**: Rate limiting and DDoS protection
- **API Key Service**: Manages API keys and authentication
- **Developer Portal**: React app for API documentation and testing

## Components

### 1. API Gateway Configuration

`openapi.yaml` (OpenAPI 3.0) defines:
- All API endpoints
- Authentication requirements
- Rate limiting specifications
- Request/response schemas
- Backend service routing via `x-google-backend` annotations

### 2. API Key Management Service

Microservice for managing API keys:
- Create/revoke/rotate API keys
- Track usage and rate limits
- Tier management (free, pro, enterprise)

### 3. Rate Limiting

Implemented via Cloud Armor:
- Free tier: 100 req/min
- Pro tier: 1000 req/min
- Enterprise tier: 10000 req/min

## Deployment

### API Gateway (GCP API Gateway)

```bash
# Deploy via Cloud Build (recommended)
gcloud builds submit --config=infra/api-gateway/cloudbuild.yaml \
  --project=$PROJECT_ID

# Or deploy manually:
# 1. Create API Gateway API
gcloud api-gateway apis create fusion-prime-api \
  --project=$PROJECT_ID \
  --display-name="Fusion Prime API Gateway" \
  --location=us-central1

# 2. Create API Config from OpenAPI spec
gcloud api-gateway api-configs create config-1 \
  --api=fusion-prime-api \
  --openapi-spec=infra/api-gateway/openapi.yaml \
  --project=$PROJECT_ID \
  --location=us-central1

# 3. Create Gateway
gcloud api-gateway gateways create fusion-prime-gateway \
  --api=fusion-prime-api \
  --api-config=config-1 \
  --project=$PROJECT_ID \
  --location=us-central1
```

### API Key Service

```bash
cd infra/api-gateway/api-key-service
gcloud builds submit --config=cloudbuild.yaml
```

## Usage

### Create API Key

```bash
curl -X POST https://api-key-service.run.app/api/v1/keys \
  -H "Content-Type: application/json" \
  -d '{
    "key_name": "My App",
    "tier": "pro"
  }'
```

### Use API Key

```bash
curl https://api.fusionprime.dev/v1/cross-chain/settlement \
  -H "X-API-Key: fp_..."
```

## Developer Portal

See `frontend/developer-portal/` for the React-based developer portal.
