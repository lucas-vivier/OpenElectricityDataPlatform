"""Load profile data source adapter.

Handles loading and processing of hourly demand profiles from Toktarova dataset.
Adapted from EPM pre-analysis load_pipeline.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from ...config.regions import resolve_country_name


def load_toktarova_data(
    csv_path: Path,
    countries: List[str],
    year: int = 2020,
    verbose: bool = False,
) -> pd.DataFrame:
    """Load Toktarova hourly load profiles for specified countries.

    The Toktarova dataset contains synthetic hourly load profiles for all countries.
    Format: semicolon-separated CSV with country names in row 3 and hourly values starting row 5.

    Args:
        csv_path: Path to Toktarova CSV file
        countries: List of country names to load
        year: Year for timestamp generation
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: zone, month, day, hour, value (normalized 0-1)
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Toktarova data file not found: {path}")

    # Read raw data
    raw = pd.read_csv(path, sep=";", decimal=",", header=None, low_memory=False)
    country_row = raw.iloc[2]
    available_countries = [c for c in country_row.tolist() if isinstance(c, str)]

    all_profiles = []

    for country in countries:
        # Resolve country name with fuzzy matching
        resolved = resolve_country_name(country, available_countries, threshold=0.75)
        if resolved is None:
            if verbose:
                print(f"Country '{country}' not found in Toktarova dataset; skipping.")
            continue

        # Find column index for this country
        col_idx = country_row[country_row == resolved].index[0]

        # Extract hourly values (starting from row 5)
        hourly = raw.iloc[5:, [0, col_idx]].copy()
        hourly.columns = ["label", "load_mw"]
        hourly["hour_of_year"] = hourly["label"].astype(str).str.extract(r"(\d+)").astype(int)
        hourly["load_mw"] = pd.to_numeric(
            hourly["load_mw"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce"
        )
        hourly = hourly.dropna(subset=["load_mw"]).sort_values("hour_of_year").reset_index(drop=True)

        if verbose:
            print(f"Loaded {len(hourly)} hourly values for '{country}' (resolved: '{resolved}')")

        # Convert to month/day/hour format
        profile = _convert_to_time_index(hourly, year, country)
        all_profiles.append(profile)

    if not all_profiles:
        return pd.DataFrame(columns=["zone", "month", "day", "hour", "value"])

    result = pd.concat(all_profiles, ignore_index=True)

    # Normalize to [0, 1] per zone
    result = _normalize_by_zone(result)

    return result


def _convert_to_time_index(hourly_df: pd.DataFrame, year: int, zone: str) -> pd.DataFrame:
    """Convert hourly values to month/day/hour format.

    Args:
        hourly_df: DataFrame with load_mw column and hour_of_year index
        year: Year for timestamp generation
        zone: Zone/country name

    Returns:
        DataFrame with zone, month, day, hour, value columns
    """
    # Generate timestamps for the year (excluding Feb 29)
    full_year = pd.date_range(
        start=f"{year}-01-01",
        end=f"{year + 1}-01-01",
        freq="h",
        inclusive="left"
    )
    timestamps = full_year[(full_year.month != 2) | (full_year.day != 29)]

    # Handle leap year data (8784 hours) by dropping Feb 29
    n_hours = len(hourly_df)
    n_expected = len(timestamps)

    if n_hours == n_expected + 24:
        # Drop Feb 29 hours (hours 1416-1439 in a leap year, 0-indexed)
        leap_day_start = 24 * 59
        hourly_df = hourly_df.drop(
            hourly_df.index[leap_day_start:leap_day_start + 24]
        ).reset_index(drop=True)
    elif n_hours != n_expected:
        # Truncate or pad as needed
        hourly_df = hourly_df.head(n_expected)

    # Build output DataFrame
    result = pd.DataFrame({
        "zone": zone,
        "month": timestamps[:len(hourly_df)].month,
        "day": timestamps[:len(hourly_df)].day,
        "hour": timestamps[:len(hourly_df)].hour,
        "value": hourly_df["load_mw"].values[:len(timestamps)],
    })

    return result


def _normalize_by_zone(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize values to [0, 1] within each zone.

    Args:
        df: DataFrame with zone and value columns

    Returns:
        DataFrame with normalized values
    """
    df = df.copy()

    for zone in df["zone"].unique():
        mask = df["zone"] == zone
        zone_max = df.loc[mask, "value"].max()
        if zone_max > 0:
            df.loc[mask, "value"] = df.loc[mask, "value"] / zone_max

    return df


def generate_mock_load_profiles(
    countries: List[str],
    year: int = 2020,
) -> pd.DataFrame:
    """Generate mock load profiles for development/testing.

    Creates synthetic hourly load profiles with typical daily and seasonal patterns.

    Args:
        countries: List of country names
        year: Year for the profiles

    Returns:
        DataFrame with zone, month, day, hour, value columns
    """
    if not countries:
        countries = ["South Africa"]

    all_profiles = []

    for country in countries:
        # Generate hourly timestamps for a non-leap year
        full_year = pd.date_range(
            start=f"{year}-01-01",
            end=f"{year + 1}-01-01",
            freq="h",
            inclusive="left"
        )
        timestamps = full_year[(full_year.month != 2) | (full_year.day != 29)]

        n_hours = len(timestamps)

        # Create synthetic load pattern
        hours = np.arange(n_hours)

        # Daily pattern (peak in evening, trough at night)
        hour_of_day = hours % 24
        daily_pattern = 0.6 + 0.4 * np.sin((hour_of_day - 6) * np.pi / 12)

        # Weekly pattern (lower on weekends)
        day_of_week = (hours // 24) % 7
        weekly_pattern = np.where(day_of_week >= 5, 0.85, 1.0)

        # Seasonal pattern (higher in winter for heating/cooling)
        day_of_year = hours // 24
        seasonal_pattern = 0.85 + 0.15 * np.cos((day_of_year - 180) * 2 * np.pi / 365)

        # Combine patterns
        load = daily_pattern * weekly_pattern * seasonal_pattern

        # Add some noise
        load = load + np.random.normal(0, 0.02, n_hours)
        load = np.clip(load, 0.3, 1.0)

        # Normalize to [0, 1]
        load = (load - load.min()) / (load.max() - load.min())

        profile = pd.DataFrame({
            "zone": country,
            "month": timestamps.month,
            "day": timestamps.day,
            "hour": timestamps.hour,
            "value": load,
        })
        all_profiles.append(profile)

    return pd.concat(all_profiles, ignore_index=True)
