# Sprint 13: Governance & Compliance

**Duration**: 3-4 weeks  
**Status**: 📋 **DRAFT**  
**Priority**: **HIGH** (Required for institutional adoption)

**Predecessor**: Sprint 12 (Advanced DeFi Features)  
**Successor**: Sprint 14 (Production Deployment)

---

## Overview

Sprint 13 implements governance and KYC/compliance enforcement to make Fusion Prime institutional-ready and community-governed.

**Key Features**:
- FP governance token
- On-chain voting for protocol parameters
- Protocol fee distribution to token holders
- KYC/compliance enforcement via ERC-735 identity claims
- Flexible compliance modes (permissioned or permissionless)

---

## Part A: Governance System (25 hours)

### 1. Governance Token (FP Token) (10 hours)

**Purpose**: Enable community governance and align incentives

**Implementation**:
```solidity
// FusionPrimeToken.sol
contract FusionPrimeToken is ERC20, ERC20Votes {
    uint256 public constant TOTAL_SUPPLY = 100_000_000 * 1e18; // 100M tokens
    
    constructor() ERC20("Fusion Prime", "FP") ERC20Permit("Fusion Prime") {
        _mint(msg.sender, TOTAL_SUPPLY);
    }
}
```

**Token Distribution**:
- 40% - Community (liquidity mining, airdrops)
- 25% - Team (4-year vesting, 1-year cliff)
- 20% - Investors (3-year vesting)
- 10% - Treasury (governance-controlled)
- 5% - Advisors (2-year vesting)

**Vesting Schedule**:
```solidity
contract TokenVesting {
    struct VestingSchedule {
        uint256 totalAmount;
        uint256 startTime;
        uint256 cliffDuration;
        uint256 vestingDuration;
        uint256 claimed;
    }
    
    mapping(address => VestingSchedule) public schedules;
}
```

**Tasks**:
- [ ] Deploy FP token (ERC20Votes)
- [ ] Create vesting contracts
- [ ] Set up initial distribution
- [ ] Configure liquidity mining
- [ ] Write unit tests
- [ ] Deploy to testnet

---

### 2. Voting Mechanism (10 hours)

**Purpose**: Allow token holders to vote on protocol parameters

**Implementation**:
```solidity
// Governance.sol
contract Governance {
    struct Proposal {
        uint256 id;
        address proposer;
        string description;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 startBlock;
        uint256 endBlock;
        bool executed;
        mapping(address => bool) hasVoted;
    }
    
    uint256 public constant VOTING_PERIOD = 3 days;
    uint256 public constant VOTING_DELAY = 1 days;
    uint256 public constant QUORUM = 4_000_000 * 1e18; // 4% of supply
    uint256 public constant PROPOSAL_THRESHOLD = 100_000 * 1e18; // 0.1% to propose
    
    function propose(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        string memory description
    ) external returns (uint256);
    
    function vote(uint256 proposalId, bool support) external;
    
    function execute(uint256 proposalId) external;
}
```

**Governable Parameters**:
- Interest rate model parameters
- Collateral factors per asset
- Liquidation bonus
- Reserve factor
- Emergency pause (multi-sig override)

**Timelock**:
```solidity
contract Timelock {
    uint256 public constant DELAY = 2 days;
    
    function queueTransaction(
        address target,
        uint256 value,
        bytes memory data,
        uint256 eta
    ) external onlyGovernance;
    
    function executeTransaction(
        address target,
        uint256 value,
        bytes memory data
    ) external onlyGovernance;
}
```

**Tasks**:
- [ ] Implement governance contract
- [ ] Add proposal creation
- [ ] Add voting mechanism
- [ ] Implement timelock
- [ ] Add proposal execution
- [ ] Write unit tests
- [ ] Create governance UI

---

### 3. Protocol Fee Distribution (5 hours)

**Purpose**: Distribute protocol revenue to FP token stakers

**Implementation**:
```solidity
// FeeDistributor.sol
contract FeeDistributor {
    IERC20 public fpToken;
    mapping(address => uint256) public stakedBalance;
    mapping(address => uint256) public rewardDebt;
    
    uint256 public accRewardPerShare;
    uint256 public totalStaked;
    
    function stake(uint256 amount) external {
        updateRewards();
        fpToken.transferFrom(msg.sender, address(this), amount);
        stakedBalance[msg.sender] += amount;
        totalStaked += amount;
    }
    
    function unstake(uint256 amount) external {
        updateRewards();
        stakedBalance[msg.sender] -= amount;
        totalStaked -= amount;
        fpToken.transfer(msg.sender, amount);
    }
    
    function claimRewards() external {
        updateRewards();
        uint256 pending = calculatePendingRewards(msg.sender);
        // Transfer rewards (ETH, USDC, etc.)
    }
    
    function distributeRevenue(address token, uint256 amount) external {
        // Called by vault when reserves are distributed
        accRewardPerShare += (amount * 1e12) / totalStaked;
    }
}
```

**Tasks**:
- [ ] Implement staking contract
- [ ] Add reward calculation
- [ ] Integrate with vault reserves
- [ ] Add claim function
- [ ] Write unit tests
- [ ] Create staking UI

---

## Part B: KYC/Compliance Enforcement (30 hours)

### 1. Identity Contract Integration (10 hours)

**Purpose**: Link user addresses to ERC-735 identity contracts with KYC claims

**Implementation**:
```solidity
// IERC735.sol (Interface)
interface IERC735 {
    function getClaim(bytes32 claimId) external view returns (
        uint256 topic,
        uint256 scheme,
        address issuer,
        bytes memory signature,
        bytes memory data,
        string memory uri
    );
    
    function getClaimIdsByTopic(uint256 topic) external view returns (bytes32[] memory);
}

// Identity.sol (Simplified)
contract Identity is IERC735 {
    uint256 public constant KYC_VERIFIED = 1;
    
    struct Claim {
        uint256 topic;
        address issuer;
        bytes data;
    }
    
    mapping(bytes32 => Claim) public claims;
}
```

**Vault Integration**:
```solidity
// CrossChainVaultV31.sol
contract CrossChainVaultV31 {
    mapping(address => address) public userIdentities; // user => identity contract
    address public complianceService; // Trusted claim issuer
    
    function registerIdentity(address identityContract) external {
        userIdentities[msg.sender] = identityContract;
    }
    
    function isKYCVerified(address user) public view returns (bool) {
        address identity = userIdentities[user];
        if (identity == address(0)) return false;
        
        bytes32[] memory claimIds = IERC735(identity).getClaimIdsByTopic(1); // KYC_VERIFIED
        
        for (uint i = 0; i < claimIds.length; i++) {
            (,, address issuer,,,) = IERC735(identity).getClaim(claimIds[i]);
            if (issuer == complianceService) {
                return true;
            }
        }
        
        return false;
    }
}
```

**Tasks**:
- [ ] Import IERC735 interface
- [ ] Add identity registry mapping
- [ ] Implement `registerIdentity()`
- [ ] Implement `isKYCVerified()`
- [ ] Set compliance service address
- [ ] Write unit tests

---

### 2. Vault Gating (8 hours)

**Purpose**: Enforce KYC requirements on critical vault operations

**Implementation**:
```solidity
modifier onlyCompliant() {
    if (complianceMode == ComplianceMode.WHITELIST) {
        require(isKYCVerified(msg.sender), "KYC verification required");
    }
    _;
}

enum ComplianceMode { PERMISSIONLESS, WHITELIST }
ComplianceMode public complianceMode = ComplianceMode.PERMISSIONLESS;

function setComplianceMode(ComplianceMode mode) external onlyGovernance {
    complianceMode = mode;
    emit ComplianceModeChanged(mode);
}

// Apply to critical functions
function supply(uint256 amount) external onlyCompliant { ... }
function borrow(uint256 amount) external onlyCompliant { ... }
function depositCollateral() external payable onlyCompliant { ... }
```

**Compliance Modes**:
- **PERMISSIONLESS**: No KYC required (default for testnet)
- **WHITELIST**: KYC required for all operations (mainnet institutional)

**Error Messages**:
```solidity
error KYCRequired(address user);
error IdentityNotRegistered(address user);
error InvalidClaimIssuer(address issuer);
```

**Tasks**:
- [ ] Add `onlyCompliant` modifier
- [ ] Add compliance mode enum
- [ ] Apply to critical functions
- [ ] Add governance toggle
- [ ] Add custom errors
- [ ] Write unit tests

---

### 3. Compliance Service Integration (12 hours)

**Purpose**: Connect vault to existing compliance service for KYC verification

**Architecture**:
```
User → Frontend → Compliance Service → Identity Contract → Vault
```

**Flow**:
1. User initiates KYC in frontend
2. Frontend calls compliance service `/kyc` endpoint
3. User completes KYC verification
4. Compliance service issues KYC claim to user's identity contract
5. User registers identity contract with vault
6. Vault checks claim before allowing operations

**Frontend Integration**:
```typescript
// KYC Flow
async function initiateKYC() {
  // 1. Call compliance service
  const response = await fetch('/compliance/kyc', {
    method: 'POST',
    body: JSON.stringify({ userId: address })
  });
  
  const { caseId } = await response.json();
  
  // 2. Redirect to KYC provider
  window.location.href = `/kyc/${caseId}`;
}

// After KYC approval
async function registerIdentity() {
  // Get identity contract address from compliance service
  const identity = await getIdentityContract(address);
  
  // Register with vault
  await vault.registerIdentity(identity);
}

// Check KYC status
async function checkKYCStatus() {
  const isVerified = await vault.isKYCVerified(address);
  return isVerified;
}
```

**Tasks**:
- [ ] Connect to compliance service API
- [ ] Implement KYC initiation flow
- [ ] Add identity registration UI
- [ ] Show KYC status in dashboard
- [ ] Add KYC warning banners
- [ ] Handle KYC errors gracefully
- [ ] Write integration tests

---

### 4. Admin Controls (Optional, 5 hours)

**Purpose**: Flexible compliance configuration for different deployments

**Implementation**:
```solidity
// Per-deployment configuration
struct ComplianceConfig {
    bool kycRequired;
    address[] trustedIssuers;
    uint256[] requiredClaims; // e.g., [1] for KYC_VERIFIED
}

ComplianceConfig public config;

function setComplianceConfig(ComplianceConfig memory newConfig) external onlyGovernance {
    config = newConfig;
}

// Multi-issuer support
function isTrustedIssuer(address issuer) public view returns (bool) {
    for (uint i = 0; i < config.trustedIssuers.length; i++) {
        if (config.trustedIssuers[i] == issuer) return true;
    }
    return false;
}
```

**Use Cases**:
- Testnet: No KYC required
- Mainnet (retail): Optional KYC
- Mainnet (institutional): Mandatory KYC
- Private deployment: Custom compliance rules

**Tasks**:
- [ ] Add compliance config struct
- [ ] Implement multi-issuer support
- [ ] Add config update function
- [ ] Write unit tests

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| FP token deployed | ✅ ERC20Votes |
| Vesting contracts working | ✅ Team/investor vesting |
| Governance proposals work | ✅ Create, vote, execute |
| Timelock enforced | ✅ 2-day delay |
| Staking functional | ✅ Stake, unstake, claim |
| Revenue distributed to stakers | ✅ Tested |
| Identity integration complete | ✅ ERC-735 support |
| KYC gating works | ✅ Blocks non-KYC users |
| Compliance service connected | ✅ End-to-end flow |
| Frontend shows KYC status | ✅ UI complete |

---

## Deliverables

### Smart Contracts
- `FusionPrimeToken.sol` - Governance token
- `Governance.sol` - Voting mechanism
- `Timelock.sol` - Execution delay
- `FeeDistributor.sol` - Staking & rewards
- `CrossChainVaultV31.sol` - Vault with compliance
- `TokenVesting.sol` - Vesting schedules

### Frontend
- Governance dashboard
- Proposal creation UI
- Voting interface
- Staking UI
- KYC verification flow
- KYC status display

### Documentation
- Governance guide
- KYC user guide
- Compliance admin guide

---

## Testing Strategy

### Unit Tests
```bash
forge test -vvv --match-contract GovernanceTest
forge test -vvv --match-contract ComplianceTest
```

**Test Cases**:
- ✅ Token minting and distribution
- ✅ Vesting schedule enforcement
- ✅ Proposal creation (threshold check)
- ✅ Voting (for/against)
- ✅ Quorum calculation
- ✅ Timelock execution
- ✅ Staking/unstaking
- ✅ Reward distribution
- ✅ Identity registration
- ✅ KYC verification check
- ✅ Compliance mode toggle
- ✅ Gated function access

### Integration Tests
- End-to-end governance proposal
- KYC verification flow
- Cross-chain with compliance
- Staking rewards from protocol revenue

---

## Dependencies

**Smart Contracts**:
- OpenZeppelin: `ERC20Votes`, `Ownable`, `TimelockController`
- ERC-735 identity contracts (existing)
- Compliance service (existing)

**Frontend**:
- Governance UI components
- KYC provider integration
- Wallet connection for voting

**Backend**:
- Compliance service API
- Identity contract deployment

---

## Risks & Mitigations

**Risk 1**: Governance attack (whale control)
- **Mitigation**: Quorum requirements, timelock, delegation

**Risk 2**: KYC provider failure
- **Mitigation**: Multi-issuer support, fallback providers

**Risk 3**: Compliance mode misconfiguration
- **Mitigation**: Governance-only changes, clear documentation

**Risk 4**: Vesting contract bugs
- **Mitigation**: Use battle-tested OpenZeppelin contracts

---

## Implementation Order

### Week 1: Governance Token & Voting
- **Days 1-2**: Deploy FP token and vesting
- **Days 3-4**: Implement governance contract
- **Day 5**: Timelock implementation

### Week 2: Fee Distribution & Testing
- **Days 6-7**: Staking and fee distribution
- **Days 8-9**: Governance testing
- **Day 10**: Frontend governance UI

### Week 3: KYC Integration
- **Days 11-12**: Identity contract integration
- **Days 13-14**: Vault gating implementation
- **Day 15**: Compliance service connection

### Week 4: Testing & Deployment
- **Days 16-17**: Integration testing
- **Day 18**: Deploy to testnet
- **Days 19-20**: Frontend KYC UI
- **Day 21**: Final testing

---

## Estimated Time

| Task | Hours |
|------|-------|
| **Part A: Governance** | |
| Governance Token | 10 |
| Voting Mechanism | 10 |
| Fee Distribution | 5 |
| **Part B: Compliance** | |
| Identity Integration | 10 |
| Vault Gating | 8 |
| Service Integration | 12 |
| Admin Controls (Optional) | 5 |
| **Total** | **55 hours** |

---

## Production Readiness (Parallel)

During Sprint 13, also complete:

### Security Audit Preparation
- Code freeze after Sprint 13
- Prepare audit documentation
- Schedule audit firm (4-6 weeks, $50k-$150k)
- Begin bug bounty program

**See**: [ROADMAP_SPRINTS_11-13.md](./ROADMAP_SPRINTS_11-13.md#4-security-audit-external)

---

## Related Documentation

- [Sprint 12 Plan](./sprint-12-plan.md)
- [Compliance & Identity Integration](/home/koita/dev/web3/fusion-prime/docs/COMPLIANCE_IDENTITY_INTEGRATION.md)
- [Roadmap Overview](./ROADMAP_SPRINTS_11-13.md)

---

**Document Version**: 1.0 (Draft)  
**Status**: 📋 Draft  
**Last Updated**: 2025-11-20  
**Next Review**: After Sprint 12 completion
