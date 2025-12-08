# Frontend Web3 Architecture - Recommended Solution

**Date**: November 3, 2025
**Project**: Fusion Prime
**Purpose**: Define the blockchain client architecture for the frontend

---

## Executive Summary

**Recommended Stack**:
- **Wallet Connection**: RainbowKit 2.x (built on wagmi)
- **Web3 Library**: wagmi 2.x + viem 2.x (NOT ethers.js)
- **Account Abstraction**: YES - via Biconomy SDK (progressive enhancement)
- **Multi-Chain**: Native support via wagmi (Sepolia, Amoy, future mainnet)
- **State Management**: TanStack Query (React Query) - built into wagmi
- **Type Safety**: Full TypeScript with auto-generated contract types

**Why This Stack?**:
- ✅ Modern, performant, and actively maintained
- ✅ Best-in-class TypeScript support
- ✅ Built for multi-chain from day 1
- ✅ Excellent developer experience
- ✅ Production-ready with major projects using it (Uniswap, ENS, etc.)
- ✅ Account Abstraction support via Biconomy
- ✅ Future-proof (EIP-4337 ready)

---

## 1. Wallet Connection Solution

### Recommendation: **RainbowKit 2.x**

**Why RainbowKit?**
- ✅ Beautiful, customizable UI out of the box
- ✅ Built on top of wagmi (best Web3 React library)
- ✅ Supports 100+ wallets automatically
- ✅ Built-in wallet detection and connection flow
- ✅ Mobile wallet support (WalletConnect v2)
- ✅ Responsive and accessible
- ✅ Custom chain support (easy to add testnets)
- ✅ Theme customization to match your brand
- ✅ Battle-tested (used by Uniswap, Zora, Highlight, etc.)

**Supported Wallets**:
- MetaMask (most popular)
- Coinbase Wallet
- WalletConnect (universal, mobile-friendly)
- Rainbow Wallet
- Trust Wallet
- Ledger (hardware wallet)
- Argent (smart contract wallet)
- Safe (Gnosis Safe multi-sig)
- And 100+ more automatically

**Alternative Considered**: Web3Modal (WalletConnect)
- ❌ Less opinionated, more configuration needed
- ❌ UI not as polished
- ✅ Good alternative if you need more control

**Installation**:
```bash
pnpm add @rainbow-me/rainbowkit wagmi viem @tanstack/react-query
```

**Basic Setup** (`src/config/wagmi.ts`):
```typescript
import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { sepolia, polygonAmoy } from 'wagmi/chains';

export const config = getDefaultConfig({
  appName: 'Fusion Prime',
  projectId: 'YOUR_WALLETCONNECT_PROJECT_ID', // Get from cloud.walletconnect.com
  chains: [sepolia, polygonAmoy],
  ssr: false, // Set to true if using Next.js
});
```

**UI Component** (`src/components/WalletConnect.tsx`):
```typescript
import { ConnectButton } from '@rainbow-me/rainbowkit';

export function WalletConnect() {
  return (
    <ConnectButton
      chainStatus="icon"
      showBalance={true}
      accountStatus="address"
    />
  );
}
// That's it! One component, full wallet connection UX
```

---

## 2. Web3 Library Solution

### Recommendation: **wagmi 2.x + viem 2.x** (NOT ethers.js)

**Why wagmi + viem?**

#### wagmi 2.x
- ✅ **React hooks for everything** - `useContractRead`, `useContractWrite`, `useAccount`, etc.
- ✅ **Multi-chain by default** - Switch networks seamlessly
- ✅ **Built-in caching** - Via TanStack Query (React Query)
- ✅ **TypeScript-first** - Excellent type inference
- ✅ **Auto-refresh** - Real-time blockchain data with `watch: true`
- ✅ **Automatic retries** - Network failures handled gracefully
- ✅ **Transaction management** - Pending, confirmed, failed states handled
- ✅ **Most popular** - Used by Uniswap, ENS, Zora, Highlight, etc.
- ✅ **Actively maintained** - Weekly updates, great community

#### viem 2.x
- ✅ **Modern ethers.js replacement** - Smaller, faster, better types
- ✅ **TypeScript-native** - Built for TypeScript from the ground up
- ✅ **Tree-shakeable** - Only import what you use (smaller bundles)
- ✅ **Better performance** - 2-5x faster than ethers.js
- ✅ **Better error messages** - Decodes contract revert reasons
- ✅ **ABIType integration** - Auto-generated types from ABIs
- ✅ **Future-proof** - Modern codebase, actively maintained

**Why NOT ethers.js?**
- ❌ Older architecture (v5 from 2020, v6 just released but less mature)
- ❌ Worse TypeScript support
- ❌ No React hooks (need to build yourself)
- ❌ Larger bundle size
- ❌ Slower performance
- ❌ No built-in caching
- ✅ Still good for backend scripts, but wagmi+viem better for React

**Example: Reading Contract Data**
```typescript
// With wagmi + viem
import { useContractRead } from 'wagmi';
import EscrowFactoryABI from '@/abis/EscrowFactory.json';

function UserEscrows({ address }: { address: Address }) {
  const { data: escrows, isLoading, error } = useContractRead({
    address: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914',
    abi: EscrowFactoryABI,
    functionName: 'getUserEscrows',
    args: [address],
    watch: true, // Auto-refresh on new blocks
    chainId: sepolia.id,
  });

  if (isLoading) return <Skeleton />;
  if (error) return <Error message={error.message} />;

  return (
    <div>
      {escrows?.map((escrowAddress) => (
        <EscrowCard key={escrowAddress} address={escrowAddress} />
      ))}
    </div>
  );
}

// That's it! Caching, loading states, errors, real-time updates - all handled.
```

**Example: Writing to Contract (Transactions)**
```typescript
import { useContractWrite, useWaitForTransaction } from 'wagmi';

function CreateEscrowButton() {
  const { write, data, isLoading, isError } = useContractWrite({
    address: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914',
    abi: EscrowFactoryABI,
    functionName: 'createEscrow',
  });

  const { isLoading: isConfirming } = useWaitForTransaction({
    hash: data?.hash,
    onSuccess: () => {
      toast.success('Escrow created successfully!');
    },
  });

  const handleCreate = () => {
    write({
      args: [payeeAddress, arbiterAddress, timelockDuration],
      value: parseEther('1.0'), // Send 1 ETH
    });
  };

  return (
    <button onClick={handleCreate} disabled={isLoading || isConfirming}>
      {isConfirming ? 'Creating...' : 'Create Escrow'}
    </button>
  );
}
```

**Type Safety with ABIType**:
```bash
# Generate TypeScript types from ABIs automatically
pnpm add -D wagmi-cli @wagmi/cli
```

```typescript
// wagmi.config.ts
import { defineConfig } from '@wagmi/cli';
import { foundry } from '@wagmi/cli/plugins';

export default defineConfig({
  out: 'src/generated.ts',
  contracts: [],
  plugins: [
    foundry({
      project: '../contracts',
      include: [
        'EscrowFactory.sol/**',
        'Escrow.sol/**',
        'CrossChainVault.sol/**',
        'BridgeManager.sol/**',
      ],
    }),
  ],
});
```

Then run:
```bash
pnpm wagmi generate
```

This auto-generates:
```typescript
// src/generated.ts
export const escrowFactoryABI = [...] as const;
export const escrowFactoryAddress = {
  11155111: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914', // Sepolia
} as const;

// Now use with perfect TypeScript inference:
const { data } = useContractRead({
  address: escrowFactoryAddress[11155111],
  abi: escrowFactoryABI,
  functionName: 'getUserEscrows', // ✅ Autocomplete!
  args: [userAddress], // ✅ Type-checked!
});
// data is fully typed based on contract return type!
```

---

## 3. Account Abstraction (AA) Solution

### Recommendation: **YES - Implement with Biconomy SDK** (Progressive Enhancement)

**Why Account Abstraction?**

For an institutional DeFi platform, Account Abstraction is **highly recommended** because:

1. **Gas Abstraction** - Users can pay gas fees in USDC instead of ETH
   - Huge UX improvement for non-crypto-native users
   - No need to maintain ETH balance for gas
   - Simpler onboarding

2. **Sponsored Transactions** - You can sponsor gas fees for users
   - "Free" transactions for users (you pay gas)
   - Great for onboarding new users
   - Can be part of premium tier benefits

3. **Batched Transactions** - Multiple operations in one transaction
   - Example: Approve USDC + Deposit collateral in one click
   - Better UX, lower gas costs

4. **Session Keys** - Pre-approve actions without wallet pop-ups
   - Example: "Allow Fusion Prime to execute settlements for 24 hours"
   - No repeated wallet confirmations
   - Mobile-friendly (fewer interruptions)

5. **Social Recovery** - Recover account without seed phrase
   - Institutional users prefer this
   - Can use email, SMS, or trusted contacts

6. **Multi-Sig & Permissions** - Built-in role-based access
   - Perfect for institutional users
   - Treasury manager vs. viewer roles

**Why Biconomy?**
- ✅ EIP-4337 compliant (standard Account Abstraction)
- ✅ Best-in-class SDK and documentation
- ✅ Supports all major chains (Ethereum, Polygon, Arbitrum, Base, etc.)
- ✅ Built-in paymaster (gas sponsorship service)
- ✅ Session keys support
- ✅ Production-ready (used by many projects)
- ✅ Integrates with wagmi/viem

**Alternatives Considered**:
- ZeroDev: Good, but less mature
- Alchemy Account Kit: Locked into Alchemy infrastructure
- Safe (Gnosis Safe): Heavier, better for multi-sig than general AA

### Implementation Strategy: Progressive Enhancement

**Phase 1: Launch without AA** (Sprint 05)
- Use regular EOA wallets (MetaMask, etc.)
- Get to market faster
- Validate core features

**Phase 2: Add AA Support** (Sprint 06-07)
- Add Biconomy SDK alongside wagmi
- Give users choice: "Use Smart Wallet" (AA) or "Use Standard Wallet" (EOA)
- AA benefits:
  - Gas-free transactions (sponsor first 10 transactions per user)
  - USDC gas payments
  - Batch operations

**Phase 3: AA-First** (Future)
- Make AA the default for new users
- Keep EOA support for power users
- Full social recovery implementation

### Biconomy Integration (Future - Sprint 06+)

**Installation**:
```bash
pnpm add @biconomy/account @biconomy/bundler @biconomy/paymaster
```

**Basic Setup**:
```typescript
import { BiconomySmartAccountV2 } from '@biconomy/account';
import { createWalletClient } from 'viem';
import { useWalletClient } from 'wagmi';

export function useBiconomySmartAccount() {
  const { data: walletClient } = useWalletClient();

  const createSmartAccount = async () => {
    if (!walletClient) return;

    const smartAccount = await BiconomySmartAccountV2.create({
      signer: walletClient, // Use connected wallet as signer
      chainId: sepolia.id,
      bundlerUrl: 'https://bundler.biconomy.io/api/v2/11155111/nJPK7B3ru.dd7f7861-190d-41bd-af80-6877f74b8f44',
      paymasterUrl: 'https://paymaster.biconomy.io/api/v1/11155111/YOUR_API_KEY',
    });

    return smartAccount;
  };

  return { createSmartAccount };
}
```

**Sponsored Transaction Example**:
```typescript
// User creates escrow WITHOUT paying gas
const tx = await smartAccount.sendTransaction({
  to: escrowFactoryAddress,
  data: encodeFunctionData({
    abi: EscrowFactoryABI,
    functionName: 'createEscrow',
    args: [payeeAddress, arbiterAddress, timelockDuration],
  }),
  value: parseEther('1.0'),
});
// Gas paid by Fusion Prime (your paymaster)
// User only signs the transaction
```

**Recommendation for Sprint 05**:
- ❌ Skip AA for now - Add in Sprint 06
- ✅ Focus on core Web3 integration with wagmi first
- ✅ Design UI with AA in mind (e.g., "Gas fees: $0.50" text can later say "Gas fees: FREE")

---

## 4. Multi-Chain Support

### Recommendation: **Native Multi-Chain with wagmi**

**Chains to Support**:

**Testnet (Sprint 05)**:
- Sepolia (Ethereum testnet) - Chain ID: 11155111
- Polygon Amoy (Polygon testnet) - Chain ID: 80002

**Mainnet (Sprint 06+)**:
- Ethereum Mainnet - Chain ID: 1
- Polygon - Chain ID: 137
- Arbitrum - Chain ID: 42161
- Base - Chain ID: 8453

**Configuration** (`src/config/chains.ts`):
```typescript
import { Chain } from 'wagmi/chains';

// Custom chain definition for Amoy (not in wagmi by default yet)
export const polygonAmoy: Chain = {
  id: 80002,
  name: 'Polygon Amoy',
  network: 'polygon-amoy',
  nativeCurrency: {
    name: 'MATIC',
    symbol: 'MATIC',
    decimals: 18,
  },
  rpcUrls: {
    default: {
      http: ['https://rpc-amoy.polygon.technology'],
    },
    public: {
      http: ['https://rpc-amoy.polygon.technology'],
    },
  },
  blockExplorers: {
    default: {
      name: 'PolygonScan',
      url: 'https://amoy.polygonscan.com',
    },
  },
  testnet: true,
};

// Contract addresses per chain
export const CONTRACTS = {
  [sepolia.id]: {
    EscrowFactory: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914',
    CrossChainVault: '0x0C95a78b0D72F882fae14CD7C842a5f000E0c4e2',
    BridgeManager: '0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56',
  },
  [polygonAmoy.id]: {
    CrossChainVault: '0x7843C2eD8930210142DC51dbDf8419C74FD27529',
    BridgeManager: '0x3481dbE036C0F4076B397e27FFb8dC32B88d8882',
  },
} as const;
```

**Network Switcher UI**:
```typescript
import { useSwitchNetwork, useNetwork } from 'wagmi';

function NetworkSwitcher() {
  const { chain } = useNetwork();
  const { switchNetwork, chains } = useSwitchNetwork();

  return (
    <select
      value={chain?.id}
      onChange={(e) => switchNetwork?.(Number(e.target.value))}
    >
      {chains.map((chain) => (
        <option key={chain.id} value={chain.id}>
          {chain.name}
        </option>
      ))}
    </select>
  );
}
```

**Multi-Chain Contract Reads**:
```typescript
// Read collateral from BOTH Sepolia and Amoy
function useMultiChainCollateral(address: Address) {
  const sepoliaCollateral = useContractRead({
    address: CONTRACTS[sepolia.id].CrossChainVault,
    abi: CrossChainVaultABI,
    functionName: 'collateralBalances',
    args: [address, 'sepolia'],
    chainId: sepolia.id,
  });

  const amoyCollateral = useContractRead({
    address: CONTRACTS[polygonAmoy.id].CrossChainVault,
    abi: CrossChainVaultABI,
    functionName: 'collateralBalances',
    args: [address, 'amoy'],
    chainId: polygonAmoy.id,
  });

  const totalCollateral = (sepoliaCollateral.data || 0n) + (amoyCollateral.data || 0n);

  return {
    sepolia: sepoliaCollateral.data,
    amoy: amoyCollateral.data,
    total: totalCollateral,
    isLoading: sepoliaCollateral.isLoading || amoyCollateral.isLoading,
  };
}
```

---

## 5. State Management

### Recommendation: **TanStack Query (Built into wagmi) + Zustand**

**TanStack Query (React Query)** - For blockchain/server state
- ✅ Built into wagmi (no extra config needed)
- ✅ Automatic caching of contract reads
- ✅ Automatic refetching
- ✅ Optimistic updates
- ✅ Infinite queries for pagination

**Zustand** - For UI state (already in your project)
- ✅ Simple, minimal boilerplate
- ✅ Good for UI state (modals, forms, filters, etc.)
- ✅ NOT for blockchain state (use wagmi for that)

**Example: UI State with Zustand**:
```typescript
// src/stores/uiStore.ts
import { create } from 'zustand';

interface UIStore {
  isWalletModalOpen: boolean;
  openWalletModal: () => void;
  closeWalletModal: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  isWalletModalOpen: false,
  openWalletModal: () => set({ isWalletModalOpen: true }),
  closeWalletModal: () => set({ isWalletModalOpen: false }),
}));
```

**Example: Blockchain State with wagmi (TanStack Query)**:
```typescript
// Automatic caching, no extra setup needed
const { data: escrows } = useContractRead({
  address: escrowFactoryAddress,
  abi: EscrowFactoryABI,
  functionName: 'getUserEscrows',
  args: [userAddress],
  // Cached automatically by TanStack Query
  // Refetched every 10 seconds by default
});
```

---

## 6. Type Safety & Developer Experience

### Auto-Generated Contract Types

**Setup wagmi CLI**:
```bash
pnpm add -D @wagmi/cli
```

**Configure** (`wagmi.config.ts`):
```typescript
import { defineConfig } from '@wagmi/cli';
import { foundry } from '@wagmi/cli/plugins';

export default defineConfig({
  out: 'src/generated.ts', // Generated types go here
  contracts: [],
  plugins: [
    foundry({
      project: '../contracts', // Path to Foundry project
      deployments: {
        EscrowFactory: {
          11155111: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914', // Sepolia
        },
        CrossChainVault: {
          11155111: '0x0C95a78b0D72F882fae14CD7C842a5f000E0c4e2', // Sepolia
          80002: '0x7843C2eD8930210142DC51dbDf8419C74FD27529', // Amoy
        },
      },
    }),
  ],
});
```

**Generate Types**:
```bash
pnpm wagmi generate
```

**Result** (`src/generated.ts`):
```typescript
// Auto-generated, fully typed ABIs and addresses
export const escrowFactoryABI = [...] as const;
export const escrowFactoryAddress = {
  11155111: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914',
} as const;

// Use with perfect type inference:
const { data } = useContractRead({
  address: escrowFactoryAddress[11155111],
  abi: escrowFactoryABI,
  functionName: 'createEscrow', // ✅ Autocomplete
  args: [payee, arbiter, 3600], // ✅ Type-checked
});
```

---

## 7. Error Handling

### Contract Errors & User Feedback

**wagmi provides excellent error handling**:
```typescript
function CreateEscrowButton() {
  const { write, error } = useContractWrite({
    address: escrowFactoryAddress,
    abi: escrowFactoryABI,
    functionName: 'createEscrow',
    onError: (error) => {
      // Parse contract revert reason
      if (error.message.includes('Insufficient funds')) {
        toast.error('You don\'t have enough ETH to create this escrow.');
      } else if (error.message.includes('User rejected')) {
        toast.error('Transaction rejected');
      } else {
        toast.error(`Transaction failed: ${error.message}`);
      }
    },
  });

  return <button onClick={() => write(...)}>Create</button>;
}
```

**Common Errors to Handle**:
1. **User rejected transaction** → "Transaction cancelled"
2. **Insufficient funds** → "Not enough ETH. You have X, need Y."
3. **Wrong network** → "Please switch to Sepolia network"
4. **Contract revert** → Parse revert reason and display
5. **RPC error** → "Network error. Please try again."

---

## 8. Security Considerations

### Best Practices

1. **Never Trust User Input**
   - Validate all addresses (use `isAddress()` from viem)
   - Validate amounts (check against max uint256)
   - Sanitize form inputs

2. **Transaction Simulation**
   - Use wagmi's built-in simulation before sending transactions
   - Show gas estimate before user confirms
   - Warn if transaction will likely fail

3. **Wallet Security**
   - Never request seed phrases or private keys
   - Use WalletConnect for mobile (more secure than QR codes with keys)
   - Support hardware wallets (Ledger)

4. **Contract Interaction Safety**
   - Verify contract addresses (don't hardcode, use config)
   - Show transaction details before signing (what function, what args)
   - Use checksummed addresses

5. **RPC Security**
   - Use multiple RPC providers (fallback if one fails)
   - Don't expose RPC URLs with API keys in frontend
   - Consider using a proxy for RPC calls

**Example: Transaction Preview**:
```typescript
function CreateEscrowPreview({ payee, amount, arbiter, timelock }) {
  return (
    <div>
      <h3>Review Transaction</h3>
      <p>You are creating an escrow:</p>
      <ul>
        <li>Payee: {payee}</li>
        <li>Amount: {formatEther(amount)} ETH</li>
        <li>Arbiter: {arbiter}</li>
        <li>Timelock: {timelock} seconds</li>
      </ul>
      <p>Estimated Gas: 0.002 ETH ($4.50)</p>
      <button onClick={confirmTransaction}>Confirm</button>
    </div>
  );
}
```

---

## 9. Recommended Architecture

### File Structure

```
frontend/risk-dashboard/src/
├── abis/                       # Contract ABIs (JSON files)
│   ├── EscrowFactory.json
│   ├── Escrow.json
│   ├── CrossChainVault.json
│   └── BridgeManager.json
├── config/
│   ├── wagmi.ts               # Wagmi configuration
│   ├── chains.ts              # Chain configurations
│   └── contracts.ts           # Contract addresses per chain
├── hooks/
│   ├── useEscrowFactory.ts    # Escrow factory interactions
│   ├── useEscrow.ts           # Individual escrow interactions
│   ├── useCrossChainVault.ts  # Vault interactions
│   └── useBridgeManager.ts    # Bridge messaging
├── components/
│   ├── WalletConnect.tsx      # RainbowKit connect button
│   ├── NetworkSwitcher.tsx    # Chain switcher
│   └── TransactionStatus.tsx  # Transaction status display
├── pages/
│   ├── escrow/
│   │   ├── create.tsx         # Create escrow page
│   │   ├── manage.tsx         # Escrow list page
│   │   └── [id].tsx           # Escrow details page
│   └── cross-chain/
│       ├── vault.tsx          # Collateral vault
│       ├── settle.tsx         # Settlement initiation
│       └── messages.tsx       # Message tracking
├── services/
│   ├── contracts/
│   │   ├── escrowFactory.ts   # Escrow factory service layer
│   │   └── crossChainVault.ts # Vault service layer
│   └── api/
│       └── backend.ts         # Backend API client
├── utils/
│   ├── formatting.ts          # Format addresses, balances, etc.
│   └── validation.ts          # Validate addresses, amounts, etc.
└── generated.ts               # Auto-generated by wagmi CLI
```

### Component Pattern

**Separate concerns**:
1. **Hooks** - Contract interactions (read/write)
2. **Components** - UI logic and rendering
3. **Pages** - Route-level composition

**Example**:
```typescript
// hooks/useEscrowFactory.ts
export function useCreateEscrow() {
  return useContractWrite({
    address: escrowFactoryAddress,
    abi: escrowFactoryABI,
    functionName: 'createEscrow',
  });
}

// components/CreateEscrowForm.tsx
export function CreateEscrowForm() {
  const { write, isLoading } = useCreateEscrow();
  const [payee, setPayee] = useState('');
  const [amount, setAmount] = useState('');

  const handleSubmit = () => {
    write({
      args: [payee, arbiter, timelock],
      value: parseEther(amount),
    });
  };

  return <form onSubmit={handleSubmit}>...</form>;
}

// pages/escrow/create.tsx
export default function CreateEscrowPage() {
  return (
    <div>
      <h1>Create Escrow</h1>
      <CreateEscrowForm />
    </div>
  );
}
```

---

## 10. Summary: Recommended Stack

### Core Libraries (Install Now - Sprint 05)
```bash
cd frontend/risk-dashboard

# Wallet connection + Web3
pnpm add @rainbow-me/rainbowkit wagmi viem

# Required by wagmi
pnpm add @tanstack/react-query

# Development tools
pnpm add -D @wagmi/cli
```

### Future Libraries (Sprint 06+)
```bash
# Account Abstraction (when ready)
pnpm add @biconomy/account @biconomy/bundler @biconomy/paymaster
```

### Configuration Summary

**Wallet Connection**: RainbowKit 2.x
- Beautiful UI, 100+ wallets supported
- Mobile-friendly via WalletConnect
- Customizable theme

**Web3 Library**: wagmi 2.x + viem 2.x
- React hooks for all blockchain operations
- Multi-chain native
- Auto-generated TypeScript types
- Best developer experience

**Account Abstraction**: Biconomy SDK (Sprint 06+)
- EIP-4337 compliant
- Gas abstraction (pay in USDC)
- Sponsored transactions (you pay gas)
- Session keys (no repeated confirmations)

**Multi-Chain**: Native wagmi support
- Sepolia + Polygon Amoy (testnet)
- Ethereum + Polygon + Arbitrum + Base (mainnet)

**State Management**:
- TanStack Query (built into wagmi) - Blockchain state
- Zustand (already installed) - UI state

**Type Safety**:
- wagmi CLI - Auto-generate contract types from ABIs
- Full TypeScript inference
- Runtime type safety

---

## 11. Migration Path

### Sprint 05 - Phase 1: Core Web3 (Week 1)
1. Install RainbowKit + wagmi + viem
2. Set up wallet connection
3. Import contract ABIs
4. Create basic contract hooks
5. Test with Sepolia testnet

### Sprint 05 - Phase 2: Escrow UI (Week 2)
1. Create escrow pages (create, manage, details)
2. Implement contract interactions
3. Add transaction status handling
4. Real-time updates with events

### Sprint 05 - Phase 3: Cross-Chain UI (Week 2-3)
1. Multi-chain collateral display
2. Cross-chain settlement initiation
3. Message tracking
4. Integration with backend monitoring service

### Sprint 06 - Phase 4: Account Abstraction (Future)
1. Add Biconomy SDK
2. Implement smart wallet option
3. Gas sponsorship for new users
4. Session keys for settlements

---

## 12. Decision Matrix

| Feature | Recommended | Alternative | Reason |
|---------|------------|-------------|---------|
| **Wallet UI** | RainbowKit | Web3Modal | Better UX, more opinionated |
| **Web3 Library** | wagmi + viem | ethers.js | Modern, faster, better DX |
| **Account Abstraction** | Biconomy | ZeroDev | More mature, better docs |
| **Multi-Chain** | wagmi native | Manual config | Built-in, less code |
| **State Management** | TanStack Query | Redux | Built into wagmi |
| **Type Generation** | wagmi CLI | typechain | Native wagmi integration |

---

## 13. Resources

### Documentation
- **wagmi**: https://wagmi.sh/
- **viem**: https://viem.sh/
- **RainbowKit**: https://rainbowkit.com/
- **Biconomy**: https://docs.biconomy.io/
- **TanStack Query**: https://tanstack.com/query/latest

### Examples
- **wagmi Examples**: https://wagmi.sh/examples
- **RainbowKit Examples**: https://github.com/rainbow-me/rainbowkit/tree/main/examples
- **Uniswap Interface** (uses wagmi): https://github.com/Uniswap/interface

### Community
- **wagmi Discord**: https://discord.gg/wagmi
- **RainbowKit Discord**: https://discord.gg/rainbowkit

---

## Conclusion

**Recommended Stack**:
- ✅ **RainbowKit** for wallet connection (best UX)
- ✅ **wagmi + viem** for Web3 (modern, performant, great DX)
- ✅ **Biconomy** for Account Abstraction (Sprint 06+, institutional-friendly)
- ✅ **Native multi-chain** support (Sepolia, Amoy, future mainnet)
- ✅ **Auto-generated types** via wagmi CLI (type safety)

**Why This Stack Wins**:
1. **Modern & Maintained** - Latest best practices (2025)
2. **Production-Ready** - Used by Uniswap, ENS, Zora, etc.
3. **Great DX** - TypeScript-first, React hooks, minimal boilerplate
4. **Institutional-Friendly** - AA support for gas abstraction
5. **Multi-Chain Native** - No extra code for cross-chain
6. **Future-Proof** - EIP-4337 ready, actively maintained

**Sprint 05 Action Items**:
1. Install RainbowKit + wagmi + viem (Week 1, Day 1)
2. Set up wallet connection (Week 1, Day 1-2)
3. Import ABIs and generate types (Week 1, Day 2-3)
4. Build escrow UI (Week 2)
5. Build cross-chain UI (Week 2-3)

**Timeline**: 4 weeks to production-ready Web3 frontend.

---

**Status**: ✅ Recommended Architecture Defined
**Next Step**: Begin implementation in Sprint 05, Week 1
