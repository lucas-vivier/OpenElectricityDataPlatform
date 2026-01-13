# OpenEnergyData

Unified access to open data for capacity expansion modeling.

## Overview

[![EPM](https://img.shields.io/badge/GitHub-EPM-181717?logo=github)](https://github.com/ESMAP-World-Bank-Group/EPM)
[![Docs](https://img.shields.io/badge/docs-EPM-blue)](https://esmap-world-bank-group.github.io/EPM/)

OpenEnergyData provides a FastAPI backend and a React frontend for:

- Unified access to key open data sources for energy modeling
- Pre-processing treatments (representative days, simplified grid)
- Export to model-ready formats (CSV, GeoJSON)
- Direct integration with [EPM (Energy Planning Model)](https://github.com/ESMAP-World-Bank-Group/EPM)
- Automatic report generation

## Target Users

- World Bank energy modelers
- External researchers working on capacity expansion models
- Open to all (no authentication required)

## EPM Integration

[![EPM](https://img.shields.io/badge/GitHub-EPM-181717?logo=github)](https://github.com/ESMAP-World-Bank-Group/EPM)

OpenEnergyData provides direct integration with the **EPM (Energy Planning Model)** developed by the World Bank ESMAP team. Data exported from this platform is formatted to be directly compatible with EPM input requirements.

- 📖 [EPM Documentation](https://esmap-world-bank-group.github.io/EPM/)
- 💻 [EPM GitHub Repository](https://github.com/ESMAP-World-Bank-Group/EPM)

## Data Sources

This platform integrates data from World Bank EPM (Electricity Planning Model) pre-analysis workflows and external APIs.

### Power Plants

| Source | Description | Coverage | Update |
|--------|-------------|----------|--------|
| [Global Integrated Power](https://globalenergymonitor.org/projects/global-integrated-power/) | Comprehensive power plant database with capacity, technology, status, and coordinates | Global (120,000+ plants) | April 2025 |

The Global Integrated Power database from Global Energy Monitor includes:
- Operating, under construction, announced, and retired plants
- Technology types: Coal, Gas, Oil, Nuclear, Hydro, Solar, Wind, Biomass, Geothermal, Battery
- Capacity in MW, start year, retirement year, owner information

### Hydropower

| Source | Description | Coverage |
|--------|-------------|----------|
| [African Hydropower Atlas v2.0](https://energydata.info/) | Detailed hydropower plants with climate scenario projections | Africa (634 plants) |
| [Global Hydropower Tracker](https://globalenergymonitor.org/projects/global-hydropower-tracker/) | Global hydropower database | Global |

The African Hydropower Atlas includes:
- Plant capacity, location, river/basin information
- Reservoir characteristics
- Climate change projections (SSP1-RCP26, SSP4-RCP60, SSP5-RCP85)

### Renewable Energy Resource Potential

| Source | Description | Coverage |
|--------|-------------|----------|
| [IRENA MSR](https://www.irena.org/) | Model Solar/Wind Resource - optimal sites covering 5% of country area | Central Africa (10 countries) |

IRENA MSR data includes:
- Site-level capacity potential (MW)
- Capacity factors
- LCOE estimates
- Distance to grid infrastructure
- Hourly generation profiles

### Socio-Economic Data

| Source | Description | Coverage |
|--------|-------------|----------|
| [Our World in Data (OWID)](https://github.com/owid/energy-data) | Energy statistics, GDP, population, electricity demand, carbon intensity | Global (200+ countries) |

OWID Energy Dataset includes:
- GDP and population by country and year
- Electricity demand and generation (TWh)
- Energy mix: renewables, fossil, nuclear shares
- Carbon intensity of electricity (gCO2/kWh)
- Per-capita energy consumption

### Time Series Data

| Source | Description | Access Method |
|--------|-----------|---------------|
| [Renewables.ninja](https://renewables.ninja) | Solar/wind capacity factors | API (requires user key) |
| [ENTSO-E Transparency](https://transparency.entsoe.eu/) | European load and generation data | API (requires user key) |
| [ERA5 (Copernicus CDS)](https://cds.climate.copernicus.eu/) | Climate reanalysis data | API (requires user key) |
| Toktarova et al. | Hourly load profiles by country | Static file |

### Data Files Location

Pre-processed data files are stored in `data/sources/`:

```
data/sources/
├── Global-Integrated-Power-April-2025.xlsx    # Global Integrated Power plants (120K+ plants)
├── African_Hydropower_Atlas_v2-0.xlsx         # African hydro with climate scenarios
├── Global-Hydropower-Tracker-April-2025.xlsx  # Global hydropower
├── SolarPV_BestMSRsToCover5%CountryArea.csv   # IRENA solar potential (170 MB)
├── Wind_BestMSRsToCover5%CountryArea.csv      # IRENA wind potential (23 MB)
├── owid-energy-data.csv                       # OWID socio-economic data (8.7 MB)
├── data_capp_solar.csv                        # Processed solar profiles
└── data_capp_wind.csv                         # Processed wind profiles
```

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/openenergydata.git
cd openenergydata

# Create and activate a conda environment
conda create -n openenergydata python=3.11
conda activate openenergydata

# Install dependencies
pip install -e .

# For PDF export support
pip install -e ".[pdf]"

# For development
pip install -e ".[dev]"
```

## Usage

### Run the API (FastAPI)

```bash
uvicorn openenergydata.api.main:app --reload --host 0.0.0.0 --port 8000
```

If you see `ModuleNotFoundError: No module named 'openenergydata'`, make sure the
package is installed (`pip install -e .`) or run with:

```bash
PYTHONPATH=src uvicorn openenergydata.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Run the Frontend (React)

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

### CLI

```bash
openenergydata --help
```

## Project Structure

```
openenergydata/
├── src/openenergydata/    # Core library
│   ├── data/              # Data loading and caching
│   ├── treatments/        # Representative days, grid simplification
│   ├── export/            # CSV, GeoJSON, PDF export
│   ├── viz/               # Maps and charts
│   └── api/               # FastAPI app and routers
├── frontend/              # React application (Vite)
├── data/                  # Metadata and region definitions
├── tests/                 # Test suite
└── scripts/               # Utility scripts
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Format code
ruff format .
```

## API Configuration

To use external APIs, copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

Required API keys:

- **Renewables.ninja**: Register at https://renewables.ninja/
- **ENTSO-E**: Register at https://transparency.entsoe.eu/
- **ERA5 (CDS)**: Register at https://cds.climate.copernicus.eu/

## License

MIT

## Data Attribution

Data sources used in this project:

- [Global Integrated Power](https://globalenergymonitor.org/projects/global-integrated-power/) - Global Energy Monitor, CC-BY
- [Global Hydropower Tracker](https://globalenergymonitor.org/projects/global-hydropower-tracker/) - Global Energy Monitor, CC-BY
- [African Hydropower Atlas](https://energydata.info/) - World Bank / IFC
- [IRENA Global Atlas](https://www.irena.org/Energy-Transition/Technology/Global-Atlas) - IRENA
- [Our World in Data Energy](https://github.com/owid/energy-data) - OWID, CC-BY
- [Renewables.ninja](https://renewables.ninja) - Pfenninger & Staffell, CC-BY-NC 4.0
- [ERA5](https://cds.climate.copernicus.eu/) - Copernicus Climate Change Service
- Grid data: OpenStreetMap contributors, ODbL
