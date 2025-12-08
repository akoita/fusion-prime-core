import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { http } from 'wagmi';
import { sepolia } from 'wagmi/chains';
import { polygonAmoy } from './chains';

/**
 * Wagmi Configuration for Fusion Prime
 *
 * This configuration sets up:
 * - Wallet connection via RainbowKit
 * - Multi-chain support (Sepolia + Polygon Amoy testnets)
 * - WalletConnect integration
 * - Automatic wallet detection
 * - Custom RPC endpoints with API keys to avoid rate limiting
 *
 * Supported wallets:
 * - MetaMask
 * - Coinbase Wallet
 * - WalletConnect (mobile wallets)
 * - Rainbow Wallet
 * - Trust Wallet
 * - And 100+ more automatically
 */

// Get WalletConnect project ID from environment variable
// You can get one for free at https://cloud.walletconnect.com
const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'YOUR_PROJECT_ID';

if (projectId === 'YOUR_PROJECT_ID') {
  console.warn(
    '⚠️ WalletConnect Project ID not set. Please add VITE_WALLETCONNECT_PROJECT_ID to your .env file.\n' +
    'Get one for free at https://cloud.walletconnect.com'
  );
}

// Get RPC URLs from environment variables
const sepoliaRpcUrl = import.meta.env.VITE_SEPOLIA_RPC_URL || sepolia.rpcUrls.default.http[0];
const polygonAmoyRpcUrl = import.meta.env.VITE_POLYGON_AMOY_RPC_URL || polygonAmoy.rpcUrls.default.http[0];

export const wagmiConfig = getDefaultConfig({
  appName: 'Fusion Prime',
  projectId,
  chains: [sepolia, polygonAmoy],
  transports: {
    [sepolia.id]: http(sepoliaRpcUrl),
    [polygonAmoy.id]: http(polygonAmoyRpcUrl),
  },
  ssr: false, // Set to true if using Next.js with SSR
});

/**
 * RPC Configuration
 *
 * wagmi will use these RPC endpoints to communicate with the blockchain.
 * For production, consider using:
 * - Infura (https://infura.io)
 * - Alchemy (https://alchemy.com)
 * - QuickNode (https://quicknode.com)
 *
 * Current configuration uses public RPCs (free, but may be rate-limited)
 */

/**
 * Chain Configuration Summary:
 *
 * Sepolia (Chain ID: 11155111)
 * - Ethereum testnet
 * - Block time: ~12 seconds
 * - Faucets:
 *   - https://sepoliafaucet.com
 *   - https://faucet.sepolia.dev
 *
 * Polygon Amoy (Chain ID: 80002)
 * - Polygon testnet
 * - Block time: ~2 seconds
 * - Faucets:
 *   - https://faucet.polygon.technology
 */
