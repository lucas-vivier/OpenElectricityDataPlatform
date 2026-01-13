export default function About() {
  return (
    <div className="page">
      <h1>About OpenEnergyData</h1>
      <p className="subtitle">
        Unified API for open energy data - capacity expansion modeling
      </p>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 className="card-title">Overview</h3>
        <p style={{ lineHeight: 1.6, color: '#374151' }}>
          <strong>OpenEnergyData</strong> provides unified access to key open data sources
          for energy capacity expansion modeling. Energy modelers at the World Bank and
          research institutions spend significant time collecting, cleaning, and formatting
          open data from multiple sources before running capacity expansion models.
          Each source has different formats, APIs, and quirks.
        </p>
        <p style={{ lineHeight: 1.6, color: '#374151', marginTop: 16 }}>
          This platform aims to:
        </p>
        <ul style={{ lineHeight: 1.8, color: '#374151', marginLeft: 20, marginTop: 8 }}>
          <li>Provide unified access to key open data sources via REST API</li>
          <li>Apply pre-processing treatments (representative days, seasonal conversion)</li>
          <li>Export to model-ready formats (CSV, GeoJSON)</li>
          <li>Enable direct integration with PyPSA, OSeMOSYS, and other models</li>
        </ul>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 className="card-title">Architecture</h3>
        <pre style={{ background: '#f3f4f6', padding: 16, borderRadius: 6, overflow: 'auto', fontSize: 13 }}>
{`┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                        │
│                                                             │
│  GET  /api/regions                                          │
│  GET  /api/power-plants?region=...                          │
│  GET  /api/load-profiles?region=...&year=...                │
│  POST /api/treatments/representative-days                   │
│  GET  /api/exports/...                                      │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      ┌──────────┐   ┌──────────┐   ┌──────────┐
      │  React   │   │  Python  │   │  Jupyter │
      │  Web UI  │   │  Script  │   │ Notebook │
      └──────────┘   └──────────┘   └──────────┘`}
        </pre>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 className="card-title">Features</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
          <div>
            <h4 style={{ fontSize: 14, marginBottom: 8 }}>Current (MVP)</h4>
            <ul style={{ lineHeight: 1.8, color: '#374151', marginLeft: 20 }}>
              <li>Power plant data (Global Integrated Power database)</li>
              <li>Load profiles (Toktarova synthetic)</li>
              <li>RE capacity factors (via API)</li>
              <li>Representative days clustering</li>
              <li>CSV and GeoJSON export</li>
            </ul>
          </div>
          <div>
            <h4 style={{ fontSize: 14, marginBottom: 8 }}>Coming Soon</h4>
            <ul style={{ lineHeight: 1.8, color: '#6b7280', marginLeft: 20 }}>
              <li>Grid data (OpenInfraMap)</li>
              <li>Hydro inflows and reservoirs</li>
              <li>PDF report generation</li>
              <li>Additional regions</li>
              <li>Model format converters</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Attribution</h3>
        <p style={{ lineHeight: 1.6, color: '#374151' }}>
          When using data from OpenEnergyData, please include the following attribution:
        </p>
        <pre style={{ background: '#f3f4f6', padding: 16, borderRadius: 6, marginTop: 12, fontSize: 13 }}>
{`Data sources:
- Global Integrated Power (https://globalenergymonitor.org) - CC-BY
- Renewables.ninja (https://renewables.ninja) - CC-BY-NC 4.0
- Toktarova et al. (2019) load profiles

Tool: OpenEnergyData API`}
        </pre>
      </div>
    </div>
  );
}
