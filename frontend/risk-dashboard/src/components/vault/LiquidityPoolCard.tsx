import { formatEther, parseEther } from 'viem';
import { useAccount } from 'wagmi';
import { useState } from 'react';
import {
  useSupplyDashboard,
  useSupplyLiquidity,
  useWithdrawSupplied,
  calculateEarnings,
  getUtilizationStatus,
} from '@/hooks/contracts/useVaultV28';

interface LiquidityPoolCardProps {
  chainId: number;
  chainName: string;
}

export function LiquidityPoolCard({ chainId, chainName }: LiquidityPoolCardProps) {
  const { address } = useAccount();
  const [supplyAmount, setSupplyAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [activeTab, setActiveTab] = useState<'supply' | 'withdraw'>('supply');

  const {
    suppliedBalance,
    dailyEarnings,
    totalLiquidity,
    utilized,
    available,
    utilizationPercentage,
    supplyAPY,
    borrowAPY,
    isLoading,
    refetch,
  } = useSupplyDashboard(address, chainId);

  const {
    supply,
    isPending: isSupplying,
    isConfirming: isConfirmingSupply,
    isSuccess: supplySuccess,
  } = useSupplyLiquidity(chainId);

  const {
    withdraw,
    isPending: isWithdrawing,
    isConfirming: isConfirmingWithdraw,
    isSuccess: withdrawSuccess,
  } = useWithdrawSupplied(chainId);

  // Refetch after successful transactions
  if (supplySuccess || withdrawSuccess) {
    setTimeout(() => refetch(), 2000);
  }

  const utilizationStatus = getUtilizationStatus(utilizationPercentage);

  const handleSupply = () => {
    if (!supplyAmount) return;
    const amount = parseEther(supplyAmount);
    const gasAmount = parseEther('0.01'); // 0.01 ETH for gas
    supply(amount, gasAmount);
    setSupplyAmount('');
  };

  const handleWithdraw = () => {
    if (!withdrawAmount) return;
    const amount = parseEther(withdrawAmount);
    const gasAmount = parseEther('0.01');
    withdraw(amount, gasAmount);
    setWithdrawAmount('');
  };

  // Calculate projections
  const weeklyEarnings = calculateEarnings(suppliedBalance, supplyAPY, 7);
  const monthlyEarnings = calculateEarnings(suppliedBalance, supplyAPY, 30);
  const yearlyEarnings = calculateEarnings(suppliedBalance, supplyAPY, 365);

  return (
    <div className="glass-panel rounded-xl p-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white mb-2">
          Liquidity Pool - <span className="text-gradient">{chainName}</span>
        </h2>
        <p className="text-gray-400">
          Supply liquidity to earn interest. Your earnings adjust dynamically based on pool utilization.
        </p>
      </div>

      {/* Pool Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Total Liquidity */}
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
          <div className="text-sm text-blue-400 font-medium mb-1">Total Pool Liquidity</div>
          <div className="text-2xl font-bold text-white">
            {formatEther(totalLiquidity)} ETH
          </div>
          <div className="text-xs text-blue-400 mt-1">
            Available: {formatEther(available)} ETH
          </div>
        </div>

        {/* Supply APY */}
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
          <div className="text-sm text-green-400 font-medium mb-1">Supply APY</div>
          <div className="text-2xl font-bold text-white">
            {supplyAPY.toFixed(2)}%
          </div>
          <div className="text-xs text-green-400 mt-1">
            Borrow APY: {borrowAPY.toFixed(2)}%
          </div>
        </div>

        {/* Utilization */}
        {/* Utilization */}
        <div className={`bg-${utilizationStatus.color}-500/10 border border-${utilizationStatus.color}-500/20 rounded-lg p-4`}>
          <div className={`text-sm text-${utilizationStatus.color}-400 font-medium mb-1`}>
            Pool Utilization
          </div>
          <div className="text-2xl font-bold text-white">
            {utilizationPercentage.toFixed(2)}%
          </div>
          <div className={`text-xs text-${utilizationStatus.color}-400 mt-1`}>
            {utilizationStatus.label}
          </div>
        </div>
      </div>

      {/* Utilization Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-400 mb-2">
          <span>Utilization Rate</span>
          <span>{utilizationPercentage.toFixed(2)}%</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-300 ${utilizationPercentage < 25 ? 'bg-green-500' :
                utilizationPercentage < 50 ? 'bg-blue-500' :
                  utilizationPercentage < 75 ? 'bg-yellow-500' :
                    'bg-orange-500'
              }`}
            style={{ width: `${Math.min(utilizationPercentage, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>Low APY</span>
          <span>High APY</span>
        </div>
      </div>

      {/* User Position */}
      {address && suppliedBalance > 0n && (
        <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20 rounded-lg p-4 mb-6">
          <div className="text-sm font-medium text-purple-300 mb-3">Your Position</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-purple-400">Supplied</div>
              <div className="text-lg font-bold text-white">
                {Number(formatEther(suppliedBalance)).toFixed(4)} ETH
              </div>
            </div>
            <div>
              <div className="text-xs text-purple-400">Daily Earnings</div>
              <div className="text-lg font-bold text-white">
                {Number(formatEther(dailyEarnings)).toFixed(6)} ETH
              </div>
            </div>
            <div>
              <div className="text-xs text-purple-400">Weekly Est.</div>
              <div className="text-lg font-bold text-white">
                {Number(formatEther(weeklyEarnings)).toFixed(5)} ETH
              </div>
            </div>
            <div>
              <div className="text-xs text-purple-400">Yearly Est.</div>
              <div className="text-lg font-bold text-white">
                {Number(formatEther(yearlyEarnings)).toFixed(4)} ETH
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Supply/Withdraw Tabs */}
      <div className="border-b border-white/10 mb-6">
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab('supply')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'supply'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
          >
            Supply Liquidity
          </button>
          <button
            onClick={() => setActiveTab('withdraw')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'withdraw'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
          >
            Withdraw
          </button>
        </div>
      </div>

      {/* Supply Panel */}
      {activeTab === 'supply' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Amount to Supply
            </label>
            <div className="relative">
              <input
                type="number"
                step="0.001"
                placeholder="0.0"
                value={supplyAmount}
                onChange={(e) => setSupplyAmount(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-500"
              />
              <div className="absolute right-3 top-3 text-gray-500 font-medium">
                ETH
              </div>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              + 0.01 ETH gas fee for cross-chain message
            </div>
          </div>

          {supplyAmount && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-sm">
              <div className="flex justify-between mb-1">
                <span className="text-blue-300">Expected Daily Earnings:</span>
                <span className="font-semibold text-white">
                  {(Number(supplyAmount) * supplyAPY / 365 / 100).toFixed(6)} ETH
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-300">Expected Yearly Earnings:</span>
                <span className="font-semibold text-white">
                  {(Number(supplyAmount) * supplyAPY / 100).toFixed(4)} ETH
                </span>
              </div>
            </div>
          )}

          <button
            onClick={handleSupply}
            disabled={!supplyAmount || isSupplying || isConfirmingSupply || !address}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {!address
              ? 'Connect Wallet'
              : isSupplying
                ? 'Confirming in Wallet...'
                : isConfirmingSupply
                  ? 'Processing Transaction...'
                  : supplySuccess
                    ? 'Supply Successful!'
                    : 'Supply Liquidity'}
          </button>
        </div>
      )}

      {/* Withdraw Panel */}
      {activeTab === 'withdraw' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Amount to Withdraw
            </label>
            <div className="relative">
              <input
                type="number"
                step="0.001"
                placeholder="0.0"
                value={withdrawAmount}
                onChange={(e) => setWithdrawAmount(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-500"
              />
              <div className="absolute right-3 top-3 text-gray-500 font-medium">
                ETH
              </div>
            </div>
            {address && suppliedBalance > 0n && (
              <div className="flex justify-between text-xs mt-1">
                <span className="text-gray-500">
                  Available: {Number(formatEther(suppliedBalance)).toFixed(4)} ETH
                </span>
                <button
                  onClick={() => setWithdrawAmount(formatEther(suppliedBalance))}
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  Max
                </button>
              </div>
            )}
          </div>

          {withdrawAmount && suppliedBalance > 0n && (
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3 text-sm">
              <div className="text-purple-300 mb-1">
                Withdrawing your supplied amount with accrued interest
              </div>
              <div className="text-white font-semibold">
                Interest earned: {Number(formatEther(suppliedBalance - parseEther(withdrawAmount))).toFixed(6)} ETH
              </div>
            </div>
          )}

          <button
            onClick={handleWithdraw}
            disabled={
              !withdrawAmount ||
              isWithdrawing ||
              isConfirmingWithdraw ||
              !address ||
              suppliedBalance === 0n
            }
            className="w-full bg-purple-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {!address
              ? 'Connect Wallet'
              : suppliedBalance === 0n
                ? 'No Balance to Withdraw'
                : isWithdrawing
                  ? 'Confirming in Wallet...'
                  : isConfirmingWithdraw
                    ? 'Processing Transaction...'
                    : withdrawSuccess
                      ? 'Withdrawal Successful!'
                      : 'Withdraw'}
          </button>
        </div>
      )}

      {/* Info Box */}
      <div className="mt-6 bg-white/5 border border-white/10 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-white mb-2">How It Works</h3>
        <ul className="text-sm text-gray-400 space-y-1">
          <li>• Supply ETH to the pool and earn interest based on utilization</li>
          <li>• APY increases as more users borrow from the pool</li>
          <li>• Interest accrues automatically and compounds your balance</li>
          <li>• Withdraw anytime (as long as funds aren't being borrowed)</li>
          <li>• Cross-chain synchronized - your balance is tracked globally</li>
        </ul>
      </div>
    </div>
  );
}
