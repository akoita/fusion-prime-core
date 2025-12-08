# Cross-Chain Integration Service - SSL Connection Fix

## Issue
The service was failing with: `connect() got an unexpected keyword argument 'sslmode'`

## Root Cause
- `asyncpg` doesn't support `sslmode` as a URL query parameter like `psycopg2` does
- The `DATABASE_URL` from Secret Manager includes `?sslmode=require`
- SQLAlchemy was passing this through to asyncpg, causing the error

## Fix Applied
Updated `infrastructure/db/session.py` to:
1. Parse and remove `sslmode` from the URL query string
2. Convert `sslmode=require` to `ssl=True` for asyncpg
3. Pass SSL configuration via `connect_args` instead of URL parameters

## Deployment Steps

1. **Build and deploy the service:**
   ```bash
   cd services/cross-chain-integration
   gcloud builds submit --config=cloudbuild.yaml
   ```

2. **Verify deployment:**
   ```bash
   # Check service logs
   gcloud run services logs read cross-chain-integration-service \
     --region=us-central1 \
     --limit=50

   # Test health endpoint
   curl https://cross-chain-integration-service-*.run.app/health
   ```

3. **Run integration tests:**
   ```bash
   cd /home/koita/dev/web3/fusion-prime
   pytest tests/test_cross_chain_integration_full.py -v
   ```

## Expected Results After Deployment

- Database connection should succeed without SSL errors
- `/api/v1/orchestrator/settlement` endpoint should work
- Message flow tests should pass (or skip gracefully if bridge not configured)

## Related Files
- `services/cross-chain-integration/infrastructure/db/session.py` - Fixed SSL handling
- `tests/test_cross_chain_integration_full.py` - Integration tests
