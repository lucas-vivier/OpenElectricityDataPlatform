/**
 * Safe formatting utilities for data display
 */

/**
 * Safe number formatting with fallback
 */
export const formatNumber = (value?: number | null, fallback = 'N/A'): string => {
  if (value === undefined || value === null || isNaN(value)) {
    return fallback;
  }
  return value.toLocaleString();
};

/**
 * Safe capacity formatting (MW/GW)
 */
export const formatCapacity = (mw?: number | null): string => {
  if (mw === undefined || mw === null || isNaN(mw)) return 'N/A';
  if (mw >= 1000) return `${(mw / 1000).toFixed(1)} GW`;
  return `${mw.toLocaleString()} MW`;
};

/**
 * Safe array access
 */
export const safeArray = <T,>(arr?: T[] | null): T[] => arr ?? [];

/**
 * Safe percentage formatting
 */
export const formatPercent = (value?: number | null, decimals = 1): string => {
  if (value === undefined || value === null || isNaN(value)) return 'N/A';
  return `${(value * 100).toFixed(decimals)}%`;
};
