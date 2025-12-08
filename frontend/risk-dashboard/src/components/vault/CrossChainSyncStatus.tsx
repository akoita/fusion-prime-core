import React from 'react';
import { type Address } from 'viem';
import { useMessageTracking } from '@/hooks/contracts/useMessageTracking';
import { Loader2, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';

interface CrossChainSyncStatusProps {
  userAddress?: Address;
  onSyncComplete?: () => void;
}

/**
 * Status indicator showing pending cross-chain message synchronization
 *
 * Displays a banner when cross-chain messages are being processed,
 * and calls onSyncComplete when all messages are confirmed.
 *
 * @example
 * <CrossChainSyncStatus
 *   userAddress={address}
 *   onSyncComplete={() => refetch()}
 * />
 */
export function CrossChainSyncStatus({ userAddress, onSyncComplete }: CrossChainSyncStatusProps) {
  const { pendingMessages, completedMessages, failedMessages, hasUnconfirmed } =
    useMessageTracking(userAddress);

  // Call onSyncComplete when a message completes
  React.useEffect(() => {
    if (completedMessages.length > 0 && !hasUnconfirmed && onSyncComplete) {
      onSyncComplete();
    }
  }, [completedMessages.length, hasUnconfirmed, onSyncComplete]);

  // Don't show anything if no messages
  if (pendingMessages.length === 0 && completedMessages.length === 0 && failedMessages.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {/* Pending Messages */}
      {pendingMessages.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-900">
                Syncing cross-chain state...
              </p>
              <p className="text-xs text-blue-700 mt-1">
                {pendingMessages.length} message{pendingMessages.length > 1 ? 's' : ''} being
                processed across chains (typically 5-10 seconds)
              </p>
            </div>
          </div>

          {/* Show individual pending messages */}
          <div className="mt-3 space-y-2">
            {pendingMessages.map((msg) => (
              <div
                key={msg.messageId}
                className="flex items-center gap-2 text-xs text-blue-800 bg-blue-100 rounded px-3 py-2"
              >
                <span className="font-mono truncate">{msg.messageId.slice(0, 10)}...</span>
                <ArrowRight className="h-3 w-3" />
                <span className="capitalize">{msg.destinationChain.replace('-', ' ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recently Completed Messages */}
      {completedMessages.length > 0 && !hasUnconfirmed && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-green-900">Cross-chain sync complete!</p>
              <p className="text-xs text-green-700 mt-1">
                All chains are now synchronized. Balances have been updated.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Failed Messages */}
      {failedMessages.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-900">
                {failedMessages.length} message{failedMessages.length > 1 ? 's' : ''} timed out
              </p>
              <p className="text-xs text-red-700 mt-1">
                The relayer may be offline. You can manually sync using the Cross-Chain Transfer
                page.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Compact status indicator for the app header/navbar
 *
 * Shows a small badge when cross-chain sync is in progress
 */
export function CompactSyncStatus({ userAddress }: { userAddress?: Address }) {
  const { hasUnconfirmed, pendingMessages } = useMessageTracking(userAddress);

  if (!hasUnconfirmed) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
      <Loader2 className="h-3 w-3 animate-spin" />
      <span>Syncing {pendingMessages.length}...</span>
    </div>
  );
}
