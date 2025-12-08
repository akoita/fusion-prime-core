# Identity System Deployment

## Deployment Information

**Network:** Sepolia Testnet (Chain ID: 11155111)
**Deployment Date:** 2025-11-04
**Deployer:** 0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA

## Deployed Contracts

### ClaimIssuerRegistry
**Address:** `0xc88BCD77b2839fDf5499e91b3618eb7049F6CE21`
**Purpose:** Manages trusted claim issuers and issues verification claims to user identities
**Etherscan:** https://sepolia.etherscan.io/address/0xc88BCD77b2839fDf5499e91b3618eb7049F6CE21

**Configuration:**
- Owner: 0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA
- Trusted Issuers:
  - `0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA` - "Fusion Prime Identity Service"
    - Allowed Topics: KYC_VERIFIED (1), AML_CLEARED (2), ACCREDITED_INVESTOR (3), SANCTIONS_CLEARED (4), COUNTRY_ALLOWED (5)

### IdentityFactory
**Address:** `0x59A97ebb44C7ebd23f5755A0C46F946d177319Ca`
**Purpose:** Factory contract for deploying user Identity contracts
**Etherscan:** https://sepolia.etherscan.io/address/0x59A97ebb44C7ebd23f5755A0C46F946d177319Ca

**Configuration:**
- Registry: 0xc88BCD77b2839fDf5499e91b3618eb7049F6CE21

## Contract Verification

To verify contracts on Etherscan:

```bash
# Verify ClaimIssuerRegistry
forge verify-contract \
  0xc88BCD77b2839fDf5499e91b3618eb7049F6CE21 \
  ClaimIssuerRegistry \
  --chain sepolia \
  --etherscan-api-key $ETHERSCAN_API_KEY

# Verify IdentityFactory
forge verify-contract \
  0x59A97ebb44C7ebd23f5755A0C46F946d177319Ca \
  IdentityFactory \
  --constructor-args $(cast abi-encode 'constructor(address)' 0xc88BCD77b2839fDf5499e91b3618eb7049F6CE21) \
  --chain sepolia \
  --etherscan-api-key $ETHERSCAN_API_KEY
```

## Identity Service Deployment

**Service URL:** https://identity-service-ggats6pubq-uc.a.run.app
**Status:** ✅ Deployed and Healthy
**Deployment Date:** 2025-11-04
**Region:** us-central1 (Cloud Run)

**Health Check:**
```bash
curl https://identity-service-ggats6pubq-uc.a.run.app/health
```

**Service Information:**
- Backend Address: 0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA
- Backend Balance: 1.55 ETH (sufficient for operations)
- Network: Sepolia (Chain ID: 11155111)
- Connected to deployed contracts

## Environment Variables

Add these to your `.env.dev`:

```bash
# Identity System (Deployed 2025-11-04)
IDENTITY_FACTORY_ADDRESS=0x59A97ebb44C7ebd23f5755A0C46F946d177319Ca
CLAIM_ISSUER_REGISTRY_ADDRESS=0xc88BCD77b2839fDf5499e91b3618eb7049F6CE21
IDENTITY_SERVICE_URL=https://identity-service-ggats6pubq-uc.a.run.app
```

Add these to frontend `.env`:

```bash
VITE_IDENTITY_FACTORY_ADDRESS=0x59A97ebb44C7ebd23f5755A0C46F946d177319Ca
VITE_CLAIM_ISSUER_REGISTRY_ADDRESS=0xc88BCD77b2839fDf5499e91b3618eb7049F6CE21
VITE_SEPOLIA_RPC_URL=https://spectrum-01.simplystaking.xyz/Y2J1emtmcWQtMDEtMjJjN2I0YTE/6CuZK_q3OlibSg/ethereum/testnet/
VITE_IDENTITY_SERVICE_URL=https://identity-service-ggats6pubq-uc.a.run.app
```

## Claim Topics

The following claim topics are supported:

| Topic ID | Name | Description |
|----------|------|-------------|
| 1 | KYC_VERIFIED | User has completed KYC verification via Persona |
| 2 | AML_CLEARED | User has passed AML screening |
| 3 | ACCREDITED_INVESTOR | User is an accredited investor |
| 4 | SANCTIONS_CLEARED | User is not on sanctions lists |
| 5 | COUNTRY_ALLOWED | User is from an allowed country |

## Usage Example

### Create Identity (Frontend)

```typescript
import { useCreateIdentity } from './hooks/contracts/useIdentityFactory';

const { createIdentity, isLoading } = useCreateIdentity();

// Call this when user clicks "Create Identity"
createIdentity();
```

### Issue KYC Claim (Backend - Identity Service)

```bash
curl -X POST https://identity-service-url/identity/issue-claim \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "0x123...",
    "user_id": "user_abc123",
    "claim_type": "kyc",
    "kyc_case_id": "case_xyz789",
    "kyc_inquiry_id": "inq_persona_123"
  }'
```

### Check Identity Status (Frontend)

```typescript
import { useIdentityStatus } from './hooks/contracts/useIdentityFactory';
import { useIdentityVerificationData } from './hooks/contracts/useIdentity';

const { hasIdentity, identityAddress } = useIdentityStatus(walletAddress);
const { claims, requiredVerified } = useIdentityVerificationData(identityAddress);

// claims array contains verification status for all claim types
// requiredVerified = true if KYC and AML are verified
```

## Gas Costs

Approximate gas costs on Sepolia:

| Operation | Gas Used | Estimated Cost (at 1 gwei) |
|-----------|----------|----------------------------|
| Deploy Identity | ~2,100,000 | ~$0.002 |
| Issue Claim | ~150,000 | ~$0.0001 |
| Add Trusted Issuer | ~80,000 | ~$0.00008 |

## Integration Points

### With Compliance Service
- Compliance Service calls Identity Service after successful KYC
- Identity Service issues KYC_VERIFIED claim on-chain
- Claim ID is stored back in Compliance Service database

### With Frontend
- Frontend reads identity status and claims via Wagmi hooks
- Users create identities directly from frontend (wallet transaction)
- Frontend displays verification badges based on claim status

### With Other Contracts
- Escrow can require identity verification before creating escrows
- Cross-Chain Vault can check accredited investor status
- Use `IdentityVerifier` library for easy integration

## Deployment Transaction Details

**Deployment Gas Used:** 5,299,670
**Deployment Cost:** 0.00000582969529637 ETH
**Block Explorer:** https://sepolia.etherscan.io/address/0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA

## Next Steps

1. **Verify Contracts on Etherscan** - Run verification commands above
2. **Deploy Identity Service** - Deploy backend service to Cloud Run with these addresses
3. **Update Frontend Environment** - Add contract addresses to frontend `.env`
4. **Test Identity Flow** - Create test identity and issue test claims
5. **Connect Persona KYC** - Complete Persona integration in Compliance Service
6. **Add Feature Gates** - Update Escrow and Vault to check identity verification

## Troubleshooting

### Identity Creation Fails
- Check wallet has ETH for gas
- Verify wallet is connected to Sepolia
- Check if identity already exists for wallet

### Claim Issuance Fails
- Verify issuer is trusted in registry
- Check issuer has permission for claim topic
- Ensure identity exists for user

### Contract Interactions Failing
- Verify RPC URL is accessible
- Check contract addresses in environment
- Ensure ABIs are up to date

## References

- [ERC-734 Specification](https://github.com/ethereum/EIPs/issues/734)
- [ERC-735 Specification](https://github.com/ethereum/EIPs/issues/735)
- [Identity Contracts README](./README.md)
- [Identity Service README](../../services/identity/README.md)
- [Frontend Integration Guide](../../docs/FRONTEND_INTEGRATION_STATUS.md)
