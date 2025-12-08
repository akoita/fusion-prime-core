import { useState } from 'react';
import { useAccount, useChainId } from 'wagmi';
import { isAddress, parseEther } from 'viem';
import { sepolia } from 'wagmi/chains';
import { polygonAmoy } from '@/config/chains';
import {
  useSendCrossChainMessage,
  useBridgeInfo,
  useEstimateCrossChainGas,
  encodeSettlementPayload,
  getBridgeChainName,
} from '@/hooks/contracts/useBridgeManager';
import { AlertCircle, Loader2, CheckCircle2, ArrowRight, Zap } from 'lucide-react';

export default function CrossChainSettle() {
  const { address, isConnected } = useAccount();
  const chainId = useChainId();

  const bridgeInfo = useBridgeInfo(chainId);
  const { sendMessage, isLoading, isSuccess, txHash, messageId } = useSendCrossChainMessage(chainId);

  const [formData, setFormData] = useState({
    destinationChain: '',
    recipient: '',
    amount: '',
    protocol: '',
    gasAmount: '0.1', // Default gas amount
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Get destination chain name for the contract
  const destinationChainName =
    formData.destinationChain === 'sepolia'
      ? 'ethereum-sepolia'
      : formData.destinationChain === 'amoy'
      ? 'polygon-amoy'
      : '';

  // Prepare payload for gas estimation
  const payload =
    formData.recipient && formData.amount && isAddress(formData.recipient)
      ? encodeSettlementPayload(formData.recipient as `0x${string}`, parseEther(formData.amount))
      : undefined;

  const gasEstimate = useEstimateCrossChainGas(destinationChainName, payload, chainId);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.destinationChain) {
      newErrors.destinationChain = 'Please select a destination chain';
    }

    if (!formData.recipient) {
      newErrors.recipient = 'Recipient address is required';
    } else if (!isAddress(formData.recipient)) {
      newErrors.recipient = 'Invalid Ethereum address';
    }

    if (!formData.amount) {
      newErrors.amount = 'Amount is required';
    } else if (parseFloat(formData.amount) <= 0) {
      newErrors.amount = 'Amount must be greater than 0';
    }

    if (!formData.protocol && bridgeInfo.protocols && bridgeInfo.protocols.length > 0) {
      // Auto-select first available protocol if not selected
      setFormData((prev) => ({ ...prev, protocol: bridgeInfo.protocols?.[0] || '' }));
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    if (!address || !formData.recipient || !formData.amount) {
      return;
    }

    const payload = encodeSettlementPayload(
      formData.recipient as `0x${string}`,
      parseEther(formData.amount)
    );

    sendMessage({
      destinationChain: destinationChainName,
      destinationAddress: formData.recipient,
      payload,
      gasToken: '0x0000000000000000000000000000000000000000' as `0x${string}`, // Native token
      gasAmount: formData.gasAmount,
    });
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error for this field
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  if (!isConnected) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-yellow-600 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Wallet Not Connected</h2>
          <p className="text-gray-600">
            Please connect your wallet to initiate cross-chain settlements.
          </p>
        </div>
      </div>
    );
  }

  if (isSuccess && txHash) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <CheckCircle2 className="mx-auto h-12 w-12 text-green-600 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Settlement Initiated Successfully!
          </h2>
          <p className="text-gray-600 mb-4">
            Your cross-chain settlement has been submitted to the bridge.
          </p>

          <div className="bg-white rounded p-4 mb-4 space-y-3">
            <div>
              <p className="text-xs text-gray-600 mb-1">Transaction Hash:</p>
              <code className="text-xs text-gray-900 break-all">{txHash}</code>
            </div>
            {messageId && (
              <div>
                <p className="text-xs text-gray-600 mb-1">Cross-Chain Message ID:</p>
                <code className="text-xs text-gray-900 break-all">{messageId}</code>
              </div>
            )}
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded p-4 mb-4">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> The settlement will be processed by the bridge. This may take
              several minutes depending on network congestion. You can track the message status in
              the Messages page.
            </p>
          </div>

          <div className="flex gap-3 justify-center">
            <button
              onClick={() => (window.location.href = '/cross-chain/messages')}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Track Message
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              New Settlement
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Cross-Chain Settlement</h1>
        <p className="text-gray-600">
          Send assets from {chainId === sepolia.id ? 'Sepolia' : 'Polygon Amoy'} to another
          blockchain using secure cross-chain bridges.
        </p>
      </div>

      {/* Current Chain */}
      <div className="mb-6">
        <div className="inline-flex items-center px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="w-3 h-3 bg-blue-600 rounded-full mr-2"></div>
          <span className="text-sm font-medium text-gray-900">
            Source: {chainId === sepolia.id ? 'Ethereum Sepolia' : 'Polygon Amoy'}
          </span>
        </div>
      </div>

      {/* Bridge Info */}
      {bridgeInfo.protocols && bridgeInfo.protocols.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            <p className="text-sm text-green-800">
              <strong>Available Bridges:</strong> {bridgeInfo.protocols.join(', ')}
            </p>
          </div>
        </div>
      )}

      {/* Settlement Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-6">
        {/* Destination Chain */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Destination Chain <span className="text-red-500">*</span>
          </label>
          <select
            name="destinationChain"
            value={formData.destinationChain}
            onChange={handleChange}
            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
              errors.destinationChain
                ? 'border-red-300 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500'
            }`}
          >
            <option value="">Select destination chain</option>
            {chainId !== sepolia.id && (
              <option value="sepolia">Ethereum Sepolia</option>
            )}
            {chainId !== polygonAmoy.id && (
              <option value="amoy">Polygon Amoy</option>
            )}
          </select>
          {errors.destinationChain && (
            <p className="mt-1 text-sm text-red-600">{errors.destinationChain}</p>
          )}
        </div>

        {/* Bridge Protocol */}
        {bridgeInfo.protocols && bridgeInfo.protocols.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Bridge Protocol <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              {bridgeInfo.protocols.map((protocol: string) => (
                <button
                  key={protocol}
                  type="button"
                  onClick={() =>
                    setFormData((prev) => ({ ...prev, protocol }))
                  }
                  className={`px-4 py-3 border-2 rounded-lg font-medium transition-colors ${
                    formData.protocol === protocol
                      ? 'border-blue-600 bg-blue-50 text-blue-900'
                      : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                  }`}
                >
                  <div className="flex items-center justify-center gap-2">
                    <Zap className="h-5 w-5" />
                    {protocol.toUpperCase()}
                  </div>
                  {formData.destinationChain &&
                    bridgeInfo.preferredProtocols?.[
                      formData.destinationChain as 'sepolia' | 'amoy'
                    ] === protocol && (
                      <span className="text-xs text-green-600 mt-1 block">
                        Recommended
                      </span>
                    )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Recipient Address */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Recipient Address <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="recipient"
            value={formData.recipient}
            onChange={handleChange}
            placeholder="0x..."
            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
              errors.recipient
                ? 'border-red-300 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500'
            }`}
          />
          {errors.recipient && (
            <p className="mt-1 text-sm text-red-600">{errors.recipient}</p>
          )}
          <p className="mt-1 text-xs text-gray-500">
            Address on the destination chain to receive funds
          </p>
        </div>

        {/* Amount */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Amount ({chainId === sepolia.id ? 'ETH' : 'MATIC'}) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            name="amount"
            value={formData.amount}
            onChange={handleChange}
            placeholder="0.0"
            step="0.001"
            min="0"
            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
              errors.amount
                ? 'border-red-300 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500'
            }`}
          />
          {errors.amount && (
            <p className="mt-1 text-sm text-red-600">{errors.amount}</p>
          )}
        </div>

        {/* Gas Estimation */}
        {gasEstimate.data && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Estimated Cross-Chain Fees
            </h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Estimated Gas:</span>
                <span className="font-semibold text-gray-900">
                  {gasEstimate.data.estimatedGas?.toString() || 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Protocol:</span>
                <span className="font-semibold text-gray-900">
                  {gasEstimate.data.protocol || formData.protocol}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Summary */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Settlement Summary</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">From:</span>
              <span className="font-semibold text-gray-900">
                {chainId === sepolia.id ? 'Sepolia' : 'Polygon Amoy'}
              </span>
            </div>
            <div className="flex items-center justify-center py-2">
              <ArrowRight className="h-5 w-5 text-blue-600" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">To:</span>
              <span className="font-semibold text-gray-900">
                {formData.destinationChain === 'sepolia'
                  ? 'Ethereum Sepolia'
                  : formData.destinationChain === 'amoy'
                  ? 'Polygon Amoy'
                  : 'Not selected'}
              </span>
            </div>
            <div className="flex items-center justify-between pt-2 border-t">
              <span className="text-gray-600">Amount:</span>
              <span className="font-bold text-gray-900">
                {formData.amount || '0.0'} {chainId === sepolia.id ? 'ETH' : 'MATIC'}
              </span>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Sending Cross-Chain Message...
            </>
          ) : (
            <>
              <ArrowRight className="h-5 w-5" />
              Initiate Settlement
            </>
          )}
        </button>
      </form>
    </div>
  );
}
