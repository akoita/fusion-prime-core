import { useParams, useNavigate } from 'react-router-dom';
import { useAccount } from 'wagmi';
import { formatEther } from 'viem';
import {
  useEscrowDetails,
  useApproveEscrow,
  useReleaseEscrow,
  useRefundEscrow,
  useIsTimelockExpired,
  getStatusText,
  getStatusColor,
} from '@/hooks/contracts/useEscrow';
import { AlertCircle, ArrowLeft, Loader2, CheckCircle2, XCircle, Clock, ExternalLink, User, Users, Shield } from 'lucide-react';
import { PageTransition, FadeIn, ScaleIn } from '@/components/common/PageTransition';

export default function EscrowDetails() {
  const { escrowAddress } = useParams<{ escrowAddress: string }>();
  const navigate = useNavigate();
  const { address, isConnected } = useAccount();

  const details = useEscrowDetails(escrowAddress as `0x${string}`);
  const { data: isTimelockExpired } = useIsTimelockExpired(escrowAddress as `0x${string}`);
  const { approve, isLoading: isApproving, isSuccess: isApproved } = useApproveEscrow(escrowAddress as `0x${string}`);
  const { release, isLoading: isReleasing, isSuccess: isReleased } = useReleaseEscrow(escrowAddress as `0x${string}`);
  const { refund, isLoading: isRefunding, isSuccess: isRefunded } = useRefundEscrow(escrowAddress as `0x${string}`);

  if (!isConnected) {
    return (
      <PageTransition>
        <div className="max-w-4xl mx-auto p-6">
          <FadeIn>
            <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-8 text-center shadow-lg">
              <div className="mx-auto w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
                <AlertCircle className="h-8 w-8 text-yellow-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Wallet Not Connected</h2>
              <p className="text-gray-600">Please connect your wallet to view escrow details.</p>
            </div>
          </FadeIn>
        </div>
      </PageTransition>
    );
  }

  if (details.isLoading) {
    return (
      <PageTransition>
        <div className="max-w-4xl mx-auto p-6">
          <div className="bg-white border border-gray-200 rounded-lg p-12 text-center shadow-md">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-gray-600 font-medium">Loading escrow details...</p>
            <p className="text-gray-500 text-sm mt-2">Please wait</p>
          </div>
        </div>
      </PageTransition>
    );
  }

  if (details.isError || !details.payer || !details.payee || !details.amount) {
    console.log('Escrow Details Debug:', {
      isError: details.isError,
      payer: details.payer,
      payee: details.payee,
      amount: details.amount,
      arbiter: details.arbiter,
      timelock: details.timelock,
    });

    return (
      <PageTransition>
        <div className="max-w-4xl mx-auto p-6">
          <FadeIn>
            <div className="bg-red-50 border-2 border-red-200 rounded-lg p-8 text-center shadow-lg">
              <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                <XCircle className="h-8 w-8 text-red-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Escrow Not Found</h2>
          <p className="text-gray-600 mb-4">
            Could not load details for this escrow contract.
          </p>
          <div className="bg-white rounded p-4 mb-4 text-left">
            <p className="text-xs text-gray-600 mb-2">Debug Information:</p>
            <code className="text-xs text-gray-900 break-all block mb-1">Address: {escrowAddress}</code>
            <code className="text-xs text-gray-700 block">Payer: {details.payer ? details.payer.toString() : 'Not loaded'}</code>
            <code className="text-xs text-gray-700 block">Payee: {details.payee ? details.payee.toString() : 'Not loaded'}</code>
            <code className="text-xs text-gray-700 block">Amount: {details.amount ? details.amount.toString() : 'Not loaded'}</code>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            {details.isError
              ? 'Error reading contract. It may not exist or have the wrong ABI.'
              : 'Contract exists but has no data. It may not be initialized yet.'}
          </p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={() => navigate('/escrow/manage')}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg"
                >
                  Back to My Escrows
                </button>
                <a
                  href={`https://sepolia.etherscan.io/address/${escrowAddress}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-all duration-200 hover:scale-105"
                >
                  View on Etherscan
                </a>
              </div>
            </div>
          </FadeIn>
        </div>
      </PageTransition>
    );
  }

  const statusColor = getStatusColor(details.status as number);
  const statusText = getStatusText(details.status as number);

  // Determine user role
  const isPayer = address?.toLowerCase() === details.payer?.toLowerCase();
  const isPayee = address?.toLowerCase() === details.payee?.toLowerCase();
  const isArbiter = address?.toLowerCase() === details.arbiter?.toLowerCase();

  const userRole = isPayer ? 'Payer' : isPayee ? 'Payee' : isArbiter ? 'Arbiter' : 'Observer';

  // Debug logging
  console.log('EscrowDetails Debug:', {
    connectedAddress: address,
    connectedAddressLower: address?.toLowerCase(),
    isPayer,
    isPayee,
    isArbiter,
    isApproved: details.isApproved,
    isTimelockExpired,
    statusText,
    payer: details.payer,
    payerLower: details.payer?.toLowerCase(),
    payee: details.payee,
    payeeLower: details.payee?.toLowerCase(),
    arbiter: details.arbiter,
    approvalsCount: details.approvalsCount,
    approvalsRequired: details.approvalsRequired,
  });

  // Success messages
  if (isApproved || isReleased || isRefunded) {
    return (
      <PageTransition>
        <div className="max-w-4xl mx-auto p-6">
          <ScaleIn>
            <div className="bg-green-50 border-2 border-green-200 rounded-lg p-8 text-center shadow-lg">
              <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <CheckCircle2 className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Transaction Successful!</h2>
              <p className="text-gray-600 mb-4">
                {isApproved && 'Escrow has been approved.'}
                {isReleased && 'Funds have been released to the payee.'}
                {isRefunded && 'Funds have been refunded to the payer.'}
              </p>
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg"
              >
                Refresh Page
              </button>
            </div>
          </ScaleIn>
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <FadeIn delay={0.1}>
          <div className="mb-6">
            <button
              onClick={() => navigate('/escrow/manage')}
              className="mb-4 flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors duration-200"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to My Escrows
            </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Escrow Details</h1>
            <code className="text-sm text-gray-600 break-all">{escrowAddress}</code>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-sm font-semibold ${
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
          </div>
        </FadeIn>

        {/* Participants */}
        <FadeIn delay={0.2}>
          <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 shadow-md hover:shadow-lg transition-all duration-300">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Participants</h2>
        <div className="space-y-4">
          {/* Payer (Creator) */}
          <div className={`flex items-start gap-3 p-4 rounded-lg border-2 ${isPayer ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
            <div className="bg-blue-100 rounded-full p-2 mt-1">
              <User className="h-5 w-5 text-blue-600" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <p className="font-semibold text-gray-900">Payer (Creator)</p>
                {isPayer && (
                  <span className="px-2 py-0.5 bg-blue-600 text-white text-xs font-semibold rounded-full">
                    YOU
                  </span>
                )}
              </div>
              <code className="text-xs text-gray-600 break-all">{details.payer as string}</code>
              <p className="text-sm text-gray-600 mt-1">
                Created escrow and deposited {formatEther(details.amount)} ETH
              </p>
            </div>
          </div>

          {/* Payee (Recipient) */}
          <div className={`flex items-start gap-3 p-4 rounded-lg border-2 ${isPayee ? 'border-green-500 bg-green-50' : 'border-gray-200'}`}>
            <div className="bg-green-100 rounded-full p-2 mt-1">
              <Users className="h-5 w-5 text-green-600" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <p className="font-semibold text-gray-900">Payee (Recipient)</p>
                {isPayee && (
                  <span className="px-2 py-0.5 bg-green-600 text-white text-xs font-semibold rounded-full">
                    YOU
                  </span>
                )}
              </div>
              <code className="text-xs text-gray-600 break-all">{details.payee as string}</code>
              <p className="text-sm text-gray-600 mt-1">
                Will receive funds when escrow is released
              </p>
            </div>
          </div>

          {/* Arbiter */}
          <div className={`flex items-start gap-3 p-4 rounded-lg border-2 ${isArbiter ? 'border-purple-500 bg-purple-50' : 'border-gray-200'}`}>
            <div className="bg-purple-100 rounded-full p-2 mt-1">
              <Shield className="h-5 w-5 text-purple-600" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <p className="font-semibold text-gray-900">Arbiter (Mediator)</p>
                {isArbiter && (
                  <span className="px-2 py-0.5 bg-purple-600 text-white text-xs font-semibold rounded-full">
                    YOU
                  </span>
                )}
              </div>
              <code className="text-xs text-gray-600 break-all">{details.arbiter as string}</code>
              <p className="text-sm text-gray-600 mt-1">
                Can release funds to payee or refund to payer
              </p>
            </div>
          </div>
        </div>
          </div>
        </FadeIn>

        {/* Timelock Status */}
        <FadeIn delay={0.3}>
          <div className={`border-2 rounded-lg p-6 mb-6 shadow-md hover:shadow-lg transition-all duration-300 ${isTimelockExpired ? 'border-green-500 bg-green-50' : 'border-yellow-500 bg-yellow-50'}`}>
        <div className="flex items-center gap-3 mb-3">
          <Clock className={`h-6 w-6 ${isTimelockExpired ? 'text-green-600' : 'text-yellow-600'}`} />
          <h2 className="text-xl font-semibold text-gray-900">Timelock Status</h2>
        </div>
        <div className="space-y-2">
          <p className={`text-lg font-semibold ${isTimelockExpired ? 'text-green-900' : 'text-yellow-900'}`}>
            {isTimelockExpired ? '✅ Timelock Expired - Funds Can Be Released' : '⏳ Timelock Active - Waiting Period'}
          </p>
          <p className="text-sm text-gray-700">
            {isTimelockExpired
              ? 'The waiting period has ended. The arbiter or payee (if approved) can now release funds.'
              : 'Funds are locked until the timelock expires. This protects both parties during the transaction.'}
          </p>
          <div className="pt-2">
            <p className="text-xs text-gray-600">
              Release Time: {details.timelock ? new Date(Number(details.timelock) * 1000).toLocaleString() : 'N/A'}
              </p>
            </div>
          </div>
          </div>
          </FadeIn>

        {/* Main Details */}
        <FadeIn delay={0.4}>
          <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 shadow-md hover:shadow-lg transition-all duration-300">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Escrow Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-gray-600 mb-1">Amount</p>
            <p className="text-3xl font-bold text-gray-900">
              {formatEther(details.amount)} ETH
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">Approval Status</p>
            <p className="text-2xl font-semibold">
              {details.isApproved ? (
                <span className="text-green-600">✓ Approved ({details.approvalsCount}/{details.approvalsRequired})</span>
              ) : (
                <span className="text-yellow-600">⏳ Pending ({details.approvalsCount || 0}/{details.approvalsRequired})</span>
              )}
            </p>
            {details.approvalsRequired && details.approvalsRequired > 1 && (
              <p className="text-xs text-gray-600 mt-1">
                Multi-signature: Requires {details.approvalsRequired} approvals from participants
              </p>
            )}
          </div>
        </div>
          </div>
        </FadeIn>

      {/* Actions */}
        <FadeIn delay={0.5}>
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Available Actions</h2>

        {statusText === 'Released' || statusText === 'Refunded' ? (
          <div className="text-center py-8 text-gray-600">
            <CheckCircle2 className="h-12 w-12 text-green-600 mx-auto mb-3" />
            <p className="font-semibold text-lg">Escrow Completed</p>
            <p className="text-sm mt-2">This escrow has been finalized. No further actions available.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Payee: Approve */}
            {isPayee && !details.isApproved && (
              <div className="border-2 border-green-500 rounded-lg p-4 bg-green-50">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <p className="font-semibold text-gray-900">
                    {details.approvalsRequired === 1
                      ? 'Approve to Enable Fund Release'
                      : `Add Your Approval (${details.approvalsCount || 0}/${details.approvalsRequired} received)`}
                  </p>
                </div>
                <p className="text-sm text-gray-700 mb-3">
                  {details.approvalsRequired === 1
                    ? "As the payee, add your approval to enable fund release. Once approved and the timelock expires, you can claim the funds."
                    : `This escrow requires ${details.approvalsRequired} approvals. Add your approval as the payee. Funds will be released when all approvals are collected and the timelock expires.`}
                </p>
                <button
                  onClick={() => approve()}
                  disabled={isApproving}
                  className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  {isApproving ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Approving...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-5 w-5" />
                      Add My Approval
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Payee: Claim Funds (after timelock expires and approved) */}
            {isPayee && details.isApproved && isTimelockExpired && (
              <div className="border-2 border-blue-500 rounded-lg p-4 bg-blue-50">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-600" />
                  <p className="font-semibold text-gray-900">Step 2: Claim Your Funds</p>
                </div>
                <p className="text-sm text-gray-700 mb-3">
                  The timelock has expired and you've approved the escrow. You can now claim the {formatEther(details.amount)} ETH!
                </p>
                <button
                  onClick={() => release()}
                  disabled={isReleasing}
                  className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  {isReleasing ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Claiming Funds...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-5 w-5" />
                      Claim Funds ({formatEther(details.amount)} ETH)
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Payee: Waiting */}
            {isPayee && details.isApproved && !isTimelockExpired && (
              <div className="border-2 border-yellow-500 rounded-lg p-4 bg-yellow-50">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="h-5 w-5 text-yellow-600" />
                  <p className="font-semibold text-gray-900">Waiting for Timelock Expiration</p>
                </div>
                <p className="text-sm text-gray-700">
                  All required approvals received ({details.approvalsCount}/{details.approvalsRequired}).
                  {details.arbiter && details.arbiter !== '0x0000000000000000000000000000000000000000'
                    ? ' The arbiter can release funds now, or you can claim them after the timelock expires.'
                    : ' You can claim the funds once the timelock expires.'}
                </p>
                <p className="text-xs text-gray-600 mt-2">
                  Release available at: {details.timelock ? new Date(Number(details.timelock) * 1000).toLocaleString() : 'N/A'}
                </p>
              </div>
            )}

            {/* Payer: Approve (for multi-sig) */}
            {isPayer && !details.isApproved && details.approvalsRequired && details.approvalsRequired > 1 && (
              <div className="border-2 border-blue-500 rounded-lg p-4 bg-blue-50">
                <div className="flex items-center gap-2 mb-2">
                  <User className="h-5 w-5 text-blue-600" />
                  <p className="font-semibold text-gray-900">
                    Add Your Approval ({details.approvalsCount || 0}/{details.approvalsRequired} received)
                  </p>
                </div>
                <p className="text-sm text-gray-700 mb-3">
                  This escrow requires {details.approvalsRequired} approvals. As the payer, add your approval to help release the funds.
                </p>
                <button
                  onClick={() => approve()}
                  disabled={isApproving}
                  className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  {isApproving ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Approving...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-5 w-5" />
                      Add My Approval
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Arbiter: Approve (for multi-sig) */}
            {isArbiter && !details.isApproved && (
              <div className="border-2 border-purple-500 rounded-lg p-4 bg-purple-50">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="h-5 w-5 text-purple-600" />
                  <p className="font-semibold text-gray-900">
                    Add Arbiter Approval ({details.approvalsCount || 0}/{details.approvalsRequired} received)
                  </p>
                </div>
                <p className="text-sm text-gray-700 mb-3">
                  As the arbiter, add your approval to authorize fund release. {details.approvalsRequired} total approvals required.
                </p>
                <button
                  onClick={() => approve()}
                  disabled={isApproving}
                  className="w-full px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  {isApproving ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Approving...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-5 w-5" />
                      Add My Approval
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Arbiter: Release to Payee */}
            {isArbiter && details.isApproved && (
              <div className="border-2 border-purple-500 rounded-lg p-4 bg-purple-50">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="h-5 w-5 text-purple-600" />
                  <p className="font-semibold text-gray-900">Arbiter Action: Release Funds</p>
                </div>
                <p className="text-sm text-gray-700 mb-3">
                  All required approvals received ({details.approvalsCount}/{details.approvalsRequired}). As the arbiter, you can release the {formatEther(details.amount)} ETH to the payee.
                </p>
                <button
                  onClick={() => release()}
                  disabled={isReleasing}
                  className="w-full px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  {isReleasing ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Releasing...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-5 w-5" />
                      Release to Payee
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Arbiter or Payer: Refund */}
            {(isArbiter || isPayer) && (
              <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                <div className="flex items-center gap-2 mb-2">
                  <XCircle className="h-5 w-5 text-gray-600" />
                  <p className="font-semibold text-gray-900">Emergency: Refund to Payer</p>
                </div>
                <p className="text-sm text-gray-700 mb-3">
                  {isArbiter
                    ? 'As the arbiter, you can refund the escrow to the payer if there\'s a dispute.'
                    : 'As the payer, you can request a refund if the timelock has expired by 30+ days.'}
                </p>
                <button
                  onClick={() => refund()}
                  disabled={isRefunding}
                  className="w-full px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  {isRefunding ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Refunding...
                    </>
                  ) : (
                    <>
                      <XCircle className="h-5 w-5" />
                      Refund to Payer
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Observer: No actions */}
            {!isPayee && !isArbiter && !isPayer && (
              <div className="text-center py-8 text-gray-600 border-2 border-dashed border-gray-300 rounded-lg">
                <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                <p className="font-semibold text-lg">Observer Mode</p>
                <p className="text-sm mt-2">You are not a participant in this escrow.</p>
                <p className="text-xs mt-1 text-gray-500">Only the payer, payee, or arbiter can perform actions.</p>
              </div>
              )}
            </div>
          )}
      </div>
        </FadeIn>

        {/* View on Explorer */}
        <FadeIn delay={0.6}>
          <div className="text-center">
        <a
          href={`https://sepolia.etherscan.io/address/${escrowAddress}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium"
        >
              <ExternalLink className="h-4 w-4" />
              View on Sepolia Etherscan
            </a>
          </div>
        </FadeIn>
      </div>
    </PageTransition>
  );
}
