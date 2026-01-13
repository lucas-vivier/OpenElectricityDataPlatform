/**
 * API client for OpenEnergyData backend
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Region {
  id: string;
  name: string;
  countries: string[];
  bbox?: number[];
  default_zoom?: number;
}

export interface PowerPlant {
  name: string;
  technology: string;
  capacity_mw: number;
  status: string;
  country: string;
  latitude?: number;
  longitude?: number;
}

export interface PowerPlantsResponse {
  count: number;
  total_capacity_mw: number;
  plants: PowerPlant[];
}

export interface TechnologySummary {
  technology: string;
  total_capacity_mw: number;
}

export interface LoadProfileValue {
  zone: string;
  month: number;
  day: number;
  hour: number;
  value: number;
}

export interface HydropowerPlant {
  name: string;
  technology: string;
  capacity_mw?: number;
  status: string;
  country: string;
  latitude?: number;
  longitude?: number;
  river_name?: string;
  river_basin?: string;
  reservoir_size_mcm?: number;
  start_year?: number;
}

export interface HydropowerResponse {
  count: number;
  total_capacity_mw: number;
  plants: HydropowerPlant[];
}

export interface ResourceSite {
  country: string;
  msr_id?: string;
  latitude?: number;
  longitude?: number;
  capacity_mw?: number;
  capacity_factor?: number;
  lcoe?: number;
  technology: string;
}

export interface ResourcePotentialResponse {
  count: number;
  total_capacity_mw: number;
  avg_capacity_factor?: number;
  sites: ResourceSite[];
}

export interface CountryPotential {
  country: string;
  total_capacity_mw: number;
  site_count: number;
  avg_capacity_factor?: number;
  avg_lcoe?: number;
}

export interface LoadProfilesResponse {
  zone: string;
  year: number;
  count: number;
  data: LoadProfileValue[];
}

export interface CountryStats {
  country: string;
  year: number;
  population?: number;
  gdp?: number;
  electricity_demand?: number;
  electricity_generation?: number;
  renewables_share_elec?: number;
  fossil_share_elec?: number;
  carbon_intensity_elec?: number;
}

export interface SocioEconomicResponse {
  count: number;
  data: CountryStats[];
}

export interface TimeSeriesPoint {
  year: number;
  values: Record<string, number | null>;
}

export interface TimeSeriesResponse {
  variable: string;
  countries: string[];
  data: TimeSeriesPoint[];
}

// API functions
export const regionsApi = {
  list: () => api.get<{ regions: Region[] }>('/api/regions').then(r => r.data.regions),
  get: (id: string) => api.get<Region>(`/api/regions/${id}`).then(r => r.data),
  getCountries: (id: string) => api.get<string[]>(`/api/regions/${id}/countries`).then(r => r.data),
};

export const powerPlantsApi = {
  list: (params: { region: string; countries?: string[]; technology?: string; status?: string }) =>
    api.get<PowerPlantsResponse>('/api/power-plants', { params }).then(r => r.data),

  summary: (params: { region: string; countries?: string[]; status?: string }) =>
    api.get<{ count: number; total_capacity_mw: number; by_technology: TechnologySummary[] }>(
      '/api/power-plants/summary',
      { params }
    ).then(r => r.data),

  geojson: (params: { region: string; countries?: string[]; technology?: string }) =>
    api.get('/api/power-plants/geojson', { params }).then(r => r.data),
};

export const loadProfilesApi = {
  list: (params: { region: string; countries?: string[]; year?: number; month?: number; limit?: number }) =>
    api.get<LoadProfilesResponse>('/api/load-profiles', { params }).then(r => r.data),

  summary: (params: { region: string; countries?: string[]; year?: number }) =>
    api.get('/api/load-profiles/summary', { params }).then(r => r.data),

  daily: (params: { region: string; countries?: string[]; year: number; month: number; day: number }) =>
    api.get('/api/load-profiles/daily', { params }).then(r => r.data),

  monthlyAverage: (params: { region: string; countries?: string[]; year?: number }) =>
    api.get('/api/load-profiles/monthly-average', { params }).then(r => r.data),
};

export const renewablesApi = {
  list: (params: { region: string; technology: string; countries?: string[]; year?: number; limit?: number }) =>
    api.get('/api/renewables', { params }).then(r => r.data),

  daily: (params: { region: string; technology: string; countries?: string[]; year: number; month: number; day: number }) =>
    api.get('/api/renewables/daily', { params }).then(r => r.data),
};

export const treatmentsApi = {
  representativeDays: (params: {
    region: string;
    countries?: string[];
    year?: number;
    n_days?: number;
    n_clusters?: number;
    include_re?: boolean;
    re_technology?: string;
  }) => api.post('/api/treatments/representative-days', null, { params }).then(r => r.data),

  seasonalConversion: (params: {
    region: string;
    countries?: string[];
    year?: number;
    data_type?: string;
  }) => api.post('/api/treatments/seasonal-conversion', null, { params }).then(r => r.data),
};

export const hydropowerApi = {
  list: (params: { region: string; countries?: string[]; source?: string; status?: string; min_capacity?: number }) =>
    api.get<HydropowerResponse>('/api/hydropower', { params }).then(r => r.data),

  summary: (params: { region: string; countries?: string[]; source?: string }) =>
    api.get('/api/hydropower/summary', { params }).then(r => r.data),

  climateScenarios: (params: { region: string; countries?: string[]; scenario?: string }) =>
    api.get('/api/hydropower/climate-scenarios', { params }).then(r => r.data),

  geojson: (params: { region: string; countries?: string[]; source?: string }) =>
    api.get('/api/hydropower/geojson', { params }).then(r => r.data),
};

export const resourcePotentialApi = {
  solar: (params: { region: string; countries?: string[]; min_capacity_factor?: number; max_lcoe?: number; limit?: number }) =>
    api.get<ResourcePotentialResponse>('/api/resource-potential/solar', { params }).then(r => r.data),

  wind: (params: { region: string; countries?: string[]; min_capacity_factor?: number; max_lcoe?: number; limit?: number }) =>
    api.get<ResourcePotentialResponse>('/api/resource-potential/wind', { params }).then(r => r.data),

  solarSummary: (params: { region: string; countries?: string[] }) =>
    api.get('/api/resource-potential/solar/summary', { params }).then(r => r.data),

  windSummary: (params: { region: string; countries?: string[] }) =>
    api.get('/api/resource-potential/wind/summary', { params }).then(r => r.data),

  solarGeojson: (params: { region: string; countries?: string[]; limit?: number }) =>
    api.get('/api/resource-potential/solar/geojson', { params }).then(r => r.data),

  windGeojson: (params: { region: string; countries?: string[]; limit?: number }) =>
    api.get('/api/resource-potential/wind/geojson', { params }).then(r => r.data),

  profiles: (technology: string, params: { region: string; zones?: string[] }) =>
    api.get(`/api/resource-potential/profiles/${technology}`, { params }).then(r => r.data),
};

export const exportsApi = {
  powerPlantsCsv: (params: { region: string; countries?: string[] }) =>
    `${API_BASE_URL}/api/exports/power-plants/csv?${new URLSearchParams(params as any)}`,

  powerPlantsGeojson: (params: { region: string; countries?: string[] }) =>
    `${API_BASE_URL}/api/exports/power-plants/geojson?${new URLSearchParams(params as any)}`,

  loadProfilesCsv: (params: { region: string; countries?: string[]; year?: number; format_type?: string }) =>
    `${API_BASE_URL}/api/exports/load-profiles/csv?${new URLSearchParams(params as any)}`,

  reProfilesCsv: (params: { region: string; technology: string; countries?: string[]; year?: number }) =>
    `${API_BASE_URL}/api/exports/re-profiles/csv?${new URLSearchParams(params as any)}`,
};

export const socioeconomicApi = {
  summary: (params: { countries?: string[]; year?: number }) =>
    api.get<SocioEconomicResponse>('/api/socioeconomic/summary', { params }).then(r => r.data),

  countries: () =>
    api.get<{ count: number; countries: string[] }>('/api/socioeconomic/countries').then(r => r.data),

  timeseries: (variable: string, params: { countries: string[]; start_year?: number; end_year?: number }) =>
    api.get<TimeSeriesResponse>(`/api/socioeconomic/timeseries/${variable}`, { params }).then(r => r.data),

  electricity: (params: { countries?: string[]; start_year?: number; end_year?: number }) =>
    api.get('/api/socioeconomic/electricity', { params }).then(r => r.data),

  renewablesShare: (params: { countries?: string[]; year?: number }) =>
    api.get('/api/socioeconomic/renewables-share', { params }).then(r => r.data),
};
