/**
 * Verification Badge Component
 * Displays verification status for claims
 */

import { CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';

interface VerificationBadgeProps {
  verified: boolean;
  loading?: boolean;
  label: string;
  required?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function VerificationBadge({
  verified,
  loading = false,
  label,
  required = false,
  size = 'md',
}: VerificationBadgeProps) {
  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2',
  };

  const iconSizes = {
    sm: 14,
    md: 16,
    lg: 20,
  };

  const iconSize = iconSizes[size];

  if (loading) {
    return (
      <div
        className={`inline-flex items-center gap-2 rounded-full bg-gray-100 text-gray-600 ${sizeClasses[size]}`}
      >
        <Clock size={iconSize} className="animate-spin" />
        <span className="font-medium">{label}</span>
        {required && <span className="text-xs opacity-70">(Required)</span>}
      </div>
    );
  }

  if (verified) {
    return (
      <div
        className={`inline-flex items-center gap-2 rounded-full bg-green-100 text-green-700 ${sizeClasses[size]}`}
      >
        <CheckCircle size={iconSize} />
        <span className="font-medium">{label}</span>
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full ${
        required ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
      } ${sizeClasses[size]}`}
    >
      {required ? <AlertCircle size={iconSize} /> : <XCircle size={iconSize} />}
      <span className="font-medium">{label}</span>
      {required && <span className="text-xs opacity-70">(Required)</span>}
    </div>
  );
}
