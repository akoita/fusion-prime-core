import { useAccount } from 'wagmi';
import { formatEther } from 'viem';
import { sepolia } from 'wagmi/chains';
import { polygonAmoy } from '@/config/chains';
import { useMultiChainVaultData } from '@/hooks/contracts/useCrossChainVault';
import { AlertCircle, Loader2, PieChart, TrendingUp, TrendingDown, Activity } from 'lucide-react';

export default function CollateralSnapshot() {
  const { address, isConnected } = useAccount();
  const vaultData = useMultiChainVaultData(address);

  if (!isConnected) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-yellow-600 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Wallet Not Connected</h2>
          <p className="text-gray-600">
            Please connect your wallet to view your collateral snapshot.
          </p>
        </div>
      </div>
    );
  }

  // Calculate totals across all chains
  const getTotalCollateral = () => {
    const sepoliaCollateral = vaultData.sepolia.totalCollateral
      ? parseFloat(formatEther(vaultData.sepolia.totalCollateral))
      : 0;
    const amoyCollateral = vaultData.polygonAmoy.totalCollateral
      ? parseFloat(formatEther(vaultData.polygonAmoy.totalCollateral))
      : 0;
    return sepoliaCollateral + amoyCollateral;
  };

  const getTotalBorrowed = () => {
    const sepoliaBorrowed = vaultData.sepolia.totalBorrowed
      ? parseFloat(formatEther(vaultData.sepolia.totalBorrowed))
      : 0;
    const amoyBorrowed = vaultData.polygonAmoy.totalBorrowed
      ? parseFloat(formatEther(vaultData.polygonAmoy.totalBorrowed))
      : 0;
    return sepoliaBorrowed + amoyBorrowed;
  };

  const getTotalCreditLine = () => {
    const sepoliaCreditLine = vaultData.sepolia.creditLine
      ? parseFloat(formatEther(vaultData.sepolia.creditLine))
      : 0;
    const amoyCreditLine = vaultData.polygonAmoy.creditLine
      ? parseFloat(formatEther(vaultData.polygonAmoy.creditLine))
      : 0;
    return sepoliaCreditLine + amoyCreditLine;
  };

  const totalCollateral = getTotalCollateral();
  const totalBorrowed = getTotalBorrowed();
  const totalCreditLine = getTotalCreditLine();

  const sepoliaCollateral = vaultData.sepolia.totalCollateral
    ? parseFloat(formatEther(vaultData.sepolia.totalCollateral))
    : 0;
  const amoyCollateral = vaultData.polygonAmoy.totalCollateral
    ? parseFloat(formatEther(vaultData.polygonAmoy.totalCollateral))
    : 0;

  // Calculate percentages for visual representation
  const sepoliaPercentage =
    totalCollateral > 0 ? (sepoliaCollateral / totalCollateral) * 100 : 0;
  const amoyPercentage = totalCollateral > 0 ? (amoyCollateral / totalCollateral) * 100 : 0;

  // Calculate health factor (simple version: collateral / borrowed)
  const healthFactor =
    totalBorrowed > 0 ? ((totalCollateral / totalBorrowed) * 100).toFixed(2) : 'N/A';

  // Calculate utilization rate (borrowed / credit line)
  const utilizationRate =
    totalCreditLine > 0 ? ((totalBorrowed / totalCreditLine) * 100).toFixed(2) : '0.00';

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Collateral Snapshot</h1>
        <p className="text-gray-600">
          Real-time view of your cross-chain collateral positions and risk metrics.
        </p>
      </div>

      {/* Overall Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Total Collateral</h3>
            <TrendingUp className="h-5 w-5 text-green-600" />
          </div>
          {vaultData.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">
              {totalCollateral.toFixed(4)}
            </p>
          )}
          <p className="text-xs text-gray-500 mt-1">Across all chains</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Total Borrowed</h3>
            <TrendingDown className="h-5 w-5 text-orange-600" />
          </div>
          {vaultData.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">
              {totalBorrowed.toFixed(4)}
            </p>
          )}
          <p className="text-xs text-gray-500 mt-1">Across all chains</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Health Factor</h3>
            <Activity className="h-5 w-5 text-blue-600" />
          </div>
          {vaultData.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          ) : (
            <p
              className={`text-2xl font-bold ${
                healthFactor === 'N/A'
                  ? 'text-gray-400'
                  : parseFloat(healthFactor) >= 150
                  ? 'text-green-600'
                  : parseFloat(healthFactor) >= 120
                  ? 'text-yellow-600'
                  : 'text-red-600'
              }`}
            >
              {healthFactor}{healthFactor !== 'N/A' && '%'}
            </p>
          )}
          <p className="text-xs text-gray-500 mt-1">Collateral / Borrowed</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Utilization</h3>
            <PieChart className="h-5 w-5 text-purple-600" />
          </div>
          {vaultData.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">{utilizationRate}%</p>
          )}
          <p className="text-xs text-gray-500 mt-1">Borrowed / Credit Line</p>
        </div>
      </div>

      {/* Collateral Distribution */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Collateral Distribution</h2>

        {vaultData.isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : totalCollateral === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <p className="text-gray-600">
              No collateral deposited yet. Start by depositing to your vault.
            </p>
          </div>
        ) : (
          <>
            {/* Visual Bar */}
            <div className="mb-6">
              <div className="flex h-8 rounded-lg overflow-hidden">
                {sepoliaPercentage > 0 && (
                  <div
                    style={{ width: `${sepoliaPercentage}%` }}
                    className="bg-blue-600 flex items-center justify-center text-white text-xs font-semibold"
                  >
                    {sepoliaPercentage.toFixed(1)}%
                  </div>
                )}
                {amoyPercentage > 0 && (
                  <div
                    style={{ width: `${amoyPercentage}%` }}
                    className="bg-purple-600 flex items-center justify-center text-white text-xs font-semibold"
                  >
                    {amoyPercentage.toFixed(1)}%
                  </div>
                )}
              </div>
            </div>

            {/* Chain Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Sepolia */}
              <div className="border-l-4 border-blue-600 pl-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-gray-900">Ethereum Sepolia</h3>
                  <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">
                    {sepoliaPercentage.toFixed(1)}%
                  </span>
                </div>
                <div className="space-y-3">
                  <div className="bg-gray-50 rounded p-3">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-sm text-gray-600">Collateral</span>
                      <span className="text-sm font-semibold text-gray-900">
                        {sepoliaCollateral.toFixed(4)} ETH
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{
                          width: `${
                            totalCollateral > 0
                              ? (sepoliaCollateral / totalCollateral) * 100
                              : 0
                          }%`,
                        }}
                      ></div>
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Borrowed:</span>
                      <span className="font-semibold text-gray-900">
                        {vaultData.sepolia.totalBorrowed
                          ? parseFloat(formatEther(vaultData.sepolia.totalBorrowed)).toFixed(4)
                          : '0.0000'}{' '}
                        ETH
                      </span>
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Available Credit:</span>
                      <span className="font-semibold text-gray-900">
                        {vaultData.sepolia.creditLine
                          ? parseFloat(formatEther(vaultData.sepolia.creditLine)).toFixed(4)
                          : '0.0000'}{' '}
                        ETH
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Polygon Amoy */}
              <div className="border-l-4 border-purple-600 pl-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-gray-900">Polygon Amoy</h3>
                  <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs font-semibold rounded-full">
                    {amoyPercentage.toFixed(1)}%
                  </span>
                </div>
                <div className="space-y-3">
                  <div className="bg-gray-50 rounded p-3">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-sm text-gray-600">Collateral</span>
                      <span className="text-sm font-semibold text-gray-900">
                        {amoyCollateral.toFixed(4)} MATIC
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-purple-600 h-2 rounded-full"
                        style={{
                          width: `${
                            totalCollateral > 0 ? (amoyCollateral / totalCollateral) * 100 : 0
                          }%`,
                        }}
                      ></div>
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Borrowed:</span>
                      <span className="font-semibold text-gray-900">
                        {vaultData.polygonAmoy.totalBorrowed
                          ? parseFloat(formatEther(vaultData.polygonAmoy.totalBorrowed)).toFixed(4)
                          : '0.0000'}{' '}
                        MATIC
                      </span>
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Available Credit:</span>
                      <span className="font-semibold text-gray-900">
                        {vaultData.polygonAmoy.creditLine
                          ? parseFloat(formatEther(vaultData.polygonAmoy.creditLine)).toFixed(4)
                          : '0.0000'}{' '}
                        MATIC
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Risk Indicators */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Risk Indicators</h2>

        <div className="space-y-4">
          {/* Health Factor Explanation */}
          <div
            className={`p-4 rounded-lg ${
              healthFactor === 'N/A'
                ? 'bg-gray-50 border border-gray-200'
                : parseFloat(healthFactor) >= 150
                ? 'bg-green-50 border border-green-200'
                : parseFloat(healthFactor) >= 120
                ? 'bg-yellow-50 border border-yellow-200'
                : 'bg-red-50 border border-red-200'
            }`}
          >
            <h3 className="font-semibold text-gray-900 mb-2">
              Health Factor: {healthFactor}{healthFactor !== 'N/A' && '%'}
            </h3>
            <p className="text-sm text-gray-700">
              {healthFactor === 'N/A' && 'No active borrowing. Your collateral is safe.'}
              {parseFloat(healthFactor) >= 150 &&
                'Excellent health! Your position is well-collateralized.'}
              {parseFloat(healthFactor) >= 120 &&
                parseFloat(healthFactor) < 150 &&
                'Good health. Consider maintaining this ratio or adding more collateral.'}
              {parseFloat(healthFactor) < 120 &&
                healthFactor !== 'N/A' &&
                'Warning: Low health factor. Add more collateral to avoid liquidation risk.'}
            </p>
          </div>

          {/* Utilization Rate Explanation */}
          <div
            className={`p-4 rounded-lg ${
              parseFloat(utilizationRate) < 50
                ? 'bg-green-50 border border-green-200'
                : parseFloat(utilizationRate) < 80
                ? 'bg-yellow-50 border border-yellow-200'
                : 'bg-red-50 border border-red-200'
            }`}
          >
            <h3 className="font-semibold text-gray-900 mb-2">
              Utilization Rate: {utilizationRate}%
            </h3>
            <p className="text-sm text-gray-700">
              {parseFloat(utilizationRate) < 50 &&
                'Low utilization. You have plenty of credit available for borrowing.'}
              {parseFloat(utilizationRate) >= 50 &&
                parseFloat(utilizationRate) < 80 &&
                'Moderate utilization. You still have credit available but approaching limits.'}
              {parseFloat(utilizationRate) >= 80 &&
                'High utilization. Consider repaying some debt or adding collateral to free up credit.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
