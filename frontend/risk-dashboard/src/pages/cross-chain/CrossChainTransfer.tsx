import { useState, useEffect } from 'react';
import { useAccount, useBalance, useSwitchChain } from 'wagmi';
import { parseEther, formatEther, type Address } from 'viem';
import { sepolia } from 'wagmi/chains';
import { polygonAmoy, CHAIN_INFO, CONTRACTS } from '@/config/chains';
import {
  useSendCrossChainMessage,
  useBridgeInfo,
  useEstimateCrossChainGas,
  encodeSettlementPayload,
  getBridgeChainName,
} from '@/hooks/contracts/useBridgeManager';
import { useVaultData } from '@/hooks/contracts/useVault';
import { PageTransition, FadeIn, StaggerChildren, StaggerItem } from '@/components/common/PageTransition';
import { AlertCircle, ArrowRight, Send, CheckCircle, Loader2, ExternalLink, Info } from 'lucide-react';

export default function CrossChainTransfer() {
  const { address, chainId, isConnected } = useAccount();
  const { switchChain } = useSwitchChain();

  // Form state
  const [amount, setAmount] = useState('');
  const [step, setStep] = useState<'form' | 'pending' | 'success' | 'error'>('form');
  const [showHelp, setShowHelp] = useState(true);

  // Determine source and destination chains based on current wallet connection
  // Support bidirectional transfers: Sepolia ⇄ Polygon Amoy
  const sourceChainId = chainId === polygonAmoy.id ? polygonAmoy.id : sepolia.id;
  const destChainId = sourceChainId === sepolia.id ? polygonAmoy.id : sepolia.id;

  // Get balance on source chain
  const { data: balance } = useBalance({
    address,
    chainId: sourceChainId,
  });

  // Get vault data to verify actual deposits
  const vaultData = useVaultData(address, sourceChainId);

  // Calculate actual vault balance on source chain
  const actualVaultBalance = sourceChainId === sepolia.id
    ? vaultData.sepoliaBalance
    : vaultData.amoyBalance;

  const actualVaultBalanceFormatted = actualVaultBalance
    ? formatEther(actualVaultBalance)
    : '0';

  // Get bridge info
  const bridgeInfo = useBridgeInfo(sourceChainId);

  // Auto-fill amount with actual vault balance when it loads
  useEffect(() => {
    if (actualVaultBalance && actualVaultBalance > 0n && !amount) {
      setAmount(actualVaultBalanceFormatted);
    }
  }, [actualVaultBalance, actualVaultBalanceFormatted, amount]);

  // Prepare payload for gas estimation (deposit to vault on destination chain)
  const payload = address && amount
    ? encodeSettlementPayload(
        address,
        parseEther(amount || '0'),
        getBridgeChainName(sourceChainId)
      )
    : undefined;

  // Estimate gas cost
  const { data: gasEstimateRaw } = useEstimateCrossChainGas(
    getBridgeChainName(destChainId),
    payload,
    sourceChainId
  );

  // Contract returns [estimatedGas: bigint, protocol: string]
  const gasEstimate = gasEstimateRaw
    ? { estimatedGas: (gasEstimateRaw as readonly [bigint, string])[0], protocol: (gasEstimateRaw as readonly [bigint, string])[1] }
    : undefined;

  // Send cross-chain message hook
  const {
    sendMessage,
    isLoading: isSending,
    isSuccess,
    isError,
    error,
    txHash,
    messageId,
  } = useSendCrossChainMessage(sourceChainId);

  // Update step based on transaction state
  useEffect(() => {
    if (isSending && step === 'form') {
      setStep('pending');
    } else if (isSuccess && step === 'pending') {
      setStep('success');
    } else if (isError && (step === 'form' || step === 'pending')) {
      setStep('error');
    }
  }, [isSending, isSuccess, isError, step]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isConnected || !address) {
      alert('Please connect your wallet');
      return;
    }

    if (chainId !== sourceChainId) {
      switchChain?.({ chainId: sourceChainId });
      return;
    }

    if (!amount) {
      alert('Please enter an amount');
      return;
    }

    // SECURITY CHECK: Validate amount doesn't exceed actual vault balance
    if (actualVaultBalance) {
      const enteredAmount = parseEther(amount);
      if (enteredAmount > actualVaultBalance) {
        alert(
          `⚠️ Security Error: You entered ${amount} but your actual vault balance is only ${actualVaultBalanceFormatted}.\n\n` +
          `You cannot sync more than you deposited! This would be fraudulent.`
        );
        return;
      }
    }

    // Warn if trying to sync with zero balance
    if (!actualVaultBalance || actualVaultBalance === 0n) {
      const confirmSync = confirm(
        `⚠️ Warning: Your vault balance on ${CHAIN_INFO[sourceChainId].name} is 0.\n\n` +
        `Are you sure you want to sync? This will have no effect since you haven't deposited anything.`
      );
      if (!confirmSync) return;
    }

    try {
      // Create payload for vault deposit on destination chain
      // This will sync your balance across chains via the vault
      const transferPayload = encodeSettlementPayload(
        address,
        parseEther(amount),
        getBridgeChainName(sourceChainId)
      );

      // Use a reasonable fixed amount for cross-chain gas fees
      // Axelar requires ~0.01-0.05 native tokens for cross-chain messages
      // The estimateGas from contract is just a placeholder and doesn't reflect actual Axelar costs
      const gasAmount = '0.02'; // 0.02 ETH/MATIC for cross-chain gas fees

      sendMessage({
        destinationChain: getBridgeChainName(destChainId),
        destinationAddress: CONTRACTS[destChainId].CrossChainVault,
        payload: transferPayload,
        gasToken: '0x0000000000000000000000000000000000000000' as Address, // Native token
        gasAmount,
      });
    } catch (err) {
      console.error('Transfer error:', err);
      setStep('error');
    }
  };

  const handleReset = () => {
    setStep('form');
    setAmount('');
  };

  // Wallet not connected
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
              <p className="text-gray-600">
                Please connect your wallet to use cross-chain transfers.
              </p>
            </div>
          </FadeIn>
        </div>
      </PageTransition>
    );
  }

  // Transaction pending
  if (step === 'pending') {
    return (
      <PageTransition>
        <div className="max-w-4xl mx-auto p-6">
          <FadeIn>
            <div className="bg-white border-2 border-blue-200 rounded-lg p-12 text-center shadow-lg">
              <div className="mx-auto w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mb-6">
                <Loader2 className="h-10 w-10 text-blue-600 animate-spin" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {txHash ? 'Confirming Transaction...' : 'Waiting for Confirmation...'}
              </h2>
              <p className="text-gray-600 mb-6">
                {txHash
                  ? 'Transaction submitted! Waiting for blockchain confirmation...'
                  : 'Please confirm the transaction in your wallet (MetaMask)'}
              </p>
              <div className="bg-gray-50 rounded-lg p-4 max-w-md mx-auto">
                <p className="text-sm text-gray-600 mb-2">Syncing Vault Balance:</p>
                <p className="text-lg font-semibold text-gray-900 mb-1">{amount} {sourceChainId === sepolia.id ? 'ETH' : 'MATIC'}</p>
                <p className="text-xs text-gray-500 mb-3">
                  (Message only - no tokens transferred)
                </p>
                <div className="flex items-center justify-center gap-3 text-sm text-gray-600">
                  <span>{CHAIN_INFO[sourceChainId].name}</span>
                  <ArrowRight className="h-4 w-4" />
                  <span>{CHAIN_INFO[destChainId].name}</span>
                </div>
              </div>

              {txHash && (
                <div className="mt-4">
                  <a
                    href={`${
                      sourceChainId === sepolia.id
                        ? 'https://sepolia.etherscan.io'
                        : 'https://amoy.polygonscan.com'
                    }/tx/${txHash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm"
                  >
                    <span>View on Block Explorer</span>
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>
              )}
            </div>
          </FadeIn>
        </div>
      </PageTransition>
    );
  }

  // Transaction success
  if (step === 'success') {
    return (
      <PageTransition>
        <div className="max-w-4xl mx-auto p-6">
          <FadeIn>
            <div className="bg-white border-2 border-green-200 rounded-lg p-12 text-center shadow-lg">
              <div className="mx-auto w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-6">
                <CheckCircle className="h-10 w-10 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Sync Message Sent!</h2>
              <p className="text-gray-600 mb-6">
                Your balance sync message has been submitted. The destination vault should update in ~3-5 minutes.
              </p>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 max-w-2xl mx-auto">
                <p className="text-sm text-blue-900">
                  ℹ️ <strong>What happens next:</strong> Axelar/CCIP relayers will deliver your message to {CHAIN_INFO[destChainId].name}. Once received, the vault will update your totalCollateral balance.
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-6 max-w-2xl mx-auto mb-6">
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Amount:</span>
                    <span className="font-semibold text-gray-900">{amount} ETH</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">From:</span>
                    <span className="font-semibold text-gray-900">{CHAIN_INFO[sourceChainId].name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">To:</span>
                    <span className="font-semibold text-gray-900">{CHAIN_INFO[destChainId].name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Your Address:</span>
                    <code className="text-xs text-gray-900">
                      {address?.slice(0, 6)}...{address?.slice(-4)}
                    </code>
                  </div>
                  {txHash && (
                    <div className="pt-3 border-t border-gray-200">
                      <a
                        href={`https://sepolia.etherscan.io/tx/${txHash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium"
                      >
                        <span>View on Etherscan</span>
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </div>
                  )}
                  {messageId && (
                    <div className="pt-2">
                      <p className="text-xs text-gray-500 mb-1">Cross-Chain Message ID:</p>
                      <code className="text-xs text-gray-900 break-all">{messageId}</code>
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 max-w-2xl mx-auto">
                <div className="flex items-start gap-3">
                  <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-900 text-left">
                    <p className="font-semibold mb-1">Transfer in Progress</p>
                    <p>
                      Cross-chain transfers typically take 3-5 minutes to complete. Funds will arrive at the recipient
                      address on {CHAIN_INFO[destChainId].name}.
                    </p>
                  </div>
                </div>
              </div>

              <button
                onClick={handleReset}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg"
              >
                Make Another Transfer
              </button>
            </div>
          </FadeIn>
        </div>
      </PageTransition>
    );
  }

  // Transaction error
  if (step === 'error') {
    return (
      <PageTransition>
        <div className="max-w-4xl mx-auto p-6">
          <FadeIn>
            <div className="bg-white border-2 border-red-200 rounded-lg p-12 text-center shadow-lg">
              <div className="mx-auto w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mb-6">
                <AlertCircle className="h-10 w-10 text-red-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Transfer Failed</h2>
              <p className="text-gray-600 mb-6">
                There was an error processing your cross-chain transfer.
              </p>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 max-w-2xl mx-auto">
                  <p className="text-sm text-red-900 text-left break-words">
                    {error.message || 'Unknown error occurred'}
                  </p>
                </div>
              )}

              <button
                onClick={handleReset}
                className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg"
              >
                Try Again
              </button>
            </div>
          </FadeIn>
        </div>
      </PageTransition>
    );
  }

  // Main form
  return (
    <PageTransition>
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <FadeIn delay={0.1}>
          <div className="mb-6">
            <div className="flex items-start gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">⚙️ Manual Balance Sync</h1>
              <div className="flex gap-2">
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded-full uppercase">
                  Troubleshooting Tool
                </span>
                <span className="px-3 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded-full uppercase">
                  Advanced
                </span>
              </div>
            </div>
            <p className="text-gray-600 mb-1">
              🔧 <strong>This is a troubleshooting tool</strong> - only use if automatic sync failed after deposit
            </p>
            <p className="text-sm text-gray-500 mb-3">
              ℹ️ Most users don't need this page. Automatic sync will be enabled in Sprint 08.
            </p>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-900">
                  <p className="font-semibold mb-2">⚠️ Important: This does NOT transfer actual funds!</p>
                  <ul className="space-y-1 list-disc list-inside text-blue-800">
                    <li>Sends a DATA MESSAGE (not tokens) through Axelar/CCIP</li>
                    <li>Tells destination vault: "User has X collateral on source chain"</li>
                    <li>Cost: ~0.02 native token (bridge fee) + small gas fee</li>
                    <li>You will NOT be charged the amount you enter</li>
                  </ul>
                  <p className="mt-2 font-medium">
                    💡 This is a temporary workaround. Automatic sync will be enabled in Sprint 08.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </FadeIn>

        {/* Wrong network warning */}
        {chainId && chainId !== sepolia.id && chainId !== polygonAmoy.id && (
          <FadeIn delay={0.2}>
            <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-yellow-900 mb-1">Wrong Network</p>
                  <p className="text-sm text-yellow-800 mb-3">
                    Please switch to Sepolia or Polygon Amoy network to send cross-chain transfers.
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => switchChain?.({ chainId: sepolia.id })}
                      className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 text-sm font-medium"
                    >
                      Switch to Sepolia
                    </button>
                    <button
                      onClick={() => switchChain?.({ chainId: polygonAmoy.id })}
                      className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 text-sm font-medium"
                    >
                      Switch to Amoy
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </FadeIn>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sync Form */}
          <div className="lg:col-span-2">
            <FadeIn delay={0.3}>
              <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Sync Message Details</h2>

                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Route Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Message Route</label>
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <div className="flex items-center justify-between">
                        <div className="text-center flex-1">
                          <div className="text-2xl mb-1">{CHAIN_INFO[sourceChainId].icon}</div>
                          <p className="text-sm font-semibold text-gray-900">
                            {CHAIN_INFO[sourceChainId].name}
                          </p>
                          <p className="text-xs text-gray-500">Source</p>
                        </div>
                        <div className="px-4">
                          <ArrowRight className="h-6 w-6 text-gray-400" />
                        </div>
                        <div className="text-center flex-1">
                          <div className="text-2xl mb-1">{CHAIN_INFO[destChainId].icon}</div>
                          <p className="text-sm font-semibold text-gray-900">{CHAIN_INFO[destChainId].name}</p>
                          <p className="text-xs text-gray-500">Destination</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Amount Input */}
                  <div>
                    <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-2">
                      Amount Already Deposited in Vault (to sync)
                    </label>

                    {/* Show vault balance prominently */}
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Your Vault Balance:</span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold text-gray-900">
                            {vaultData.isLoading ? (
                              <Loader2 className="h-4 w-4 animate-spin inline" />
                            ) : (
                              `${Number(actualVaultBalanceFormatted).toFixed(4)} ${sourceChainId === sepolia.id ? 'ETH' : 'MATIC'}`
                            )}
                          </span>
                          {actualVaultBalance && actualVaultBalance > 0n && (
                            <button
                              type="button"
                              onClick={() => setAmount(actualVaultBalanceFormatted)}
                              className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                            >
                              Use Max
                            </button>
                          )}
                        </div>
                      </div>
                      {(!actualVaultBalance || actualVaultBalance === 0n) && (
                        <p className="text-xs text-red-600 mt-2">
                          ⚠️ You haven't deposited anything yet! Go to Vault Dashboard to deposit first.
                        </p>
                      )}
                    </div>

                    <input
                      type="text"
                      id="amount"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="0.1"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      disabled={chainId !== sourceChainId}
                    />
                    {balance && (
                      <p className="text-sm text-gray-500 mt-2">
                        Wallet Balance: {Number(formatEther(balance.value)).toFixed(4)} {balance.symbol}
                      </p>
                    )}
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mt-2">
                      <p className="text-xs text-yellow-900">
                        ⚠️ <strong>You will NOT be charged this amount!</strong> This field tells the system how much collateral you already deposited. Only bridge fees (~0.02 tokens) will be charged.
                      </p>
                      <p className="text-xs text-red-600 mt-2 font-semibold">
                        🚨 SECURITY: You cannot sync more than your actual vault balance ({actualVaultBalanceFormatted}). The system will reject fraudulent amounts.
                      </p>
                    </div>
                  </div>

                  {/* Info about vault deposits */}
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <Info className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-purple-900">
                        <p className="font-semibold mb-2">What this does:</p>
                        <ol className="list-decimal list-inside space-y-1">
                          <li>Sends a message (not funds) through Axelar/CCIP</li>
                          <li>Message says: "User has [amount] collateral on {CHAIN_INFO[sourceChainId].name}"</li>
                          <li>Destination vault updates: totalCollateral += [amount]</li>
                          <li>Now you can borrow on {CHAIN_INFO[destChainId].name}!</li>
                        </ol>
                        <p className="mt-2 text-xs text-purple-700">
                          💡 This is needed because automatic sync is broken (bug in deposit function). Will be fixed in Sprint 08.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Gas Estimate */}
                  {gasEstimate && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-blue-900">
                          <p className="font-semibold mb-1">Estimated Cost</p>
                          <p>
                            Gas Fee: ~0.02 {sourceChainId === sepolia.id ? 'ETH' : 'MATIC'} (~$0.05)
                            <br />
                            Bridge Protocol: {gasEstimate.protocol}
                            <br />
                            <span className="text-xs text-gray-600">Transfer time: ~3-5 minutes</span>
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={
                      !amount ||
                      isSending ||
                      chainId !== sourceChainId ||
                      !isConnected ||
                      !actualVaultBalance ||
                      actualVaultBalance === 0n ||
                      (amount && actualVaultBalance && parseEther(amount || '0') > actualVaultBalance)
                    }
                    className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:bg-gray-300 disabled:cursor-not-allowed transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                  >
                    <Send className="h-5 w-5" />
                    🔄 Send Sync Message (Cost: ~0.02 {sourceChainId === sepolia.id ? 'ETH' : 'MATIC'})
                  </button>

                  {/* Validation feedback messages */}
                  {!actualVaultBalance || actualVaultBalance === 0n ? (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-3">
                      <p className="text-sm text-red-900 font-semibold">
                        ⚠️ Button disabled: Your vault balance is 0
                      </p>
                      <p className="text-xs text-red-700 mt-1">
                        You must deposit collateral in the Vault Dashboard first before syncing.
                      </p>
                    </div>
                  ) : amount && parseEther(amount || '0') > actualVaultBalance ? (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-3">
                      <p className="text-sm text-red-900 font-semibold">
                        ⚠️ Button disabled: Amount exceeds vault balance
                      </p>
                      <p className="text-xs text-red-700 mt-1">
                        You entered {amount} but your vault only has {actualVaultBalanceFormatted}. You cannot sync more than you deposited.
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-center text-gray-500 mt-2">
                      You will only pay bridge fees (~$50), not the amount entered above
                    </p>
                  )}
                </form>
              </div>
            </FadeIn>
          </div>

          {/* Info Sidebar */}
          <div className="lg:col-span-1">
            <StaggerChildren className="space-y-4">
              {/* Bridge Info */}
              <StaggerItem>
                <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Bridge Information</h3>
                  <div className="space-y-3 text-sm">
                    <div>
                      <p className="text-gray-600 mb-1">Supported Protocols:</p>
                      {bridgeInfo?.protocols && Array.isArray(bridgeInfo.protocols) && bridgeInfo.protocols.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {bridgeInfo.protocols.map((protocol: string) => (
                            <span
                              key={protocol}
                              className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium"
                            >
                              {protocol}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-500">Loading...</p>
                      )}
                    </div>
                    <div>
                      <p className="text-gray-600 mb-1">Transfer Time:</p>
                      <p className="text-gray-900 font-medium">~3-5 minutes</p>
                    </div>
                    <div>
                      <p className="text-gray-600 mb-1">Fee Structure:</p>
                      <p className="text-gray-900 font-medium">0.2% + gas costs</p>
                    </div>
                  </div>
                </div>
              </StaggerItem>

              {/* Security Features */}
              <StaggerItem>
                <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Security</h3>
                  <div className="space-y-2 text-sm text-gray-700">
                    <div className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                      <span>Audited bridge protocols</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                      <span>Multi-signature validation</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                      <span>Automatic protocol failover</span>
                    </div>
                  </div>
                </div>
              </StaggerItem>
            </StaggerChildren>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
