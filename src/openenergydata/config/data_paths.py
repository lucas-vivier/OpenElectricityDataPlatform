"""Data source paths configuration.

Centralized configuration for all data source file paths.
"""

from pathlib import Path
from typing import Optional

# Base data directory (relative to project root)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = _PROJECT_ROOT / "data"
SOURCES_DIR = DATA_DIR / "sources"
LOCAL_DIR = DATA_DIR / "local"
METADATA_DIR = DATA_DIR / "metadata"


# Data source file paths
DATA_SOURCES = {
    # Power Plants
    "global_integrated_power_plants": SOURCES_DIR / "Global-Integrated-Power-April-2025.xlsx",
    "global_power_plant_database": SOURCES_DIR / "global_power_plant_database.csv",

    # Hydropower
    "african_hydro_atlas": SOURCES_DIR / "African_Hydropower_Atlas_v2-0.xlsx",
    "global_hydro_tracker": SOURCES_DIR / "Global-Hydropower-Tracker-April-2025.xlsx",

    # IRENA Resource Potential
    "irena_solar_msr": SOURCES_DIR / "SolarPV_BestMSRsToCover5%CountryArea.csv",
    "irena_wind_msr": SOURCES_DIR / "Wind_BestMSRsToCover5%CountryArea.csv",

    # Processed RE Profiles (representative days)
    "re_profiles_solar": SOURCES_DIR / "data_capp_solar.csv",
    "re_profiles_wind": SOURCES_DIR / "data_capp_wind.csv",

    # Socio-Economic Data
    "owid_energy": SOURCES_DIR / "owid-energy-data.csv",
}


def get_data_source_path(source_name: str) -> Optional[Path]:
    """Get the path for a data source.

    Args:
        source_name: Name of the data source (e.g., 'global_integrated_power_plants')

    Returns:
        Path to the data source file, or None if not configured
    """
    return DATA_SOURCES.get(source_name)


def get_local_region_path(region: str) -> Path:
    """Get the local data directory for a region.

    Args:
        region: Region identifier (e.g., 'south_africa')

    Returns:
        Path to the region's local data directory
    """
    return LOCAL_DIR / region.lower().replace(" ", "_")


def data_source_exists(source_name: str) -> bool:
    """Check if a data source file exists.

    Args:
        source_name: Name of the data source

    Returns:
        True if the file exists
    """
    path = get_data_source_path(source_name)
    return path is not None and path.exists()
