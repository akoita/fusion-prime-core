import { useAccount } from 'wagmi';
import { formatEther } from 'viem';
import { sepolia } from 'wagmi/chains';
import { polygonAmoy } from '@/config/chains';
import {
  useUserEscrows,
  useEscrowCount,
  useCreateEscrow,
} from '@/hooks/contracts/useEscrowFactory';
import {
  useEscrowDetails,
  getStatusText,
  getStatusColor,
} from '@/hooks/contracts/useEscrow';
import { useMultiChainVaultData } from '@/hooks/contracts/useCrossChainVault';
import { useBridgeInfo, useRegisteredProtocols } from '@/hooks/contracts/useBridgeManager';

/**
 * Demo component to test Web3 contract hooks
 * This component displays real blockchain data from:
 * - EscrowFactory contract (user's escrows)
 * - CrossChainVault contract (collateral, borrowed, credit line)
 * - BridgeManager contract (cross-chain bridge info)
 */
export default function Web3Demo() {
  const { address, isConnected, chain } = useAccount();

  // Fetch user's escrows
  const { data: userEscrows, isLoading: escrowsLoading } = useUserEscrows(address);

  // Fetch total escrow count
  const { data: escrowCount } = useEscrowCount();

  // Fetch multi-chain vault data
  const vaultData = useMultiChainVaultData(address);

  // Fetch bridge information
  const bridgeInfo = useBridgeInfo(chain?.id || sepolia.id);

  if (!isConnected) {
    return (
      <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-yellow-800">
          Please connect your wallet to view blockchain data
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Connection Info */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Connection Info</h2>
        <div className="space-y-2 text-sm">
          <p>
            <span className="font-medium">Address:</span>{' '}
            <code className="bg-gray-100 px-2 py-1 rounded">{address}</code>
          </p>
          <p>
            <span className="font-medium">Network:</span> {chain?.name} (Chain ID:{' '}
            {chain?.id})
          </p>
        </div>
      </div>

      {/* Escrow Factory Data */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Escrow Factory (Sepolia)
        </h2>

        <div className="space-y-4">
          <div>
            <p className="text-sm text-gray-600">Total Escrows Created</p>
            <p className="text-2xl font-bold text-gray-900">
              {escrowCount ? escrowCount.toString() : '0'}
            </p>
          </div>

          <div>
            <p className="text-sm text-gray-600 mb-2">Your Escrows</p>
            {escrowsLoading ? (
              <p className="text-sm text-gray-500">Loading...</p>
            ) : userEscrows && Array.isArray(userEscrows) && userEscrows.length > 0 ? (
              <div className="space-y-2">
                {userEscrows.map((escrowAddress: string, index: number) => (
                  <EscrowCard key={index} escrowAddress={escrowAddress as `0x${string}`} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No escrows found</p>
            )}
          </div>
        </div>
      </div>

      {/* Cross-Chain Vault Data */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Cross-Chain Vault Data
        </h2>

        {vaultData.isLoading ? (
          <p className="text-sm text-gray-500">Loading vault data...</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Sepolia Vault Data */}
            <div className="border border-blue-200 rounded-lg p-4 bg-blue-50">
              <h3 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                Sepolia Testnet
              </h3>
              <div className="space-y-2 text-sm">
                <div>
                  <p className="text-blue-700">Total Collateral</p>
                  <p className="text-lg font-bold text-blue-900">
                    {vaultData.sepolia.totalCollateral
                      ? `${formatEther(vaultData.sepolia.totalCollateral)} ETH`
                      : '0 ETH'}
                  </p>
                </div>
                <div>
                  <p className="text-blue-700">Total Borrowed</p>
                  <p className="text-lg font-bold text-blue-900">
                    {vaultData.sepolia.totalBorrowed
                      ? `${formatEther(vaultData.sepolia.totalBorrowed)} ETH`
                      : '0 ETH'}
                  </p>
                </div>
                <div>
                  <p className="text-blue-700">Credit Line Available</p>
                  <p className="text-lg font-bold text-blue-900">
                    {vaultData.sepolia.creditLine
                      ? `${formatEther(vaultData.sepolia.creditLine)} ETH`
                      : '0 ETH'}
                  </p>
                </div>
              </div>
            </div>

            {/* Polygon Amoy Vault Data */}
            <div className="border border-purple-200 rounded-lg p-4 bg-purple-50">
              <h3 className="font-semibold text-purple-900 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-purple-600 rounded-full"></span>
                Polygon Amoy Testnet
              </h3>
              <div className="space-y-2 text-sm">
                <div>
                  <p className="text-purple-700">Total Collateral</p>
                  <p className="text-lg font-bold text-purple-900">
                    {vaultData.polygonAmoy.totalCollateral
                      ? `${formatEther(vaultData.polygonAmoy.totalCollateral)} MATIC`
                      : '0 MATIC'}
                  </p>
                </div>
                <div>
                  <p className="text-purple-700">Total Borrowed</p>
                  <p className="text-lg font-bold text-purple-900">
                    {vaultData.polygonAmoy.totalBorrowed
                      ? `${formatEther(vaultData.polygonAmoy.totalBorrowed)} MATIC`
                      : '0 MATIC'}
                  </p>
                </div>
                <div>
                  <p className="text-purple-700">Credit Line Available</p>
                  <p className="text-lg font-bold text-purple-900">
                    {vaultData.polygonAmoy.creditLine
                      ? `${formatEther(vaultData.polygonAmoy.creditLine)} MATIC`
                      : '0 MATIC'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bridge Manager Data */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Cross-Chain Bridge Info
        </h2>

        {bridgeInfo.isLoading ? (
          <p className="text-sm text-gray-500">Loading bridge data...</p>
        ) : (
          <div className="space-y-4">
            {/* Registered Protocols */}
            <div>
              <p className="text-sm text-gray-600 mb-2">Registered Bridge Protocols</p>
              <div className="flex gap-2">
                {bridgeInfo.protocols && Array.isArray(bridgeInfo.protocols) ? (
                  bridgeInfo.protocols.map((protocol: string, index: number) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-indigo-100 text-indigo-800 text-sm font-medium rounded"
                    >
                      {protocol}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-gray-500">No protocols found</span>
                )}
              </div>
            </div>

            {/* Supported Chains */}
            <div>
              <p className="text-sm text-gray-600 mb-2">Supported Chains</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="border border-gray-200 rounded p-3">
                  <p className="text-xs text-gray-600">Ethereum Sepolia</p>
                  <p className="text-sm font-medium mt-1">
                    {bridgeInfo.supportedChains?.sepolia ? (
                      <span className="text-green-600">✓ Supported</span>
                    ) : (
                      <span className="text-red-600">✗ Not Supported</span>
                    )}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Protocol: {bridgeInfo.preferredProtocols?.sepolia || 'N/A'}
                  </p>
                </div>
                <div className="border border-gray-200 rounded p-3">
                  <p className="text-xs text-gray-600">Polygon Amoy</p>
                  <p className="text-sm font-medium mt-1">
                    {bridgeInfo.supportedChains?.amoy ? (
                      <span className="text-green-600">✓ Supported</span>
                    ) : (
                      <span className="text-red-600">✗ Not Supported</span>
                    )}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Protocol: {bridgeInfo.preferredProtocols?.amoy || 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Component to display individual escrow details
 */
function EscrowCard({ escrowAddress }: { escrowAddress: `0x${string}` }) {
  const { data: details, isLoading } = useEscrowDetails(escrowAddress);

  if (isLoading) {
    return (
      <div className="border border-gray-200 rounded p-3 bg-gray-50">
        <p className="text-xs text-gray-500">Loading escrow details...</p>
      </div>
    );
  }

  const statusColor = getStatusColor(details?.status as number);
  const statusText = getStatusText(details?.status as number);

  return (
    <div className="border border-gray-200 rounded p-3 bg-gray-50 hover:bg-gray-100 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <code className="text-xs text-gray-600 break-all">{escrowAddress}</code>
        <span
          className={`text-xs px-2 py-1 rounded font-medium ${
            statusColor === 'blue'
              ? 'bg-blue-100 text-blue-800'
              : statusColor === 'green'
              ? 'bg-green-100 text-green-800'
              : statusColor === 'yellow'
              ? 'bg-yellow-100 text-yellow-800'
              : statusColor === 'red'
              ? 'bg-red-100 text-red-800'
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {statusText}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <p className="text-gray-600">Amount</p>
          <p className="font-medium text-gray-900">
            {details?.amount ? formatEther(details.amount) : '0'} ETH
          </p>
        </div>
        <div>
          <p className="text-gray-600">Approved</p>
          <p className="font-medium text-gray-900">
            {details?.isApproved ? 'Yes' : 'No'}
          </p>
        </div>
      </div>
    </div>
  );
}
