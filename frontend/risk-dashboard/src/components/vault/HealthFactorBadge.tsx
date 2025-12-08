import { formatHealthFactor, getHealthFactorStatus } from '@/hooks/contracts/useVaultV24';

interface HealthFactorBadgeProps {
  healthFactor: bigint;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function HealthFactorBadge({
  healthFactor,
  showLabel = true,
  size = 'md'
}: HealthFactorBadgeProps) {
  const { status, color, label } = getHealthFactorStatus(healthFactor);
  const formatted = formatHealthFactor(healthFactor);

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2',
  };

  const colorClasses = {
    green: 'bg-green-100 text-green-800 border-green-300',
    blue: 'bg-blue-100 text-blue-800 border-blue-300',
    yellow: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    orange: 'bg-orange-100 text-orange-800 border-orange-300',
    red: 'bg-red-100 text-red-800 border-red-300',
  };

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${sizeClasses[size]} ${colorClasses[color]}`}
      >
        <span className={`h-2 w-2 rounded-full ${
          color === 'green' ? 'bg-green-500' :
          color === 'blue' ? 'bg-blue-500' :
          color === 'yellow' ? 'bg-yellow-500' :
          color === 'orange' ? 'bg-orange-500' :
          'bg-red-500'
        }`} />
        {showLabel && <span>{label}</span>}
        <span className="font-semibold">{formatted}</span>
      </span>
    </div>
  );
}

interface HealthFactorProgressProps {
  healthFactor: bigint;
  showPercentage?: boolean;
}

export function HealthFactorProgress({
  healthFactor,
  showPercentage = true
}: HealthFactorProgressProps) {
  const { status, color } = getHealthFactorStatus(healthFactor);
  const formatted = formatHealthFactor(healthFactor);

  // Calculate progress bar width (cap at 200% for display)
  const maxUint256 = BigInt('115792089237316195423570985008687907853269984665640564039457584007913129639935');
  let progressPercent = 0;

  if (healthFactor > 0n && healthFactor !== maxUint256) {
    const hfDecimal = Number(healthFactor) / Number(1e18);
    progressPercent = Math.min((hfDecimal / 2.0) * 100, 100);
  } else if (healthFactor === maxUint256) {
    progressPercent = 100;
  }

  const progressColorClasses = {
    green: 'bg-green-500',
    blue: 'bg-blue-500',
    yellow: 'bg-yellow-500',
    orange: 'bg-orange-500',
    red: 'bg-red-500',
  };

  return (
    <div className="w-full">
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium text-gray-700">Health Factor</span>
        {showPercentage && (
          <span className="text-sm font-medium text-gray-700">{formatted}</span>
        )}
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full ${progressColorClasses[color]} transition-all duration-300`}
          style={{ width: `${progressPercent}%` }}
        />
      </div>
      <div className="flex justify-between mt-1 text-xs text-gray-500">
        <span>Liquidatable (&lt;100%)</span>
        <span>Safe (≥200%)</span>
      </div>
    </div>
  );
}

interface HealthFactorCardProps {
  healthFactor: bigint;
  collateralUSD: bigint;
  borrowedUSD: bigint;
}

export function HealthFactorCard({
  healthFactor,
  collateralUSD,
  borrowedUSD
}: HealthFactorCardProps) {
  const { status, label } = getHealthFactorStatus(healthFactor);
  const formatted = formatHealthFactor(healthFactor);

  const collateralValue = Number(collateralUSD) / 1e18;
  const borrowedValue = Number(borrowedUSD) / 1e18;
  const liquidationValue = collateralValue * 0.8;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Health Factor</h3>

      <div className="mb-4">
        <HealthFactorBadge healthFactor={healthFactor} size="lg" />
      </div>

      <HealthFactorProgress healthFactor={healthFactor} />

      <div className="mt-6 space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Total Collateral:</span>
          <span className="font-medium">${collateralValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Total Borrowed:</span>
          <span className="font-medium">${borrowedValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div className="flex justify-between text-sm border-t pt-3">
          <span className="text-gray-600">Liquidation Threshold (80%):</span>
          <span className="font-medium">${liquidationValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
      </div>

      {status === 'warning' || status === 'danger' && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-sm text-yellow-800">
            <strong>Warning:</strong> Your health factor is approaching the liquidation threshold.
            Consider adding more collateral or repaying some debt.
          </p>
        </div>
      )}

      {status === 'liquidatable' && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-800">
            <strong>Danger:</strong> Your position can be liquidated! Add collateral or repay debt immediately.
          </p>
        </div>
      )}
    </div>
  );
}
