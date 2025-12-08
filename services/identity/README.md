# Identity Service

Backend microservice that bridges the Compliance Service and blockchain for identity and claim management.

## Overview

The Identity Service is the blockchain integration layer for the Fusion Prime identity system. It:
- Creates on-chain identities for users
- Issues compliance claims (KYC, AML) to user identities
- Integrates with the Compliance Service
- Manages blockchain transactions
- Updates Compliance Service with claim references

## Architecture

```
┌─────────────────────┐
│ Compliance Service  │
│ (Persona KYC)       │
└──────────┬──────────┘
           │ HTTP POST /identity/issue-claim
           ↓
┌─────────────────────┐
│  Identity Service   │ ← This service
│  ┌───────────────┐  │
│  │ FastAPI       │  │
│  │ Web3.py       │  │
│  │ Async tasks   │  │
│  └───────────────┘  │
└──────────┬──────────┘
           │ Web3 RPC
           ↓
┌─────────────────────┐
│   Blockchain        │
│  ┌───────────────┐  │
│  │ IdentityFactory│ │
│  │ ClaimIssuer   │  │
│  │ Registry      │  │
│  │ Identity      │  │
│  │ Contracts     │  │
│  └───────────────┘  │
└─────────────────────┘
```

## Features

- ✅ **Identity Creation**: Deploy Identity contracts for new users
- ✅ **Claim Issuance**: Issue KYC, AML, and other compliance claims
- ✅ **Blockchain Integration**: Web3.py for Ethereum interactions
- ✅ **Compliance Integration**: HTTP client for Compliance Service
- ✅ **Async Processing**: Background task handling
- ✅ **Health Monitoring**: Blockchain connection and balance checks
- ✅ **Production Ready**: Docker, Cloud Run, logging

## API Endpoints

### Identity Management

**POST /identity/create**
Create a new identity for a user.

Request:
```json
{
  "user_id": "user_123",
  "wallet_address": "0x..."
}
```

Response:
```json
{
  "user_id": "user_123",
  "wallet_address": "0x...",
  "identity_address": "0x...",
  "tx_hash": "0x...",
  "already_exists": false,
  "block_number": 12345,
  "created_at": "2025-11-04T12:00:00"
}
```

**POST /identity/issue-claim**
Issue a compliance claim to a user's identity.

Request:
```json
{
  "user_id": "user_123",
  "wallet_address": "0x...",
  "claim_type": "KYC_VERIFIED",
  "case_id": "kyc-case-456",
  "inquiry_id": "inq_ABC123"
}
```

Response:
```json
{
  "user_id": "user_123",
  "wallet_address": "0x...",
  "identity_address": "0x...",
  "claim_topic": 1,
  "claim_topic_name": "KYC_VERIFIED",
  "claim_id": "0x...",
  "tx_hash": "0x...",
  "block_number": 12346,
  "issued_at": "2025-11-04T12:05:00"
}
```

**GET /identity/{wallet_address}**
Get identity information for a wallet.

Response:
```json
{
  "wallet_address": "0x...",
  "identity_address": "0x...",
  "has_identity": true
}
```

### Service Health

**GET /health**
Health check with blockchain connection status.

Response:
```json
{
  "status": "healthy",
  "service": "identity-service",
  "network": "sepolia",
  "chain_id": 11155111,
  "backend_address": "0x...",
  "backend_balance_eth": 0.5,
  "contracts": {
    "identity_factory": "0x...",
    "claim_issuer_registry": "0x..."
  }
}
```

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL (optional, for persistence)
- Ethereum RPC endpoint (Infura, Alchemy, etc.)
- Deployed identity contracts (see contracts/identity/)

### Local Development

1. **Clone and setup:**
```bash
cd services/identity
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Required environment variables:**
```bash
# Blockchain
RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
BACKEND_PRIVATE_KEY=0x...  # Private key with ETH for gas
IDENTITY_FACTORY_ADDRESS=0x...  # From deployment
CLAIM_ISSUER_REGISTRY_ADDRESS=0x...  # From deployment

# Compliance Service
COMPLIANCE_SERVICE_URL=http://localhost:8001
```

4. **Run service:**
```bash
python -m app.main
```

Service will start on `http://localhost:8002`

## Integration Flow

### Complete User Journey

```
1. User signs up → Wallet created
   ↓
2. POST /identity/create
   → IdentityFactory.createIdentityFor(wallet)
   → Identity contract deployed
   ← identity_address returned
   ↓
3. User completes KYC in Persona
   → Compliance Service receives webhook
   ↓
4. Compliance Service → POST /identity/issue-claim
   {
     "user_id": "user_123",
     "wallet_address": "0x...",
     "claim_type": "KYC_VERIFIED",
     "case_id": "kyc-case-456"
   }
   ↓
5. Identity Service:
   - Gets identity address from IdentityFactory
   - Prepares claim data (hash of KYC info)
   - Calls ClaimIssuerRegistry.issueClaim()
   - Waits for transaction confirmation
   ↓
6. Identity Service → PUT /compliance/kyc/{case_id}/claim
   {
     "claim_id": "0x...",
     "claim_tx_hash": "0x..."
   }
   ↓
7. Compliance Service updates database
   ✓ KYC claim stored with blockchain reference
```

### Compliance Service Integration

The Compliance Service should call Identity Service after KYC verification:

```python
# In Compliance Service after KYC approval
import httpx

async def on_kyc_approved(kyc_case):
    # Call Identity Service to issue claim
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{IDENTITY_SERVICE_URL}/identity/issue-claim",
            json={
                "user_id": kyc_case.user_id,
                "wallet_address": kyc_case.wallet_address,
                "claim_type": "KYC_VERIFIED",
                "case_id": kyc_case.case_id,
                "inquiry_id": kyc_case.persona_inquiry_id
            }
        )

        claim_data = response.json()

        # Store claim reference
        kyc_case.kyc_claim_id = claim_data["claim_id"]
        kyc_case.kyc_claim_tx_hash = claim_data["tx_hash"]
        await db.commit()
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RPC_URL` | Ethereum RPC endpoint | `https://sepolia.infura.io/v3/...` |
| `CHAIN_ID` | Network chain ID | `11155111` (Sepolia) |
| `BACKEND_PRIVATE_KEY` | Private key for signing | `0x...` |
| `IDENTITY_FACTORY_ADDRESS` | IdentityFactory contract | `0x...` |
| `CLAIM_ISSUER_REGISTRY_ADDRESS` | Registry contract | `0x...` |
| `COMPLIANCE_SERVICE_URL` | Compliance Service URL | `http://localhost:8001` |

### Contract ABIs

The service expects contract ABIs in one of these locations:
1. `../../contracts/out/<ContractName>.sol/<ContractName>.json` (Foundry build output)
2. `./abis/<ContractName>.json`

Build contracts first:
```bash
cd ../../contracts
forge build
```

## Deployment

### Docker

```bash
# Build image
docker build -t identity-service .

# Run container
docker run -p 8002:8002 \
  -e RPC_URL=... \
  -e BACKEND_PRIVATE_KEY=... \
  -e IDENTITY_FACTORY_ADDRESS=... \
  -e CLAIM_ISSUER_REGISTRY_ADDRESS=... \
  identity-service
```

### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml

# Configure secrets in Secret Manager:
# - backend-private-key
# - ethereum-rpc-url
# - identity-database-url (if using DB)
```

## Monitoring

### Health Checks

The `/health` endpoint provides:
- Service status
- Blockchain connection
- Backend wallet balance
- Contract addresses

Monitor backend wallet balance to ensure sufficient gas:
```bash
curl http://localhost:8002/health | jq '.backend_balance_eth'
```

### Logging

All operations are logged with structured logging:
- Identity creation events
- Claim issuance events
- Blockchain transactions
- Errors and retries

View logs:
```bash
# Local
tail -f logs/identity-service.log

# Cloud Run
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=identity-service" --limit 50
```

## Security Considerations

1. **Private Key Management**: Store `BACKEND_PRIVATE_KEY` in Secret Manager
2. **RPC Endpoint**: Use authenticated endpoints (Infura, Alchemy)
3. **Gas Management**: Monitor backend wallet balance
4. **Rate Limiting**: Implement for production
5. **Authentication**: Add API key authentication for production

## Testing

```bash
# Run tests
pytest tests/

# Test identity creation
curl -X POST http://localhost:8002/identity/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_1",
    "wallet_address": "0x..."
  }'

# Test claim issuance
curl -X POST http://localhost:8002/identity/issue-claim \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_1",
    "wallet_address": "0x...",
    "claim_type": "KYC_VERIFIED",
    "case_id": "test-case-1"
  }'
```

## Troubleshooting

### "Identity service not initialized"
- Check blockchain connection
- Verify RPC_URL is accessible
- Ensure contracts are deployed

### "Transaction failed"
- Check backend wallet has sufficient ETH for gas
- Verify contract addresses are correct
- Check RPC endpoint status

### "No identity found"
- User must have identity created first
- Call `/identity/create` before issuing claims

## Next Steps

### Week 5: Frontend Integration

Update Compliance Service to call Identity Service:
1. Add Identity Service URL to config
2. Call `/identity/create` on user onboarding
3. Call `/identity/issue-claim` after KYC approval
4. Store claim references in database

### Future Enhancements

- [ ] Event monitoring for blockchain events
- [ ] Claim revocation support
- [ ] Batch claim issuance
- [ ] Database persistence for tracking
- [ ] Webhook notifications
- [ ] Gas price optimization

## Files

```
services/identity/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuration
│   ├── main.py                # FastAPI application
│   ├── routes/
│   │   └── identity.py        # API endpoints
│   ├── services/
│   │   └── identity_service.py # Business logic
│   └── integrations/
│       └── compliance_client.py # Compliance Service client
├── infrastructure/
│   └── blockchain/
│       └── web3_client.py     # Web3 blockchain client
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
├── cloudbuild.yaml           # Cloud Build config
├── .env.example              # Environment template
└── README.md                 # This file
```

## Support

For issues or questions:
1. Check health endpoint: `GET /health`
2. Review logs for error details
3. Verify blockchain connection
4. Test with Sepolia testnet first

---

**Status:** Implementation complete ✓
**Network:** Sepolia testnet ready
**Next:** Deploy and integrate with Compliance Service
