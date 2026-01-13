import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell, Legend, AreaChart, Area } from 'recharts';
import { Loader2, Download, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { regionsApi, powerPlantsApi, loadProfilesApi, hydropowerApi, resourcePotentialApi, socioeconomicApi, renewablesApi, dataQualityApi, type RenewablesNinjaResponse } from '../api/client';
import SourceInfo, { DATA_SOURCES } from '../components/SourceInfo';
import MapLayerControl, { DEFAULT_LAYERS, type MapLayer } from '../components/MapLayerControl';
import TimeSelector from '../components/TimeSelector';
import { useLoading } from '../contexts/LoadingContext';
import { useApiKeys } from '../contexts/ApiKeyContext';
import 'leaflet/dist/leaflet.css';

// Technology colors for visualization
const TECH_COLORS: Record<string, string> = {
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
};

const getTechColor = (tech: string): string => {
  const normalized = tech?.toLowerCase() || '';
  for (const [key, color] of Object.entries(TECH_COLORS)) {
    if (normalized.includes(key.toLowerCase())) return color;
  }
  return TECH_COLORS['Other'];
};

type TabType = 'map' | 'plants' | 'hydropower' | 'renewables' | 'socioeconomic' | 'load';

// Available power plant data sources
const POWER_PLANT_SOURCES = [
  { id: 'gem', name: 'Global Energy Monitor', description: 'Global Integrated Power (April 2025)' },
  { id: 'gppd', name: 'Global Power Plant Database', description: 'World Resources Institute' },
];

export default function DataExplorer() {
  const [selectedRegion, setSelectedRegion] = useState('sapp');
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('map');
  const [enabledLayers, setEnabledLayers] = useState<string[]>(['power_plants']);
  const [loadYear, setLoadYear] = useState(2020);
  const [loadMonths, setLoadMonths] = useState<number[]>([]);  // Empty = all months
  const [powerPlantSources, setPowerPlantSources] = useState<string[]>(['gem']);

  // Renewables.ninja state
  const [ninjaYear, setNinjaYear] = useState(2019);
  const [ninjaTechnology, setNinjaTechnology] = useState<'solar' | 'wind'>('solar');
  const [ninjaData, setNinjaData] = useState<RenewablesNinjaResponse | null>(null);
  const [ninjaError, setNinjaError] = useState<string | null>(null);

  // Global loading state
  const { startLoading, stopLoading } = useLoading();
  const { getApiKey, hasApiKey } = useApiKeys();

  // Fetch regions
  const { data: regions } = useQuery({
    queryKey: ['regions'],
    queryFn: regionsApi.list,
  });

  // Get countries for current region
  const currentRegion = regions?.find(r => r.id === selectedRegion);
  const regionCountries = currentRegion?.countries || [];
  const countriesParam = selectedCountries.length > 0 ? selectedCountries : undefined;

  // Fetch power plants for each selected source
  const { data: plantsDataGem, isLoading: plantsLoadingGem, isFetching: plantsFetchingGem } = useQuery({
    queryKey: ['power-plants', selectedRegion, selectedCountries, 'gem'],
    queryFn: () => powerPlantsApi.list({ region: selectedRegion, countries: countriesParam, source: 'gem' }),
    enabled: !!selectedRegion && powerPlantSources.includes('gem'),
  });

  const { data: plantsDataGppd, isLoading: plantsLoadingGppd, isFetching: plantsFetchingGppd } = useQuery({
    queryKey: ['power-plants', selectedRegion, selectedCountries, 'gppd'],
    queryFn: () => powerPlantsApi.list({ region: selectedRegion, countries: countriesParam, source: 'gppd' }),
    enabled: !!selectedRegion && powerPlantSources.includes('gppd'),
  });

  // Fetch power plants summary for each source
  const { data: summaryGem } = useQuery({
    queryKey: ['power-plants-summary', selectedRegion, selectedCountries, 'gem'],
    queryFn: () => powerPlantsApi.summary({ region: selectedRegion, countries: countriesParam, source: 'gem' }),
    enabled: !!selectedRegion && powerPlantSources.includes('gem'),
  });

  const { data: summaryGppd } = useQuery({
    queryKey: ['power-plants-summary', selectedRegion, selectedCountries, 'gppd'],
    queryFn: () => powerPlantsApi.summary({ region: selectedRegion, countries: countriesParam, source: 'gppd' }),
    enabled: !!selectedRegion && powerPlantSources.includes('gppd'),
  });

  // Combined data for backward compatibility (use first available source for map/summary)
  const plantsData = plantsDataGem || plantsDataGppd;
  const plantsLoading = plantsLoadingGem || plantsLoadingGppd;
  const summary = summaryGem || summaryGppd;

  // Fetch load profiles (daily average - all months, filtered client-side)
  const { data: loadData } = useQuery({
    queryKey: ['load-monthly', selectedRegion, selectedCountries, loadYear],
    queryFn: () => loadProfilesApi.monthlyAverage({ region: selectedRegion, countries: countriesParam, year: loadYear }),
    enabled: !!selectedRegion,
  });

  // Fetch hydropower data
  const { data: hydroData, isLoading: hydroLoading, isError: hydroError } = useQuery({
    queryKey: ['hydropower', selectedRegion, selectedCountries],
    queryFn: () => hydropowerApi.list({ region: selectedRegion, countries: countriesParam, source: 'both' }),
    enabled: !!selectedRegion && activeTab === 'hydropower',
  });

  // Fetch data availability for countries
  const { data: availabilityData } = useQuery({
    queryKey: ['availability', selectedRegion],
    queryFn: () => dataQualityApi.availability({ region: selectedRegion }),
    enabled: !!selectedRegion,
  });

  // Fetch resource potential data (only when tab is active)
  const { data: solarPotential } = useQuery({
    queryKey: ['solar-potential', selectedRegion, selectedCountries],
    queryFn: () => resourcePotentialApi.solarSummary({ region: selectedRegion, countries: countriesParam }),
    enabled: !!selectedRegion && activeTab === 'renewables',
  });

  const { data: windPotential } = useQuery({
    queryKey: ['wind-potential', selectedRegion, selectedCountries],
    queryFn: () => resourcePotentialApi.windSummary({ region: selectedRegion, countries: countriesParam }),
    enabled: !!selectedRegion && activeTab === 'renewables',
  });

  // Map layer data queries (fetch only when layer is enabled and map tab is active)
  const { data: hydroGeoJson } = useQuery({
    queryKey: ['hydro-geojson', selectedRegion, selectedCountries],
    queryFn: () => hydropowerApi.geojson({ region: selectedRegion, countries: countriesParam }),
    enabled: !!selectedRegion && activeTab === 'map' && enabledLayers.includes('hydropower'),
  });

  const { data: solarGeoJson } = useQuery({
    queryKey: ['solar-geojson', selectedRegion, selectedCountries],
    queryFn: () => resourcePotentialApi.solarGeojson({ region: selectedRegion, countries: countriesParam, limit: 500 }),
    enabled: !!selectedRegion && activeTab === 'map' && enabledLayers.includes('solar_potential'),
  });

  const { data: windGeoJson } = useQuery({
    queryKey: ['wind-geojson', selectedRegion, selectedCountries],
    queryFn: () => resourcePotentialApi.windGeojson({ region: selectedRegion, countries: countriesParam, limit: 500 }),
    enabled: !!selectedRegion && activeTab === 'map' && enabledLayers.includes('wind_potential'),
  });

  // Fetch socioeconomic data (uses region countries)
  const { data: socioData, isLoading: socioLoading } = useQuery({
    queryKey: ['socioeconomic', selectedRegion, selectedCountries],
    queryFn: async () => {
      const countries = selectedCountries.length > 0 ? selectedCountries : regionCountries;
      return socioeconomicApi.summary({ countries });
    },
    enabled: !!selectedRegion && activeTab === 'socioeconomic' && !!regions,
  });

  // Fetch electricity time series for socioeconomic tab
  const { data: electricityTimeSeries } = useQuery({
    queryKey: ['electricity-timeseries', selectedRegion, selectedCountries],
    queryFn: async () => {
      const countries = selectedCountries.length > 0 ? selectedCountries : regionCountries;
      if (countries.length === 0) return null;
      return socioeconomicApi.timeseries('electricity_generation', {
        countries: countries.slice(0, 5),  // Limit to 5 countries for chart clarity
        start_year: 2000
      });
    },
    enabled: !!selectedRegion && activeTab === 'socioeconomic' && !!regions,
  });

  // Track overall loading state for progress bar
  const isAnyFetching = plantsFetchingGem || plantsFetchingGppd;

  useEffect(() => {
    if (isAnyFetching) {
      startLoading('Loading data for ' + selectedRegion + '...');
    } else {
      stopLoading();
    }
  }, [isAnyFetching, selectedRegion, startLoading, stopLoading]);

  // Renewables.ninja fetch mutation
  const ninjaFetchMutation = useMutation({
    mutationFn: async ({ country, year, technology }: { country: string; year: number; technology: 'solar' | 'wind' }) => {
      const apiKey = getApiKey('renewablesNinja');
      if (!apiKey) {
        throw new Error('No Renewables.ninja API key configured. Please add your API key in Settings.');
      }

      // Get country centroid
      const centroid = await renewablesApi.getCountryCentroid(country);

      // Fetch from Renewables.ninja
      return renewablesApi.fetchFromNinja({
        lat: centroid.lat,
        lon: centroid.lon,
        year,
        technology,
        api_key: apiKey,
      });
    },
    onSuccess: (data) => {
      setNinjaData(data);
      setNinjaError(null);
    },
    onError: (error: Error) => {
      setNinjaError(error.message);
      setNinjaData(null);
    },
  });

  // Clear ninja data when country/region changes
  useEffect(() => {
    setNinjaData(null);
    setNinjaError(null);
  }, [selectedRegion, selectedCountries]);

  // Prepare ninja chart data - daily average by hour
  const ninjaChartData = useMemo(() => {
    if (!ninjaData?.data) return [];

    // Group by hour and calculate average
    const hourlyAverages: Record<number, { sum: number; count: number }> = {};
    for (let h = 0; h < 24; h++) {
      hourlyAverages[h] = { sum: 0, count: 0 };
    }

    for (const d of ninjaData.data) {
      hourlyAverages[d.hour].sum += d.capacity_factor;
      hourlyAverages[d.hour].count += 1;
    }

    return Object.entries(hourlyAverages).map(([hour, { sum, count }]) => ({
      hour: parseInt(hour),
      capacity_factor: count > 0 ? sum / count : 0,
    }));
  }, [ninjaData]);

  // Prepare ninja monthly data
  const ninjaMonthlyData = useMemo(() => {
    if (!ninjaData?.data) return [];

    const monthlyAverages: Record<number, { sum: number; count: number }> = {};
    for (let m = 1; m <= 12; m++) {
      monthlyAverages[m] = { sum: 0, count: 0 };
    }

    for (const d of ninjaData.data) {
      monthlyAverages[d.month].sum += d.capacity_factor;
      monthlyAverages[d.month].count += 1;
    }

    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return Object.entries(monthlyAverages).map(([month, { sum, count }]) => ({
      month: monthNames[parseInt(month) - 1],
      capacity_factor: count > 0 ? sum / count : 0,
    }));
  }, [ninjaData]);

  const mapCenter: [number, number] = currentRegion?.bbox
    ? [(currentRegion.bbox[1] + currentRegion.bbox[3]) / 2, (currentRegion.bbox[0] + currentRegion.bbox[2]) / 2]
    : [-29, 24];

  // Prepare chart data for each source
  const techPieDataGem = useMemo(() =>
    summaryGem?.by_technology?.slice(0, 8).map(t => ({
      name: t.technology,
      value: Math.round(t.total_capacity_mw),
      fill: getTechColor(t.technology),
    })) || []
  , [summaryGem]);

  const techPieDataGppd = useMemo(() =>
    summaryGppd?.by_technology?.slice(0, 8).map(t => ({
      name: t.technology,
      value: Math.round(t.total_capacity_mw),
      fill: getTechColor(t.technology),
    })) || []
  , [summaryGppd]);

  // Get countries available in load data
  const loadCountries = useMemo(() => loadData?.countries || [], [loadData]);

  // Compute load chart data with per-country lines
  const loadChartData = useMemo(() => {
    if (!loadData?.profiles_by_country) return [];

    const hours = Array.from({ length: 24 }, (_, i) => i);
    const countries = Object.keys(loadData.profiles_by_country);

    if (countries.length === 0) return [];

    // Determine which months to include
    const monthsToUse = loadMonths.length > 0 && loadMonths.length < 12
      ? loadMonths
      : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];  // All months if empty or all selected

    return hours.map(hour => {
      const dataPoint: Record<string, number> = { hour };

      for (const country of countries) {
        const countryProfiles = loadData.profiles_by_country[country];
        if (!countryProfiles) continue;

        // Average across selected months
        let sum = 0;
        let count = 0;
        for (const m of monthsToUse) {
          const monthData = countryProfiles[m];
          if (monthData?.values?.[hour] !== undefined) {
            sum += monthData.values[hour];
            count++;
          }
        }
        if (count > 0) {
          dataPoint[country] = sum / count;
        }
      }

      return dataPoint;
    });
  }, [loadData, loadMonths]);

  // Map layers configuration
  const mapLayers: MapLayer[] = useMemo(() =>
    DEFAULT_LAYERS.map(layer => ({
      ...layer,
      enabled: enabledLayers.includes(layer.id),
    })),
    [enabledLayers]
  );

  const toggleLayer = (layerId: string) => {
    setEnabledLayers(prev =>
      prev.includes(layerId)
        ? prev.filter(id => id !== layerId)
        : [...prev, layerId]
    );
  };

  // Helper to get availability status for a country
  const getCountryAvailability = (country: string) => {
    const countryData = availabilityData?.countries?.find(c => c.country === country);
    if (!countryData) return { level: 'unknown', datasets: {} };

    const datasets = countryData.datasets || {};
    const availableCount = Object.values(datasets).filter((d: any) => d?.available).length;
    const totalCount = Object.keys(datasets).length;

    let level: 'good' | 'partial' | 'limited' | 'unknown' = 'unknown';
    if (totalCount > 0) {
      const ratio = availableCount / totalCount;
      if (ratio >= 0.6) level = 'good';
      else if (ratio >= 0.3) level = 'partial';
      else level = 'limited';
    }

    return { level, datasets };
  };

  // Get the country to use for Renewables.ninja fetch
  const ninjaCountry = selectedCountries.length > 0 ? selectedCountries[0] : regionCountries[0];

  return (
    <div className="explorer-layout">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="card">
          <h3 className="card-title">1. Select Region</h3>
          <div className="form-group">
            <label className="form-label">Region</label>
            <select
              className="form-select"
              value={selectedRegion}
              onChange={(e) => {
                setSelectedRegion(e.target.value);
                setSelectedCountries([]);
              }}
            >
              {regions?.map(region => (
                <option key={region.id} value={region.id}>
                  {region.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {regionCountries.length > 0 && (
          <div className="card">
            <h3 className="card-title">2. Select Countries</h3>
            <div className="checkbox-group" style={{ maxHeight: 200, overflowY: 'auto' }}>
              <label className="checkbox-label" style={{ fontWeight: 500, borderBottom: '1px solid #e5e7eb', paddingBottom: 8, marginBottom: 4 }}>
                <input
                  type="checkbox"
                  checked={selectedCountries.length === 0}
                  onChange={() => setSelectedCountries([])}
                />
                All Countries ({regionCountries.length})
              </label>
              {regionCountries.map(country => {
                const availability = getCountryAvailability(country);
                const dotColor = availability.level === 'good' ? '#22c55e' :
                                 availability.level === 'partial' ? '#eab308' :
                                 availability.level === 'limited' ? '#9ca3af' : '#d1d5db';
                const datasets = availability.datasets as Record<string, { available: boolean; source?: string }>;

                return (
                  <label key={country} className="checkbox-label country-item" style={{ position: 'relative' }}>
                    <input
                      type="checkbox"
                      checked={selectedCountries.includes(country)}
                      onChange={() => {
                        setSelectedCountries(prev =>
                          prev.includes(country)
                            ? prev.filter(c => c !== country)
                            : [...prev, country]
                        );
                      }}
                    />
                    <span style={{ flex: 1 }}>{country}</span>
                    <span
                      className="availability-dot"
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: dotColor,
                        flexShrink: 0,
                      }}
                    />
                    {availabilityData && (
                      <div className="country-tooltip">
                        <div style={{ fontWeight: 600, marginBottom: 6, borderBottom: '1px solid #e5e7eb', paddingBottom: 4 }}>
                          Data Availability
                        </div>
                        <div style={{ fontSize: 11, lineHeight: 1.6 }}>
                          {Object.entries(datasets).map(([key, val]) => (
                            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                              <span style={{ color: '#6b7280' }}>{key.replace(/_/g, ' ')}</span>
                              <span style={{ color: val?.available ? '#22c55e' : '#9ca3af' }}>
                                {val?.available ? 'Available' : 'Not available'}
                              </span>
                            </div>
                          ))}
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                            <span style={{ color: '#6b7280' }}>RE Profiles</span>
                            <span style={{ color: '#eab308' }}>Requires API key</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </label>
                );
              })}
            </div>
            {selectedCountries.length > 0 && (
              <button
                className="btn btn-secondary"
                style={{ marginTop: 12, width: '100%', justifyContent: 'center' }}
                onClick={() => setSelectedCountries([])}
              >
                Clear Selection
              </button>
            )}
          </div>
        )}

        <div className="card">
          <h3 className="card-title">Summary</h3>
          {plantsLoading ? (
            <div className="loading"><Loader2 className="animate-spin" /></div>
          ) : (
            <div className="stats">
              <div className="stat">
                <div className="stat-value">{plantsData?.count || 0}</div>
                <div className="stat-label">Plants</div>
              </div>
              <div className="stat">
                <div className="stat-value">
                  {Math.round((plantsData?.total_capacity_mw || 0) / 1000)}
                </div>
                <div className="stat-label">GW Total</div>
              </div>
              <div className="stat">
                <div className="stat-value">{summary?.by_technology?.length || 0}</div>
                <div className="stat-label">Technologies</div>
              </div>
            </div>
          )}
        </div>

      </div>

      {/* Main Content */}
      <div className="content">
        <div className="card" style={{ flex: 1 }}>
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'map' ? 'active' : ''}`}
              onClick={() => setActiveTab('map')}
            >
              Map
            </button>
            <button
              className={`tab ${activeTab === 'plants' ? 'active' : ''}`}
              onClick={() => setActiveTab('plants')}
            >
              Power Plants
            </button>
            <button
              className={`tab ${activeTab === 'hydropower' ? 'active' : ''}`}
              onClick={() => setActiveTab('hydropower')}
            >
              Hydropower
            </button>
            <button
              className={`tab ${activeTab === 'renewables' ? 'active' : ''}`}
              onClick={() => setActiveTab('renewables')}
            >
              Renewables
            </button>
            <button
              className={`tab ${activeTab === 'socioeconomic' ? 'active' : ''}`}
              onClick={() => setActiveTab('socioeconomic')}
            >
              Socio-Economic
            </button>
            <button
              className={`tab ${activeTab === 'load' ? 'active' : ''}`}
              onClick={() => setActiveTab('load')}
            >
              Load Profiles
            </button>
          </div>

          {activeTab === 'map' && (
            <div>
              <div className="data-source-selector" style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16, padding: '12px 16px', background: 'var(--gray-50)', borderRadius: 8 }}>
                <span style={{ fontWeight: 500, color: 'var(--gray-700)' }}>Power Plant Source:</span>
                <div style={{ display: 'flex', gap: 12 }}>
                  {POWER_PLANT_SOURCES.map(source => (
                    <label key={source.id} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                      <input
                        type="radio"
                        name="map-power-source"
                        checked={powerPlantSources[0] === source.id}
                        onChange={() => setPowerPlantSources([source.id])}
                      />
                      <span style={{ fontSize: 14 }}>{source.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              <SourceInfo source={DATA_SOURCES.power_plants} />
              <div className="map-container-wrapper">
                <MapLayerControl layers={mapLayers} onToggle={toggleLayer} />
                <div className="map-container" style={{ height: '100%' }}>
                  <MapContainer
                    center={mapCenter}
                    zoom={currentRegion?.default_zoom || 5}
                    style={{ height: '100%', width: '100%' }}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                      url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                    />

                    {/* Power Plants Layer */}
                    {enabledLayers.includes('power_plants') && plantsData?.plants?.filter(p => p.latitude && p.longitude).map((plant, i) => (
                      <CircleMarker
                        key={`plant-${i}`}
                        center={[plant.latitude!, plant.longitude!]}
                        radius={Math.max(3, Math.min(15, Math.sqrt(plant.capacity_mw) / 5))}
                        fillColor={getTechColor(plant.technology)}
                        color={getTechColor(plant.technology)}
                        weight={1}
                        opacity={0.8}
                        fillOpacity={0.6}
                      >
                        <Popup>
                          <strong>{plant.name}</strong><br />
                          {plant.technology} - {plant.capacity_mw.toLocaleString()} MW<br />
                          {plant.status}
                        </Popup>
                      </CircleMarker>
                    ))}

                    {/* Hydropower Layer */}
                    {enabledLayers.includes('hydropower') && hydroGeoJson?.features?.map((feature: any, i: number) => {
                      const coords = feature.geometry?.coordinates;
                      if (!coords || coords.length < 2) return null;
                      const props = feature.properties || {};
                      return (
                        <CircleMarker
                          key={`hydro-${i}`}
                          center={[coords[1], coords[0]]}
                          radius={Math.max(4, Math.min(12, Math.sqrt(props.capacity_mw || 10) / 3))}
                          fillColor="#0ea5e9"
                          color="#0284c7"
                          weight={2}
                          opacity={0.9}
                          fillOpacity={0.7}
                        >
                          <Popup>
                            <strong>{props.name}</strong><br />
                            Hydropower - {(props.capacity_mw || 0).toLocaleString()} MW<br />
                            {props.status}
                          </Popup>
                        </CircleMarker>
                      );
                    })}

                    {/* Solar Potential Layer */}
                    {enabledLayers.includes('solar_potential') && solarGeoJson?.features?.slice(0, 200).map((feature: any, i: number) => {
                      const coords = feature.geometry?.coordinates;
                      if (!coords || coords.length < 2) return null;
                      const props = feature.properties || {};
                      return (
                        <CircleMarker
                          key={`solar-${i}`}
                          center={[coords[1], coords[0]]}
                          radius={4}
                          fillColor="#eab308"
                          color="#ca8a04"
                          weight={1}
                          opacity={0.7}
                          fillOpacity={0.5}
                        >
                          <Popup>
                            <strong>Solar Site</strong><br />
                            CF: {((props.capacity_factor || 0) * 100).toFixed(1)}%<br />
                            {props.country}
                          </Popup>
                        </CircleMarker>
                      );
                    })}

                    {/* Wind Potential Layer */}
                    {enabledLayers.includes('wind_potential') && windGeoJson?.features?.slice(0, 200).map((feature: any, i: number) => {
                      const coords = feature.geometry?.coordinates;
                      if (!coords || coords.length < 2) return null;
                      const props = feature.properties || {};
                      return (
                        <CircleMarker
                          key={`wind-${i}`}
                          center={[coords[1], coords[0]]}
                          radius={4}
                          fillColor="#22c55e"
                          color="#16a34a"
                          weight={1}
                          opacity={0.7}
                          fillOpacity={0.5}
                        >
                          <Popup>
                            <strong>Wind Site</strong><br />
                            CF: {((props.capacity_factor || 0) * 100).toFixed(1)}%<br />
                            {props.country}
                          </Popup>
                        </CircleMarker>
                      );
                    })}
                  </MapContainer>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'plants' && (
            <div>
              {/* Data Source Selector - checkboxes for comparison */}
              <div className="data-source-selector" style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16, padding: '12px 16px', background: 'var(--gray-50)', borderRadius: 8 }}>
                <span style={{ fontWeight: 500, color: 'var(--gray-700)' }}>Compare Sources:</span>
                <div style={{ display: 'flex', gap: 16 }}>
                  {POWER_PLANT_SOURCES.map(source => (
                    <label key={source.id} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={powerPlantSources.includes(source.id)}
                        onChange={() => {
                          setPowerPlantSources(prev => {
                            if (prev.includes(source.id)) {
                              if (prev.length === 1) return prev;
                              return prev.filter(s => s !== source.id);
                            }
                            return [...prev, source.id];
                          });
                        }}
                      />
                      <span style={{ fontSize: 14 }}>{source.name}</span>
                    </label>
                  ))}
                </div>
                <span style={{ fontSize: 12, color: 'var(--gray-500)', marginLeft: 'auto' }}>
                  Select multiple to compare side-by-side
                </span>
              </div>

              <SourceInfo source={DATA_SOURCES.power_plants} />

              {/* Technology Mix Pie Charts - side by side when multiple sources selected */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: powerPlantSources.length > 1 ? '1fr 1fr' : '1fr',
                gap: 24,
                marginBottom: 24
              }}>
                {powerPlantSources.includes('gem') && (
                  <div>
                    <h4 style={{ marginBottom: 16 }}>
                      {powerPlantSources.length > 1 ? 'Global Energy Monitor' : 'Technology Mix'}
                    </h4>
                    <ResponsiveContainer width="100%" height={280}>
                      <PieChart>
                        <Pie
                          data={techPieDataGem}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={powerPlantSources.length > 1 ? 70 : 90}
                          label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                          labelLine={false}
                        >
                          {techPieDataGem.map((entry, index) => (
                            <Cell key={index} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => `${Number(value).toLocaleString()} MW`} />
                      </PieChart>
                    </ResponsiveContainer>
                    <p style={{ textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
                      Total: {Math.round((summaryGem?.total_capacity_mw || 0) / 1000).toLocaleString()} GW
                    </p>
                  </div>
                )}
                {powerPlantSources.includes('gppd') && (
                  <div>
                    <h4 style={{ marginBottom: 16 }}>
                      {powerPlantSources.length > 1 ? 'Global Power Plant Database' : 'Technology Mix'}
                    </h4>
                    <ResponsiveContainer width="100%" height={280}>
                      <PieChart>
                        <Pie
                          data={techPieDataGppd}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={powerPlantSources.length > 1 ? 70 : 90}
                          label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                          labelLine={false}
                        >
                          {techPieDataGppd.map((entry, index) => (
                            <Cell key={index} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => `${Number(value).toLocaleString()} MW`} />
                      </PieChart>
                    </ResponsiveContainer>
                    <p style={{ textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
                      Total: {Math.round((summaryGppd?.total_capacity_mw || 0) / 1000).toLocaleString()} GW
                    </p>
                  </div>
                )}
              </div>

              <h4 style={{ margin: '24px 0 16px' }}>Plant List (Top 20 by Capacity)</h4>
              <div style={{ maxHeight: 300, overflow: 'auto' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Technology</th>
                      <th>Capacity (MW)</th>
                      <th>Status</th>
                      <th>Country</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plantsData?.plants?.slice(0, 20).map((plant, i) => (
                      <tr key={i}>
                        <td>{plant.name}</td>
                        <td>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: getTechColor(plant.technology) }}></span>
                            {plant.technology}
                          </span>
                        </td>
                        <td>{plant.capacity_mw.toLocaleString()}</td>
                        <td>{plant.status}</td>
                        <td>{plant.country}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'hydropower' && (
            <div>
              <SourceInfo source={DATA_SOURCES.hydropower} />
              <h4 style={{ marginBottom: 16 }}>Hydropower Plants</h4>
              {hydroLoading ? (
                <div className="loading"><Loader2 className="animate-spin" /></div>
              ) : hydroError ? (
                <div style={{ padding: 24, background: 'var(--red-50)', border: '1px solid var(--red-200)', borderRadius: 8, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <AlertCircle size={20} style={{ color: 'var(--red-700)', flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <p style={{ fontWeight: 500, color: 'var(--red-700)', marginBottom: 4 }}>Error Loading Data</p>
                    <p style={{ color: 'var(--red-700)', fontSize: 14 }}>
                      Could not load hydropower data for this selection. Please try again or select a different region.
                    </p>
                  </div>
                </div>
              ) : !hydroData?.plants || hydroData.plants.length === 0 ? (
                <div style={{ padding: 24, background: 'var(--gray-50)', border: '1px solid var(--gray-200)', borderRadius: 8, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <Info size={20} style={{ color: 'var(--gray-500)', flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <p style={{ fontWeight: 500, color: 'var(--gray-700)', marginBottom: 4 }}>No Hydropower Data</p>
                    <p style={{ color: 'var(--gray-600)', fontSize: 14 }}>
                      No hydropower plant data found for {selectedCountries.length > 0 ? `the selected countries (${selectedCountries.join(', ')})` : `the ${currentRegion?.name || 'selected region'}`}.
                      This may be because the countries in this selection don't have hydropower facilities in our database.
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="stats" style={{ marginBottom: 24 }}>
                    <div className="stat">
                      <div className="stat-value">{hydroData?.count || 0}</div>
                      <div className="stat-label">Hydro Plants</div>
                    </div>
                    <div className="stat">
                      <div className="stat-value">
                        {Math.round((hydroData?.total_capacity_mw || 0) / 1000)}
                      </div>
                      <div className="stat-label">GW Capacity</div>
                    </div>
                  </div>

                  <div style={{ maxHeight: 400, overflow: 'auto' }}>
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Name</th>
                          <th>Capacity (MW)</th>
                          <th>Status</th>
                          <th>Country</th>
                          <th>River</th>
                        </tr>
                      </thead>
                      <tbody>
                        {hydroData?.plants?.slice(0, 30).map((plant, i) => (
                          <tr key={i}>
                            <td>{plant.name}</td>
                            <td>{plant.capacity_mw?.toLocaleString() || '-'}</td>
                            <td>{plant.status}</td>
                            <td>{plant.country}</td>
                            <td>{plant.river_name || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === 'renewables' && (
            <div>
              <SourceInfo source={DATA_SOURCES.renewables_ninja} />

              {/* Renewables.ninja Fetch Section */}
              <div className="card" style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                  <h4 style={{ margin: 0 }}>Fetch Capacity Factor Profiles from Renewables.ninja</h4>
                  {ninjaData && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '4px 10px',
                      background: '#dcfce7',
                      color: '#166534',
                      borderRadius: 12,
                      fontSize: 12,
                      fontWeight: 500,
                    }}>
                      <CheckCircle2 size={14} />
                      Data loaded
                    </span>
                  )}
                </div>

                {!hasApiKey('renewablesNinja') ? (
                  <div style={{ padding: 16, background: 'var(--yellow-50)', border: '1px solid var(--yellow-200)', borderRadius: 8, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                    <AlertCircle size={20} style={{ color: 'var(--yellow-600)', flexShrink: 0, marginTop: 2 }} />
                    <div>
                      <p style={{ fontWeight: 500, color: 'var(--yellow-800)', marginBottom: 4 }}>API Key Required</p>
                      <p style={{ color: 'var(--yellow-700)', fontSize: 14 }}>
                        To fetch capacity factor profiles from Renewables.ninja, please add your API key in the{' '}
                        <a href="/settings" style={{ color: 'var(--yellow-800)', textDecoration: 'underline' }}>Settings</a> page.
                        You can get a free API key at{' '}
                        <a href="https://www.renewables.ninja/" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--yellow-800)', textDecoration: 'underline' }}>
                          renewables.ninja
                        </a>.
                      </p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 16 }}>
                      <div className="form-group" style={{ margin: 0, minWidth: 200 }}>
                        <label className="form-label">Country</label>
                        <div style={{ padding: '8px 12px', background: 'var(--gray-100)', borderRadius: 6, fontSize: 14, color: 'var(--gray-700)', border: '1px solid var(--gray-200)' }}>
                          {ninjaCountry || 'Select a country in sidebar'}
                        </div>
                        <span style={{ fontSize: 11, color: 'var(--gray-500)', marginTop: 4, display: 'block' }}>
                          Using first selected country from sidebar
                        </span>
                      </div>

                      <div className="form-group" style={{ margin: 0, minWidth: 120 }}>
                        <label className="form-label">Technology</label>
                        <select
                          className="form-select"
                          value={ninjaTechnology}
                          onChange={(e) => setNinjaTechnology(e.target.value as 'solar' | 'wind')}
                        >
                          <option value="solar">Solar PV</option>
                          <option value="wind">Wind</option>
                        </select>
                      </div>

                      <div className="form-group" style={{ margin: 0, minWidth: 100 }}>
                        <label className="form-label">Year</label>
                        <select
                          className="form-select"
                          value={ninjaYear}
                          onChange={(e) => setNinjaYear(parseInt(e.target.value))}
                        >
                          {Array.from({ length: 24 }, (_, i) => 2000 + i).map(year => (
                            <option key={year} value={year}>{year}</option>
                          ))}
                        </select>
                      </div>

                      <button
                        className="btn btn-primary"
                        onClick={() => {
                          if (ninjaCountry) {
                            ninjaFetchMutation.mutate({ country: ninjaCountry, year: ninjaYear, technology: ninjaTechnology });
                          }
                        }}
                        disabled={ninjaFetchMutation.isPending || !ninjaCountry}
                        style={{ display: 'flex', alignItems: 'center', gap: 8 }}
                      >
                        {ninjaFetchMutation.isPending ? (
                          <>
                            <Loader2 className="animate-spin" size={16} />
                            Fetching...
                          </>
                        ) : (
                          <>
                            <Download size={16} />
                            Fetch Profiles
                          </>
                        )}
                      </button>
                    </div>

                    <p style={{ color: 'var(--gray-500)', fontSize: 13 }}>
                      Data will be fetched for the country centroid. Renewables.ninja provides hourly capacity factor data based on NASA MERRA-2 reanalysis.
                    </p>
                  </>
                )}

                {ninjaError && (
                  <div style={{ marginTop: 16, padding: 16, background: 'var(--red-50)', border: '1px solid var(--red-200)', borderRadius: 8, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                    <AlertCircle size={20} style={{ color: 'var(--red-700)', flexShrink: 0, marginTop: 2 }} />
                    <div>
                      <p style={{ fontWeight: 500, color: 'var(--red-700)', marginBottom: 4 }}>
                        {ninjaError.includes('502') || ninjaError.includes('503') ? 'Service Temporarily Unavailable' :
                         ninjaError.includes('401') || ninjaError.includes('403') ? 'API Key Invalid' :
                         ninjaError.includes('429') ? 'Rate Limit Exceeded' :
                         ninjaError.includes('API key') ? 'API Key Required' :
                         'Request Failed'}
                      </p>
                      <p style={{ color: 'var(--red-700)', fontSize: 14, marginBottom: 8 }}>
                        {ninjaError.includes('502') || ninjaError.includes('503') ?
                          'The Renewables.ninja service is temporarily unavailable. Please try again in a few minutes.' :
                         ninjaError.includes('401') || ninjaError.includes('403') ?
                          'Your API key appears to be invalid. Please check your API key in Settings.' :
                         ninjaError.includes('429') ?
                          'You have exceeded the rate limit for the Renewables.ninja API. Please wait a moment before trying again.' :
                         ninjaError}
                      </p>
                      {(ninjaError.includes('502') || ninjaError.includes('503')) && (
                        <p style={{ color: 'var(--gray-600)', fontSize: 12 }}>
                          Tip: Renewables.ninja may experience high load. If this persists, try again later.
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Ninja Results */}
              {ninjaData && (
                <div style={{ marginBottom: 24 }}>
                  <h4 style={{ marginBottom: 16 }}>
                    {ninjaTechnology === 'solar' ? 'Solar PV' : 'Wind'} Capacity Factor Profile - {ninjaCountry} ({ninjaData.year})
                  </h4>

                  <div className="stats" style={{ marginBottom: 24 }}>
                    <div className="stat">
                      <div className="stat-value">{(ninjaData.mean_cf * 100).toFixed(1)}%</div>
                      <div className="stat-label">Mean CF</div>
                    </div>
                    <div className="stat">
                      <div className="stat-value">{ninjaData.count.toLocaleString()}</div>
                      <div className="stat-label">Data Points</div>
                    </div>
                    <div className="stat">
                      <div className="stat-value">{ninjaData.location.lat.toFixed(2)}, {ninjaData.location.lon.toFixed(2)}</div>
                      <div className="stat-label">Location</div>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                    <div className="card">
                      <h5 style={{ marginBottom: 12, color: ninjaTechnology === 'solar' ? '#eab308' : '#22c55e' }}>Average Daily Profile</h5>
                      <ResponsiveContainer width="100%" height={250}>
                        <AreaChart data={ninjaChartData}>
                          <XAxis dataKey="hour" label={{ value: 'Hour', position: 'bottom', offset: -5 }} />
                          <YAxis domain={[0, 'auto']} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                          <Tooltip formatter={(value) => `${(Number(value) * 100).toFixed(1)}%`} labelFormatter={(h) => `Hour ${h}:00`} />
                          <Area
                            type="monotone"
                            dataKey="capacity_factor"
                            name="Capacity Factor"
                            fill={ninjaTechnology === 'solar' ? '#fef08a' : '#bbf7d0'}
                            stroke={ninjaTechnology === 'solar' ? '#eab308' : '#22c55e'}
                            strokeWidth={2}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="card">
                      <h5 style={{ marginBottom: 12, color: ninjaTechnology === 'solar' ? '#eab308' : '#22c55e' }}>Monthly Average</h5>
                      <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={ninjaMonthlyData}>
                          <XAxis dataKey="month" />
                          <YAxis domain={[0, 'auto']} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                          <Tooltip formatter={(value) => `${(Number(value) * 100).toFixed(1)}%`} />
                          <Bar
                            dataKey="capacity_factor"
                            name="Avg Capacity Factor"
                            fill={ninjaTechnology === 'solar' ? '#eab308' : '#22c55e'}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              )}

              {/* IRENA Resource Potential (existing) */}
              <h4 style={{ marginBottom: 16, marginTop: 24 }}>Resource Potential (IRENA MSR Data)</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                <div className="card">
                  <h5 style={{ color: '#eab308', marginBottom: 12 }}>Solar PV Potential</h5>
                  {solarPotential?.by_country?.length > 0 ? (
                    <>
                      <div className="stats" style={{ marginBottom: 16 }}>
                        <div className="stat">
                          <div className="stat-value">{Math.round(solarPotential.total_capacity_mw / 1000)}</div>
                          <div className="stat-label">GW Total</div>
                        </div>
                        <div className="stat">
                          <div className="stat-value">{solarPotential.country_count}</div>
                          <div className="stat-label">Countries</div>
                        </div>
                      </div>
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={solarPotential.by_country.slice(0, 5)}>
                          <XAxis dataKey="country" fontSize={11} />
                          <YAxis />
                          <Tooltip formatter={(value) => `${Number(value).toLocaleString()} MW`} />
                          <Bar dataKey="total_capacity_mw" fill="#eab308" name="Capacity (MW)" />
                        </BarChart>
                      </ResponsiveContainer>
                    </>
                  ) : (
                    <p style={{ color: '#6b7280' }}>No solar data available for this region. IRENA MSR data covers Central African countries.</p>
                  )}
                </div>

                <div className="card">
                  <h5 style={{ color: '#22c55e', marginBottom: 12 }}>Wind Potential</h5>
                  {windPotential?.by_country?.length > 0 ? (
                    <>
                      <div className="stats" style={{ marginBottom: 16 }}>
                        <div className="stat">
                          <div className="stat-value">{Math.round(windPotential.total_capacity_mw / 1000)}</div>
                          <div className="stat-label">GW Total</div>
                        </div>
                        <div className="stat">
                          <div className="stat-value">{windPotential.country_count}</div>
                          <div className="stat-label">Countries</div>
                        </div>
                      </div>
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={windPotential.by_country.slice(0, 5)}>
                          <XAxis dataKey="country" fontSize={11} />
                          <YAxis />
                          <Tooltip formatter={(value) => `${Number(value).toLocaleString()} MW`} />
                          <Bar dataKey="total_capacity_mw" fill="#22c55e" name="Capacity (MW)" />
                        </BarChart>
                      </ResponsiveContainer>
                    </>
                  ) : (
                    <p style={{ color: '#6b7280' }}>No wind data available for this region. IRENA MSR data covers Central African countries.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'socioeconomic' && (
            <div>
              <SourceInfo source={DATA_SOURCES.socioeconomic} />
              <h4 style={{ marginBottom: 16 }}>Socio-Economic Indicators (OWID Energy Data)</h4>
              {socioLoading ? (
                <div className="loading"><Loader2 className="animate-spin" /></div>
              ) : (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
                    <div>
                      <h5 style={{ marginBottom: 12 }}>Electricity Generation by Country (TWh)</h5>
                      {socioData?.data && socioData.data.length > 0 ? (
                        <ResponsiveContainer width="100%" height={250}>
                          <BarChart data={socioData.data.filter(d => d.electricity_generation).slice(0, 10)}>
                            <XAxis dataKey="country" angle={-45} textAnchor="end" height={80} fontSize={11} />
                            <YAxis />
                            <Tooltip formatter={(value) => `${Number(value).toLocaleString()} TWh`} />
                            <Bar dataKey="electricity_generation" fill="#2563eb" name="Electricity (TWh)" />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <p style={{ color: '#6b7280' }}>No electricity data available for selected region.</p>
                      )}
                    </div>
                    <div>
                      <h5 style={{ marginBottom: 12 }}>Renewables Share in Electricity (%)</h5>
                      {socioData?.data && socioData.data.length > 0 ? (
                        <ResponsiveContainer width="100%" height={250}>
                          <BarChart data={socioData.data.filter(d => d.renewables_share_elec != null).slice(0, 10)}>
                            <XAxis dataKey="country" angle={-45} textAnchor="end" height={80} fontSize={11} />
                            <YAxis domain={[0, 100]} />
                            <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                            <Bar dataKey="renewables_share_elec" fill="#22c55e" name="Renewables %" />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <p style={{ color: '#6b7280' }}>No renewables data available for selected region.</p>
                      )}
                    </div>
                  </div>

                  {electricityTimeSeries?.data && electricityTimeSeries.data.length > 0 && (
                    <div style={{ marginBottom: 24 }}>
                      <h5 style={{ marginBottom: 12 }}>Electricity Generation Trend (2000-present)</h5>
                      <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={electricityTimeSeries.data}>
                          <XAxis dataKey="year" />
                          <YAxis />
                          <Tooltip formatter={(value) => value != null ? `${Number(value).toFixed(1)} TWh` : 'N/A'} />
                          {electricityTimeSeries.countries.map((country, idx) => (
                            <Line
                              key={country}
                              type="monotone"
                              dataKey={`values.${country}`}
                              name={country}
                              stroke={['#2563eb', '#dc2626', '#22c55e', '#f97316', '#7c3aed'][idx % 5]}
                              strokeWidth={2}
                              dot={false}
                              connectNulls
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <h5 style={{ margin: '24px 0 12px' }}>Country Statistics (Latest Available Year)</h5>
                  <div style={{ maxHeight: 300, overflow: 'auto' }}>
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Country</th>
                          <th>Year</th>
                          <th>Population (M)</th>
                          <th>GDP (B$)</th>
                          <th>Elec. Gen. (TWh)</th>
                          <th>Renewables %</th>
                          <th>CO₂ (g/kWh)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {socioData?.data?.slice(0, 20).map((row, i) => (
                          <tr key={i}>
                            <td>{row.country}</td>
                            <td>{row.year}</td>
                            <td>{row.population ? (row.population / 1e6).toFixed(1) : '-'}</td>
                            <td>{row.gdp ? (row.gdp / 1e9).toFixed(0) : '-'}</td>
                            <td>{row.electricity_generation?.toFixed(1) || '-'}</td>
                            <td>{row.renewables_share_elec?.toFixed(1) || '-'}%</td>
                            <td>{row.carbon_intensity_elec?.toFixed(0) || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p style={{ color: '#6b7280', fontSize: 12, marginTop: 8 }}>
                    Data source: Our World in Data (OWID) Energy Dataset
                  </p>
                </>
              )}
            </div>
          )}

          {activeTab === 'load' && (
            <div>
              <SourceInfo source={DATA_SOURCES.load_profiles} />
              <h4 style={{ marginBottom: 16 }}>Average Daily Load Profile</h4>
              <TimeSelector
                year={loadYear}
                months={loadMonths}
                onYearChange={setLoadYear}
                onMonthsChange={setLoadMonths}
                multiSelect
              />
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={loadChartData}>
                  <XAxis dataKey="hour" label={{ value: 'Hour', position: 'bottom' }} />
                  <YAxis domain={[0, 1]} label={{ value: 'Normalized Load', angle: -90, position: 'insideLeft' }} />
                  <Tooltip formatter={(value) => typeof value === 'number' ? value.toFixed(3) : value} />
                  {loadCountries.length > 1 && <Legend />}
                  {loadCountries.map((country: string, idx: number) => (
                    <Line
                      key={country}
                      type="monotone"
                      dataKey={country}
                      name={country}
                      stroke={['#2563eb', '#dc2626', '#22c55e', '#f97316', '#7c3aed', '#0ea5e9', '#eab308', '#ec4899', '#14b8a6', '#8b5cf6', '#f43f5e', '#06b6d4'][idx % 12]}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              <p style={{ color: '#6b7280', fontSize: 14, marginTop: 8 }}>
                Values normalized to [0, 1]. Peak load = 1.0.
                {loadCountries.length > 1 ? ` Showing ${loadCountries.length} countries.` : ''}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
