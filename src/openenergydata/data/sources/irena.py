"""IRENA MSR (Model Solar/Wind Resource) data source adapter.

Handles loading and processing of IRENA resource potential data from:
- SolarPV_BestMSRsToCover5%CountryArea.csv (170 MB)
- Wind_BestMSRsToCover5%CountryArea.csv (23 MB)

These files contain the best solar/wind sites to cover 5% of each country's area,
with detailed location data, capacity factors, LCOE, and hourly profiles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

from ...config.regions import resolve_country_name


def load_irena_solar_msr(
    csv_path: Path,
    countries: Optional[List[str]] = None,
    include_hourly: bool = False,
    verbose: bool = False,
) -> pd.DataFrame:
    """Load IRENA solar resource potential data.

    Args:
        csv_path: Path to the SolarPV MSR CSV file
        countries: List of countries to filter by (None = all)
        include_hourly: Whether to include hourly profiles (H1-H366)
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: country, msr_id, latitude, longitude, capacity_mw,
        capacity_factor, lcoe, ghi, area_km2, plus optionally H1-H366 hourly columns
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"IRENA Solar MSR file not found: {path}")

    if verbose:
        print(f"Loading IRENA Solar MSR from {path}...")

    # Read CSV - this is a large file (170 MB)
    # Use chunking if memory is an issue
    df = pd.read_csv(path, low_memory=False)

    if verbose:
        print(f"Loaded {len(df)} solar resource sites")
        print(f"Columns: {list(df.columns)[:20]}...")

    # Normalize column names - actual format from EPM pre-analysis files
    column_mapping = {
        # Primary names (actual file format)
        "CtryName": "country",
        "\ufeffCtryName": "country",  # Handle BOM
        "MSR_ID": "msr_id",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "CapacityMW": "capacity_mw",
        "CF": "capacity_factor",
        "LCOE-MWh": "lcoe",
        "sLCOE-MWh": "lcoe_solar",
        "tLCOE-MWh": "lcoe_transmission",
        "rLCOE-MWh": "lcoe_road",
        "GHIkWhm2d": "ghi",
        "AreakM2": "area_km2",
        "RoadDist": "distance_road_km",
        "SubstnDist": "distance_substation_km",
        "Load_dst": "distance_load_km",
        "Y_GWh": "annual_generation_gwh",
        # Alternate names
        "Country": "country",
        "AreaKm2": "area_km2",
        "Distance_Grid": "distance_grid_km",
        "Distance_Road": "distance_road_km",
    }

    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    # Filter by countries if provided
    if countries and "country" in df.columns:
        available = df["country"].dropna().unique().tolist()
        resolved = []
        for country in countries:
            match = resolve_country_name(country, available, threshold=0.75)
            if match:
                resolved.append(match)
            elif verbose:
                print(f"No match found for '{country}' in solar MSR data")

        if resolved:
            df = df[df["country"].isin(resolved)]
        else:
            df = pd.DataFrame(columns=df.columns)

    # Add technology column
    df["technology"] = "Solar PV"

    # Select output columns
    base_columns = [
        "country", "msr_id", "latitude", "longitude", "capacity_mw",
        "capacity_factor", "lcoe", "ghi", "area_km2",
        "distance_grid_km", "distance_road_km", "elevation_m", "technology"
    ]
    base_columns = [c for c in base_columns if c in df.columns]

    if include_hourly:
        # Include H1-H366 columns for hourly profiles
        hourly_cols = [c for c in df.columns if c.startswith("H") and c[1:].isdigit()]
        output_columns = base_columns + sorted(hourly_cols, key=lambda x: int(x[1:]))
    else:
        output_columns = base_columns

    if verbose:
        print(f"{len(df)} solar sites after filtering")

    return df[output_columns].reset_index(drop=True)


def load_irena_wind_msr(
    csv_path: Path,
    countries: Optional[List[str]] = None,
    include_hourly: bool = False,
    verbose: bool = False,
) -> pd.DataFrame:
    """Load IRENA wind resource potential data.

    Args:
        csv_path: Path to the Wind MSR CSV file
        countries: List of countries to filter by (None = all)
        include_hourly: Whether to include hourly profiles (H1-H366)
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: country, msr_id, latitude, longitude, capacity_mw,
        capacity_factor_100m, mean_speed, iec_class, area_km2, plus optionally H1-H366
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"IRENA Wind MSR file not found: {path}")

    if verbose:
        print(f"Loading IRENA Wind MSR from {path}...")

    df = pd.read_csv(path, low_memory=False)

    if verbose:
        print(f"Loaded {len(df)} wind resource sites")
        print(f"Columns: {list(df.columns)[:20]}...")

    # Normalize column names - actual format from EPM pre-analysis files
    column_mapping = {
        # Primary names (actual file format)
        "CtryName": "country",
        "\ufeffCtryName": "country",  # Handle BOM
        "MSR_ID": "msr_id",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "CapacityMW": "capacity_mw",
        "CF100m": "capacity_factor_100m",
        "MeanSpeed": "mean_speed",
        "IEC_Class": "iec_class",
        "ERA_WSpeed": "era_wind_speed",
        "LCOE-MWh": "lcoe",
        "sLCOE-MWh": "lcoe_site",
        "tLCOE-MWh": "lcoe_transmission",
        "rLCOE-MWh": "lcoe_road",
        "AreakM2": "area_km2",
        "RoadDist": "distance_road_km",
        "SubstnDist": "distance_substation_km",
        "Load_dst": "distance_load_km",
        "Y_GWh100m": "annual_generation_gwh",
        # Alternate names
        "Country": "country",
        "AreaKm2": "area_km2",
    }

    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    # Filter by countries if provided
    if countries and "country" in df.columns:
        available = df["country"].dropna().unique().tolist()
        resolved = []
        for country in countries:
            match = resolve_country_name(country, available, threshold=0.75)
            if match:
                resolved.append(match)
            elif verbose:
                print(f"No match found for '{country}' in wind MSR data")

        if resolved:
            df = df[df["country"].isin(resolved)]
        else:
            df = pd.DataFrame(columns=df.columns)

    # Add technology column
    df["technology"] = "Wind"

    # Select output columns
    base_columns = [
        "country", "msr_id", "latitude", "longitude", "capacity_mw",
        "capacity_factor_100m", "mean_speed", "iec_class", "lcoe",
        "area_km2", "distance_grid_km", "distance_road_km", "elevation_m", "technology"
    ]
    base_columns = [c for c in base_columns if c in df.columns]

    if include_hourly:
        hourly_cols = [c for c in df.columns if c.startswith("H") and c[1:].isdigit()]
        output_columns = base_columns + sorted(hourly_cols, key=lambda x: int(x[1:]))
    else:
        output_columns = base_columns

    if verbose:
        print(f"{len(df)} wind sites after filtering")

    return df[output_columns].reset_index(drop=True)


def get_msr_hourly_profile(
    df: pd.DataFrame,
    msr_id: Union[str, int],
) -> Optional[pd.Series]:
    """Extract the hourly profile for a specific MSR site.

    Args:
        df: DataFrame with H1-H366 columns
        msr_id: The MSR_ID to extract

    Returns:
        Series with 366 hourly values (representative days), or None if not found
    """
    if "msr_id" not in df.columns:
        return None

    row = df[df["msr_id"] == msr_id]
    if row.empty:
        return None

    hourly_cols = sorted(
        [c for c in df.columns if c.startswith("H") and c[1:].isdigit()],
        key=lambda x: int(x[1:])
    )

    if not hourly_cols:
        return None

    return row[hourly_cols].iloc[0]


def summarize_msr_by_country(
    df: pd.DataFrame,
    technology: str = "solar",
) -> pd.DataFrame:
    """Summarize resource potential by country.

    Args:
        df: MSR DataFrame with country, capacity_mw, capacity_factor columns
        technology: 'solar' or 'wind' (affects column names)

    Returns:
        Summary DataFrame with country, total_capacity_mw, avg_capacity_factor,
        site_count, total_area_km2
    """
    if df.empty or "country" not in df.columns:
        return pd.DataFrame(columns=["country", "total_capacity_mw", "avg_capacity_factor", "site_count"])

    cf_col = "capacity_factor" if technology == "solar" else "capacity_factor_100m"

    agg_dict = {
        "capacity_mw": "sum",
        "msr_id": "count",
    }

    if cf_col in df.columns:
        agg_dict[cf_col] = "mean"

    if "area_km2" in df.columns:
        agg_dict["area_km2"] = "sum"

    if "lcoe" in df.columns:
        agg_dict["lcoe"] = "mean"

    summary = (
        df.groupby("country", dropna=False)
        .agg(agg_dict)
        .reset_index()
    )

    # Rename columns
    rename_map = {
        "capacity_mw": "total_capacity_mw",
        "msr_id": "site_count",
        cf_col: "avg_capacity_factor",
        "area_km2": "total_area_km2",
        "lcoe": "avg_lcoe",
    }
    summary = summary.rename(columns=rename_map)

    return summary.sort_values("total_capacity_mw", ascending=False)


def load_processed_re_profiles(
    csv_path: Path,
    technology: str = "solar",
    zones: Optional[List[str]] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Load processed RE profiles from data_capp_*.csv files.

    These files contain representative day profiles in format:
    zone, season, day, hour, year_value

    Args:
        csv_path: Path to the data_capp_solar.csv or data_capp_wind.csv file
        technology: 'solar' or 'wind'
        zones: List of zones to filter by
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: zone, season, day, hour, capacity_factor
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Processed RE profiles file not found: {path}")

    if verbose:
        print(f"Loading processed RE profiles from {path}...")

    df = pd.read_csv(path)

    if verbose:
        print(f"Loaded {len(df)} profile records")
        print(f"Columns: {list(df.columns)}")

    # Normalize column names
    df.columns = df.columns.str.lower().str.strip()

    # Look for the value column (might be named by year like '2023')
    value_cols = [c for c in df.columns if c not in ['zone', 'season', 'day', 'hour']]
    if value_cols:
        # Use the first value column as capacity_factor
        df = df.rename(columns={value_cols[0]: "capacity_factor"})

    # Filter by zones if provided
    if zones and "zone" in df.columns:
        df = df[df["zone"].isin(zones)]

    # Add technology column
    df["technology"] = technology.title()

    if verbose:
        print(f"{len(df)} profile records after filtering")

    return df.reset_index(drop=True)
