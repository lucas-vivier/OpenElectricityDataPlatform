# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenEnergyData provides a FastAPI backend and React frontend for unified access to open data sources for capacity expansion modeling. It targets World Bank energy modelers and researchers who need pre-processed energy data.

## Tech Stack

- **Python 3.10+** with hatchling build system
- **FastAPI** for the REST API backend
- **React + Vite** for the frontend
- **Pandas/GeoPandas** for data processing
- **Folium** for map visualizations
- **scikit-learn** for clustering (representative days)
- **WeasyPrint** for PDF report generation (optional)

## Project Structure

```
src/openenergydata/     # Core library (installable package)
├── api/                # FastAPI app and routers
├── data/               # Data loaders and caching
├── treatments/         # Representative days, grid simplification
├── export/             # CSV, GeoJSON, PDF export
└── viz/                # Maps and charts

frontend/               # React application (Vite)
├── src/
│   ├── pages/          # Page components
│   └── components/     # Reusable UI components
└── dist/               # Production build

data/metadata/          # Region definitions, source configs
tests/                  # pytest test suite
```

## Common Commands

```bash
# Run the API (FastAPI)
uvicorn openenergydata.api.main:app --reload --host 0.0.0.0 --port 8000

# Run the frontend (React)
cd frontend && npm run dev

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/openenergydata

# Lint and format
ruff check .
ruff format .

# Install in development mode
pip install -e ".[dev]"
```

## Architecture Notes

- **Stateless app**: All data is fetched from external sources (Zenodo/HuggingFace), no database
- **REST API**: FastAPI backend serves data to the React frontend
- **Separation of concerns**: Core logic in `src/openenergydata/`, API in `src/openenergydata/api/`, UI in `frontend/`

## Data Flow

1. User selects region/countries in React frontend
2. Frontend calls FastAPI endpoints
3. API fetches pre-processed data from local files or Zenodo
4. User applies treatments (representative days, grid simplification)
5. User previews data with maps and charts
6. User exports to CSV/GeoJSON/PDF

## Code Style

- Line length: 120 characters
- Linting: ruff with E, F, I, W rules
- Type hints encouraged but not enforced
- Docstrings for public functions

## Key Dependencies

See `pyproject.toml` for full list. Core dependencies:
- fastapi>=0.109
- uvicorn>=0.27
- pandas>=2.0
- geopandas>=0.14
- folium>=0.15
- scikit-learn>=1.4

## Safety Rules

### Before Making Major Changes

1. **Create a checkpoint commit** before any significant refactoring or multi-file changes:
   ```bash
   git add -A && git commit -m "checkpoint: before [description]"
   ```

2. **Update PLAN.md** with your current task status

### Never Do

- **Never modify** `.env`, `.env.*`, or any file with "secret" in the name
- **Never write** to `config/prod/` directory
- **Never run** `rm -rf`, `sudo`, or destructive commands
- **Never push** to remote without explicit user approval
- **Never commit** without explicit user approval

### Always Do

- **Ask before deleting** any files - use `git rm` for tracked files
- **Update PLAN.md** status after completing each task
- **Run tests** after making changes: `pytest` or `npm test`
- **Check for errors** before considering a task complete

### Recovery

If something goes wrong, run:
```bash
./scripts/claude-reset.sh
```

This will restore the working directory to the last commit.
