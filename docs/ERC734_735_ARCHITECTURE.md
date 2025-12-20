# ERC-734/735 Identity Architecture for Fusion Prime

**Status**: Active Development
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

The system is composed of several core contracts:

### 1. Identity Contract (ERC-734/735)
**`contracts/identity/Identity.sol`** - Manages keys and claims for a user.

### 2. Identity Factory
**`contracts/identity/IdentityFactory.sol`** - Deploys new identity contracts.

### 3. Claim Issuer Registry
**`contracts/identity/ClaimIssuerRegistry.sol`** - Manages trusted KYC issuers.

### 4. Escrow with Identity Checks
**`contracts/identity/EscrowWithIdentity.sol`** - Escrow requiring KYC verification.

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
| **Best For** | Quick MVP | Production DeFi |
