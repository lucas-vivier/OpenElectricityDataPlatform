import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Loader2, CheckCircle, AlertCircle, AlertTriangle, XCircle, Database, ChevronRight } from 'lucide-react';
import { regionsApi, dataQualityApi, type CountryQuality } from '../api/client';
import 'leaflet/dist/leaflet.css';

// Quality level colors
const QUALITY_COLORS: Record<string, string> = {
  excellent: '#22c55e',  // green
  good: '#84cc16',       // lime
  fair: '#eab308',       // yellow
  poor: '#f97316',       // orange
  no_data: '#9ca3af',    // gray
};

const QUALITY_LABELS: Record<string, string> = {
  excellent: 'Excellent',
  good: 'Good',
  fair: 'Fair',
  poor: 'Poor',
  no_data: 'No Data',
};

const getQualityIcon = (level: string, size: number = 16) => {
  switch (level) {
    case 'excellent':
      return <CheckCircle size={size} color={QUALITY_COLORS.excellent} />;
    case 'good':
      return <CheckCircle size={size} color={QUALITY_COLORS.good} />;
    case 'fair':
      return <AlertTriangle size={size} color={QUALITY_COLORS.fair} />;
    case 'poor':
      return <AlertCircle size={size} color={QUALITY_COLORS.poor} />;
    default:
      return <XCircle size={size} color={QUALITY_COLORS.no_data} />;
  }
};

// Map bounds updater component
function MapBoundsUpdater({ bbox }: { bbox?: number[] }) {
  const map = useMap();
  if (bbox && bbox.length === 4) {
    map.fitBounds([
      [bbox[1], bbox[0]],
      [bbox[3], bbox[2]],
    ]);
  }
  return null;
}

export default function DataQuality() {
  const [selectedRegion, setSelectedRegion] = useState('southern_africa');
  const [selectedCountry, setSelectedCountry] = useState<CountryQuality | null>(null);

  // Fetch regions
  const { data: regions } = useQuery({
    queryKey: ['regions'],
    queryFn: regionsApi.list,
  });

  // Fetch quality data for region
  const { data: qualityData, isLoading: qualityLoading } = useQuery({
    queryKey: ['data-quality', selectedRegion],
    queryFn: () => dataQualityApi.region({ region: selectedRegion }),
    enabled: !!selectedRegion,
  });

  const currentRegion = regions?.find(r => r.id === selectedRegion);
  const mapCenter: [number, number] = currentRegion?.bbox
    ? [(currentRegion.bbox[1] + currentRegion.bbox[3]) / 2, (currentRegion.bbox[0] + currentRegion.bbox[2]) / 2]
    : [-15, 25];

  // Prepare chart data
  const qualityDistribution = useMemo(() => {
    if (!qualityData?.summary) return [];
    return Object.entries(qualityData.summary.by_quality_level)
      .filter(([_, count]) => count > 0)
      .map(([level, count]) => ({
        name: QUALITY_LABELS[level] || level,
        value: count,
        fill: QUALITY_COLORS[level] || QUALITY_COLORS.no_data,
      }));
  }, [qualityData]);

  const datasetCoverage = useMemo(() => {
    if (!qualityData?.summary?.datasets_coverage) return [];
    return Object.entries(qualityData.summary.datasets_coverage).map(([dataset, data]) => ({
      name: dataset.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
      coverage: data.coverage_pct,
      countries: data.countries_with_data,
    }));
  }, [qualityData]);

  const countriesSorted = useMemo(() => {
    if (!qualityData?.countries) return [];
    return [...qualityData.countries].sort((a, b) => b.overall_score - a.overall_score);
  }, [qualityData]);

  return (
    <div className="quality-layout">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="card">
          <h3 className="card-title">Select Region</h3>
          <div className="form-group">
            <select
              className="form-select"
              value={selectedRegion}
              onChange={(e) => {
                setSelectedRegion(e.target.value);
                setSelectedCountry(null);
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

        {qualityLoading ? (
          <div className="card">
            <div className="loading"><Loader2 className="animate-spin" /></div>
          </div>
        ) : qualityData?.summary && (
          <>
            <div className="card">
              <h3 className="card-title">Region Summary</h3>
              <div className="stats">
                <div className="stat">
                  <div className="stat-value">{qualityData.summary.total_countries}</div>
                  <div className="stat-label">Countries</div>
                </div>
                <div className="stat">
                  <div className="stat-value">{qualityData.summary.average_score.toFixed(0)}%</div>
                  <div className="stat-label">Avg Score</div>
                </div>
              </div>
            </div>

            <div className="card">
              <h3 className="card-title">Quality Distribution</h3>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie
                    data={qualityDistribution}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={30}
                    outerRadius={55}
                  >
                    {qualityDistribution.map((entry, index) => (
                      <Cell key={index} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="quality-legend">
                {qualityDistribution.map((item) => (
                  <span key={item.name} className="legend-item">
                    <span className="legend-color" style={{ backgroundColor: item.fill }}></span>
                    {item.name}: {item.value}
                  </span>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Main Content */}
      <div className="content">
        <div className="card" style={{ marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 20 }}>Data Quality Assessment</h2>
          <p style={{ color: '#6b7280', margin: '8px 0 0' }}>
            Navigate the map to explore data availability and quality for each country.
            Click on a country marker to see detailed quality metrics.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: selectedCountry ? '1fr 400px' : '1fr', gap: 16 }}>
          {/* Map */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ height: 500 }}>
              {qualityLoading ? (
                <div className="loading" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Loader2 className="animate-spin" size={32} />
                </div>
              ) : (
                <MapContainer
                  center={mapCenter}
                  zoom={currentRegion?.default_zoom || 4}
                  style={{ height: '100%', width: '100%' }}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                  />
                  <MapBoundsUpdater bbox={currentRegion?.bbox} />
                  {qualityData?.countries?.filter(c => c.latitude && c.longitude).map((country) => (
                    <CircleMarker
                      key={country.country}
                      center={[country.latitude!, country.longitude!]}
                      radius={Math.max(12, Math.min(25, country.overall_score / 4))}
                      fillColor={QUALITY_COLORS[country.quality_level] || QUALITY_COLORS.no_data}
                      color="#fff"
                      weight={2}
                      opacity={1}
                      fillOpacity={0.8}
                      eventHandlers={{
                        click: () => setSelectedCountry(country),
                      }}
                    >
                      <Popup>
                        <strong>{country.country}</strong><br />
                        Score: {country.overall_score}%<br />
                        Quality: {QUALITY_LABELS[country.quality_level]}
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>
              )}
            </div>
            <div className="map-legend" style={{ padding: '12px 16px', borderTop: '1px solid #e5e7eb' }}>
              {Object.entries(QUALITY_COLORS).map(([level, color]) => (
                <span key={level} className="legend-item">
                  <span className="legend-color" style={{ backgroundColor: color }}></span>
                  {QUALITY_LABELS[level]}
                </span>
              ))}
            </div>
          </div>

          {/* Country Detail Panel */}
          {selectedCountry && (
            <div className="card country-detail-panel">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 style={{ margin: 0 }}>{selectedCountry.country}</h3>
                <button
                  onClick={() => setSelectedCountry(null)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
                >
                  <XCircle size={20} color="#6b7280" />
                </button>
              </div>

              <div className="quality-score-badge" style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '12px 16px',
                backgroundColor: `${QUALITY_COLORS[selectedCountry.quality_level]}15`,
                borderRadius: 8,
                marginBottom: 16,
              }}>
                {getQualityIcon(selectedCountry.quality_level, 32)}
                <div>
                  <div style={{ fontSize: 24, fontWeight: 600 }}>{selectedCountry.overall_score}%</div>
                  <div style={{ color: '#6b7280', fontSize: 14 }}>{QUALITY_LABELS[selectedCountry.quality_level]} Quality</div>
                </div>
              </div>

              <p style={{ color: '#6b7280', fontSize: 14, marginBottom: 16 }}>{selectedCountry.summary}</p>

              <h4 style={{ marginBottom: 12 }}>Dataset Quality</h4>
              <div className="dataset-list">
                {Object.entries(selectedCountry.datasets).map(([name, dataset]) => (
                  <div key={name} className="dataset-item" style={{
                    padding: '12px',
                    backgroundColor: '#f9fafb',
                    borderRadius: 6,
                    marginBottom: 8,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Database size={16} color="#6b7280" />
                        <span style={{ fontWeight: 500 }}>{name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                      </div>
                      {getQualityIcon(dataset.quality_level, 18)}
                    </div>

                    {dataset.available ? (
                      <>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6b7280' }}>
                          <span>Records: {dataset.record_count.toLocaleString()}</span>
                          <span>Completeness: {dataset.completeness}%</span>
                        </div>
                        <div style={{ marginTop: 6, height: 4, backgroundColor: '#e5e7eb', borderRadius: 2 }}>
                          <div style={{
                            width: `${dataset.completeness}%`,
                            height: '100%',
                            backgroundColor: QUALITY_COLORS[dataset.quality_level],
                            borderRadius: 2,
                          }} />
                        </div>
                        {dataset.issues.length > 0 && (
                          <div style={{ marginTop: 8 }}>
                            {dataset.issues.map((issue, i) => (
                              <div key={i} style={{ fontSize: 12, color: '#f97316', display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                                <AlertTriangle size={12} />
                                {issue}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    ) : (
                      <div style={{ fontSize: 13, color: '#9ca3af' }}>No data available</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Countries Table */}
        <div className="card" style={{ marginTop: 16 }}>
          <h3 className="card-title">All Countries</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div>
              <h4 style={{ marginBottom: 12, fontSize: 14 }}>Dataset Coverage</h4>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={datasetCoverage} layout="vertical">
                  <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                  <YAxis type="category" dataKey="name" width={120} fontSize={12} />
                  <Tooltip formatter={(value) => `${value}%`} />
                  <Bar dataKey="coverage" fill="#2563eb" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <h4 style={{ marginBottom: 12, fontSize: 14 }}>Country Scores</h4>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={countriesSorted.slice(0, 10)}>
                  <XAxis dataKey="country" angle={-45} textAnchor="end" height={60} fontSize={11} />
                  <YAxis domain={[0, 100]} />
                  <Tooltip formatter={(value) => `${value}%`} />
                  <Bar dataKey="overall_score" name="Score">
                    {countriesSorted.slice(0, 10).map((entry, index) => (
                      <Cell key={index} fill={QUALITY_COLORS[entry.quality_level]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ maxHeight: 300, overflow: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Country</th>
                  <th>Score</th>
                  <th>Quality</th>
                  <th>Power Plants</th>
                  <th>Load Profiles</th>
                  <th>Hydropower</th>
                  <th>Resources</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {countriesSorted.map((country) => (
                  <tr
                    key={country.country}
                    onClick={() => setSelectedCountry(country)}
                    style={{ cursor: 'pointer' }}
                    className={selectedCountry?.country === country.country ? 'selected' : ''}
                  >
                    <td style={{ fontWeight: 500 }}>{country.country}</td>
                    <td>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        backgroundColor: `${QUALITY_COLORS[country.quality_level]}20`,
                        color: QUALITY_COLORS[country.quality_level],
                        borderRadius: 4,
                        fontWeight: 500,
                        fontSize: 13,
                      }}>
                        {country.overall_score}%
                      </span>
                    </td>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        {getQualityIcon(country.quality_level, 14)}
                        {QUALITY_LABELS[country.quality_level]}
                      </span>
                    </td>
                    <td>{country.datasets.power_plants?.available ? <CheckCircle size={16} color="#22c55e" /> : <XCircle size={16} color="#9ca3af" />}</td>
                    <td>{country.datasets.load_profiles?.available ? <CheckCircle size={16} color="#22c55e" /> : <XCircle size={16} color="#9ca3af" />}</td>
                    <td>{country.datasets.hydropower?.available ? <CheckCircle size={16} color="#22c55e" /> : <XCircle size={16} color="#9ca3af" />}</td>
                    <td>{country.datasets.resource_potential?.available ? <CheckCircle size={16} color="#22c55e" /> : <XCircle size={16} color="#9ca3af" />}</td>
                    <td><ChevronRight size={16} color="#9ca3af" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
