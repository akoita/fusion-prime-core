import { useState } from 'react';
import { useAccount, useSwitchChain } from 'wagmi';
import { formatEther } from 'viem';
import { sepolia } from 'wagmi/chains';
import { polygonAmoy, CHAIN_INFO } from '@/config/chains';
import {
  useAggregatedVaultData,
  useDepositToVault,
  useWithdrawFromVault,
  useBorrowFromVault,
  useRepayToVault,
} from '@/hooks/contracts/useVault';
import { PageTransition, FadeIn, StaggerChildren, StaggerItem } from '@/components/common/PageTransition';
import { Wallet, TrendingUp, TrendingDown, Lock, AlertCircle, Loader2, DollarSign, ArrowDownCircle, ArrowUpCircle } from 'lucide-react';
import { CrossChainSyncStatus } from '@/components/vault/CrossChainSyncStatus';
import { LiquidityPoolCard } from '@/components/vault/LiquidityPoolCard';

export default function VaultDashboard() {
  const { address, chainId, isConnected } = useAccount();
  const { switchChain } = useSwitchChain();

  const [depositAmount, setDepositAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [borrowAmount, setBorrowAmount] = useState('');
  const [repayAmount, setRepayAmount] = useState('');
  const [activeTab, setActiveTab] = useState<'deposit' | 'withdraw' | 'borrow' | 'repay'>('deposit');

  // Determine which vault to query based on connected chain
  const vaultChainId = chainId === polygonAmoy.id ? polygonAmoy.id : sepolia.id;

  // Get aggregated vault data from BOTH chains
  const vaultData = useAggregatedVaultData(address, vaultChainId);
  const depositHook = useDepositToVault(vaultChainId);
  const withdrawHook = useWithdrawFromVault(vaultChainId);
  const borrowHook = useBorrowFromVault(vaultChainId);
  const repayHook = useRepayToVault(vaultChainId);

  const { deposit, isLoading: isDepositing, isSuccess: depositSuccess } = depositHook;
  const { withdraw, isLoading: isWithdrawing, isSuccess: withdrawSuccess } = withdrawHook;
  const { borrow, isLoading: isBorrowing, isSuccess: borrowSuccess } = borrowHook;
  const { repay, isLoading: isRepaying, isSuccess: repaySuccess } = repayHook;

  const handleDeposit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address || !depositAmount) return;
    deposit(address, depositAmount);
  };

  const handleWithdraw = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!withdrawAmount) return;
    withdraw(withdrawAmount);
  };

  const handleBorrow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!borrowAmount) return;
    // Default gas amount: 0.001 ETH for cross-chain messaging
    borrow(borrowAmount, '0.001');
  };

  const handleRepay = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repayAmount) return;
    repay(repayAmount);
  };

  // Calculate health factor (simple version: collateral / borrowed)
  const healthFactor = vaultData.totalBorrowed && vaultData.totalBorrowed > 0n
    ? Number(vaultData.totalCollateral || 0n) / Number(vaultData.totalBorrowed)
    : Infinity;

  // Wallet not connected
  if (!isConnected) {
    return (
      <PageTransition>
        <div className="max-w-6xl mx-auto p-6">
          <FadeIn>
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-8 text-center shadow-lg backdrop-blur-sm">
              <div className="mx-auto w-16 h-16 bg-yellow-500/20 rounded-full flex items-center justify-center mb-4">
                <AlertCircle className="h-8 w-8 text-yellow-500" />
              </div>
              <h2 className="text-xl font-semibold text-white mb-2">Wallet Not Connected</h2>
              <p className="text-gray-400">
                Please connect your wallet to view your vault.
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
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">CrossChain <span className="text-gradient">Vault Dashboard</span></h1>
            <p className="text-gray-400">
              View and manage your collateral across Ethereum Sepolia and Polygon Amoy networks.
            </p>
          </div>
        </FadeIn>

        {/* Network Selector */}
        <FadeIn delay={0.2}>
          <div className="glass-panel rounded-xl p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Lock className="h-5 w-5 text-blue-400" />
                <span className="text-sm font-medium text-white">
                  Viewing vault on: <strong className="text-blue-400">{CHAIN_INFO[vaultChainId].name}</strong>
                </span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => switchChain?.({ chainId: sepolia.id })}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${vaultChainId === sepolia.id
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                    : 'bg-white/5 text-blue-400 border border-blue-500/30 hover:bg-blue-500/10'
                    }`}
                >
                  Sepolia
                </button>
                <button
                  onClick={() => switchChain?.({ chainId: polygonAmoy.id })}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${vaultChainId === polygonAmoy.id
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                    : 'bg-white/5 text-purple-400 border border-purple-500/30 hover:bg-purple-500/10'
                    }`}
                >
                  Amoy
                </button>
              </div>
            </div>
          </div>
        </FadeIn>

        {/* Cross-Chain Sync Status */}
        <FadeIn delay={0.25}>
          <CrossChainSyncStatus
            userAddress={address}
            onSyncComplete={() => {
              // Force re-render by calling window.location.reload()
              // In production, we'd use queryClient.invalidateQueries() or similar
              window.location.reload();
            }}
          />
        </FadeIn>

        {/* Stats Grid */}
        <StaggerChildren delay={0.3}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {/* Total Collateral */}
            <StaggerItem>
              <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-400">Total Collateral (Aggregated)</span>
                  <Wallet className="h-5 w-5 text-green-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {vaultData.isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  ) : (
                    <>
                      {`${Number(formatEther(vaultData.aggregatedTotal || 0n)).toFixed(4)} ETH`}
                      {!vaultData.syncStatus?.allSynced && (
                        <span className="ml-2 text-xs text-orange-600">⏳</span>
                      )}
                    </>
                  )}
                </div>
                {!vaultData.syncStatus?.allSynced && !vaultData.isLoading && (
                  <div className="mt-2 text-xs text-orange-600">
                    Syncing across chains...
                  </div>
                )}
              </div>
            </StaggerItem>

            {/* Sepolia Balance */}
            <StaggerItem>
              <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-400">Sepolia Balance</span>
                  <span className="text-2xl">{CHAIN_INFO[sepolia.id].icon}</span>
                </div>
                <div className="text-2xl font-bold text-white">
                  {vaultData.isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  ) : (
                    <>
                      {`${Number(formatEther(vaultData.sepoliaBalance || 0n)).toFixed(4)} ETH`}
                      {!vaultData.syncStatus?.sepoliaSynced && (
                        <span className="ml-2 text-xs text-orange-600">⏳</span>
                      )}
                    </>
                  )}
                </div>
                {!vaultData.syncStatus?.sepoliaSynced && !vaultData.isLoading && (
                  <div className="mt-2 text-xs text-orange-600">
                    Out of sync
                  </div>
                )}
              </div>
            </StaggerItem>

            {/* Amoy Balance */}
            <StaggerItem>
              <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-400">Amoy Balance</span>
                  <span className="text-2xl">{CHAIN_INFO[polygonAmoy.id].icon}</span>
                </div>
                <div className="text-2xl font-bold text-white">
                  {vaultData.isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  ) : (
                    <>
                      {`${Number(formatEther(vaultData.amoyBalance || 0n)).toFixed(4)} MATIC`}
                      {!vaultData.syncStatus?.amoySynced && (
                        <span className="ml-2 text-xs text-orange-600">⏳</span>
                      )}
                    </>
                  )}
                </div>
                {!vaultData.syncStatus?.amoySynced && !vaultData.isLoading && (
                  <div className="mt-2 text-xs text-orange-600">
                    Out of sync
                  </div>
                )}
              </div>
            </StaggerItem>

            {/* Credit Line */}
            <StaggerItem>
              <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-400">Available Credit (This Chain)</span>
                  <DollarSign className="h-5 w-5 text-green-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {vaultData.isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  ) : (
                    `${Number(formatEther(vaultData.localCreditLine || 0n)).toFixed(4)} ETH`
                  )}
                </div>
                {!vaultData.syncStatus?.allSynced && !vaultData.isLoading && (
                  <div className="mt-2 text-xs text-gray-400">
                    Based on {CHAIN_INFO[vaultChainId].name} vault
                  </div>
                )}
              </div>
            </StaggerItem>

            {/* Total Borrowed */}
            <StaggerItem>
              <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-400">Total Borrowed (This Chain)</span>
                  <ArrowDownCircle className="h-5 w-5 text-red-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {vaultData.isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  ) : (
                    `${Number(formatEther(vaultData.localBorrowed || 0n)).toFixed(4)} ETH`
                  )}
                </div>
              </div>
            </StaggerItem>

            {/* Sepolia Borrowed */}
            <StaggerItem>
              <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-400">Sepolia Borrowed</span>
                  <span className="text-2xl">{CHAIN_INFO[sepolia.id].icon}</span>
                </div>
                <div className="text-2xl font-bold text-white">
                  {vaultData.isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  ) : (
                    `${Number(formatEther(vaultData.sepoliaBorrowed || 0n)).toFixed(4)} ETH`
                  )}
                </div>
              </div>
            </StaggerItem>

            {/* Amoy Borrowed */}
            <StaggerItem>
              <div className="glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-400">Amoy Borrowed</span>
                  <span className="text-2xl">{CHAIN_INFO[polygonAmoy.id].icon}</span>
                </div>
                <div className="text-2xl font-bold text-white">
                  {vaultData.isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  ) : (
                    `${Number(formatEther(vaultData.amoyBorrowed || 0n)).toFixed(4)} MATIC`
                  )}
                </div>
              </div>
            </StaggerItem>

            {/* Health Factor */}
            <StaggerItem>
              <div className={`glass-panel rounded-xl p-6 transition-all duration-300 hover:scale-[1.02] ${healthFactor === Infinity ? 'border-white/10' :
                healthFactor >= 2 ? 'border-green-500/30 shadow-[0_0_15px_rgba(34,197,94,0.1)]' :
                  healthFactor >= 1.2 ? 'border-yellow-500/30 shadow-[0_0_15px_rgba(234,179,8,0.1)]' :
                    'border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.1)]'
                }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-400">Health Factor</span>
                  <div className={`h-3 w-3 rounded-full ${healthFactor === Infinity ? 'bg-gray-400' :
                    healthFactor >= 2 ? 'bg-green-500' :
                      healthFactor >= 1.2 ? 'bg-yellow-500' :
                        'bg-red-500'
                    }`} />
                </div>
                <div className={`text-2xl font-bold ${healthFactor === Infinity ? 'text-white' :
                  healthFactor >= 2 ? 'text-green-400' :
                    healthFactor >= 1.2 ? 'text-yellow-400' :
                      'text-red-400'
                  }`}>
                  {vaultData.isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  ) : healthFactor === Infinity ? (
                    '∞'
                  ) : (
                    healthFactor.toFixed(2)
                  )}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {healthFactor === Infinity ? 'No debt' :
                    healthFactor >= 2 ? 'Healthy' :
                      healthFactor >= 1.2 ? 'Caution' :
                        'At Risk'}
                </div>
              </div>
            </StaggerItem>
          </div>
        </StaggerChildren>

        {/* Sync Warning Banner */}
        {!vaultData.syncStatus?.allSynced && !vaultData.isLoading && (
          <FadeIn delay={0.35}>
            <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-6 mb-6 shadow-lg backdrop-blur-sm">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                  <AlertCircle className="h-6 w-6 text-orange-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-orange-400 mb-2">
                    ⚠️ Cross-Chain Sync in Progress
                  </h3>
                  <p className="text-sm text-orange-300 mb-3">
                    Your vaults on Sepolia and Amoy are currently out of sync. Cross-chain messages via Chainlink CCIP can take 2-20 minutes on testnet.
                  </p>

                  {/* Detailed sync status */}
                  <div className="bg-orange-500/10 rounded-lg p-3 mb-3 text-xs space-y-2 border border-orange-500/20">
                    <div className="font-semibold text-orange-300">Current Sync Status:</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="font-medium text-orange-300">Sepolia Vault View:</div>
                        <div className="text-orange-200">
                          • Sepolia: {Number(formatEther(vaultData.syncStatus?.sepoliaVaultView?.sepoliaBalance || 0n)).toFixed(4)} ETH
                        </div>
                        <div className="text-orange-200">
                          • Amoy: {Number(formatEther(vaultData.syncStatus?.sepoliaVaultView?.amoyBalance || 0n)).toFixed(4)} MATIC
                        </div>
                        <div className="text-orange-200">
                          • Total: {Number(formatEther(vaultData.syncStatus?.sepoliaVaultView?.total || 0n)).toFixed(4)} ETH
                        </div>
                      </div>
                      <div>
                        <div className="font-medium text-orange-300">Amoy Vault View:</div>
                        <div className="text-orange-200">
                          • Sepolia: {Number(formatEther(vaultData.syncStatus?.amoyVaultView?.sepoliaBalance || 0n)).toFixed(4)} ETH
                        </div>
                        <div className="text-orange-200">
                          • Amoy: {Number(formatEther(vaultData.syncStatus?.amoyVaultView?.amoyBalance || 0n)).toFixed(4)} MATIC
                        </div>
                        <div className="text-orange-200">
                          • Total: {Number(formatEther(vaultData.syncStatus?.amoyVaultView?.total || 0n)).toFixed(4)} MATIC
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2 text-sm text-orange-300">
                    <p className="font-semibold">What this means:</p>
                    <ul className="list-disc list-inside space-y-1 ml-2">
                      <li>
                        <strong>Available Credit on {CHAIN_INFO[vaultChainId].name}</strong> is based only on what this vault has confirmed.
                      </li>
                      <li>
                        You can still deposit, borrow, and repay, but the credit line may be lower than your actual collateral until sync completes.
                      </li>
                      <li>
                        The "Total Collateral (Aggregated)" shows your real balance by querying both chains directly.
                      </li>
                      <li>
                        Wait a few minutes and refresh to check if sync has completed.
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </FadeIn>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Manage Vault Card */}
          <FadeIn delay={0.4}>
            <div className="glass-panel rounded-xl p-6">
              <h2 className="text-xl font-bold text-white mb-4">Manage Vault</h2>

              {/* Tabs */}
              <div className="grid grid-cols-2 gap-2 mb-6">
                <button
                  onClick={() => setActiveTab('deposit')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'deposit'
                    ? 'bg-green-600 text-white shadow-lg shadow-green-500/20'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                    }`}
                >
                  <TrendingUp className="h-4 w-4 inline mr-2" />
                  Deposit
                </button>
                <button
                  onClick={() => setActiveTab('withdraw')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'withdraw'
                    ? 'bg-red-600 text-white shadow-lg shadow-red-500/20'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                    }`}
                >
                  <TrendingDown className="h-4 w-4 inline mr-2" />
                  Withdraw
                </button>
                <button
                  onClick={() => setActiveTab('borrow')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'borrow'
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                    }`}
                >
                  <ArrowDownCircle className="h-4 w-4 inline mr-2" />
                  Borrow
                </button>
                <button
                  onClick={() => setActiveTab('repay')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'repay'
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                    }`}
                >
                  <ArrowUpCircle className="h-4 w-4 inline mr-2" />
                  Repay
                </button>
              </div>

              {/* Deposit Form */}
              {activeTab === 'deposit' && (
                <form onSubmit={handleDeposit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Amount to Deposit
                    </label>
                    <input
                      type="number"
                      step="0.001"
                      value={depositAmount}
                      onChange={(e) => setDepositAmount(e.target.value)}
                      placeholder="0.0"
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent text-white placeholder-gray-500"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={!depositAmount || isDepositing}
                    className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                  >
                    {isDepositing ? (
                      <>
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Depositing...
                      </>
                    ) : (
                      <>
                        <TrendingUp className="h-5 w-5" />
                        Deposit to Vault
                      </>
                    )}
                  </button>
                  {depositSuccess && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
                      ✓ Deposit successful!
                    </div>
                  )}
                  {depositHook.isError && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-sm font-semibold text-red-900 mb-1">❌ Deposit Failed</p>
                      <p className="text-xs text-red-800">
                        {depositHook.error?.message || 'Transaction was rejected or reverted'}
                      </p>
                      {depositHook.txHash && (
                        <a
                          href={`${vaultChainId === sepolia.id ? 'https://sepolia.etherscan.io' : 'https://amoy.polygonscan.com'}/tx/${depositHook.txHash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-red-600 hover:text-red-700 underline mt-1 inline-block"
                        >
                          View transaction →
                        </a>
                      )}
                    </div>
                  )}
                </form>
              )}

              {/* Withdraw Form */}
              {activeTab === 'withdraw' && (
                <form onSubmit={handleWithdraw} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Amount to Withdraw
                    </label>
                    <input
                      type="number"
                      step="0.001"
                      value={withdrawAmount}
                      onChange={(e) => setWithdrawAmount(e.target.value)}
                      placeholder="0.0"
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent text-white placeholder-gray-500"
                    />
                    <p className="text-sm text-gray-500 mt-2">
                      Available: {Number(formatEther(vaultData.totalCollateral || 0n)).toFixed(4)} ETH
                    </p>
                  </div>
                  <button
                    type="submit"
                    disabled={!withdrawAmount || isWithdrawing}
                    className="w-full px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                  >
                    {isWithdrawing ? (
                      <>
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Withdrawing...
                      </>
                    ) : (
                      <>
                        <TrendingDown className="h-5 w-5" />
                        Withdraw from Vault
                      </>
                    )}
                  </button>
                  {withdrawSuccess && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
                      ✓ Withdrawal successful!
                    </div>
                  )}
                  {withdrawHook.isError && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-sm font-semibold text-red-900 mb-1">❌ Withdrawal Failed</p>
                      <p className="text-xs text-red-800">
                        {withdrawHook.error?.message || 'Transaction was rejected or reverted'}
                      </p>
                      {withdrawHook.txHash && (
                        <a
                          href={`${vaultChainId === sepolia.id ? 'https://sepolia.etherscan.io' : 'https://amoy.polygonscan.com'}/tx/${withdrawHook.txHash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-red-600 hover:text-red-700 underline mt-1 inline-block"
                        >
                          View transaction →
                        </a>
                      )}
                    </div>
                  )}
                </form>
              )}

              {/* Borrow Form */}
              {activeTab === 'borrow' && (
                <form onSubmit={handleBorrow} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Amount to Borrow
                    </label>
                    <input
                      type="number"
                      step="0.001"
                      value={borrowAmount}
                      onChange={(e) => setBorrowAmount(e.target.value)}
                      placeholder="0.0"
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-500"
                    />
                    <p className="text-sm text-gray-500 mt-2">
                      Available Credit: {Number(formatEther(vaultData.creditLine || 0n)).toFixed(4)} ETH
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Note: 0.001 ETH gas fee will be added for cross-chain messaging
                    </p>
                  </div>
                  <button
                    type="submit"
                    disabled={!borrowAmount || isBorrowing}
                    className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                  >
                    {isBorrowing ? (
                      <>
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Borrowing...
                      </>
                    ) : (
                      <>
                        <ArrowDownCircle className="h-5 w-5" />
                        Borrow from Vault
                      </>
                    )}
                  </button>
                  {borrowSuccess && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
                      ✓ Borrow successful!
                    </div>
                  )}
                  {borrowHook.isError && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-sm font-semibold text-red-900 mb-1">❌ Borrow Failed</p>
                      <p className="text-xs text-red-800">
                        {borrowHook.error?.message || 'Transaction was rejected or reverted'}
                      </p>
                      {borrowHook.txHash && (
                        <a
                          href={`${vaultChainId === sepolia.id ? 'https://sepolia.etherscan.io' : 'https://amoy.polygonscan.com'}/tx/${borrowHook.txHash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-red-600 hover:text-red-700 underline mt-1 inline-block"
                        >
                          View transaction →
                        </a>
                      )}
                    </div>
                  )}
                </form>
              )}

              {/* Repay Form */}
              {activeTab === 'repay' && (
                <form onSubmit={handleRepay} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Amount to Repay
                    </label>
                    <input
                      type="number"
                      step="0.001"
                      value={repayAmount}
                      onChange={(e) => setRepayAmount(e.target.value)}
                      placeholder="0.0"
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-white placeholder-gray-500"
                    />
                    <p className="text-sm text-gray-500 mt-2">
                      Total Borrowed: {Number(formatEther(vaultData.totalBorrowed || 0n)).toFixed(4)} ETH
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Note: 0.001 ETH gas fee will be added for cross-chain messaging
                    </p>
                  </div>
                  <button
                    type="submit"
                    disabled={!repayAmount || isRepaying}
                    className="w-full px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                  >
                    {isRepaying ? (
                      <>
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Repaying...
                      </>
                    ) : (
                      <>
                        <ArrowUpCircle className="h-5 w-5" />
                        Repay to Vault
                      </>
                    )}
                  </button>
                  {repaySuccess && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
                      ✓ Repayment successful!
                    </div>
                  )}
                  {repayHook.isError && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-sm font-semibold text-red-900 mb-1">❌ Repayment Failed</p>
                      <p className="text-xs text-red-800">
                        {repayHook.error?.message || 'Transaction was rejected or reverted'}
                      </p>
                      {repayHook.txHash && (
                        <a
                          href={`${vaultChainId === sepolia.id ? 'https://sepolia.etherscan.io' : 'https://amoy.polygonscan.com'}/tx/${repayHook.txHash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-red-600 hover:text-red-700 underline mt-1 inline-block"
                        >
                          View transaction →
                        </a>
                      )}
                    </div>
                  )}
                </form>
              )}
            </div>
          </FadeIn>

          {/* Info Card */}
          <FadeIn delay={0.5}>
            <div className="glass-panel rounded-xl p-6">
              <h2 className="text-xl font-bold text-white mb-4">How It Works</h2>
              <div className="space-y-4 text-sm text-gray-400">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                    1
                  </span>
                  <p>
                    <strong>Deposit Collateral:</strong> Add funds to the vault on either Sepolia or Amoy.
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                    2
                  </span>
                  <p>
                    <strong>Cross-Chain Sync:</strong> Use the "Cross-Chain Vault Sync" page to sync your balance across chains via Chainlink CCIP.
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                    3
                  </span>
                  <p>
                    <strong>Track Balances:</strong> View your collateral on each chain and total collateral aggregated across all chains.
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                    4
                  </span>
                  <p>
                    <strong>Withdraw:</strong> Withdraw your collateral from the vault back to your wallet on the current chain.
                  </p>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-white/10">
                <h3 className="font-semibold text-white mb-2">Important Notes</h3>
                <ul className="space-y-2 text-sm text-gray-400">
                  <li className="flex items-start gap-2">
                    <span className="text-blue-600">•</span>
                    Funds are tracked in the vault's internal accounting, not in your wallet's native balance.
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-600">•</span>
                    Cross-chain syncs take 2-20 minutes via Chainlink CCIP.
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-600">•</span>
                    You can deposit/withdraw on the chain you're currently connected to.
                  </li>
                </ul>
              </div>
            </div>
          </FadeIn>
        </div>

        {/* Liquidity Pool Section */}
        <FadeIn delay={0.6}>
          <div className="mt-8">
            <LiquidityPoolCard
              chainId={vaultChainId}
              chainName={CHAIN_INFO[vaultChainId].name}
            />
          </div>
        </FadeIn>
      </div>
    </PageTransition>
  );
}
