import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAccount } from 'wagmi';
import { isAddress } from 'viem';
import { useCreateEscrow } from '@/hooks/contracts/useEscrowFactory';
import { AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import { PageTransition, FadeIn, ScaleIn } from '@/components/common/PageTransition';

export default function CreateEscrow() {
  const navigate = useNavigate();
  const { address, isConnected } = useAccount();
  const { createEscrow, isLoading, isSuccess, txHash, error } = useCreateEscrow();

  const [formData, setFormData] = useState({
    payee: '',
    amount: '',
    arbiter: '',
    timelock: '86400', // 1 day in seconds
    description: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.payee) {
      newErrors.payee = 'Payee address is required';
    } else if (!isAddress(formData.payee)) {
      newErrors.payee = 'Invalid Ethereum address';
    }

    if (!formData.amount) {
      newErrors.amount = 'Amount is required';
    } else if (parseFloat(formData.amount) <= 0) {
      newErrors.amount = 'Amount must be greater than 0';
    }

    if (!formData.arbiter) {
      newErrors.arbiter = 'Arbiter address is required';
    } else if (!isAddress(formData.arbiter)) {
      newErrors.arbiter = 'Invalid Ethereum address';
    }

    if (formData.arbiter === formData.payee) {
      newErrors.arbiter = 'Arbiter cannot be the same as payee';
    }

    if (address && formData.payee === address) {
      newErrors.payee = 'Payee cannot be yourself (the payer)';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      createEscrow({
        payee: formData.payee as `0x${string}`,
        arbiter: formData.arbiter as `0x${string}`,
        timelock: parseInt(formData.timelock),
        amount: formData.amount
      });
    } catch (err: any) {
      console.error('Escrow creation error:', err);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error for this field
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  if (!isConnected) {
    return (
      <PageTransition>
        <div className="max-w-2xl mx-auto p-6">
          <FadeIn>
            <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-8 text-center shadow-lg">
              <div className="mx-auto w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
                <AlertCircle className="h-8 w-8 text-yellow-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Wallet Not Connected</h2>
              <p className="text-gray-600">
                Please connect your wallet using the button in the header to create an escrow.
              </p>
            </div>
          </FadeIn>
        </div>
      </PageTransition>
    );
  }

  if (isSuccess && txHash) {
    return (
      <PageTransition>
        <div className="max-w-2xl mx-auto p-6">
          <ScaleIn>
            <div className="bg-green-50 border-2 border-green-200 rounded-lg p-8 text-center shadow-lg">
              <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <CheckCircle2 className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Escrow Created Successfully!</h2>
          <p className="text-gray-600 mb-4">
            Your escrow has been created on the blockchain.
          </p>
          <div className="bg-white rounded p-3 mb-4">
            <p className="text-xs text-gray-600 mb-1">Transaction Hash:</p>
            <code className="text-xs text-gray-900 break-all">{txHash}</code>
          </div>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={() => navigate('/escrow/manage')}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg"
                >
                  View My Escrows
                </button>
                <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-all duration-200 hover:scale-105"
                >
                  Create Another
                </button>
              </div>
            </div>
          </ScaleIn>
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="max-w-2xl mx-auto p-6">
        <FadeIn delay={0.1}>
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Create Escrow</h1>
            <p className="text-gray-600">
              Create a secure escrow transaction on the blockchain. Funds will be held until released by the arbiter or approved by the payee.
            </p>
          </div>
        </FadeIn>

        <FadeIn delay={0.2}>
          <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-all duration-300 border border-gray-200 p-6 space-y-6">
        {/* Payee Address */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Payee Address <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="payee"
            value={formData.payee}
            onChange={handleChange}
            placeholder="0x..."
            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
              errors.payee
                ? 'border-red-300 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500'
            }`}
          />
          {errors.payee && (
            <p className="mt-1 text-sm text-red-600">{errors.payee}</p>
          )}
          <p className="mt-1 text-xs text-gray-500">
            The recipient who will receive the funds
          </p>
        </div>

        {/* Amount */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Amount (ETH) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            name="amount"
            value={formData.amount}
            onChange={handleChange}
            placeholder="0.1"
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
          <p className="mt-1 text-xs text-gray-500">
            Amount in ETH to be held in escrow
          </p>
        </div>

        {/* Arbiter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Arbiter Address <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="arbiter"
            value={formData.arbiter}
            onChange={handleChange}
            placeholder="0x..."
            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
              errors.arbiter
                ? 'border-red-300 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500'
            }`}
          />
          {errors.arbiter && (
            <p className="mt-1 text-sm text-red-600">{errors.arbiter}</p>
          )}
          <p className="mt-1 text-xs text-gray-500">
            Trusted third party who can release or refund the escrow
          </p>
        </div>

        {/* Timelock */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Timelock Duration <span className="text-red-500">*</span>
          </label>
          <select
            name="timelock"
            value={formData.timelock}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="3600">1 Hour</option>
            <option value="86400">1 Day</option>
            <option value="259200">3 Days</option>
            <option value="604800">1 Week</option>
            <option value="2592000">30 Days</option>
          </select>
          <p className="mt-1 text-xs text-gray-500">
            Minimum time before funds can be released
          </p>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description (Optional)
          </label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Describe the purpose of this escrow..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Note: Description is stored locally only, not on-chain
          </p>
        </div>

        {/* Summary */}
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Summary</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">You (Payer):</span>
              <code className="text-gray-900 text-xs">{address}</code>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Amount:</span>
              <span className="font-semibold text-gray-900">{formData.amount || '0'} ETH</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Network:</span>
              <span className="text-gray-900">Sepolia Testnet</span>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-semibold text-red-900 mb-1">Transaction Failed</h4>
                <p className="text-sm text-red-700">{error.message || 'Unknown error occurred'}</p>
              </div>
            </div>
          </div>
        )}

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2 transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg disabled:hover:scale-100"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Creating Escrow...
                  </>
                ) : (
                  'Create Escrow'
                )}
              </button>
              <button
                type="button"
                onClick={() => navigate('/escrow/manage')}
                className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium transition-all duration-200 hover:scale-105"
              >
                Cancel
              </button>
            </div>
          </form>
        </FadeIn>
      </div>
    </PageTransition>
  );
}
