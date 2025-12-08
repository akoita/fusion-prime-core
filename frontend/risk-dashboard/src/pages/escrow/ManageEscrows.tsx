import { useState } from 'react';
import { useAccount } from 'wagmi';
import { useNavigate } from 'react-router-dom';
import { useEscrowCount } from '@/hooks/contracts/useEscrowFactory';
import { useEscrowDetails, getStatusText, getStatusColor } from '@/hooks/contracts/useEscrow';
import { useEscrowsByRole } from '@/hooks/contracts/useEscrowsByRole';
import { formatEther } from 'viem';
import { AlertCircle, Plus, ExternalLink, Loader2, User, Users, Shield } from 'lucide-react';
import { PageTransition, FadeIn, StaggerChildren, StaggerItem } from '@/components/common/PageTransition';
import { CardSkeleton } from '@/components/common/SkeletonLoader';

function EscrowCard({ escrowAddress }: { escrowAddress: `0x${string}` }) {
  const navigate = useNavigate();
  const details = useEscrowDetails(escrowAddress);

  if (details.isLoading) {
    return <CardSkeleton />;
  }

  const statusColor = getStatusColor(details.status as number);
  const statusText = getStatusText(details.status as number);

  // Check if escrow has data
  const hasData = details.payer && details.payee && details.amount;

  if (!hasData) {
    return (
      <div className="bg-gray-50 border border-gray-300 rounded-lg p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 mb-2">Empty Escrow Contract</h3>
            <code className="text-xs text-gray-600 break-all">{escrowAddress}</code>
          </div>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
          <p className="text-sm text-yellow-800">
            ⚠️ This escrow contract has no data. It may have failed during creation.
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={`https://sepolia.etherscan.io/address/${escrowAddress}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm font-medium flex items-center gap-1"
          >
            <ExternalLink className="h-4 w-4" />
            View on Etherscan
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-md hover:shadow-xl transition-all duration-300 hover:scale-[1.02] hover:border-blue-300">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="font-semibold text-gray-900">Escrow</h3>
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
          <code className="text-xs text-gray-600 break-all">{escrowAddress}</code>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-600 mb-1">Amount</p>
          <p className="text-lg font-bold text-gray-900">
            {details.amount ? formatEther(details.amount) : '0'} ETH
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-1">Approved</p>
          <p className="text-lg font-semibold text-gray-900">
            {details.isApproved ? (
              <span className="text-green-600">Yes ✓</span>
            ) : (
              <span className="text-gray-400">No</span>
            )}
          </p>
        </div>
      </div>

      <div className="space-y-2 text-xs mb-4">
        <div className="flex justify-between">
          <span className="text-gray-600">Payer:</span>
          <code className="text-gray-900">
            {details.payer ? `${(details.payer as string).slice(0, 6)}...${(details.payer as string).slice(-4)}` : 'N/A'}
          </code>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Payee:</span>
          <code className="text-gray-900">
            {details.payee ? `${(details.payee as string).slice(0, 6)}...${(details.payee as string).slice(-4)}` : 'N/A'}
          </code>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Arbiter:</span>
          <code className="text-gray-900">
            {details.arbiter ? `${(details.arbiter as string).slice(0, 6)}...${(details.arbiter as string).slice(-4)}` : 'N/A'}
          </code>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => navigate(`/escrow/${escrowAddress}`)}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
        >
          View Details
        </button>
        <a
          href={`https://sepolia.etherscan.io/address/${escrowAddress}`}
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm font-medium flex items-center gap-1"
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>
    </div>
  );
}

export default function ManageEscrows() {
  const navigate = useNavigate();
  const { address, isConnected } = useAccount();
  const { data: escrowCount } = useEscrowCount();
  const escrowsByRole = useEscrowsByRole(address);
  const [activeTab, setActiveTab] = useState<'payer' | 'payee' | 'arbiter'>('payer');

  if (!isConnected) {
    return (
      <PageTransition>
        <div className="max-w-6xl mx-auto p-6">
          <FadeIn>
            <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-8 text-center shadow-lg">
              <div className="mx-auto w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
                <AlertCircle className="h-8 w-8 text-yellow-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Wallet Not Connected</h2>
              <p className="text-gray-600">
                Please connect your wallet to view your escrows.
              </p>
            </div>
          </FadeIn>
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <FadeIn delay={0.1}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">My Escrows</h1>
              <p className="text-gray-600">
                View and manage escrows by your role
              </p>
            </div>
            <button
              onClick={() => navigate('/escrow/create')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium flex items-center gap-2 transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg"
            >
              <Plus className="h-5 w-5" />
              Create Escrow
            </button>
          </div>
        </FadeIn>

        {/* Role Tabs */}
        <FadeIn delay={0.2}>
          <div className="bg-white border border-gray-200 rounded-lg mb-6 shadow-md">
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setActiveTab('payer')}
            className={`flex-1 px-6 py-4 text-sm font-medium flex items-center justify-center gap-2 transition-all duration-200 ${
              activeTab === 'payer'
                ? 'border-b-2 border-blue-600 text-blue-600 bg-blue-50'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            }`}
          >
            <User className="h-5 w-5" />
            As Payer ({escrowsByRole.asPayer.length})
          </button>
          <button
            onClick={() => setActiveTab('payee')}
            className={`flex-1 px-6 py-4 text-sm font-medium flex items-center justify-center gap-2 transition-all duration-200 ${
              activeTab === 'payee'
                ? 'border-b-2 border-green-600 text-green-600 bg-green-50'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            }`}
          >
            <Users className="h-5 w-5" />
            As Payee ({escrowsByRole.asPayee.length})
          </button>
          <button
            onClick={() => setActiveTab('arbiter')}
            className={`flex-1 px-6 py-4 text-sm font-medium flex items-center justify-center gap-2 transition-all duration-200 ${
              activeTab === 'arbiter'
                ? 'border-b-2 border-purple-600 text-purple-600 bg-purple-50'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            }`}
          >
            <Shield className="h-5 w-5" />
            As Arbiter ({escrowsByRole.asArbiter.length})
          </button>
        </div>

        <div className="p-4 bg-gray-50">
          <p className="text-sm text-gray-700">
            {activeTab === 'payer' && (
              <>Escrows you created and funded as the payer</>
            )}
            {activeTab === 'payee' && (
              <>Escrows where you will receive funds as the payee</>
            )}
            {activeTab === 'arbiter' && (
              <>Escrows where you can mediate disputes as the arbiter</>
            )}
          </p>
        </div>
          </div>
        </FadeIn>

        {/* Stats */}
        <StaggerChildren className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StaggerItem>
            <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-md hover:shadow-lg transition-all duration-300">
              <p className="text-sm text-gray-600 mb-1">As Payer</p>
              <p className="text-2xl font-bold text-blue-600">
                {escrowsByRole.asPayer.length}
              </p>
            </div>
          </StaggerItem>
          <StaggerItem>
            <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-md hover:shadow-lg transition-all duration-300">
              <p className="text-sm text-gray-600 mb-1">As Payee</p>
              <p className="text-2xl font-bold text-green-600">
                {escrowsByRole.asPayee.length}
              </p>
            </div>
          </StaggerItem>
          <StaggerItem>
            <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-md hover:shadow-lg transition-all duration-300">
              <p className="text-sm text-gray-600 mb-1">As Arbiter</p>
              <p className="text-2xl font-bold text-purple-600">
                {escrowsByRole.asArbiter.length}
              </p>
            </div>
          </StaggerItem>
          <StaggerItem>
            <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-md hover:shadow-lg transition-all duration-300">
              <p className="text-sm text-gray-600 mb-1">Total (All Roles)</p>
              <p className="text-2xl font-bold text-gray-900">
                {new Set([...escrowsByRole.asPayer, ...escrowsByRole.asPayee, ...escrowsByRole.asArbiter]).size}
              </p>
            </div>
          </StaggerItem>
        </StaggerChildren>

        {/* Escrow List */}
        <FadeIn delay={0.4}>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          {activeTab === 'payer' && 'Escrows You Created'}
          {activeTab === 'payee' && 'Escrows Where You Receive Funds'}
          {activeTab === 'arbiter' && 'Escrows You Arbitrate'}
        </h2>

        {escrowsByRole.isLoading ? (
          <div className="bg-white border border-gray-200 rounded-lg p-12 text-center shadow-md">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-gray-600 font-medium">Scanning blockchain for your escrows...</p>
            <p className="text-gray-500 text-sm mt-2">This may take a few moments</p>
          </div>
        ) : (() => {
            const currentEscrows =
              activeTab === 'payer' ? escrowsByRole.asPayer :
              activeTab === 'payee' ? escrowsByRole.asPayee :
              escrowsByRole.asArbiter;

            return currentEscrows.length > 0 ? (
              <StaggerChildren className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {currentEscrows.map((escrowAddress, index) => (
                  <StaggerItem key={index}>
                    <EscrowCard escrowAddress={escrowAddress} />
                  </StaggerItem>
                ))}
              </StaggerChildren>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg p-12 text-center shadow-md">
                <div className="max-w-md mx-auto">
                  <div className="bg-gray-100 rounded-full h-16 w-16 flex items-center justify-center mx-auto mb-4">
                    {activeTab === 'payer' && <User className="h-8 w-8 text-gray-400" />}
                    {activeTab === 'payee' && <Users className="h-8 w-8 text-gray-400" />}
                    {activeTab === 'arbiter' && <Shield className="h-8 w-8 text-gray-400" />}
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">No Escrows Found</h3>
                  <p className="text-gray-600 mb-6">
                    {activeTab === 'payer' && "You haven't created any escrows yet. Create your first escrow to get started."}
                    {activeTab === 'payee' && "You are not a payee in any escrows yet."}
                    {activeTab === 'arbiter' && "You are not an arbiter in any escrows yet."}
                  </p>
                  {activeTab === 'payer' && (
                    <button
                      onClick={() => navigate('/escrow/create')}
                      className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium inline-flex items-center gap-2 transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg"
                    >
                      <Plus className="h-5 w-5" />
                      Create Your First Escrow
                    </button>
                  )}
                </div>
              </div>
            );
          })()
        }
        </FadeIn>
      </div>
    </PageTransition>
  );
}
