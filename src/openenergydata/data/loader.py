"""Main data loader for OpenEnergyData.

Provides unified functions to load power plants, load profiles, and RE profiles
from local files or remote sources.

Loading cascade (country-based):
1. Country-based parquet files (fastest, preprocessed per country)
2. Source files (raw data, requires processing) - cached per country after processing
3. Mock data (for development only)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from ..config.data_paths import get_data_source_path
from ..config.regions import get_countries_for_region
from .cache import (
    cache_country_data,
    load_cached_countries,
)
from .sources.power_plants import load_global_integrated_power_data, load_gppd_data
from .sources.load_profiles import load_toktarova_data, generate_mock_load_profiles
from .sources.renewables import fetch_renewables_ninja
from .sources.hydropower import (
    load_african_hydro_atlas,
    load_hydro_climate_scenarios,
)
from .sources.irena import (
    load_irena_solar_msr,
    load_irena_wind_msr,
    load_processed_re_profiles,
)

logger = logging.getLogger(__name__)


def load_power_plants(
    region: str,
    countries: List[str],
    source_path: Optional[Path] = None,
    source: str = "gem",
) -> Optional[pd.DataFrame]:
    """Load power plant data for the specified region and countries.

    Uses country-based caching: each country's data is cached separately.
    Missing countries are processed from source and cached individually.

    Args:
        region: Region identifier (used to get default countries if none specified)
        countries: List of country names to include
        source_path: Optional path to data file. If None, uses default.
        source: Data source to use - 'gem' for Global Energy Monitor (default),
                'gppd' for Global Power Plant Database

    Returns:
        DataFrame with columns: name, technology, capacity_mw, status,
        country, latitude, longitude
        Returns None if no data found.
    """
    # Get countries from region if not provided
    if not countries:
        countries = get_countries_for_region(region)

    if not countries:
        logger.warning(f"No countries found for region {region}")
        return None

    # For GPPD source, use dedicated loader (no caching for GPPD)
    if source == "gppd":
        gppd_path = get_data_source_path("global_power_plant_database")
        if gppd_path and gppd_path.exists():
            return load_gppd_data(gppd_path, countries)
        return _generate_mock_power_plants(countries)

    # GEM source - use country-based caching
    data_type = "power_plants"

    # Step 1: Load cached countries
    cached_df, missing_countries = load_cached_countries(data_type, countries)

    if not missing_countries:
        # All countries cached - return combined result
        logger.debug(f"All {len(countries)} countries loaded from cache")
        return cached_df

    # Step 2: Process missing countries from source
    logger.info(f"Processing {len(missing_countries)} missing countries from source: {missing_countries}")

    # Determine source file
    if source_path is not None and source_path.exists():
        gip_path = source_path
    else:
        gip_path = get_data_source_path("global_integrated_power_plants")

    if gip_path is None or not gip_path.exists():
        if not cached_df.empty:
            logger.warning(f"Source file not found, returning {len(cached_df)} cached rows only")
            return cached_df
        return _generate_mock_power_plants(countries)

    # Process all missing countries from source at once (more efficient)
    all_source_df = load_global_integrated_power_data(gip_path, missing_countries)

    if all_source_df is not None and not all_source_df.empty:
        # Cache each country individually
        source_filename = gip_path.name
        for country in missing_countries:
            country_df = all_source_df[all_source_df["country"] == country]
            if not country_df.empty:
                cache_country_data(
                    country_df,
                    data_type,
                    country,
                    source="gem",
                    source_file=source_filename,
                )

        # Combine cached + newly processed
        if not cached_df.empty:
            return pd.concat([cached_df, all_source_df], ignore_index=True)
        return all_source_df

    # Return cached data if source processing failed
    if not cached_df.empty:
        return cached_df

    return _generate_mock_power_plants(countries)


def load_load_profiles(
    region: str,
    countries: List[str],
    year: int = 2020,
    source_path: Optional[Path] = None,
) -> Optional[pd.DataFrame]:
    """Load hourly demand profiles for the specified region and countries.

    Uses country-based caching: each country's profiles cached separately.

    Args:
        region: Region identifier
        countries: List of country names to include
        year: Year for the profiles
        source_path: Optional path to Toktarova CSV. If None, uses default.

    Returns:
        DataFrame with columns: zone, month, day, hour, value (normalized 0-1)
        Returns None if no data found.
    """
    # Get countries from region if not provided
    if not countries:
        countries = get_countries_for_region(region)

    if not countries:
        logger.warning(f"No countries found for region {region}")
        return generate_mock_load_profiles([], year)

    data_type = "load_profiles"

    # Step 1: Load cached countries
    cached_df, missing_countries = load_cached_countries(data_type, countries)

    if not missing_countries:
        logger.debug(f"All {len(countries)} countries loaded from cache")
        return cached_df

    # Step 2: Process missing countries from source
    logger.info(f"Processing load profiles for {len(missing_countries)} missing countries")

    # Try loading from Toktarova source
    toktarova_path = source_path
    if toktarova_path is None:
        # No default Toktarova path configured - return cached or mock
        if not cached_df.empty:
            return cached_df
        return generate_mock_load_profiles(countries, year)

    if toktarova_path.exists():
        all_source_df = load_toktarova_data(toktarova_path, missing_countries, year)

        if all_source_df is not None and not all_source_df.empty:
            # Cache each country individually
            source_filename = toktarova_path.name
            for country in missing_countries:
                country_df = all_source_df[all_source_df["zone"] == country]
                if not country_df.empty:
                    cache_country_data(
                        country_df,
                        data_type,
                        country,
                        source="toktarova",
                        source_file=source_filename,
                    )

            if not cached_df.empty:
                return pd.concat([cached_df, all_source_df], ignore_index=True)
            return all_source_df

    # Return cached or mock data
    if not cached_df.empty:
        return cached_df
    return generate_mock_load_profiles(countries, year)


def load_re_profiles(
    region: str,
    countries: List[str],
    year: int,
    tech: str = "solar",
    api_key: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Optional[pd.DataFrame]:
    """Load renewable energy capacity factor profiles.

    Uses country-based caching for stored profiles.

    Args:
        region: Region identifier
        countries: List of country names (used if lat/lon not provided)
        year: Year for the profiles
        tech: Technology type ('solar' or 'wind')
        api_key: Renewables.ninja API key (required for API access)
        latitude: Optional latitude for profile location
        longitude: Optional longitude for profile location

    Returns:
        DataFrame with columns: zone, month, day, hour, capacity_factor (0-1)
        Returns None if no data or API key available.
    """
    # Get countries from region if not provided
    if not countries:
        countries = get_countries_for_region(region)

    data_type = f"re_profiles_{tech}"

    # Step 1: Load cached countries
    if countries:
        cached_df, missing_countries = load_cached_countries(data_type, countries)

        if not missing_countries:
            logger.debug(f"All {len(countries)} countries loaded from cache")
            return cached_df
    else:
        cached_df = pd.DataFrame()
        missing_countries = []

    # Step 2: Try fetching from Renewables.ninja API for missing data
    if api_key and latitude is not None and longitude is not None:
        api_df = fetch_renewables_ninja(
            api_key=api_key,
            lat=latitude,
            lon=longitude,
            year=year,
            technology=tech,
        )
        if api_df is not None and not api_df.empty:
            if not cached_df.empty:
                return pd.concat([cached_df, api_df], ignore_index=True)
            return api_df

    # Return cached data if available
    if not cached_df.empty:
        return cached_df

    return None


def load_hydropower(
    region: str,
    countries: Optional[List[str]] = None,
    source: str = "both",
    verbose: bool = False,
) -> Optional[pd.DataFrame]:
    """Load hydropower data for the specified region and countries.

    Uses country-based caching: each country's data cached separately.

    Args:
        region: Region identifier (e.g., 'southern_africa')
        countries: List of country names to include. If None, uses region countries.
        source: Data source - 'african_atlas', 'gem' (filtered from Global Integrated Power), or 'both'
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: name, technology, capacity_mw, status, country,
        latitude, longitude, river_name, river_basin, reservoir_size_mcm
        Returns None if no data found.
    """
    # Get countries from region if not provided
    if countries is None:
        countries = get_countries_for_region(region)

    if not countries:
        logger.warning(f"No countries found for region {region}")
        return None

    data_type = "hydropower"

    # Step 1: Load cached countries
    cached_df, missing_countries = load_cached_countries(data_type, countries)

    if not missing_countries:
        logger.debug(f"All {len(countries)} countries loaded from cache")
        return cached_df

    # Step 2: Process missing countries from source
    logger.info(f"Processing hydropower for {len(missing_countries)} missing countries")

    dfs = []

    # Load from African Hydropower Atlas
    if source in ("african_atlas", "both"):
        atlas_path = get_data_source_path("african_hydro_atlas")
        if atlas_path and atlas_path.exists():
            try:
                df = load_african_hydro_atlas(atlas_path, missing_countries, verbose=verbose)
                if df is not None and not df.empty:
                    df["source"] = "African Hydropower Atlas"
                    dfs.append(df)
            except Exception as e:
                if verbose:
                    print(f"Error loading African Hydro Atlas: {e}")

    # Load hydropower from Global Energy Monitor (filtered from Global Integrated Power)
    if source in ("gem", "both"):
        gip_path = get_data_source_path("global_integrated_power_plants")
        if gip_path and gip_path.exists():
            try:
                all_power_df = load_global_integrated_power_data(gip_path, missing_countries, verbose=verbose)
                if all_power_df is not None and not all_power_df.empty:
                    # Filter for hydropower technologies
                    hydro_keywords = ['hydro', 'pumped', 'run-of-river', 'reservoir']
                    hydro_mask = all_power_df['technology'].str.lower().str.contains(
                        '|'.join(hydro_keywords), na=False
                    )
                    hydro_df = all_power_df[hydro_mask].copy()
                    if not hydro_df.empty:
                        hydro_df["source"] = "Global Energy Monitor"
                        dfs.append(hydro_df)
            except Exception as e:
                if verbose:
                    print(f"Error loading GEM hydro data: {e}")

    if dfs:
        all_source_df = pd.concat(dfs, ignore_index=True)

        # Cache each country individually
        source_name = "african_hydro_atlas" if source == "african_atlas" else "gem"
        if source == "both":
            source_name = "combined_hydro_sources"

        for country in missing_countries:
            country_df = all_source_df[all_source_df["country"] == country]
            if not country_df.empty:
                cache_country_data(
                    country_df,
                    data_type,
                    country,
                    source=source_name,
                    source_file=source_name,
                )

        if not cached_df.empty:
            return pd.concat([cached_df, all_source_df], ignore_index=True)
        return all_source_df

    # Return cached data if source processing failed
    if not cached_df.empty:
        return cached_df

    return None


def load_hydro_scenarios(
    region: str,
    countries: Optional[List[str]] = None,
    scenario: str = "SSP1-RCP26",
    verbose: bool = False,
) -> Optional[pd.DataFrame]:
    """Load hydropower climate scenario projections.

    Args:
        region: Region identifier
        countries: List of country names to include
        scenario: Climate scenario (SSP1-RCP26, SSP4-RCP60, SSP5-RCP85)
        verbose: Whether to print progress messages

    Returns:
        DataFrame with hydropower projections under climate scenario
    """
    if countries is None:
        countries = get_countries_for_region(region)

    atlas_path = get_data_source_path("african_hydro_atlas")
    if atlas_path and atlas_path.exists():
        try:
            return load_hydro_climate_scenarios(
                atlas_path, scenario=scenario, countries=countries, verbose=verbose
            )
        except Exception as e:
            if verbose:
                print(f"Error loading hydro scenarios: {e}")

    return None


def load_resource_potential(
    region: str,
    countries: Optional[List[str]] = None,
    technology: str = "solar",
    include_hourly: bool = False,
    verbose: bool = False,
) -> Optional[pd.DataFrame]:
    """Load IRENA resource potential data for solar or wind.

    Uses country-based caching: each country's data cached separately.

    Args:
        region: Region identifier
        countries: List of country names to include. If None, uses region countries.
        technology: 'solar' or 'wind'
        include_hourly: Whether to include hourly profiles (large data)
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: country, msr_id, latitude, longitude, capacity_mw,
        capacity_factor, lcoe, etc.
        Returns None if no data found.
    """
    if countries is None:
        countries = get_countries_for_region(region)

    if not countries:
        logger.warning(f"No countries found for region {region}")
        return None

    data_type = f"resource_potential_{technology}"

    # Step 1: Load cached countries
    cached_df, missing_countries = load_cached_countries(data_type, countries)

    if not missing_countries:
        logger.debug(f"All {len(countries)} countries loaded from cache")
        return cached_df

    # Step 2: Process missing countries from source
    logger.info(f"Processing {technology} resource potential for {len(missing_countries)} missing countries")

    all_source_df = None

    if technology == "solar":
        msr_path = get_data_source_path("irena_solar_msr")
        if msr_path and msr_path.exists():
            try:
                all_source_df = load_irena_solar_msr(
                    msr_path, missing_countries, include_hourly=include_hourly, verbose=verbose
                )
            except Exception as e:
                if verbose:
                    print(f"Error loading IRENA solar MSR: {e}")
    elif technology == "wind":
        msr_path = get_data_source_path("irena_wind_msr")
        if msr_path and msr_path.exists():
            try:
                all_source_df = load_irena_wind_msr(
                    msr_path, missing_countries, include_hourly=include_hourly, verbose=verbose
                )
            except Exception as e:
                if verbose:
                    print(f"Error loading IRENA wind MSR: {e}")
    else:
        logger.error(f"Unknown technology: {technology}")
        return cached_df if not cached_df.empty else None

    if all_source_df is not None and not all_source_df.empty:
        # Cache each country individually
        source_file = f"irena_{technology}_msr"
        for country in missing_countries:
            country_df = all_source_df[all_source_df["country"] == country]
            if not country_df.empty:
                cache_country_data(
                    country_df,
                    data_type,
                    country,
                    source="irena",
                    source_file=source_file,
                )

        if not cached_df.empty:
            return pd.concat([cached_df, all_source_df], ignore_index=True)
        return all_source_df

    # Return cached data if source processing failed
    if not cached_df.empty:
        return cached_df

    return None


def load_re_profiles_processed(
    region: str,
    technology: str = "solar",
    zones: Optional[List[str]] = None,
    verbose: bool = False,
) -> Optional[pd.DataFrame]:
    """Load processed RE profiles from data_capp files.

    These are representative day profiles suitable for capacity expansion modeling.

    Args:
        region: Region identifier
        technology: 'solar' or 'wind'
        zones: List of zones to filter by
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: zone, season, day, hour, capacity_factor
    """
    source_key = f"re_profiles_{technology}"
    csv_path = get_data_source_path(source_key)

    if csv_path and csv_path.exists():
        try:
            return load_processed_re_profiles(csv_path, technology, zones, verbose=verbose)
        except Exception as e:
            if verbose:
                print(f"Error loading processed RE profiles: {e}")

    return None


def _generate_mock_power_plants(countries: List[str]) -> pd.DataFrame:
    """Generate mock power plant data for development/testing."""
    import numpy as np

    if not countries:
        countries = ["South Africa"]

    # Sample data based on South Africa's actual mix
    mock_data = []
    techs = ["Coal", "Solar", "Wind", "Gas", "Hydro", "Nuclear"]
    capacities = [35000, 5000, 4000, 3000, 2000, 1800]
    n_plants = [15, 20, 15, 5, 8, 1]

    for country in countries:
        # Use South Africa's approximate center
        base_lat = -29.0
        base_lon = 24.0

        for tech, total_cap, n in zip(techs, capacities, n_plants):
            for i in range(n):
                mock_data.append({
                    "name": f"{country} {tech} Plant {i+1}",
                    "technology": tech,
                    "capacity_mw": total_cap / n * np.random.uniform(0.5, 1.5),
                    "status": "Operating",
                    "country": country,
                    "latitude": base_lat + np.random.uniform(-5, 5),
                    "longitude": base_lon + np.random.uniform(-5, 5),
                })

    return pd.DataFrame(mock_data)
