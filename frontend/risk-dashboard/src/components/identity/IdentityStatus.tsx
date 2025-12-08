/**
 * Identity Status Component
 * Shows user's identity and verification status
 */

import { useAccount } from 'wagmi';
import { useIdentityStatus } from '../../hooks/contracts/useIdentityFactory';
import { useIdentityVerificationData } from '../../hooks/contracts/useIdentity';
import { VerificationBadge } from './VerificationBadge';
import { Shield, Loader2, AlertCircle } from 'lucide-react';

export function IdentityStatus() {
  const { address, isConnected } = useAccount();
  const { hasIdentity, identityAddress, isLoading: identityLoading } = useIdentityStatus(address);
  const { claims, allLoading, requiredVerified } = useIdentityVerificationData(identityAddress);

  if (!isConnected) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-center gap-3 text-gray-500">
          <Shield size={24} />
          <p>Connect your wallet to view identity status</p>
        </div>
      </div>
    );
  }

  if (identityLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-center gap-3">
          <Loader2 size={24} className="animate-spin text-blue-600" />
          <p className="text-gray-600">Loading identity status...</p>
        </div>
      </div>
    );
  }

  if (!hasIdentity) {
    return (
      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-6">
        <div className="flex items-start gap-3">
          <AlertCircle size={24} className="text-yellow-600 mt-0.5" />
          <div>
            <h3 className="font-semibold text-yellow-900 mb-1">Identity Not Created</h3>
            <p className="text-sm text-yellow-700 mb-3">
              You need to create an identity before using the platform features.
            </p>
            <button className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors">
              Create Identity
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-100">
            <Shield size={24} className="text-blue-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Identity Status</h3>
            <p className="text-sm text-gray-500 font-mono">
              {identityAddress?.slice(0, 6)}...{identityAddress?.slice(-4)}
            </p>
          </div>
        </div>

        {requiredVerified ? (
          <div className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
            Verified
          </div>
        ) : (
          <div className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm font-medium">
            Incomplete
          </div>
        )}
      </div>

      <div className="space-y-2">
        {claims.map((claim) => (
          <VerificationBadge
            key={claim.topic}
            verified={claim.verified}
            loading={claim.loading}
            label={claim.name}
            required={claim.required}
            size="md"
          />
        ))}
      </div>

      {!requiredVerified && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Complete Verification
          </button>
        </div>
      )}
    </div>
  );
}
