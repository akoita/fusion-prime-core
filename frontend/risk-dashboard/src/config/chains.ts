import { Chain } from 'wagmi/chains';
import { sepolia } from 'wagmi/chains';

/**
 * Polygon Amoy Testnet
 * Custom chain definition (not in wagmi by default yet)
 */
export const polygonAmoy: Chain = {
  id: 80002,
  name: 'Polygon Amoy',
  nativeCurrency: {
    name: 'MATIC',
    symbol: 'MATIC',
    decimals: 18,
  },
  rpcUrls: {
    default: {
      http: [
        'https://rpc-amoy.polygon.technology',
        'https://polygon-amoy-bor-rpc.publicnode.com',
        'https://polygon-amoy.infura.io/v3/6c474ab8fd5f48b294e1a082adc2c826',
      ],
    },
    public: {
      http: [
        'https://rpc-amoy.polygon.technology',
        'https://polygon-amoy-bor-rpc.publicnode.com',
      ],
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

/**
 * Contract addresses per chain
 *
 * Sepolia (Chain ID: 11155111):
 * - Ethereum testnet
 * - Used for Escrow contracts and Cross-Chain Vault
 *
 * Polygon Amoy (Chain ID: 80002):
 * - Polygon testnet
 * - Used for Cross-Chain Vault
 *
 * @note V23 Update: Absolute State Sync (Fixes Double-Counting Bug)
 * - Added ACTION_SYNC_STATE (value 5) for absolute state replacement
 * - reconcileBalance() now uses ACTION_SYNC_STATE instead of ACTION_DEPOSIT
 * - Prevents double-counting: uses `=` instead of `+=` for state updates
 * - Relayer has persistent state tracking to prevent missing/reprocessing messages
 * - Uses MessageBridge with direct callback mechanism
 * - executeMessage() function receives cross-chain messages
 * - No external bridge fees, relayer-based execution
 * - MIN_GAS_AMOUNT enforcement (0.01 ETH)
 *
 * @note V23 Deployment (Currently Active):
 * - Deployed using custom MessageBridge (relayer-based)
 * - trustedVaults configured bidirectionally on both chains
 * - MessageBridge contracts: Sepolia 0xA8d853C5b945924d217Ec4119E9f0e2eFf714B8a, Amoy 0xEEcd2114162D577c4668B8e92a6FB34d0eA6A149
 * - Sepolia V23 Vault: 0x397c9aFDBB18803931154bbB6F9854fcbdaEeCff
 * - Amoy V23 Vault: 0xf0dba0090aaAEAe37dBe9Ce1c3a117b766b8A31d
 * - Enables AUTOMATIC cross-chain message execution via relayer
 * - Lower gas costs, no external protocol dependencies
 *
 * @note V25 Deployment (In Progress - Cross-Chain Messaging Blocked):
 * - Sepolia V25 Vault: 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312
 * - Amoy V25 Vault: 0xbafd9d789f96d18cedd057899a4ba3273c9f6d0e
 * - Issue: BridgeManager cross-chain messaging fails with "execution reverted"
 * - Requires debugging of Axelar/CCIP integration or gas estimation
 */
export const CONTRACTS = {
  // Sepolia Testnet (11155111)
  [sepolia.id]: {
    EscrowFactory: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914' as const,
    // V23 deployment - MessageBridge with absolute state sync (fixes double-counting)
    CrossChainVault: '0x397c9aFDBB18803931154bbB6F9854fcbdaEeCff' as const,
    MessageBridge: '0xA8d853C5b945924d217Ec4119E9f0e2eFf714B8a' as const,
  },
  // Polygon Amoy Testnet (80002)
  [polygonAmoy.id]: {
    // V23 deployment - MessageBridge with absolute state sync (fixes double-counting)
    CrossChainVault: '0xf0dba0090aaAEAe37dBe9Ce1c3a117b766b8A31d' as const,
    MessageBridge: '0xEEcd2114162D577c4668B8e92a6FB34d0eA6A149' as const,
  },
} as const;

/**
 * Get contract address for the current chain
 */
export function getContractAddress(
  chainId: number,
  contractName: keyof typeof CONTRACTS[typeof sepolia.id] | keyof typeof CONTRACTS[typeof polygonAmoy.id]
): string | undefined {
  const chainContracts = CONTRACTS[chainId as keyof typeof CONTRACTS];
  if (!chainContracts) return undefined;
  return chainContracts[contractName as keyof typeof chainContracts];
}

/**
 * Chain metadata for UI display
 */
export const CHAIN_INFO = {
  [sepolia.id]: {
    name: 'Sepolia',
    shortName: 'SEP',
    color: '#627EEA', // Ethereum blue
    icon: '⟠', // Ethereum symbol
  },
  [polygonAmoy.id]: {
    name: 'Polygon Amoy',
    shortName: 'AMOY',
    color: '#8247E5', // Polygon purple
    icon: '⬡', // Polygon symbol
  },
} as const;

/**
 * Supported chains for the application
 */
export const SUPPORTED_CHAINS = [sepolia, polygonAmoy] as const;
