"""Renewable energy profile data source adapter.

Handles fetching solar and wind capacity factor profiles from Renewables.ninja API.
Adapted from EPM pre-analysis vre_pipeline.py.
"""

from __future__ import annotations

import time
from typing import Optional

import pandas as pd
import requests


RENEWABLES_NINJA_BASE_URL = "https://www.renewables.ninja/api/data"


def fetch_renewables_ninja(
    api_key: str,
    lat: float,
    lon: float,
    year: int,
    technology: str = "solar",
    capacity: float = 1.0,
    system_loss: float = 0.1,
    tracking: int = 0,
    tilt: Optional[float] = None,
    azimuth: float = 180,
    turbine_model: str = "Vestas V80 2000",
    hub_height: float = 80,
    verbose: bool = False,
) -> Optional[pd.DataFrame]:
    """Fetch hourly capacity factor profiles from Renewables.ninja API.

    Args:
        api_key: Renewables.ninja API token
        lat: Latitude of the location
        lon: Longitude of the location
        year: Year for the profile (e.g., 2019)
        technology: 'solar' or 'wind'
        capacity: System capacity in kW (default: 1 kW)
        system_loss: System losses as fraction (default: 0.1 = 10%)
        tracking: Solar tracking type (0=fixed, 1=1-axis, 2=2-axis)
        tilt: Solar panel tilt angle (None = optimal)
        azimuth: Solar panel azimuth angle (180 = south)
        turbine_model: Wind turbine model name
        hub_height: Wind turbine hub height in meters
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: zone, month, day, hour, capacity_factor
        Returns None if API call fails.
    """
    if not api_key:
        if verbose:
            print("No API key provided for Renewables.ninja")
        return None

    # Build API request parameters
    if technology.lower() == "solar":
        endpoint = f"{RENEWABLES_NINJA_BASE_URL}/pv"
        params = {
            "lat": lat,
            "lon": lon,
            "date_from": f"{year}-01-01",
            "date_to": f"{year}-12-31",
            "dataset": "merra2",
            "capacity": capacity,
            "system_loss": system_loss,
            "tracking": tracking,
            "azim": azimuth,
            "format": "json",
        }
        if tilt is not None:
            params["tilt"] = tilt

    elif technology.lower() == "wind":
        endpoint = f"{RENEWABLES_NINJA_BASE_URL}/wind"
        params = {
            "lat": lat,
            "lon": lon,
            "date_from": f"{year}-01-01",
            "date_to": f"{year}-12-31",
            "dataset": "merra2",
            "capacity": capacity,
            "height": hub_height,
            "turbine": turbine_model,
            "format": "json",
        }
    else:
        raise ValueError(f"Unknown technology: {technology}. Must be 'solar' or 'wind'.")

    headers = {
        "Authorization": f"Token {api_key}",
    }

    if verbose:
        print(f"Fetching {technology} profile from Renewables.ninja for ({lat}, {lon}), year {year}")

    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        if verbose:
            print(f"API request failed: {e}")
        return None

    # Parse response
    if "data" not in data:
        if verbose:
            print(f"Unexpected API response: {data}")
        return None

    hourly_data = data["data"]

    # Convert to DataFrame
    records = []
    for timestamp_str, values in hourly_data.items():
        ts = pd.Timestamp(timestamp_str)

        # Skip Feb 29 for consistency
        if ts.month == 2 and ts.day == 29:
            continue

        cf = values.get("electricity", 0) / capacity if capacity > 0 else 0

        records.append({
            "zone": f"{lat:.2f},{lon:.2f}",
            "month": ts.month,
            "day": ts.day,
            "hour": ts.hour,
            "capacity_factor": cf,
        })

    df = pd.DataFrame(records)

    if verbose:
        print(f"Retrieved {len(df)} hourly values, mean CF: {df['capacity_factor'].mean():.3f}")

    return df


def fetch_renewables_ninja_batch(
    api_key: str,
    locations: list,
    year: int,
    technology: str = "solar",
    delay: float = 1.0,
    verbose: bool = False,
) -> Optional[pd.DataFrame]:
    """Fetch profiles for multiple locations with rate limiting.

    Args:
        api_key: Renewables.ninja API token
        locations: List of dicts with 'name', 'lat', 'lon' keys
        year: Year for the profiles
        technology: 'solar' or 'wind'
        delay: Delay between API calls in seconds (to respect rate limits)
        verbose: Whether to print progress messages

    Returns:
        DataFrame with all locations' profiles concatenated
    """
    if not api_key or not locations:
        return None

    all_profiles = []

    for i, loc in enumerate(locations):
        if verbose:
            print(f"Fetching {i+1}/{len(locations)}: {loc.get('name', 'unnamed')}")

        profile = fetch_renewables_ninja(
            api_key=api_key,
            lat=loc["lat"],
            lon=loc["lon"],
            year=year,
            technology=technology,
            verbose=verbose,
        )

        if profile is not None:
            profile["zone"] = loc.get("name", f"{loc['lat']:.2f},{loc['lon']:.2f}")
            all_profiles.append(profile)

        # Rate limiting
        if i < len(locations) - 1:
            time.sleep(delay)

    if not all_profiles:
        return None

    return pd.concat(all_profiles, ignore_index=True)


def generate_mock_re_profiles(
    countries: list,
    year: int = 2020,
    technology: str = "solar",
) -> pd.DataFrame:
    """Generate mock RE profiles for development/testing.

    Args:
        countries: List of country/zone names
        year: Year for the profiles
        technology: 'solar' or 'wind'

    Returns:
        DataFrame with zone, month, day, hour, capacity_factor columns
    """
    import numpy as np

    if not countries:
        countries = ["South Africa"]

    all_profiles = []

    for country in countries:
        # Generate hourly timestamps
        full_year = pd.date_range(
            start=f"{year}-01-01",
            end=f"{year + 1}-01-01",
            freq="h",
            inclusive="left"
        )
        timestamps = full_year[(full_year.month != 2) | (full_year.day != 29)]

        n_hours = len(timestamps)
        hours = np.arange(n_hours)
        hour_of_day = hours % 24
        day_of_year = hours // 24

        if technology.lower() == "solar":
            # Solar pattern: peak at noon, zero at night
            # Seasonal variation (higher in summer for Southern Hemisphere)
            solar_elevation = np.sin((hour_of_day - 6) * np.pi / 12)
            solar_elevation = np.clip(solar_elevation, 0, 1)

            # Seasonal factor (South Africa summer = Dec-Feb)
            seasonal = 0.8 + 0.2 * np.cos((day_of_year - 355) * 2 * np.pi / 365)

            cf = solar_elevation * seasonal * np.random.uniform(0.7, 1.0, n_hours)
            cf = np.clip(cf, 0, 1)

        else:  # wind
            # Wind pattern: more variable, slight increase at night
            base_wind = 0.3 + 0.2 * np.sin((hour_of_day - 12) * np.pi / 24)

            # Random daily variation
            daily_factor = np.repeat(
                np.random.uniform(0.3, 1.0, n_hours // 24 + 1),
                24
            )[:n_hours]

            cf = base_wind * daily_factor
            cf = np.clip(cf, 0, 1)

        profile = pd.DataFrame({
            "zone": country,
            "month": timestamps.month,
            "day": timestamps.day,
            "hour": timestamps.hour,
            "capacity_factor": cf,
        })
        all_profiles.append(profile)

    return pd.concat(all_profiles, ignore_index=True)
