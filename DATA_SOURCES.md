# Data Sources

This document describes all data sources used by OpenEnergyData, their origins, formats, and how they flow through the system.

## Data Loading Cascade

When requesting data, the system checks sources in this order:

1. **Local Parquet** (`data/local/{region}/`) - Preprocessed, fastest
2. **Zenodo** - Downloads on-demand if local not found
3. **Source Files** (`data/sources/`) - Raw data, requires processing
4. **Mock Data** - Development fallback only

## Data Sources Overview

| Dataset | Source | License | Format | Update Frequency |
|---------|--------|---------|--------|------------------|
| Power Plants | Global Energy Monitor | CC-BY | Excel/CSV | Quarterly |
| Load Profiles | Toktarova et al. | CC-BY | CSV | Static (2020) |
| Solar/Wind Profiles | Renewables.ninja | API Terms | API/CSV | On-demand |
| Hydropower | African Hydropower Atlas | CC-BY | GeoPackage | Annual |
| Resource Potential | IRENA GlobalAtlas | CC-BY | NetCDF/CSV | Static |

---

## Power Plants

### Global Integrated Power (GIP)

- **Provider**: [Global Energy Monitor](https://globalenergymonitor.org/)
- **Description**: Comprehensive database of power plants worldwide including capacity, technology, status, and coordinates
- **License**: CC-BY 4.0
- **Local Path**: `data/sources/Global-Integrated-Power-*.xlsx`
- **Output**: `power_plants.parquet`

**Columns**:
- `name`: Plant name
- `technology`: Coal, Gas, Solar, Wind, Hydro, Nuclear, etc.
- `capacity_mw`: Installed capacity in megawatts
- `status`: Operating, Construction, Planned, Retired
- `country`: Country name
- `latitude`, `longitude`: Coordinates

---

## Load Profiles

### Toktarova Demand Profiles

- **Provider**: Toktarova et al. (2019)
- **Description**: Hourly electricity demand profiles for African countries
- **Citation**: Toktarova, A., et al. "Long term load projection in high resolution for all countries globally"
- **License**: CC-BY 4.0
- **Local Path**: `data/sources/Toktarova_*.csv`
- **Output**: `load_profiles.parquet`

**Columns**:
- `zone`: Country/region name
- `month`, `day`, `hour`: Time indices
- `value`: Normalized demand (0-1)

---

## Renewable Energy Profiles

### Renewables.ninja

- **Provider**: [Renewables.ninja](https://www.renewables.ninja/)
- **Description**: Simulated hourly capacity factors for solar PV and wind
- **License**: API terms of service
- **API Key Required**: Yes (`API_TOKEN_RENEWABLES_NINJA`)
- **Output**: `re_profiles_solar.parquet`, `re_profiles_wind.parquet`

**Columns**:
- `zone`: Location identifier
- `month`, `day`, `hour`: Time indices
- `capacity_factor`: Output as fraction of capacity (0-1)

### IRENA Global Atlas

- **Provider**: [IRENA](https://globalatlas.irena.org/)
- **Description**: Multi-Site Resource (MSR) data with solar/wind potential
- **License**: CC-BY 4.0
- **Local Path**: `data/sources/IRENA_MSR_*.nc`
- **Output**: `resource_potential_solar.parquet`, `resource_potential_wind.parquet`

**Columns**:
- `country`: Country name
- `msr_id`: Site identifier
- `latitude`, `longitude`: Coordinates
- `capacity_mw`: Potential capacity
- `capacity_factor`: Annual average
- `lcoe`: Levelized cost of electricity

---

## Hydropower

### African Hydropower Atlas

- **Provider**: [African Hydropower Atlas](https://africahydropoweratlas.org/)
- **Description**: Existing and planned hydropower plants in Africa with climate scenarios
- **License**: CC-BY 4.0
- **Local Path**: `data/sources/african_hydro_atlas.gpkg`
- **Output**: `hydropower.parquet`

**Columns**:
- `name`: Plant name
- `technology`: Run-of-river, Reservoir, Pumped storage
- `capacity_mw`: Installed capacity
- `status`: Operating, Construction, Planned
- `country`: Country name
- `latitude`, `longitude`: Coordinates
- `river_name`, `river_basin`: Hydrological info
- `reservoir_size_mcm`: Reservoir volume in million cubic meters

### Global Hydropower Tracker

- **Provider**: [Global Energy Monitor](https://globalenergymonitor.org/projects/global-hydropower-tracker/)
- **Description**: Global database of hydropower plants
- **License**: CC-BY 4.0
- **Local Path**: `data/sources/Global-Hydropower-Tracker-*.xlsx`

---

## Preprocessed Data (data_capp)

These are pre-processed files ready for capacity expansion modeling:

| File | Description |
|------|-------------|
| `data_capp_solar.csv` | Representative solar profiles by zone |
| `data_capp_wind.csv` | Representative wind profiles by zone |
| `data_capp_load.csv` | Representative load profiles by zone |

---

## Directory Structure

```
data/
├── local/                    # Preprocessed parquet files (per region)
│   ├── south_africa/
│   │   ├── power_plants.parquet
│   │   ├── hydropower.parquet
│   │   ├── load_profiles.parquet
│   │   └── zenodo_record.json  # Zenodo upload metadata
│   └── west_africa/
│       └── ...
├── sources/                  # Raw source files
│   ├── Global-Integrated-Power-*.xlsx
│   ├── african_hydro_atlas.gpkg
│   └── ...
└── metadata/                 # Region definitions
    ├── regions.yaml
    └── data_sources.yaml
```

---

## Adding New Data Sources

1. Place raw files in `data/sources/`
2. Create a loader in `src/openenergydata/data/sources/`
3. Add preprocessing to `scripts/preprocess_data.py`
4. Update `data/metadata/data_sources.yaml`
5. Run preprocessing to generate parquet files
6. Upload to Zenodo with `scripts/zenodo/upload_to_zenodo.py`

---

## Zenodo Integration

Preprocessed data is hosted on [Zenodo](https://zenodo.org/) for:
- Reproducibility (DOI for each dataset version)
- Fast downloads without processing
- Version tracking

### Upload workflow:
```bash
# Set API token
export ZENODO_API_TOKEN=your_token

# Upload a region
python scripts/zenodo/upload_to_zenodo.py --region south_africa --publish
```

### Download workflow:
```bash
# Download a region
python scripts/zenodo/download_from_zenodo.py --region south_africa

# Or let the loader download automatically (default behavior)
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ZENODO_API_TOKEN` | Token for Zenodo uploads |
| `ZENODO_ENABLED` | Enable/disable Zenodo downloads (default: true) |
| `ZENODO_RECORD_{REGION}` | Override Zenodo record ID for a region |
| `API_TOKEN_RENEWABLES_NINJA` | Renewables.ninja API key |
| `API_TOKEN_ENTSOE` | ENTSO-E API key |
| `CDS_API_KEY` | Copernicus CDS API key |
