/**
 * Identity Dashboard
 * Complete view of user's identity and verification status
 */

import { useAccount } from 'wagmi';
import { useIdentityStatus } from '../../hooks/contracts/useIdentityFactory';
import { useIdentityVerificationData } from '../../hooks/contracts/useIdentity';
import { IdentityStatus } from './IdentityStatus';
import { Shield, FileCheck, TrendingUp, Lock } from 'lucide-react';

export function IdentityDashboard() {
  const { address, isConnected } = useAccount();
  const { hasIdentity, identityAddress } = useIdentityStatus(address);
  const { claims, requiredVerified } = useIdentityVerificationData(identityAddress);

  const features = [
    {
      icon: FileCheck,
      title: 'Create Escrows',
      description: 'Create and manage secure escrow transactions',
      enabled: requiredVerified,
      requiredClaims: ['KYC Verified'],
    },
    {
      icon: TrendingUp,
      title: 'Cross-Chain Transfers',
      description: 'Transfer assets across different blockchains',
      enabled: requiredVerified,
      requiredClaims: ['KYC Verified', 'AML Cleared'],
    },
    {
      icon: Lock,
      title: 'Advanced Features',
      description: 'Access premium platform features',
      enabled: claims.every((c) => c.verified),
      requiredClaims: ['All Claims'],
    },
  ];

  if (!isConnected) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center py-12">
          <Shield size={64} className="mx-auto text-gray-400 mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect Your Wallet</h2>
          <p className="text-gray-600">
            Connect your wallet to view your identity and verification status
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Identity Dashboard</h1>
        <p className="text-gray-600">
          Manage your decentralized identity and compliance verification
        </p>
      </div>

      {/* Identity Status Card */}
      <IdentityStatus />

      {/* Feature Access */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Feature Access</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className={`rounded-lg border p-4 ${
                  feature.enabled
                    ? 'border-green-200 bg-green-50'
                    : 'border-gray-200 bg-gray-50'
                }`}
              >
                <div className="flex items-start gap-3 mb-3">
                  <div
                    className={`p-2 rounded-lg ${
                      feature.enabled ? 'bg-green-200' : 'bg-gray-200'
                    }`}
                  >
                    <Icon
                      size={20}
                      className={feature.enabled ? 'text-green-700' : 'text-gray-600'}
                    />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1">{feature.title}</h3>
                    <p className="text-sm text-gray-600">{feature.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`h-2 w-2 rounded-full ${
                      feature.enabled ? 'bg-green-500' : 'bg-gray-400'
                    }`}
                  />
                  <span
                    className={`text-xs font-medium ${
                      feature.enabled ? 'text-green-700' : 'text-gray-600'
                    }`}
                  >
                    {feature.enabled ? 'Enabled' : 'Requires Verification'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* How It Works */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">How It Works</h2>
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold">
              1
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Create Identity</h3>
              <p className="text-sm text-gray-600">
                Deploy your own Identity smart contract on the blockchain
              </p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold">
              2
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Complete KYC</h3>
              <p className="text-sm text-gray-600">
                Verify your identity through our secure KYC provider (Persona)
              </p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold">
              3
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Receive Claims</h3>
              <p className="text-sm text-gray-600">
                Get verification claims added to your identity contract
              </p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold">
              4
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Access Features</h3>
              <p className="text-sm text-gray-600">
                Use verified identity to access platform features
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Contract Info */}
      {hasIdentity && identityAddress && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Contract Information</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Identity Contract:</span>
              <span className="font-mono text-gray-900">
                {identityAddress.slice(0, 10)}...{identityAddress.slice(-8)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Network:</span>
              <span className="text-gray-900">Sepolia Testnet</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Standard:</span>
              <span className="text-gray-900">ERC-734/735</span>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-200">
            <a
              href={`https://sepolia.etherscan.io/address/${identityAddress}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              View on Etherscan →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
