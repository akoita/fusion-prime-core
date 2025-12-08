# Persona KYC Integration - Implementation Complete

## Overview

This document describes the **Persona KYC integration** implemented in the Compliance Service as part of the ERC-734/735 identity strategy. This integration provides real, production-ready KYC verification using Persona's identity verification platform.

## What Was Implemented

### 1. Persona API Client (`app/integrations/persona_client.py`)

A comprehensive client for the Persona API with the following capabilities:

- **Inquiry Creation**: Create Persona verification inquiries for users
- **Inquiry Status**: Retrieve inquiry status and details
- **Manual Controls**: Approve/decline inquiries (for testing/admin)
- **Webhook Verification**: Verify webhook signatures for security
- **Health Check**: Monitor Persona API connectivity

```python
from app.integrations.persona_client import PersonaKYCClient

client = PersonaKYCClient(api_key="...", environment="sandbox")
inquiry = await client.create_inquiry(
    user_id="user_123",
    reference_id="kyc-case-456"
)
```

### 2. Enhanced Database Models (`infrastructure/db/models.py`)

Updated `KYCCase` model with new fields:

**Persona Integration Fields:**
- `persona_inquiry_id`: Persona inquiry ID
- `persona_session_token`: Session token for embedded verification flow
- `persona_status`: Persona inquiry status (completed, failed, etc.)

**Identity Claim References (for future ERC-735 integration):**
- `kyc_claim_id`: On-chain claim ID
- `kyc_claim_tx_hash`: Blockchain transaction hash

**Database Index:**
- Index on `persona_inquiry_id` for efficient webhook lookups

### 3. Updated Compliance Engine (`app/core/compliance_engine_production.py`)

Enhanced KYC flow with three new methods:

#### `initiate_kyc()` - Enhanced
Now creates both:
1. Database KYC case
2. Persona inquiry with session token

Returns `persona_session_token` for frontend to embed Persona verification flow.

#### `process_persona_webhook()` - New
Processes Persona webhook callbacks:
- Maps Persona status to internal KYC status
- Updates verification scores
- Logs when ready for claim issuance

**Status Mapping:**
- `completed` → `verified` (score: 1.0)
- `failed`/`declined` → `rejected` (score: 0.0)
- `needs_review` → `review` (score: 0.5)
- Other → `pending`

#### `update_kyc_claim()` - New
Called by Identity Service to store claim references after on-chain issuance.

### 4. Webhook Endpoint (`app/routes/webhooks.py`)

New webhook handler for Persona callbacks:

**Endpoint:** `POST /webhooks/persona/inquiry`

**Features:**
- Signature verification for security
- Handles all inquiry events (created, completed, failed, etc.)
- Updates KYC case status automatically
- Logs verification completion

**Events Supported:**
- `inquiry.created`
- `inquiry.started`
- `inquiry.completed`
- `inquiry.failed`
- `inquiry.needs-review`
- `inquiry.approved`
- `inquiry.declined`

### 5. Compliance API Endpoint (`app/routes/compliance.py`)

New endpoint for Identity Service integration:

**Endpoint:** `PUT /compliance/kyc/{case_id}/claim`

**Purpose:** Identity Service calls this after issuing an on-chain claim to update the KYC case with claim references.

### 6. Database Migration

**File:** `alembic/versions/002_add_persona_identity_fields.py`

Adds all new fields to `kyc_cases` table with proper indexing.

**To run migration:**
```bash
cd /home/koita/dev/web3/fusion-prime/services/compliance
alembic upgrade head
```

## User Flow

### Phase 1: KYC Initiation

1. **Frontend calls:** `POST /compliance/kyc`
   ```json
   {
     "user_id": "user_123",
     "document_type": "passport",
     "document_data": {...},
     "personal_info": {...}
   }
   ```

2. **Backend creates:**
   - KYC case in database
   - Persona inquiry via API

3. **Backend returns:**
   ```json
   {
     "case_id": "kyc-user_123-1699123456",
     "persona_inquiry_id": "inq_ABC123",
     "persona_session_token": "sess_XYZ789",
     "status": "pending"
   }
   ```

### Phase 2: User Verification

4. **Frontend embeds Persona Client:**
   ```typescript
   import { Client } from 'persona';

   const client = new Client({
     templateId: 'tmpl_...',
     environment: 'sandbox',
     onComplete: ({ inquiryId }) => {
       // Verification submitted
     }
   });

   client.open(sessionToken);
   ```

5. **User completes verification** in Persona UI:
   - Photo ID upload
   - Selfie capture
   - Liveness check

### Phase 3: Webhook Callback

6. **Persona sends webhook:** `POST /webhooks/persona/inquiry`
   ```json
   {
     "type": "inquiry.completed",
     "data": {
       "id": "inq_ABC123",
       "attributes": {
         "status": "completed",
         "reference_id": "kyc-user_123-1699123456"
       }
     }
   }
   ```

7. **Backend processes:**
   - Verifies webhook signature
   - Finds KYC case by `persona_inquiry_id`
   - Updates status to "verified"
   - Logs: "Ready to issue identity claim"

### Phase 4: Claim Issuance (Future - Identity Service)

8. **Identity Service** (to be implemented):
   - Detects verified KYC case
   - Issues ERC-735 claim on blockchain
   - Calls: `PUT /compliance/kyc/{case_id}/claim`

9. **KYC case updated** with claim references

## Configuration Required

### Environment Variables

```bash
# Persona Configuration
PERSONA_API_KEY=persona_sandbox_...
PERSONA_WEBHOOK_SECRET=whsec_...
PERSONA_TEMPLATE_ID=tmpl_...
PERSONA_ENVIRONMENT=sandbox  # or 'production'

# Database
DATABASE_URL=postgresql+asyncpg://...
```

### Persona Dashboard Setup

1. **Create Inquiry Template:**
   - Go to Persona Dashboard → Templates
   - Configure verification steps (ID + Selfie)
   - Note the `template_id`

2. **Configure Webhook:**
   - URL: `https://<your-domain>/webhooks/persona/inquiry`
   - Events: All inquiry events
   - Copy webhook secret to `PERSONA_WEBHOOK_SECRET`

## API Endpoints Summary

### New Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/webhooks/persona/inquiry` | Receive Persona webhooks |
| GET | `/webhooks/persona/health` | Webhook health check |
| PUT | `/compliance/kyc/{case_id}/claim` | Update claim references |

### Modified Endpoints

| Method | Endpoint | Changes |
|--------|----------|---------|
| POST | `/compliance/kyc` | Now returns `persona_session_token` |
| GET | `/compliance/kyc/{case_id}` | Now includes Persona and claim fields |

## Testing

### Manual Testing

1. **Start service:**
   ```bash
   cd /home/koita/dev/web3/fusion-prime/services/compliance
   python -m app.main
   ```

2. **Create KYC case:**
   ```bash
   curl -X POST http://localhost:8000/compliance/kyc \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "test_user_1",
       "document_type": "passport",
       "document_data": {},
       "personal_info": {}
     }'
   ```

3. **Check webhook endpoint:**
   ```bash
   curl http://localhost:8000/webhooks/persona/health
   ```

### Webhook Testing

Use Persona Dashboard → Webhooks → Test to send test events.

## Next Steps

### Immediate (Week 1-2)

1. **Deploy to Cloud Run:**
   - Update `cloudbuild.yaml` if needed
   - Deploy with Persona environment variables
   - Configure Persona webhook to point to Cloud Run URL

2. **Run Database Migration:**
   ```bash
   alembic upgrade head
   ```

3. **Test End-to-End:**
   - Create test inquiry
   - Complete verification in Persona sandbox
   - Verify webhook processing

### Future (Week 3-4) - Identity Service

The next phase involves creating the **Identity Service** to handle on-chain claim issuance:

1. **Smart Contracts:**
   - Deploy Identity.sol (ERC-734/735)
   - Deploy IdentityFactory.sol
   - Deploy ClaimIssuerRegistry.sol

2. **Identity Service:**
   - Monitor verified KYC cases
   - Issue claims on blockchain
   - Call `/compliance/kyc/{case_id}/claim` to update references

3. **Frontend Integration:**
   - Embed Persona Client
   - Display claim status
   - Show blockchain verification

## Architecture Diagram

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │ 1. Initiate KYC
       ↓
┌─────────────────────────┐
│  Compliance Service     │
│  ┌──────────────────┐   │
│  │ POST /kyc        │   │
│  │ - Create case    │   │
│  │ - Call Persona   │   │
│  └────┬─────────────┘   │
└───────┼─────────────────┘
        │ 2. Create inquiry
        ↓
┌──────────────────┐
│  Persona API     │
│  - Verify ID     │
│  - Liveness      │
└────────┬─────────┘
         │ 3. Webhook
         ↓
┌─────────────────────────┐
│  Compliance Service     │
│  ┌──────────────────┐   │
│  │ Webhook Handler  │   │
│  │ - Update status  │   │
│  │ - Log verified   │   │
│  └──────────────────┘   │
└─────────────────────────┘
         │ 4. Detected
         ↓
┌─────────────────────────┐
│  Identity Service       │  (Future)
│  ┌──────────────────┐   │
│  │ Claim Issuance   │   │
│  │ - Issue on-chain │   │
│  │ - Update case    │   │
│  └──────────────────┘   │
└─────────────────────────┘
```

## Security Considerations

1. **Webhook Signature Verification**: Always verify Persona signatures
2. **HTTPS Required**: Webhooks must use HTTPS in production
3. **API Key Security**: Store Persona API key in Secret Manager
4. **Database Access**: Use connection with least privilege
5. **Rate Limiting**: Consider rate limiting on webhook endpoint

## Files Modified/Created

### Created
- ✅ `app/integrations/persona_client.py` - Persona API client
- ✅ `app/integrations/__init__.py` - Module exports
- ✅ `app/routes/webhooks.py` - Webhook endpoints
- ✅ `alembic/versions/002_add_persona_identity_fields.py` - Database migration

### Modified
- ✅ `requirements.txt` - Added `persona>=3.0.0`
- ✅ `infrastructure/db/models.py` - Updated KYCCase model
- ✅ `app/core/compliance_engine_production.py` - Enhanced with Persona integration
- ✅ `app/routes/compliance.py` - Added claim update endpoint
- ✅ `app/main.py` - Registered webhook routes

## Integration Points

### Ready for Identity Service
The Compliance Service is now **ready to integrate** with the Identity Service:

**Compliance Service provides:**
- Verified KYC status via database
- Webhook-driven status updates
- Endpoint to receive claim references

**Identity Service will:**
- Poll/subscribe to verified KYC cases
- Issue ERC-735 claims on blockchain
- Call `PUT /compliance/kyc/{case_id}/claim`

## Success Metrics

- ✅ Persona client implemented
- ✅ Webhook handler functional
- ✅ Database schema updated
- ✅ API endpoints created
- ✅ Integration points defined
- ⏳ Migration run (pending deployment)
- ⏳ End-to-end test (pending deployment)
- ⏳ Production deployment (pending)

## Support

For issues or questions:
1. Check Persona Dashboard → Logs
2. Check service logs: `docker logs compliance-service`
3. Verify webhook configuration
4. Test with Persona sandbox environment first

---

**Status:** Implementation complete, ready for deployment and testing
**Next:** Run database migration and deploy to Cloud Run with Persona credentials
