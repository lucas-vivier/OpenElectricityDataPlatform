"""Main data loader for OpenEnergyData.

Provides unified functions to load power plants, load profiles, and RE profiles
from local files or remote sources.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd

from ..config import get_settings
from ..config.data_paths import get_data_source_path, data_source_exists, get_local_region_path
from ..config.regions import get_countries_for_region
from .sources.power_plants import load_global_integrated_power_data, filter_by_country
from .sources.load_profiles import load_toktarova_data, generate_mock_load_profiles
from .sources.renewables import fetch_renewables_ninja
from .sources.hydropower import (
    load_african_hydro_atlas,
    load_global_hydro_tracker,
    load_hydro_climate_scenarios,
    summarize_hydro_by_country,
)
from .sources.irena import (
    load_irena_solar_msr,
    load_irena_wind_msr,
    summarize_msr_by_country,
    load_processed_re_profiles,
)


def _get_local_data_path(region: str) -> Path:
    """Get the local data directory for a region."""
    return get_local_region_path(region)


def load_power_plants(
    region: str,
    countries: List[str],
    source_path: Optional[Path] = None,
) -> Optional[pd.DataFrame]:
    """Load power plant data for the specified region and countries.

    Args:
        region: Region identifier (e.g., 'south_africa')
        countries: List of country names to include
        source_path: Optional path to Global Integrated Power Excel file. If None, uses default.

    Returns:
        DataFrame with columns: name, technology, capacity_mw, status, status_category,
        country, latitude, longitude, fuel, start_year, retired_year
        Returns None if no data found.
    """
    # Try local parquet first (cached preprocessed data)
    local_path = _get_local_data_path(region) / "power_plants.parquet"
    if local_path.exists():
        df = pd.read_parquet(local_path)
        return filter_by_country(df, countries) if countries else df

    # Try custom source path
    if source_path is not None and source_path.exists():
        df = load_global_integrated_power_data(source_path, countries)
        return df

    # Try default Global Integrated Power data source
    gip_path = get_data_source_path("global_integrated_power_plants")
    if gip_path and gip_path.exists():
        df = load_global_integrated_power_data(gip_path, countries)
        return df

    # Return mock data for development only
    return _generate_mock_power_plants(countries)


def load_load_profiles(
    region: str,
    countries: List[str],
    year: int = 2020,
    source_path: Optional[Path] = None,
) -> Optional[pd.DataFrame]:
    """Load hourly demand profiles for the specified region and countries.

    Args:
        region: Region identifier
        countries: List of country names to include
        year: Year for the profiles
        source_path: Optional path to Toktarova CSV. If None, uses default.

    Returns:
        DataFrame with columns: zone, month, day, hour, value (normalized 0-1)
        Returns None if no data found.
    """
    # Try local parquet first
    local_path = _get_local_data_path(region) / "load_profiles.parquet"
    if local_path.exists():
        df = pd.read_parquet(local_path)
        if countries:
            df = df[df["zone"].isin(countries)]
        return df

    # Try loading from Toktarova
    if source_path is not None and source_path.exists():
        return load_toktarova_data(source_path, countries, year)

    # Return mock data for development
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
    # Try local parquet first
    local_path = _get_local_data_path(region) / f"re_profiles_{tech}.parquet"
    if local_path.exists():
        df = pd.read_parquet(local_path)
        if countries:
            df = df[df["zone"].isin(countries)]
        return df

    # Try fetching from Renewables.ninja API
    if api_key and latitude is not None and longitude is not None:
        return fetch_renewables_ninja(
            api_key=api_key,
            lat=latitude,
            lon=longitude,
            year=year,
            technology=tech,
        )

    return None


def load_hydropower(
    region: str,
    countries: Optional[List[str]] = None,
    source: str = "african_atlas",
    verbose: bool = False,
) -> Optional[pd.DataFrame]:
    """Load hydropower data for the specified region and countries.

    Args:
        region: Region identifier (e.g., 'southern_africa')
        countries: List of country names to include. If None, uses region countries.
        source: Data source - 'african_atlas', 'global_tracker', or 'both'
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: name, technology, capacity_mw, status, country,
        latitude, longitude, river_name, river_basin, reservoir_size_mcm
        Returns None if no data found.
    """
    # Get countries from region if not provided
    if countries is None:
        countries = get_countries_for_region(region)

    # Try local parquet first
    local_path = _get_local_data_path(region) / "hydropower.parquet"
    if local_path.exists():
        df = pd.read_parquet(local_path)
        if countries:
            df = df[df["country"].isin(countries)]
        return df

    dfs = []

    # Load from African Hydropower Atlas
    if source in ("african_atlas", "both"):
        atlas_path = get_data_source_path("african_hydro_atlas")
        if atlas_path and atlas_path.exists():
            try:
                df = load_african_hydro_atlas(atlas_path, countries, verbose=verbose)
                df["source"] = "African Hydropower Atlas"
                dfs.append(df)
            except Exception as e:
                if verbose:
                    print(f"Error loading African Hydro Atlas: {e}")

    # Load from Global Hydropower Tracker
    if source in ("global_tracker", "both"):
        tracker_path = get_data_source_path("global_hydro_tracker")
        if tracker_path and tracker_path.exists():
            try:
                df = load_global_hydro_tracker(tracker_path, countries, verbose=verbose)
                df["source"] = "Global Hydropower Tracker"
                dfs.append(df)
            except Exception as e:
                if verbose:
                    print(f"Error loading Global Hydro Tracker: {e}")

    if dfs:
        return pd.concat(dfs, ignore_index=True)

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

    # Try local parquet first
    local_path = _get_local_data_path(region) / f"resource_potential_{technology}.parquet"
    if local_path.exists():
        df = pd.read_parquet(local_path)
        if countries:
            df = df[df["country"].isin(countries)]
        return df

    # Load from IRENA MSR files
    if technology == "solar":
        msr_path = get_data_source_path("irena_solar_msr")
        if msr_path and msr_path.exists():
            try:
                return load_irena_solar_msr(
                    msr_path, countries, include_hourly=include_hourly, verbose=verbose
                )
            except Exception as e:
                if verbose:
                    print(f"Error loading IRENA solar MSR: {e}")
    elif technology == "wind":
        msr_path = get_data_source_path("irena_wind_msr")
        if msr_path and msr_path.exists():
            try:
                return load_irena_wind_msr(
                    msr_path, countries, include_hourly=include_hourly, verbose=verbose
                )
            except Exception as e:
                if verbose:
                    print(f"Error loading IRENA wind MSR: {e}")

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
