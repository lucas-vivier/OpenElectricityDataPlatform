"""Data source paths configuration.

Centralized configuration for all data source file paths.
Supports country-based caching with metadata tracking.
"""

import re
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


# Valid data types for country-based caching
VALID_DATA_TYPES = frozenset({
    "power_plants",
    "load_profiles",
    "hydropower",
    "resource_potential_solar",
    "resource_potential_wind",
    "re_profiles_solar",
    "re_profiles_wind",
})


def normalize_country_name_for_path(country: str) -> str:
    """Convert country name to safe filesystem path component.

    Examples:
        "South Africa" -> "south_africa"
        "Cote d'Ivoire" -> "cote_divoire"
        "Democratic Republic of the Congo" -> "democratic_republic_of_the_congo"

    Args:
        country: Country name in any format

    Returns:
        Lowercase, underscore-separated, filesystem-safe string
    """
    normalized = country.lower()
    normalized = normalized.replace(" ", "_")
    normalized = normalized.replace("'", "")
    normalized = normalized.replace("-", "_")
    # Remove any other special characters
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    return normalized


def get_country_cache_dir(data_type: str) -> Path:
    """Get the directory for country-based cache files.

    Args:
        data_type: One of 'power_plants', 'load_profiles', 'hydropower',
                   'resource_potential_solar', 'resource_potential_wind',
                   're_profiles_solar', 're_profiles_wind'

    Returns:
        Path to data/local/{data_type}/

    Raises:
        ValueError: If data_type is not valid
    """
    if data_type not in VALID_DATA_TYPES:
        raise ValueError(f"Invalid data type: {data_type}. Must be one of {VALID_DATA_TYPES}")
    return LOCAL_DIR / data_type


def get_country_cache_path(data_type: str, country: str) -> Path:
    """Get the cache file path for a specific country and data type.

    Args:
        data_type: Data type identifier
        country: Country name (will be normalized)

    Returns:
        Path to data/local/{data_type}/{country_normalized}.parquet
    """
    normalized = normalize_country_name_for_path(country)
    return get_country_cache_dir(data_type) / f"{normalized}.parquet"


def get_cache_metadata_path(data_type: str) -> Path:
    """Get the metadata file path for a data type.

    Args:
        data_type: Data type identifier

    Returns:
        Path to data/local/{data_type}/_metadata.json
    """
    return get_country_cache_dir(data_type) / "_metadata.json"
