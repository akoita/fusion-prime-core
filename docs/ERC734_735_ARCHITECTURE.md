# ERC-734/735 Identity Architecture for Fusion Prime

**Date**: November 4, 2025
**Status**: Architecture Planning
**Standards**: ERC-734 (Keys) + ERC-735 (Claims)

---

## 🎯 Why ERC-734/735?

**Perfect for Fusion Prime because:**
- ✅ Decentralized identity management
- ✅ On-chain KYC claims (verifiable)
- ✅ Flexible (not tied to tokens)
- ✅ Portable across DeFi
- ✅ Integrates perfectly with Privy + Persona
- ✅ Lower complexity than ERC-3643
- ✅ Can add claims progressively (KYC, accreditation, etc.)

**Use cases:**
- KYC verification claims
- Escrow eligibility
- Cross-chain identity verification
- Feature access control
- Compliance enforcement

---

## 📊 System Architecture

### Components:

```
┌─────────────────────────────────────────────────────────────┐
│                    IDENTITY LAYER                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  Identity        │      │  Claim Issuer    │            │
│  │  Factory         │      │  Registry        │            │
│  └────────┬─────────┘      └────────┬─────────┘            │
│           │                         │                       │
│           │ Creates                 │ Trusted issuers       │
│           ▼                         ▼                       │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  User Identity   │◀────▶│  Persona Issuer  │            │
│  │  Contract        │      │  (KYC Claims)    │            │
│  │  (ERC-734/735)   │      └──────────────────┘            │
│  └────────┬─────────┘                                       │
│           │                                                 │
│           │ Has claims                                      │
│           ▼                                                 │
│  ┌──────────────────┐                                      │
│  │  Claims:         │                                      │
│  │  - KYC Verified  │                                      │
│  │  - Email Verified│                                      │
│  │  - Country: USA  │                                      │
│  └──────────────────┘                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         │
         │ Used by smart contracts
         ▼
┌─────────────────────────────────────────────────────────────┐
│                 APPLICATION LAYER                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Escrow     │  │ Cross-Chain  │  │ Fiat Gateway │     │
│  │   Factory    │  │    Vault     │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│        ▲                  ▲                  ▲              │
│        │                  │                  │              │
│        └──────────────────┴──────────────────┘              │
│                 All check identity claims                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Smart Contracts

### 1. Identity Contract (ERC-734/735)

**`contracts/identity/Identity.sol`**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IERC734.sol";
import "./IERC735.sol";

/**
 * @title Identity
 * @dev Implementation of ERC-734 (keys) and ERC-735 (claims)
 */
contract Identity is IERC734, IERC735 {
    // Key management (ERC-734)
    mapping(bytes32 => Key) public keys;
    mapping(uint256 => bytes32[]) public keysByPurpose;

    struct Key {
        uint256 purpose;
        uint256 keyType;
        bytes32 key;
    }

    // Claim management (ERC-735)
    mapping(bytes32 => Claim) public claims;
    bytes32[] public claimIds;

    struct Claim {
        uint256 topic;
        uint256 scheme;
        address issuer;
        bytes signature;
        bytes data;
        string uri;
    }

    // Claim topics (standardized)
    uint256 public constant CLAIM_KYC_VERIFIED = 1;
    uint256 public constant CLAIM_EMAIL_VERIFIED = 2;
    uint256 public constant CLAIM_COUNTRY = 3;
    uint256 public constant CLAIM_ACCREDITED_INVESTOR = 4;

    // Key purposes
    uint256 public constant MANAGEMENT = 1;
    uint256 public constant ACTION = 2;
    uint256 public constant CLAIM = 3;

    // Owner (has MANAGEMENT key)
    address public owner;

    constructor(address _owner) {
        owner = _owner;

        // Add owner as management key
        bytes32 ownerKey = keccak256(abi.encodePacked(_owner));
        keys[ownerKey] = Key(MANAGEMENT, 1, ownerKey);
        keysByPurpose[MANAGEMENT].push(ownerKey);

        emit KeyAdded(ownerKey, MANAGEMENT, 1);
    }

    /**
     * @dev Add a claim to the identity
     * Only addresses with CLAIM purpose key can add claims
     */
    function addClaim(
        uint256 _topic,
        uint256 _scheme,
        address _issuer,
        bytes memory _signature,
        bytes memory _data,
        string memory _uri
    ) public override returns (bytes32 claimRequestId) {
        // Check caller has CLAIM key purpose
        require(
            keyHasPurpose(keccak256(abi.encodePacked(msg.sender)), CLAIM) ||
            msg.sender == owner,
            "Sender does not have CLAIM key"
        );

        // Create claim ID
        claimRequestId = keccak256(abi.encodePacked(_issuer, _topic));

        // Store claim
        claims[claimRequestId] = Claim({
            topic: _topic,
            scheme: _scheme,
            issuer: _issuer,
            signature: _signature,
            data: _data,
            uri: _uri
        });

        claimIds.push(claimRequestId);

        emit ClaimAdded(
            claimRequestId,
            _topic,
            _scheme,
            _issuer,
            _signature,
            _data,
            _uri
        );

        return claimRequestId;
    }

    /**
     * @dev Remove a claim
     */
    function removeClaim(bytes32 _claimId) public override {
        require(
            msg.sender == owner ||
            claims[_claimId].issuer == msg.sender,
            "Only owner or issuer can remove"
        );

        emit ClaimRemoved(_claimId, claims[_claimId].topic);
        delete claims[_claimId];
    }

    /**
     * @dev Get a claim by ID
     */
    function getClaim(bytes32 _claimId)
        public
        view
        override
        returns (
            uint256 topic,
            uint256 scheme,
            address issuer,
            bytes memory signature,
            bytes memory data,
            string memory uri
        )
    {
        Claim memory c = claims[_claimId];
        return (c.topic, c.scheme, c.issuer, c.signature, c.data, c.uri);
    }

    /**
     * @dev Check if identity has a specific claim from trusted issuer
     */
    function hasClaim(uint256 _topic, address _issuer)
        public
        view
        returns (bool)
    {
        bytes32 claimId = keccak256(abi.encodePacked(_issuer, _topic));
        return claims[claimId].issuer != address(0);
    }

    /**
     * @dev Check if a key has a specific purpose
     */
    function keyHasPurpose(bytes32 _key, uint256 _purpose)
        public
        view
        returns (bool)
    {
        return keys[_key].purpose == _purpose;
    }

    /**
     * @dev Add a key
     */
    function addKey(
        bytes32 _key,
        uint256 _purpose,
        uint256 _keyType
    ) public override {
        require(
            msg.sender == owner ||
            keyHasPurpose(keccak256(abi.encodePacked(msg.sender)), MANAGEMENT),
            "Only management keys can add keys"
        );

        keys[_key] = Key(_purpose, _keyType, _key);
        keysByPurpose[_purpose].push(_key);

        emit KeyAdded(_key, _purpose, _keyType);
    }

    /**
     * @dev Remove a key
     */
    function removeKey(bytes32 _key) public override {
        require(msg.sender == owner, "Only owner can remove keys");

        uint256 purpose = keys[_key].purpose;
        emit KeyRemoved(_key, purpose);

        delete keys[_key];
        // Note: Not removing from keysByPurpose array for gas efficiency
    }

    // ERC-734 Events
    event KeyAdded(bytes32 indexed key, uint256 indexed purpose, uint256 indexed keyType);
    event KeyRemoved(bytes32 indexed key, uint256 indexed purpose);

    // ERC-735 Events
    event ClaimAdded(
        bytes32 indexed claimId,
        uint256 indexed topic,
        uint256 scheme,
        address indexed issuer,
        bytes signature,
        bytes data,
        string uri
    );
    event ClaimRemoved(bytes32 indexed claimId, uint256 indexed topic);
}
```

### 2. Identity Factory

**`contracts/identity/IdentityFactory.sol`**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Identity.sol";

/**
 * @title IdentityFactory
 * @dev Factory contract to create user identities
 */
contract IdentityFactory {
    // Map user address to their identity contract
    mapping(address => address) public identities;

    // Map identity contract to user (reverse lookup)
    mapping(address => address) public identityToUser;

    // All created identities
    address[] public allIdentities;

    event IdentityCreated(address indexed user, address indexed identity);

    /**
     * @dev Create an identity contract for a user
     * @param _user The user's wallet address
     * @return identity The deployed identity contract address
     */
    function createIdentity(address _user) external returns (address identity) {
        require(identities[_user] == address(0), "Identity already exists");

        // Deploy new Identity contract
        Identity newIdentity = new Identity(_user);
        identity = address(newIdentity);

        // Store mappings
        identities[_user] = identity;
        identityToUser[identity] = _user;
        allIdentities.push(identity);

        emit IdentityCreated(_user, identity);

        return identity;
    }

    /**
     * @dev Get identity contract for a user
     */
    function getIdentity(address _user) external view returns (address) {
        return identities[_user];
    }

    /**
     * @dev Check if user has an identity
     */
    function hasIdentity(address _user) external view returns (bool) {
        return identities[_user] != address(0);
    }

    /**
     * @dev Get total number of identities created
     */
    function getIdentityCount() external view returns (uint256) {
        return allIdentities.length;
    }
}
```

### 3. Claim Issuer Registry

**`contracts/identity/ClaimIssuerRegistry.sol`**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title ClaimIssuerRegistry
 * @dev Manages trusted claim issuers (KYC providers, etc.)
 */
contract ClaimIssuerRegistry is Ownable {
    // Trusted issuers
    mapping(address => bool) public isTrustedIssuer;
    mapping(address => string) public issuerNames;

    address[] public trustedIssuers;

    event IssuerAdded(address indexed issuer, string name);
    event IssuerRemoved(address indexed issuer);

    constructor() Ownable(msg.sender) {}

    /**
     * @dev Add a trusted claim issuer
     */
    function addTrustedIssuer(address _issuer, string memory _name)
        external
        onlyOwner
    {
        require(!isTrustedIssuer[_issuer], "Already trusted");

        isTrustedIssuer[_issuer] = true;
        issuerNames[_issuer] = _name;
        trustedIssuers.push(_issuer);

        emit IssuerAdded(_issuer, _name);
    }

    /**
     * @dev Remove a trusted claim issuer
     */
    function removeTrustedIssuer(address _issuer) external onlyOwner {
        require(isTrustedIssuer[_issuer], "Not trusted");

        isTrustedIssuer[_issuer] = false;

        emit IssuerRemoved(_issuer);
    }

    /**
     * @dev Check if an issuer is trusted
     */
    function isIssuerTrusted(address _issuer) external view returns (bool) {
        return isTrustedIssuer[_issuer];
    }

    /**
     * @dev Get all trusted issuers
     */
    function getTrustedIssuers() external view returns (address[] memory) {
        return trustedIssuers;
    }
}
```

### 4. Updated Escrow with Identity Checks

**`contracts/escrow/IdentityEscrowFactory.sol`**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./EscrowFactory.sol";
import "../identity/IdentityFactory.sol";
import "../identity/Identity.sol";
import "../identity/ClaimIssuerRegistry.sol";

/**
 * @title IdentityEscrowFactory
 * @dev Escrow factory that requires KYC verification via ERC-735 claims
 */
contract IdentityEscrowFactory is EscrowFactory {
    IdentityFactory public identityFactory;
    ClaimIssuerRegistry public issuerRegistry;

    // KYC claim topic
    uint256 public constant CLAIM_KYC_VERIFIED = 1;

    constructor(
        address _identityFactory,
        address _issuerRegistry
    ) {
        identityFactory = IdentityFactory(_identityFactory);
        issuerRegistry = ClaimIssuerRegistry(_issuerRegistry);
    }

    /**
     * @dev Check if an address has valid KYC claim
     */
    function isKYCVerified(address _user) public view returns (bool) {
        // Get user's identity contract
        address identityAddr = identityFactory.getIdentity(_user);
        if (identityAddr == address(0)) {
            return false; // No identity = not verified
        }

        Identity identity = Identity(identityAddr);

        // Check for KYC claim from any trusted issuer
        address[] memory trustedIssuers = issuerRegistry.getTrustedIssuers();

        for (uint256 i = 0; i < trustedIssuers.length; i++) {
            if (identity.hasClaim(CLAIM_KYC_VERIFIED, trustedIssuers[i])) {
                return true;
            }
        }

        return false;
    }

    /**
     * @dev Create escrow with KYC requirement
     */
    function createEscrow(
        address payee,
        address arbiter,
        uint256 timelock
    ) public payable override returns (address) {
        // Check all parties are KYC verified
        require(isKYCVerified(msg.sender), "Payer not KYC verified");
        require(isKYCVerified(payee), "Payee not KYC verified");
        require(isKYCVerified(arbiter), "Arbiter not KYC verified");

        // Create escrow using parent function
        return super.createEscrow(payee, arbiter, timelock);
    }
}
```

---

## 🔄 User Journey Flow

### Complete Flow: Privy → Persona → ERC-735 Claims → Escrow

```
1. User Authentication (Privy)
   ↓
   User signs in with Google
   Wallet address: 0x742d35Cc...
   ↓
2. Identity Creation (First time)
   ↓
   Frontend calls: IdentityFactory.createIdentity(0x742d...)
   Identity contract deployed: 0xABC123... (user's identity)
   ↓
3. KYC Verification (Persona)
   ↓
   User uploads ID to Persona widget
   Persona verifies off-chain
   Persona webhook → Backend confirms "verified"
   ↓
4. Claim Issuance (Backend)
   ↓
   Backend generates claim signature:
     topic: 1 (KYC_VERIFIED)
     issuer: PERSONA_ISSUER_ADDRESS
     data: hash(kycData)
     signature: sign(claim, BACKEND_KEY)
   ↓
   Backend calls: identity.addClaim(...)
   On-chain claim stored ✅
   ↓
5. Use Features (Smart Contracts)
   ↓
   User tries to create escrow
   Contract checks: isKYCVerified(user)?
     → Gets identity: identityFactory.getIdentity(user)
     → Checks claim: identity.hasClaim(KYC_VERIFIED, PERSONA_ISSUER)
     → If true: Allow escrow creation ✅
     → If false: Revert transaction ❌
```

---

## 💻 Backend Implementation

### Claim Issuance Service

**`services/identity/app/services/claim_service.py`**

```python
from web3 import Web3
from eth_account import Account
import os

class ClaimService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.issuer_key = os.getenv("CLAIM_ISSUER_PRIVATE_KEY")
        self.issuer_address = Account.from_key(self.issuer_key).address

    def create_kyc_claim(self, user_address: str, kyc_data: dict) -> dict:
        """
        Create a signed KYC claim for a user
        """
        # Claim data
        topic = 1  # KYC_VERIFIED
        scheme = 1  # ECDSA signature

        # Hash KYC data (don't store PII on-chain)
        data_hash = self.w3.keccak(text=str(kyc_data))

        # Create signature
        message = self.w3.solidity_keccak(
            ['address', 'uint256', 'bytes32'],
            [user_address, topic, data_hash]
        )

        signed_message = Account.signHash(message, self.issuer_key)

        return {
            "topic": topic,
            "scheme": scheme,
            "issuer": self.issuer_address,
            "signature": signed_message.signature.hex(),
            "data": data_hash.hex(),
            "uri": ""
        }

    async def issue_claim_on_chain(
        self,
        identity_address: str,
        claim: dict
    ):
        """
        Issue claim to user's identity contract on-chain
        """
        # Load Identity contract ABI
        identity_contract = self.w3.eth.contract(
            address=identity_address,
            abi=IDENTITY_ABI
        )

        # Build transaction
        txn = identity_contract.functions.addClaim(
            claim["topic"],
            claim["scheme"],
            claim["issuer"],
            bytes.fromhex(claim["signature"][2:]),
            bytes.fromhex(claim["data"][2:]),
            claim["uri"]
        ).build_transaction({
            'from': self.issuer_address,
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.issuer_address),
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, self.issuer_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "txHash": tx_hash.hex(),
            "status": receipt.status,
            "claimId": self.w3.keccak(text=f"{claim['issuer']}{claim['topic']}").hex()
        }
```

### API Endpoint

**`services/identity/app/routes/identity.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from app.services.claim_service import ClaimService
from app.services.user_service import UserService

router = APIRouter(prefix="/identity", tags=["identity"])

@router.post("/create")
async def create_identity(
    claims: dict = Depends(verify_privy_token),
    db: Session = Depends(get_db),
):
    """
    Create identity contract for user
    """
    user_address = claims.get("wallet_address")

    # Deploy identity contract
    identity_contract = await deploy_identity(user_address)

    # Store in database
    user_service = UserService(db)
    user_service.update_identity(user_address, identity_contract.address)

    return {
        "identityAddress": identity_contract.address,
        "userAddress": user_address
    }

@router.post("/issue-kyc-claim")
async def issue_kyc_claim(
    claims: dict = Depends(verify_privy_token),
    db: Session = Depends(get_db),
):
    """
    Issue KYC claim after Persona verification
    Called by backend after Persona webhook confirms KYC
    """
    user_service = UserService(db)
    user = user_service.get_user(claims.get("sub"))

    # Check KYC status
    if user.kyc_status != "approved":
        raise HTTPException(status_code=400, detail="KYC not approved")

    # Get user's identity contract
    if not user.identity_address:
        raise HTTPException(status_code=400, detail="No identity contract")

    # Create claim
    claim_service = ClaimService()
    claim = claim_service.create_kyc_claim(
        user.wallet_address,
        {"kyc_id": user.kyc_inquiry_id}
    )

    # Issue claim on-chain
    result = await claim_service.issue_claim_on_chain(
        user.identity_address,
        claim
    )

    # Update user
    user.kyc_claim_id = result["claimId"]
    user.kyc_claim_issued_at = datetime.utcnow()
    db.commit()

    return {
        "claimId": result["claimId"],
        "txHash": result["txHash"],
        "status": "issued"
    }
```

---

## 🎨 Frontend Integration

### Identity Hook

**`src/hooks/useIdentity.ts`**

```typescript
import { useReadContract, useWriteContract } from 'wagmi';
import { useAccount } from 'wagmi';
import IdentityFactoryABI from '@/abis/IdentityFactory.json';
import IdentityABI from '@/abis/Identity.json';

const IDENTITY_FACTORY_ADDRESS = '0x...'; // Deployed factory

export function useIdentity() {
  const { address } = useAccount();

  // Check if user has identity
  const { data: identityAddress } = useReadContract({
    address: IDENTITY_FACTORY_ADDRESS,
    abi: IdentityFactoryABI,
    functionName: 'getIdentity',
    args: address ? [address] : undefined,
  });

  const hasIdentity = !!identityAddress && identityAddress !== '0x0000000000000000000000000000000000000000';

  // Create identity
  const { writeContract: createIdentity, isLoading: isCreating } = useWriteContract();

  const create = () => {
    createIdentity({
      address: IDENTITY_FACTORY_ADDRESS,
      abi: IdentityFactoryABI,
      functionName: 'createIdentity',
      args: [address],
    });
  };

  return {
    identityAddress,
    hasIdentity,
    createIdentity: create,
    isCreating,
  };
}

export function useKYCClaim(identityAddress?: string) {
  const CLAIM_KYC_VERIFIED = 1;
  const PERSONA_ISSUER = '0x...'; // Your backend issuer address

  const { data: hasKYC } = useReadContract({
    address: identityAddress as `0x${string}`,
    abi: IdentityABI,
    functionName: 'hasClaim',
    args: [CLAIM_KYC_VERIFIED, PERSONA_ISSUER],
    query: {
      enabled: !!identityAddress,
    },
  });

  return {
    hasKYCClaim: !!hasKYC,
    isVerified: !!hasKYC,
  };
}
```

---

## 📊 Comparison: Database KYC vs ERC-735 Claims

| Aspect | Database Only | ERC-735 Claims |
|--------|--------------|----------------|
| **Storage** | PostgreSQL | Blockchain |
| **Verification** | Backend checks DB | Smart contract checks on-chain |
| **Portability** | Per-app only | Works across all DApps |
| **Transparency** | Private | Public (pseudonymous) |
| **Auditability** | Manual | Automatic (on-chain) |
| **Cost** | $0 | Gas fees (~$5-10 one-time) |
| **Speed** | Fast | Slower (blockchain confirmation) |
| **Censorship** | Can be changed | Immutable (unless removed) |
| **Best For** | Quick MVP | Production DeFi |

---

## 🎯 Recommendation for Fusion Prime

### Hybrid Approach (Best of Both Worlds):

```
Phase 1 (Weeks 1-3): Database KYC
├─ Privy authentication
├─ Persona KYC verification
├─ Store in PostgreSQL
└─ Backend checks for feature access

Phase 2 (Week 4+): Add ERC-735 Claims
├─ Deploy identity contracts
├─ Issue claims after Persona KYC
├─ Smart contracts check claims
└─ Full on-chain compliance
```

### Why Hybrid?

**Database KYC** (Phase 1):
- ✅ Faster to implement
- ✅ Lower gas costs for users
- ✅ Good for testing/MVP

**ERC-735 Claims** (Phase 2):
- ✅ Adds on-chain verification
- ✅ Portable across DeFi
- ✅ More secure/transparent
- ✅ Institutional-grade

**Together**:
- Database for quick checks
- On-chain claims for critical operations
- Best user experience + security

---

## 💰 Cost Analysis

### Implementation Costs:

**Development**:
- Identity contracts: 3-4 days
- Backend integration: 2-3 days
- Frontend integration: 2 days
- **Total**: 7-9 days (~$10-15K)

**Gas Costs** (per user):
- Deploy identity: ~$8-12 (one-time)
- Issue KYC claim: ~$3-5 (one-time)
- Verify claim (reads): Free
- **Total per user**: ~$11-17 (one-time)

**Operational**:
- Backend issuer account (gas): ~$50/month
- **Total**: ~$50/month ongoing

### Benefits:

**Quantifiable**:
- Portable identity: Users don't re-KYC for other DApps
- Institutional trust: On-chain compliance proof
- Reduced fraud: Cryptographic verification

**Strategic**:
- Competitive advantage (few DeFi platforms have this)
- Future-proof (regulatory trends toward on-chain identity)
- Network effects (more platforms adopt ERC-735)

---

## 🚀 Implementation Timeline

### Week 4-5: Identity Layer

**Day 1-2**: Smart Contracts
- [ ] Write Identity contract (ERC-734/735)
- [ ] Write IdentityFactory
- [ ] Write ClaimIssuerRegistry
- [ ] Unit tests

**Day 3-4**: Deployment
- [ ] Deploy to Sepolia testnet
- [ ] Deploy to Polygon Amoy testnet
- [ ] Register backend as trusted issuer
- [ ] Verify on Etherscan

**Day 5-6**: Backend Integration
- [ ] ClaimService (create + issue claims)
- [ ] Update KYC webhook (issue claim after Persona)
- [ ] API endpoints (/identity/create, /claim/issue)
- [ ] Testing

**Day 7-8**: Frontend Integration
- [ ] useIdentity hook
- [ ] useKYCClaim hook
- [ ] Identity creation flow
- [ ] Update Escrow UI (check claims)

**Day 9**: Testing
- [ ] End-to-end test: Create identity → KYC → Claim → Escrow
- [ ] Gas optimization
- [ ] Security review

**Total**: 9 days

---

## ✅ Success Criteria

**MVP Success** (Phase 1 - Database KYC):
- [ ] Users can register with Privy
- [ ] Users can complete KYC with Persona
- [ ] Backend tracks KYC status
- [ ] Features gated by KYC status

**Full Success** (Phase 2 - ERC-735):
- [ ] Users have on-chain identity contracts
- [ ] KYC claims issued on-chain
- [ ] Smart contracts verify claims
- [ ] Identity portable across DApps

---

Would you like me to start implementing the ERC-734/735 identity layer? I can begin with:

1. **Smart contracts** (Identity, Factory, Registry)
2. **Backend claim issuance** service
3. **Frontend hooks** for identity management

Or would you prefer to stick with **database-only KYC** for now and add identity claims later?

What's your preference? 🎯
