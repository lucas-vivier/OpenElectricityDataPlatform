import { Link } from 'react-router-dom';
import { Key, ExternalLink } from 'lucide-react';

interface DataSource {
  name: string;
  type: string;
  coverage: string;
  license: string;
  url: string;
  requiresApiKey?: boolean;
  apiKeyNote?: string;
}

export default function Catalog() {
  const sources: DataSource[] = [
    {
      name: 'Global Integrated Power',
      type: 'Power plant database',
      coverage: 'Global',
      license: 'CC-BY',
      url: 'https://globalenergymonitor.org/',
    },
    {
      name: 'Global Power Plant Database',
      type: 'Power plant database',
      coverage: 'Global (historical)',
      license: 'CC-BY 4.0',
      url: 'https://datasets.wri.org/dataset/globalpowerplantdatabase',
    },
    {
      name: 'Renewables.ninja',
      type: 'Solar/wind capacity factors',
      coverage: 'Global (gridded)',
      license: 'CC-BY-NC 4.0',
      url: 'https://renewables.ninja/',
      requiresApiKey: true,
      apiKeyNote: 'Free registration required',
    },
    {
      name: 'ERA5 Climate Data',
      type: 'Climate reanalysis',
      coverage: 'Global (gridded)',
      license: 'Copernicus License',
      url: 'https://cds.climate.copernicus.eu/',
      requiresApiKey: true,
      apiKeyNote: 'CDS account required',
    },
    {
      name: 'Toktarova (2019)',
      type: 'Hourly load profiles',
      coverage: 'Global (country-level)',
      license: 'Research use',
      url: 'https://doi.org/10.1016/j.energy.2019.02.051',
    },
    {
      name: 'African Hydropower Atlas',
      type: 'Hydropower plants',
      coverage: 'Africa',
      license: 'IHA Terms',
      url: 'https://www.hydropower.org/',
    },
    {
      name: 'Global Hydropower Tracker',
      type: 'Hydropower plants',
      coverage: 'Global',
      license: 'CC-BY',
      url: 'https://globalenergymonitor.org/projects/global-hydropower-tracker/',
    },
    {
      name: 'IRENA MSR Data',
      type: 'Solar/Wind resource potential',
      coverage: 'Central Africa',
      license: 'IRENA Terms',
      url: 'https://www.irena.org/',
    },
    {
      name: 'Our World in Data Energy',
      type: 'Socio-economic indicators',
      coverage: 'Global',
      license: 'CC-BY',
      url: 'https://github.com/owid/energy-data',
    },
  ];

  return (
    <div className="page">
      <h1>Data Catalog</h1>
      <p className="subtitle">
        Overview of data sources available in OpenEnergyData
      </p>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 className="card-title">Available Data Sources</h3>
        <p style={{ color: '#6b7280', fontSize: 14, marginBottom: 16 }}>
          Some data sources require API keys. Configure your keys in{' '}
          <Link to="/settings" style={{ color: '#2563eb' }}>Settings</Link>.
        </p>
        <table className="table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Data Type</th>
              <th>Coverage</th>
              <th>License</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source, i) => (
              <tr key={i}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <strong>{source.name}</strong>
                    {source.requiresApiKey && (
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        padding: '2px 8px',
                        background: '#fef3c7',
                        color: '#92400e',
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 500,
                      }}>
                        <Key size={12} />
                        API Key
                      </span>
                    )}
                  </div>
                  {source.apiKeyNote && (
                    <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
                      {source.apiKeyNote}
                    </div>
                  )}
                </td>
                <td>{source.type}</td>
                <td>{source.coverage}</td>
                <td>{source.license}</td>
                <td>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                  >
                    Visit <ExternalLink size={14} />
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 className="card-title">API Endpoints</h3>
        <p style={{ marginBottom: 16, color: '#6b7280' }}>
          Access data programmatically using the REST API:
        </p>
        <pre style={{ background: '#f3f4f6', padding: 16, borderRadius: 6, overflow: 'auto' }}>
{`# List regions
GET /api/regions

# Get power plants
GET /api/power-plants?region=south_africa

# Get load profiles
GET /api/load-profiles?region=south_africa&year=2020

# Compute representative days
POST /api/treatments/representative-days?region=south_africa&n_days=12

# Export as CSV
GET /api/exports/power-plants/csv?region=south_africa`}
        </pre>
      </div>

      <div className="card">
        <h3 className="card-title">Python Usage Example</h3>
        <pre style={{ background: '#f3f4f6', padding: 16, borderRadius: 6, overflow: 'auto' }}>
{`import requests

# Fetch power plants
response = requests.get(
    "http://localhost:8000/api/power-plants",
    params={"region": "south_africa"}
)
plants = response.json()

print(f"Found {plants['count']} power plants")
print(f"Total capacity: {plants['total_capacity_mw']:,.0f} MW")

# Use in your model
for plant in plants['plants']:
    print(f"{plant['name']}: {plant['capacity_mw']} MW ({plant['technology']})")`}
        </pre>
      </div>
    </div>
  );
}
