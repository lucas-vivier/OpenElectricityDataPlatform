import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';
import { Download, Loader2, ChevronDown, ChevronUp, ExternalLink, Copy, Check } from 'lucide-react';
import { regionsApi, powerPlantsApi, loadProfilesApi, exportsApi, hydropowerApi, resourcePotentialApi, socioeconomicApi } from '../api/client';
import SourceInfo, { DATA_SOURCES } from '../components/SourceInfo';
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

type TabType = 'map' | 'plants' | 'hydropower' | 'renewables' | 'socioeconomic' | 'load' | 'export' | 'api';

export default function DataExplorer() {
  const [selectedRegion, setSelectedRegion] = useState('south_africa');
  const [activeTab, setActiveTab] = useState<TabType>('map');

  // Fetch regions
  const { data: regions } = useQuery({
    queryKey: ['regions'],
    queryFn: regionsApi.list,
  });

  // Fetch power plants
  const { data: plantsData, isLoading: plantsLoading } = useQuery({
    queryKey: ['power-plants', selectedRegion],
    queryFn: () => powerPlantsApi.list({ region: selectedRegion }),
    enabled: !!selectedRegion,
  });

  // Fetch power plants summary
  const { data: summary } = useQuery({
    queryKey: ['power-plants-summary', selectedRegion],
    queryFn: () => powerPlantsApi.summary({ region: selectedRegion }),
    enabled: !!selectedRegion,
  });

  // Fetch load profiles (daily average for January)
  const { data: loadData } = useQuery({
    queryKey: ['load-monthly', selectedRegion],
    queryFn: () => loadProfilesApi.monthlyAverage({ region: selectedRegion, year: 2020 }),
    enabled: !!selectedRegion,
  });

  // Fetch hydropower data
  const { data: hydroData, isLoading: hydroLoading } = useQuery({
    queryKey: ['hydropower', selectedRegion],
    queryFn: () => hydropowerApi.list({ region: selectedRegion, source: 'both' }),
    enabled: !!selectedRegion && activeTab === 'hydropower',
  });

  // Fetch resource potential data (only when tab is active)
  const { data: solarPotential } = useQuery({
    queryKey: ['solar-potential', selectedRegion],
    queryFn: () => resourcePotentialApi.solarSummary({ region: selectedRegion }),
    enabled: !!selectedRegion && activeTab === 'renewables',
  });

  const { data: windPotential } = useQuery({
    queryKey: ['wind-potential', selectedRegion],
    queryFn: () => resourcePotentialApi.windSummary({ region: selectedRegion }),
    enabled: !!selectedRegion && activeTab === 'renewables',
  });

  // Fetch socioeconomic data (uses region countries)
  const { data: socioData, isLoading: socioLoading } = useQuery({
    queryKey: ['socioeconomic', selectedRegion],
    queryFn: async () => {
      const regionData = regions?.find(r => r.id === selectedRegion);
      const countries = regionData?.countries || [];
      return socioeconomicApi.summary({ countries });
    },
    enabled: !!selectedRegion && activeTab === 'socioeconomic' && !!regions,
  });

  // Fetch electricity time series for socioeconomic tab
  const { data: electricityTimeSeries } = useQuery({
    queryKey: ['electricity-timeseries', selectedRegion],
    queryFn: async () => {
      const regionData = regions?.find(r => r.id === selectedRegion);
      const countries = regionData?.countries || [];
      if (countries.length === 0) return null;
      return socioeconomicApi.timeseries('electricity_generation', {
        countries: countries.slice(0, 5),  // Limit to 5 countries for chart clarity
        start_year: 2000
      });
    },
    enabled: !!selectedRegion && activeTab === 'socioeconomic' && !!regions,
  });

  const currentRegion = regions?.find(r => r.id === selectedRegion);
  const mapCenter: [number, number] = currentRegion?.bbox
    ? [(currentRegion.bbox[1] + currentRegion.bbox[3]) / 2, (currentRegion.bbox[0] + currentRegion.bbox[2]) / 2]
    : [-29, 24];

  // Prepare chart data
  const techChartData = useMemo(() =>
    summary?.by_technology?.map(t => ({
      name: t.technology,
      capacity: Math.round(t.total_capacity_mw),
      fill: getTechColor(t.technology),
    })) || []
  , [summary]);

  const techPieData = useMemo(() =>
    summary?.by_technology?.slice(0, 8).map(t => ({
      name: t.technology,
      value: Math.round(t.total_capacity_mw),
      fill: getTechColor(t.technology),
    })) || []
  , [summary]);

  const loadChartData = loadData?.monthly_profiles?.[1]?.hours?.map((hour: number, i: number) => ({
    hour,
    value: loadData.monthly_profiles[1].values[i],
  })) || [];

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
              onChange={(e) => setSelectedRegion(e.target.value)}
            >
              {regions?.map(region => (
                <option key={region.id} value={region.id}>
                  {region.name}
                </option>
              ))}
            </select>
          </div>
        </div>

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

        <div className="card">
          <h3 className="card-title">Quick Export</h3>
          <div className="export-buttons">
            <a
              href={exportsApi.powerPlantsCsv({ region: selectedRegion })}
              className="btn btn-secondary"
              download
            >
              <Download size={16} />
              Plants CSV
            </a>
            <a
              href={exportsApi.loadProfilesCsv({ region: selectedRegion, year: 2020 })}
              className="btn btn-secondary"
              download
            >
              <Download size={16} />
              Load CSV
            </a>
          </div>
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
            <button
              className={`tab ${activeTab === 'export' ? 'active' : ''}`}
              onClick={() => setActiveTab('export')}
            >
              Export
            </button>
            <button
              className={`tab ${activeTab === 'api' ? 'active' : ''}`}
              onClick={() => setActiveTab('api')}
            >
              API
            </button>
          </div>

          {activeTab === 'map' && (
            <div>
              <SourceInfo source={DATA_SOURCES.power_plants} />
              <div className="map-container">
                <MapContainer
                center={mapCenter}
                zoom={currentRegion?.default_zoom || 5}
                style={{ height: '100%', width: '100%' }}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                />
                {plantsData?.plants?.filter(p => p.latitude && p.longitude).map((plant, i) => (
                  <CircleMarker
                    key={i}
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
                </MapContainer>
                <div className="map-legend">
                  {Object.entries(TECH_COLORS).slice(0, 7).map(([tech, color]) => (
                    <span key={tech} className="legend-item">
                      <span className="legend-color" style={{ backgroundColor: color }}></span>
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'plants' && (
            <div>
              <SourceInfo source={DATA_SOURCES.power_plants} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
                <div>
                  <h4 style={{ marginBottom: 16 }}>Capacity by Technology</h4>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={techChartData}>
                      <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} fontSize={12} />
                      <YAxis />
                      <Tooltip formatter={(value) => `${Number(value).toLocaleString()} MW`} />
                      <Bar dataKey="capacity">
                        {techChartData.map((entry, index) => (
                          <Cell key={index} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div>
                  <h4 style={{ marginBottom: 16 }}>Technology Mix</h4>
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={techPieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {techPieData.map((entry, index) => (
                          <Cell key={index} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => `${Number(value).toLocaleString()} MW`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
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
              <SourceInfo source={DATA_SOURCES.resource_potential} />
              <h4 style={{ marginBottom: 16 }}>Renewable Energy Resource Potential (IRENA MSR Data)</h4>
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
              <h4 style={{ marginBottom: 16 }}>Average Daily Load Profile (January)</h4>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={loadChartData}>
                  <XAxis dataKey="hour" />
                  <YAxis domain={[0, 1]} />
                  <Tooltip formatter={(value) => Number(value).toFixed(3)} />
                  <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
              <p style={{ color: '#6b7280', fontSize: 14, marginTop: 8 }}>
                Values normalized to [0, 1]. Peak load = 1.0
              </p>
            </div>
          )}

          {activeTab === 'export' && (
            <div>
              <h4 style={{ marginBottom: 16 }}>Download Data</h4>
              <p style={{ color: '#6b7280', marginBottom: 24 }}>
                Export data in model-ready formats for use in PyPSA, OSeMOSYS, or other capacity expansion models.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
                <div className="card">
                  <h5 style={{ marginBottom: 12 }}>Power Plants</h5>
                  <div className="export-buttons">
                    <a href={exportsApi.powerPlantsCsv({ region: selectedRegion })} className="btn btn-primary" download>
                      <Download size={16} /> CSV
                    </a>
                    <a href={exportsApi.powerPlantsGeojson({ region: selectedRegion })} className="btn btn-secondary" download>
                      <Download size={16} /> GeoJSON
                    </a>
                  </div>
                </div>

                <div className="card">
                  <h5 style={{ marginBottom: 12 }}>Load Profiles</h5>
                  <div className="export-buttons">
                    <a href={exportsApi.loadProfilesCsv({ region: selectedRegion, year: 2020 })} className="btn btn-primary" download>
                      <Download size={16} /> Standard CSV
                    </a>
                    <a href={exportsApi.loadProfilesCsv({ region: selectedRegion, year: 2020, format_type: 'epm' })} className="btn btn-secondary" download>
                      <Download size={16} /> EPM Format
                    </a>
                  </div>
                </div>

                <div className="card">
                  <h5 style={{ marginBottom: 12 }}>Solar Profiles</h5>
                  <div className="export-buttons">
                    <a href={exportsApi.reProfilesCsv({ region: selectedRegion, technology: 'solar', year: 2020 })} className="btn btn-primary" download>
                      <Download size={16} /> CSV
                    </a>
                  </div>
                </div>

                <div className="card">
                  <h5 style={{ marginBottom: 12 }}>Wind Profiles</h5>
                  <div className="export-buttons">
                    <a href={exportsApi.reProfilesCsv({ region: selectedRegion, technology: 'wind', year: 2020 })} className="btn btn-primary" download>
                      <Download size={16} /> CSV
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'api' && (
            <ApiTab selectedRegion={selectedRegion} />
          )}
        </div>
      </div>
    </div>
  );
}

// API Tab Component
function ApiTab({ selectedRegion }: { selectedRegion: string }) {
  const [expandedEndpoint, setExpandedEndpoint] = useState<string | null>('power-plants');
  const [codeTab, setCodeTab] = useState<'python' | 'curl' | 'javascript'>('python');
  const [copied, setCopied] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const endpoints = [
    {
      id: 'power-plants',
      name: 'Power Plants',
      path: '/api/power-plants',
      description: 'Retrieve power plant data with optional filtering by region, country, technology, and capacity.',
      params: [
        { name: 'region', type: 'string', description: 'Region ID (required)' },
        { name: 'countries', type: 'string[]', description: 'Filter by country names' },
        { name: 'technology', type: 'string', description: 'Filter by technology (Solar, Wind, etc.)' },
        { name: 'status', type: 'string', description: 'Filter by status (Operating, Construction)' },
        { name: 'min_capacity', type: 'float', description: 'Minimum capacity in MW' },
      ],
      subEndpoints: ['/api/power-plants/summary', '/api/power-plants/geojson'],
    },
    {
      id: 'load-profiles',
      name: 'Load Profiles',
      path: '/api/load-profiles',
      description: 'Retrieve hourly electricity demand profiles for countries.',
      params: [
        { name: 'region', type: 'string', description: 'Region ID (required)' },
        { name: 'countries', type: 'string[]', description: 'Filter by country names' },
        { name: 'year', type: 'int', description: 'Reference year (default: 2020)' },
      ],
    },
    {
      id: 'hydropower',
      name: 'Hydropower',
      path: '/api/hydropower',
      description: 'Retrieve hydropower plant data and climate scenario projections.',
      params: [
        { name: 'region', type: 'string', description: 'Region ID (required)' },
        { name: 'countries', type: 'string[]', description: 'Filter by country names' },
        { name: 'source', type: 'string', description: 'Data source (atlas, tracker, both)' },
      ],
    },
    {
      id: 'resource-potential',
      name: 'Resource Potential',
      path: '/api/resource-potential',
      description: 'Retrieve IRENA solar and wind resource potential data.',
      params: [
        { name: 'region', type: 'string', description: 'Region ID (required)' },
        { name: 'technology', type: 'string', description: 'solar or wind' },
      ],
      subEndpoints: ['/api/resource-potential/solar', '/api/resource-potential/wind'],
    },
    {
      id: 'socioeconomic',
      name: 'Socio-Economic',
      path: '/api/socioeconomic',
      description: 'Retrieve socio-economic indicators from Our World in Data.',
      params: [
        { name: 'countries', type: 'string[]', description: 'Country names' },
        { name: 'year', type: 'int', description: 'Reference year' },
      ],
    },
  ];

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const pythonExample = `import requests

# Fetch power plants for ${selectedRegion}
response = requests.get(
    "${API_BASE_URL}/api/power-plants",
    params={
        "region": "${selectedRegion}",
        "status": "Operating"
    }
)
data = response.json()

print(f"Found {data['count']} power plants")
print(f"Total capacity: {data['total_capacity_mw']:.0f} MW")`;

  const curlExample = `curl -X GET "${API_BASE_URL}/api/power-plants?region=${selectedRegion}&status=Operating"`;

  const jsExample = `const response = await fetch(
  "${API_BASE_URL}/api/power-plants?" + new URLSearchParams({
    region: "${selectedRegion}",
    status: "Operating"
  })
);
const data = await response.json();
console.log(\`Found \${data.count} power plants\`);`;

  const codeExamples = { python: pythonExample, curl: curlExample, javascript: jsExample };

  return (
    <div>
      <h4 style={{ marginBottom: 8 }}>API Access</h4>
      <p style={{ color: '#6b7280', marginBottom: 24 }}>
        Access the same data programmatically via our REST API. The API returns JSON responses
        and supports filtering and multiple output formats.
      </p>

      <div className="api-section">
        <h5 style={{ marginBottom: 12 }}>Available Endpoints</h5>
        {endpoints.map((endpoint) => (
          <div key={endpoint.id} className="api-endpoint">
            <div
              className="api-endpoint-header"
              onClick={() => setExpandedEndpoint(expandedEndpoint === endpoint.id ? null : endpoint.id)}
            >
              <div className="api-endpoint-title">
                <span className="api-method">GET</span>
                <span className="api-path">{endpoint.path}</span>
              </div>
              {expandedEndpoint === endpoint.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>

            {expandedEndpoint === endpoint.id && (
              <div className="api-endpoint-content">
                <p style={{ marginBottom: 12, color: '#6b7280' }}>{endpoint.description}</p>

                <div className="api-url-box">
                  {API_BASE_URL}{endpoint.path}?region={selectedRegion}
                </div>

                <table className="api-params-table">
                  <thead>
                    <tr>
                      <th>Parameter</th>
                      <th>Type</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {endpoint.params.map((param) => (
                      <tr key={param.name}>
                        <td><code>{param.name}</code></td>
                        <td>{param.type}</td>
                        <td>{param.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {endpoint.subEndpoints && (
                  <div style={{ marginTop: 12 }}>
                    <span style={{ fontSize: 12, color: '#6b7280' }}>Additional endpoints: </span>
                    {endpoint.subEndpoints.map((sub, i) => (
                      <code key={sub} style={{ fontSize: 12, marginLeft: i > 0 ? 8 : 4 }}>{sub}</code>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="api-section">
        <h5 style={{ marginBottom: 12 }}>Code Examples</h5>
        <div className="code-tabs">
          <button
            className={`code-tab ${codeTab === 'python' ? 'active' : ''}`}
            onClick={() => setCodeTab('python')}
          >
            Python
          </button>
          <button
            className={`code-tab ${codeTab === 'curl' ? 'active' : ''}`}
            onClick={() => setCodeTab('curl')}
          >
            cURL
          </button>
          <button
            className={`code-tab ${codeTab === 'javascript' ? 'active' : ''}`}
            onClick={() => setCodeTab('javascript')}
          >
            JavaScript
          </button>
          <button
            className="code-tab"
            onClick={() => copyToClipboard(codeExamples[codeTab])}
            style={{ marginLeft: 'auto' }}
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <div className="code-block">
          {codeExamples[codeTab]}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, marginTop: 24 }}>
        <a
          href={`${API_BASE_URL}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-primary"
        >
          <ExternalLink size={16} />
          API Documentation
        </a>
        <a
          href={`${API_BASE_URL}/redoc`}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-secondary"
        >
          <ExternalLink size={16} />
          OpenAPI Spec
        </a>
      </div>
    </div>
  );
}
