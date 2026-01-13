/**
 * Application constants
 */

// Default selections
export const DEFAULT_REGION = 'sapp';
export const DEFAULT_LOAD_YEAR = 2020;
export const DEFAULT_NINJA_YEAR = 2019;
export const DEFAULT_POWER_PLANT_SOURCE = 'gem';

// Year ranges
export const NINJA_YEAR_RANGE = { min: 2000, max: 2023 };
export const LOAD_YEAR_RANGE = { min: 2015, max: 2025 };

// Power plant sources
export const POWER_PLANT_SOURCES = [
  { id: 'gem', name: 'Global Energy Monitor', description: 'Global Integrated Power (April 2025)' },
  { id: 'gppd', name: 'Global Power Plant Database', description: 'World Resources Institute' },
] as const;

// Technology colors for visualization
export const TECH_COLORS: Record<string, string> = {
  'Coal': '#4a4a4a',
  'Gas': '#f97316',
  'Oil': '#854d0e',
  'Nuclear': '#7c3aed',
  'Hydro': '#0ea5e9',
  'Solar': '#eab308',
  'Wind': '#22c55e',
  'Biomass': '#84cc16',
  'Geothermal': '#dc2626',
  'Battery': '#06b6d4',
  'Other': '#9ca3af',
} as const;

// Map defaults
export const DEFAULT_MAP_CENTER: [number, number] = [-29, 24];
export const DEFAULT_MAP_ZOOM = 5;

// Chart colors (for multi-line charts)
export const CHART_COLORS = [
  '#2563eb', '#dc2626', '#22c55e', '#f97316', '#7c3aed',
  '#0ea5e9', '#eab308', '#ec4899', '#14b8a6', '#8b5cf6',
  '#f43f5e', '#06b6d4'
] as const;
