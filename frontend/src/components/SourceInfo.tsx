import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

export interface DataSource {
  name: string;
  provider: string;
  url: string;
  license: string;
  description: string;
  update_frequency: string;
  requires_api_key?: boolean;
  columns?: Record<string, string>;
}

interface SourceInfoProps {
  source?: DataSource;
  sources?: DataSource[];  // Support multiple sources
  defaultExpanded?: boolean;
}

export default function SourceInfo({ source, sources, defaultExpanded = false }: SourceInfoProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  // Support both single source and multiple sources
  const allSources = sources || (source ? [source] : []);

  // Guard against no sources
  if (allSources.length === 0) {
    return null;
  }

  return (
    <div className="source-info">
      <button
        className="source-info-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        <span>About this data {allSources.length > 1 && `(${allSources.length} sources)`}</span>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {expanded && (
        <div className="source-info-content">
          {allSources.map((src, index) => (
            <div key={src.name} style={{ marginBottom: index < allSources.length - 1 ? 16 : 0 }}>
              {allSources.length > 1 && (
                <h5 style={{
                  margin: '0 0 12px 0',
                  paddingBottom: 8,
                  borderBottom: '1px solid var(--gray-200)',
                  color: 'var(--gray-700)',
                  fontSize: 14,
                  fontWeight: 600
                }}>
                  {src.name}
                </h5>
              )}
              <div className="source-info-grid">
                <div className="source-info-item">
                  <span className="source-info-label">Source</span>
                  <a href={src.url} target="_blank" rel="noopener noreferrer" className="source-info-link">
                    {src.name} <ExternalLink size={12} />
                  </a>
                </div>
                <div className="source-info-item">
                  <span className="source-info-label">Provider</span>
                  <span>{src.provider}</span>
                </div>
                <div className="source-info-item">
                  <span className="source-info-label">License</span>
                  <span>{src.license}</span>
                </div>
                <div className="source-info-item">
                  <span className="source-info-label">Updates</span>
                  <span>{src.update_frequency}</span>
                </div>
              </div>

              <p className="source-info-description">{src.description}</p>

              {src.columns && Object.keys(src.columns).length > 0 && (
                <div className="source-info-columns">
                  <span className="source-info-label">Data Fields</span>
                  <ul>
                    {Object.entries(src.columns).map(([col, desc]) => (
                      <li key={col}>
                        <code>{col}</code>: {desc}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Data sources metadata - matches sources.json
export const DATA_SOURCES: Record<string, DataSource> = {
  // Legacy key for backwards compatibility
  power_plants: {
    name: 'Global Integrated Power',
    provider: 'Global Energy Monitor',
    url: 'https://globalenergymonitor.org/',
    license: 'CC-BY',
    description: 'Comprehensive database of power generation facilities worldwide',
    update_frequency: 'quarterly',
    columns: {
      name: 'Plant or project name',
      technology: 'Generation technology (Solar, Wind, Hydro, etc.)',
      capacity_mw: 'Installed capacity in megawatts',
      status: 'Operating status (Operating, Construction, etc.)',
      country: 'Country name',
      latitude: 'Geographic latitude',
      longitude: 'Geographic longitude',
    },
  },
  // GEM - Global Energy Monitor
  gem: {
    name: 'Global Integrated Power (GEM)',
    provider: 'Global Energy Monitor',
    url: 'https://globalenergymonitor.org/',
    license: 'CC-BY',
    description: 'Comprehensive database of power generation facilities worldwide, including coal, gas, oil, nuclear, hydro, solar, wind, and other technologies. Updated quarterly with global coverage.',
    update_frequency: 'quarterly',
    columns: {
      name: 'Plant or project name',
      technology: 'Generation technology (Solar, Wind, Hydro, etc.)',
      capacity_mw: 'Installed capacity in megawatts',
      status: 'Operating status (Operating, Construction, etc.)',
      country: 'Country name',
      latitude: 'Geographic latitude',
      longitude: 'Geographic longitude',
    },
  },
  // GPPD - Global Power Plant Database
  gppd: {
    name: 'Global Power Plant Database (GPPD)',
    provider: 'World Resources Institute',
    url: 'https://datasets.wri.org/dataset/globalpowerplantdatabase',
    license: 'CC-BY 4.0',
    description: 'A comprehensive, open source database of power plants around the world. Contains data on approximately 35,000 power plants from 167 countries.',
    update_frequency: 'static (June 2021)',
    columns: {
      name: 'Plant name',
      technology: 'Primary fuel type',
      capacity_mw: 'Installed capacity in megawatts',
      country: 'Country name',
      latitude: 'Geographic latitude',
      longitude: 'Geographic longitude',
      commissioning_year: 'Year of commissioning',
      owner: 'Plant owner',
    },
  },
  load_profiles: {
    name: 'Synthetic Load Profiles',
    provider: 'Toktarova et al. (2019)',
    url: 'https://doi.org/10.1016/j.energy.2019.02.051',
    license: 'Research use',
    description: 'Synthetic hourly electricity demand profiles for all countries',
    update_frequency: 'static',
    columns: {
      zone: 'Country or zone identifier',
      month: 'Month (1-12)',
      day: 'Day of month (1-31)',
      hour: 'Hour of day (0-23)',
      value: 'Normalized demand (0-1)',
    },
  },
  renewables_ninja: {
    name: 'Renewables.ninja',
    provider: 'Renewables.ninja',
    url: 'https://renewables.ninja/',
    license: 'CC-BY-NC 4.0',
    description: 'Simulated hourly solar and wind power output based on weather data',
    update_frequency: 'on-demand API',
    requires_api_key: true,
    columns: {
      zone: 'Location identifier',
      month: 'Month (1-12)',
      day: 'Day of month (1-31)',
      hour: 'Hour of day (0-23)',
      capacity_factor: 'Capacity factor (0-1)',
    },
  },
  hydropower: {
    name: 'African Hydropower Atlas & Global Energy Monitor',
    provider: 'IHA / Global Energy Monitor',
    url: 'https://www.hydropower.org/',
    license: 'Various',
    description: 'Hydropower plant data from African Hydropower Atlas (with river/reservoir info) and Global Integrated Power (hydropower filtered)',
    update_frequency: 'annual',
    columns: {
      name: 'Plant name',
      capacity_mw: 'Installed capacity in MW',
      status: 'Operating status',
      country: 'Country name',
      river_name: 'River name',
    },
  },
  resource_potential: {
    name: 'IRENA MSR Data',
    provider: 'IRENA',
    url: 'https://www.irena.org/',
    license: 'IRENA Terms',
    description: 'Solar and wind resource potential from Modelled Suitable Regions (MSR) analysis',
    update_frequency: 'periodic',
    columns: {
      country: 'Country name',
      capacity_mw: 'Technical potential capacity (MW)',
      capacity_factor: 'Average capacity factor',
      lcoe: 'Levelized cost of electricity',
    },
  },
  socioeconomic: {
    name: 'Our World in Data Energy',
    provider: 'Our World in Data',
    url: 'https://github.com/owid/energy-data',
    license: 'CC-BY',
    description: 'Comprehensive energy and socio-economic indicators by country and year',
    update_frequency: 'annual',
    columns: {
      country: 'Country name',
      year: 'Reference year',
      population: 'Total population',
      gdp: 'GDP in current USD',
      electricity_generation: 'Electricity generation (TWh)',
      renewables_share_elec: 'Renewables share in electricity (%)',
    },
  },
};
