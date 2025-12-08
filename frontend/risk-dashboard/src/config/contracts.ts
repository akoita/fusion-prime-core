/**
 * Contract addresses and configuration
 * Update these after deployment
 */

export const CONTRACT_ADDRESSES = {
  // Identity System (Sepolia Testnet)
  IDENTITY_FACTORY: (import.meta.env.VITE_IDENTITY_FACTORY_ADDRESS ||
    '0x0000000000000000000000000000000000000000') as `0x${string}`,

  CLAIM_ISSUER_REGISTRY: (import.meta.env.VITE_CLAIM_ISSUER_REGISTRY_ADDRESS ||
    '0x0000000000000000000000000000000000000000') as `0x${string}`,

  // Escrow System (from previous deployment)
  ESCROW_FACTORY: (import.meta.env.VITE_ESCROW_FACTORY_ADDRESS ||
    '0x0000000000000000000000000000000000000000') as `0x${string}`,

  // Cross-Chain System V24 (with Chainlink Oracle Integration)
  // Sepolia (Chain ID: 11155111)
  SEPOLIA_VAULT_V24: (import.meta.env.VITE_SEPOLIA_VAULT_V24 ||
    '0x3d0be24dDa36816769819f899d45f01a45979e8B') as `0x${string}`,
  SEPOLIA_BRIDGE_MANAGER: (import.meta.env.VITE_SEPOLIA_BRIDGE_MANAGER ||
    '0xA8d853C5b945924d217Ec4119E9f0e2eFf714B8a') as `0x${string}`,

  // Amoy (Chain ID: 80002)
  AMOY_VAULT_V24: (import.meta.env.VITE_AMOY_VAULT_V24 ||
    '0x4B5e551288713992945c6E96b0C9A106d0DD1115') as `0x${string}`,
  AMOY_BRIDGE_MANAGER: (import.meta.env.VITE_AMOY_BRIDGE_MANAGER ||
    '0xEEcd2114162D577c4668B8e92a6FB34d0eA6A149') as `0x${string}`,

  // Legacy (for backward compatibility)
  BRIDGE_MANAGER: (import.meta.env.VITE_BRIDGE_MANAGER_ADDRESS ||
    '0xA8d853C5b945924d217Ec4119E9f0e2eFf714B8a') as `0x${string}`,
  CROSS_CHAIN_VAULT: (import.meta.env.VITE_CROSS_CHAIN_VAULT_ADDRESS ||
    '0x3d0be24dDa36816769819f899d45f01a45979e8B') as `0x${string}`,
} as const;

export const NETWORK_CONFIG = {
  SEPOLIA_CHAIN_ID: 11155111,
  SEPOLIA_RPC_URL: import.meta.env.VITE_SEPOLIA_RPC_URL || 'https://sepolia.infura.io/v3/',
} as const;

// Service URLs
export const SERVICE_URLS = {
  IDENTITY_SERVICE: import.meta.env.VITE_IDENTITY_SERVICE_URL || 'http://localhost:8002',
  COMPLIANCE_SERVICE: import.meta.env.VITE_COMPLIANCE_SERVICE_URL || 'http://localhost:8001',
} as const;

// Claim topics
export const CLAIM_TOPICS = {
  KYC_VERIFIED: 1,
  AML_CLEARED: 2,
  ACCREDITED_INVESTOR: 3,
  SANCTIONS_CLEARED: 4,
  COUNTRY_ALLOWED: 5,
} as const;

// Feature flags
export const FEATURES = {
  IDENTITY_SYSTEM_ENABLED: import.meta.env.VITE_IDENTITY_ENABLED !== 'false',
  PERSONA_KYC_ENABLED: import.meta.env.VITE_PERSONA_ENABLED !== 'false',
} as const;
