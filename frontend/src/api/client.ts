/**
 * API client for OpenEnergyData backend
 */

import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Serialize arrays as repeated params (countries=A&countries=B) for FastAPI compatibility
  paramsSerializer: (params) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach(v => searchParams.append(key, v));
      } else if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });
    return searchParams.toString();
  },
});

// Response interceptor for centralized error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Unknown error';
    console.error('[API Error]', {
      url: error.config?.url,
      status: error.response?.status,
      message,
    });
    return Promise.reject(error);
  }
);

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

// Data Quality types
export interface DatasetQuality {
  dataset: string;
  available: boolean;
  record_count: number;
  completeness: number;
  quality_level: string;
  issues: string[];
  metrics: Record<string, any>;
}

export interface CountryQuality {
  country: string;
  iso_code?: string;
  latitude?: number;
  longitude?: number;
  overall_score: number;
  quality_level: string;
  datasets: Record<string, DatasetQuality>;
  summary: string;
}

export interface RegionQualitySummary {
  total_countries: number;
  by_quality_level: Record<string, number>;
  average_score: number;
  datasets_coverage: Record<string, { countries_with_data: number; coverage_pct: number }>;
}

export interface RegionQualityResponse {
  region: string;
  summary: RegionQualitySummary;
  countries: CountryQuality[];
}

export interface QualitySummaryResponse {
  region: string;
  total_countries: number;
  average_score: number;
  by_quality_level: Record<string, number>;
  datasets_coverage: Record<string, { countries_with_data: number; coverage_pct: number }>;
  countries_by_level: Record<string, Array<{ country: string; score: number }>>;
}

// Lightweight availability types
export interface DatasetAvailability {
  available: boolean;
  source: string;
  source_exists: boolean;
}

export interface CountryAvailability {
  country: string;
  datasets: Record<string, DatasetAvailability>;
}

export interface RegionAvailabilityResponse {
  region: string;
  total_countries: number;
  data_sources: Record<string, boolean>;
  countries: CountryAvailability[];
}

// API functions
export const regionsApi = {
  list: () => api.get<{ regions: Region[] }>('/api/regions').then(r => r.data.regions),
  get: (id: string) => api.get<Region>(`/api/regions/${id}`).then(r => r.data),
  getCountries: (id: string) => api.get<string[]>(`/api/regions/${id}/countries`).then(r => r.data),
};

export const powerPlantsApi = {
  list: (params: { region: string; countries?: string[]; technology?: string; status?: string; source?: string }) =>
    api.get<PowerPlantsResponse>('/api/power-plants', { params }).then(r => r.data),

  summary: (params: { region: string; countries?: string[]; status?: string; source?: string }) =>
    api.get<{ count: number; total_capacity_mw: number; by_technology: TechnologySummary[] }>(
      '/api/power-plants/summary',
      { params }
    ).then(r => r.data),

  geojson: (params: { region: string; countries?: string[]; technology?: string; source?: string }) =>
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

export interface RenewablesNinjaResponse {
  location: { lat: number; lon: number };
  technology: string;
  year: number;
  count: number;
  mean_cf: number;
  data: Array<{
    zone: string;
    month: number;
    day: number;
    hour: number;
    capacity_factor: number;
  }>;
}

export interface CountryCentroid {
  lat: number;
  lon: number;
}

export const renewablesApi = {
  list: (params: { region: string; technology: string; countries?: string[]; year?: number; limit?: number }) =>
    api.get('/api/renewables', { params }).then(r => r.data),

  daily: (params: { region: string; technology: string; countries?: string[]; year: number; month: number; day: number }) =>
    api.get('/api/renewables/daily', { params }).then(r => r.data),

  fetchFromNinja: (params: { lat: number; lon: number; year: number; technology: string; api_key: string }) =>
    api.get<RenewablesNinjaResponse>('/api/renewables/fetch', { params }).then(r => r.data),

  getCountryCentroid: (country: string) =>
    api.get<CountryCentroid>('/api/regions/country-centroid', { params: { country } }).then(r => r.data),
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

export const dataQualityApi = {
  country: (params: { region: string; country: string }) =>
    api.get<CountryQuality>('/api/data-quality/country', { params }).then(r => r.data),

  region: (params: { region: string }) =>
    api.get<RegionQualityResponse>('/api/data-quality/region', { params }).then(r => r.data),

  regionGeojson: (params: { region: string }) =>
    api.get('/api/data-quality/region/geojson', { params }).then(r => r.data),

  summary: (params: { region: string }) =>
    api.get<QualitySummaryResponse>('/api/data-quality/summary', { params }).then(r => r.data),

  availability: (params: { region: string }) =>
    api.get<RegionAvailabilityResponse>('/api/data-quality/availability', { params }).then(r => r.data),
};
