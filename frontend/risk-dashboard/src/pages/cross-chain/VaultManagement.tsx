import { useState } from 'react';
import { useAccount, useChainId } from 'wagmi';
import { formatEther } from 'viem';
import { sepolia } from 'wagmi/chains';
import { polygonAmoy } from '@/config/chains';
import {
  useMultiChainVaultData,
  useDepositCollateral,
  useWithdrawCollateral,
} from '@/hooks/contracts/useCrossChainVault';
import { addPolygonAmoyNetwork } from '@/utils/addNetwork';
import { AlertCircle, Loader2, CheckCircle2, TrendingUp, TrendingDown, DollarSign, Wifi } from 'lucide-react';

// Minimum gas required for cross-chain messages (must match contract MIN_GAS_AMOUNT)
const MIN_GAS_AMOUNT = '0.01';

export default function VaultManagement() {
  const { address, isConnected } = useAccount();
  const chainId = useChainId();

  const vaultData = useMultiChainVaultData(address);

  const { depositCollateral, isLoading: isDepositing, isSuccess: depositSuccess, txHash: depositTxHash } = useDepositCollateral(chainId);
  const { withdrawCollateral, isLoading: isWithdrawing, isSuccess: withdrawSuccess, txHash: withdrawTxHash } = useWithdrawCollateral(chainId);

  const [depositAmount, setDepositAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [depositError, setDepositError] = useState('');
  const [withdrawError, setWithdrawError] = useState('');
  const [showRpcAlert, setShowRpcAlert] = useState(true);
  const [updatingRpc, setUpdatingRpc] = useState(false);

  const currentChain = chainId === sepolia.id ? 'sepolia' : 'polygonAmoy';
  const currentVaultData = vaultData[currentChain];

  const handleUpdateRpc = async () => {
    setUpdatingRpc(true);
    try {
      await addPolygonAmoyNetwork();
      setShowRpcAlert(false);
      alert('Network RPC updated successfully! Please try your transaction again.');
    } catch (error) {
      console.error('Failed to update RPC:', error);
      alert('Failed to update network RPC. Please update manually in MetaMask settings.');
    } finally {
      setUpdatingRpc(false);
    }
  };

  const handleDeposit = () => {
    setDepositError('');

    if (!depositAmount || parseFloat(depositAmount) <= 0) {
      setDepositError('Please enter a valid amount');
      return;
    }

    if (!address) {
      setDepositError('Wallet not connected');
      return;
    }

    console.log('Deposit params:', {
      user: address,
      amount: depositAmount,
      gasAmount: MIN_GAS_AMOUNT,
      totalValue: (parseFloat(depositAmount) + parseFloat(MIN_GAS_AMOUNT)).toString(),
    });

    depositCollateral({
      user: address,
      amount: depositAmount,
      gasAmount: MIN_GAS_AMOUNT,
    });
  };

  const handleWithdraw = () => {
    setWithdrawError('');

    if (!withdrawAmount || parseFloat(withdrawAmount) <= 0) {
      setWithdrawError('Please enter a valid amount');
      return;
    }

    withdrawCollateral({
      amount: withdrawAmount,
      gasAmount: MIN_GAS_AMOUNT,
    });
  };

  if (!isConnected) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-yellow-600 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Wallet Not Connected</h2>
          <p className="text-gray-600">
            Please connect your wallet to manage your cross-chain vault.
          </p>
        </div>
      </div>
    );
  }

  // Success screens
  if (depositSuccess && depositTxHash) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <CheckCircle2 className="mx-auto h-12 w-12 text-green-600 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Deposit Successful!</h2>
          <p className="text-gray-600 mb-4">
            Your collateral has been deposited to the vault.
          </p>
          <div className="bg-white rounded p-3 mb-4">
            <p className="text-xs text-gray-600 mb-1">Transaction Hash:</p>
            <code className="text-xs text-gray-900 break-all">{depositTxHash}</code>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  if (withdrawSuccess && withdrawTxHash) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <CheckCircle2 className="mx-auto h-12 w-12 text-green-600 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Withdrawal Successful!</h2>
          <p className="text-gray-600 mb-4">
            Your collateral has been withdrawn from the vault.
          </p>
          <div className="bg-white rounded p-3 mb-4">
            <p className="text-xs text-gray-600 mb-1">Transaction Hash:</p>
            <code className="text-xs text-gray-900 break-all">{withdrawTxHash}</code>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Cross-Chain Vault</h1>
        <p className="text-gray-600">
          Manage your collateral across multiple blockchains. Deposit, withdraw, and monitor your cross-chain positions.
        </p>
      </div>

      {/* RPC Configuration Alert - Only show on Polygon Amoy */}
      {chainId === polygonAmoy.id && showRpcAlert && (
        <div className="mb-6 bg-orange-50 border border-orange-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Wifi className="h-5 w-5 text-orange-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-gray-900 mb-1">
                RPC Configuration Recommended
              </h3>
              <p className="text-sm text-gray-700 mb-3">
                To avoid rate limiting errors, update your Polygon Amoy network to use Infura RPC endpoints.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleUpdateRpc}
                  disabled={updatingRpc}
                  className="px-3 py-1.5 bg-orange-600 text-white text-sm rounded hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {updatingRpc ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Updating...
                    </>
                  ) : (
                    'Update Network RPC'
                  )}
                </button>
                <button
                  onClick={() => setShowRpcAlert(false)}
                  className="px-3 py-1.5 bg-white text-gray-700 text-sm rounded border border-gray-300 hover:bg-gray-50"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Current Chain Badge */}
      <div className="mb-6">
        <div className="inline-flex items-center px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="w-3 h-3 bg-blue-600 rounded-full mr-2"></div>
          <span className="text-sm font-medium text-gray-900">
            Current Network: {chainId === sepolia.id ? 'Sepolia Testnet' : 'Polygon Amoy'}
          </span>
        </div>
      </div>

      {/* Vault Statistics - Current Chain */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Total Collateral</h3>
            <TrendingUp className="h-5 w-5 text-green-600" />
          </div>
          {currentVaultData.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">
              {currentVaultData.totalCollateral
                ? `${parseFloat(formatEther(currentVaultData.totalCollateral)).toFixed(4)} ETH`
                : '0.0000 ETH'}
            </p>
          )}
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Total Borrowed</h3>
            <TrendingDown className="h-5 w-5 text-orange-600" />
          </div>
          {currentVaultData.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">
              {currentVaultData.totalBorrowed
                ? `${parseFloat(formatEther(currentVaultData.totalBorrowed)).toFixed(4)} ETH`
                : '0.0000 ETH'}
            </p>
          )}
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Available Credit</h3>
            <DollarSign className="h-5 w-5 text-blue-600" />
          </div>
          {currentVaultData.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">
              {currentVaultData.creditLine
                ? `${parseFloat(formatEther(currentVaultData.creditLine)).toFixed(4)} ETH`
                : '0.0000 ETH'}
            </p>
          )}
        </div>
      </div>

      {/* Multi-Chain Overview */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Multi-Chain Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Sepolia */}
          <div className="border-l-4 border-blue-600 pl-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Ethereum Sepolia</h3>
            {vaultData.sepolia.isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            ) : (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Collateral:</span>
                  <span className="font-semibold text-gray-900">
                    {vaultData.sepolia.totalCollateral
                      ? `${parseFloat(formatEther(vaultData.sepolia.totalCollateral)).toFixed(4)} ETH`
                      : '0.0000 ETH'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Borrowed:</span>
                  <span className="font-semibold text-gray-900">
                    {vaultData.sepolia.totalBorrowed
                      ? `${parseFloat(formatEther(vaultData.sepolia.totalBorrowed)).toFixed(4)} ETH`
                      : '0.0000 ETH'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Credit Line:</span>
                  <span className="font-semibold text-gray-900">
                    {vaultData.sepolia.creditLine
                      ? `${parseFloat(formatEther(vaultData.sepolia.creditLine)).toFixed(4)} ETH`
                      : '0.0000 ETH'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Polygon Amoy */}
          <div className="border-l-4 border-purple-600 pl-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Polygon Amoy</h3>
            {vaultData.polygonAmoy.isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            ) : (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Collateral:</span>
                  <span className="font-semibold text-gray-900">
                    {vaultData.polygonAmoy.totalCollateral
                      ? `${parseFloat(formatEther(vaultData.polygonAmoy.totalCollateral)).toFixed(4)} MATIC`
                      : '0.0000 MATIC'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Borrowed:</span>
                  <span className="font-semibold text-gray-900">
                    {vaultData.polygonAmoy.totalBorrowed
                      ? `${parseFloat(formatEther(vaultData.polygonAmoy.totalBorrowed)).toFixed(4)} MATIC`
                      : '0.0000 MATIC'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Credit Line:</span>
                  <span className="font-semibold text-gray-900">
                    {vaultData.polygonAmoy.creditLine
                      ? `${parseFloat(formatEther(vaultData.polygonAmoy.creditLine)).toFixed(4)} MATIC`
                      : '0.0000 MATIC'}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Deposit Card */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Deposit Collateral</h2>
          <p className="text-sm text-gray-600 mb-4">
            Deposit {chainId === sepolia.id ? 'ETH' : 'MATIC'} to your vault on {chainId === sepolia.id ? 'Sepolia' : 'Polygon Amoy'}
          </p>

          <div className="space-y-4">
            {/* Gas Fee Info Banner */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-xs text-blue-800">
                <strong>Cross-Chain Gas Fee:</strong> {MIN_GAS_AMOUNT} {chainId === sepolia.id ? 'ETH' : 'MATIC'} will be added automatically for message delivery. Any excess will be refunded.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Amount ({chainId === sepolia.id ? 'ETH' : 'MATIC'})
              </label>
              <input
                type="number"
                value={depositAmount}
                onChange={(e) => {
                  setDepositAmount(e.target.value);
                  setDepositError('');
                }}
                placeholder="0.0"
                step="0.001"
                min="0"
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                  depositError
                    ? 'border-red-300 focus:ring-red-500'
                    : 'border-gray-300 focus:ring-blue-500'
                }`}
              />
              {depositError && (
                <p className="mt-1 text-sm text-red-600">{depositError}</p>
              )}
              {depositAmount && parseFloat(depositAmount) > 0 && (
                <p className="mt-1 text-xs text-gray-500">
                  Total cost: {(parseFloat(depositAmount) + parseFloat(MIN_GAS_AMOUNT)).toFixed(4)} {chainId === sepolia.id ? 'ETH' : 'MATIC'} (includes {MIN_GAS_AMOUNT} gas)
                </p>
              )}
            </div>

            <button
              onClick={handleDeposit}
              disabled={isDepositing}
              className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
            >
              {isDepositing ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Depositing...
                </>
              ) : (
                'Deposit Collateral'
              )}
            </button>
          </div>
        </div>

        {/* Withdraw Card */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Withdraw Collateral</h2>
          <p className="text-sm text-gray-600 mb-4">
            Withdraw {chainId === sepolia.id ? 'ETH' : 'MATIC'} from your vault on {chainId === sepolia.id ? 'Sepolia' : 'Polygon Amoy'}
          </p>

          <div className="space-y-4">
            {/* Gas Fee Info Banner */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-xs text-blue-800">
                <strong>Cross-Chain Gas Fee:</strong> {MIN_GAS_AMOUNT} {chainId === sepolia.id ? 'ETH' : 'MATIC'} required for message delivery. Any excess will be refunded.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Amount ({chainId === sepolia.id ? 'ETH' : 'MATIC'})
              </label>
              <input
                type="number"
                value={withdrawAmount}
                onChange={(e) => {
                  setWithdrawAmount(e.target.value);
                  setWithdrawError('');
                }}
                placeholder="0.0"
                step="0.001"
                min="0"
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                  withdrawError
                    ? 'border-red-300 focus:ring-red-500'
                    : 'border-gray-300 focus:ring-blue-500'
                }`}
              />
              {withdrawError && (
                <p className="mt-1 text-sm text-red-600">{withdrawError}</p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Available: {currentVaultData.totalCollateral
                  ? parseFloat(formatEther(currentVaultData.totalCollateral)).toFixed(4)
                  : '0.0000'} {chainId === sepolia.id ? 'ETH' : 'MATIC'}
              </p>
              {withdrawAmount && parseFloat(withdrawAmount) > 0 && (
                <p className="mt-1 text-xs text-gray-500">
                  Gas required: {MIN_GAS_AMOUNT} {chainId === sepolia.id ? 'ETH' : 'MATIC'} (separate from withdrawal amount)
                </p>
              )}
            </div>

            <button
              onClick={handleWithdraw}
              disabled={isWithdrawing}
              className="w-full px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
            >
              {isWithdrawing ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Withdrawing...
                </>
              ) : (
                'Withdraw Collateral'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
