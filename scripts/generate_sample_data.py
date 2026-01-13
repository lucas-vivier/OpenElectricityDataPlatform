#!/usr/bin/env python3
"""Generate sample data for South Africa for development and testing.

This script creates mock data that demonstrates the data format
expected by the OpenEnergyData platform.

Usage:
    python scripts/generate_sample_data.py
"""

from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import numpy as np
import pandas as pd


def generate_power_plants_data() -> pd.DataFrame:
    """Generate sample power plant data for South Africa."""
    np.random.seed(42)

    # Based on South Africa's actual generation mix
    plants_data = [
        # Coal plants (Eskom's major coal stations)
        {"name": "Medupi Power Station", "technology": "Coal", "capacity_mw": 4764, "status": "Operating", "latitude": -23.68, "longitude": 27.54},
        {"name": "Kusile Power Station", "technology": "Coal", "capacity_mw": 4800, "status": "Construction", "latitude": -26.03, "longitude": 28.93},
        {"name": "Matimba Power Station", "technology": "Coal", "capacity_mw": 3990, "status": "Operating", "latitude": -23.67, "longitude": 27.6},
        {"name": "Lethabo Power Station", "technology": "Coal", "capacity_mw": 3708, "status": "Operating", "latitude": -26.74, "longitude": 27.98},
        {"name": "Kendal Power Station", "technology": "Coal", "capacity_mw": 4116, "status": "Operating", "latitude": -26.08, "longitude": 28.97},
        {"name": "Majuba Power Station", "technology": "Coal", "capacity_mw": 4110, "status": "Operating", "latitude": -27.08, "longitude": 29.77},
        {"name": "Duvha Power Station", "technology": "Coal", "capacity_mw": 3600, "status": "Operating", "latitude": -25.98, "longitude": 29.35},
        {"name": "Tutuka Power Station", "technology": "Coal", "capacity_mw": 3654, "status": "Operating", "latitude": -26.78, "longitude": 29.35},

        # Nuclear
        {"name": "Koeberg Nuclear Power Station", "technology": "Nuclear", "capacity_mw": 1860, "status": "Operating", "latitude": -33.68, "longitude": 18.43},

        # Gas
        {"name": "Ankerlig Power Station", "technology": "Gas", "capacity_mw": 1338, "status": "Operating", "latitude": -33.55, "longitude": 18.48},
        {"name": "Gourikwa Power Station", "technology": "Gas", "capacity_mw": 746, "status": "Operating", "latitude": -34.01, "longitude": 22.17},

        # Hydro
        {"name": "Gariep Dam", "technology": "Hydro", "capacity_mw": 360, "status": "Operating", "latitude": -30.62, "longitude": 25.5},
        {"name": "Vanderkloof Dam", "technology": "Hydro", "capacity_mw": 240, "status": "Operating", "latitude": -29.99, "longitude": 24.73},
        {"name": "Drakensberg Pumped Storage", "technology": "Hydro", "capacity_mw": 1000, "status": "Operating", "latitude": -28.93, "longitude": 29.33},

        # Solar
        {"name": "De Aar Solar", "technology": "Solar", "capacity_mw": 175, "status": "Operating", "latitude": -30.65, "longitude": 24.01},
        {"name": "Jasper Solar", "technology": "Solar", "capacity_mw": 96, "status": "Operating", "latitude": -28.46, "longitude": 23.17},
        {"name": "Kalkbult Solar", "technology": "Solar", "capacity_mw": 75, "status": "Operating", "latitude": -30.93, "longitude": 24.13},
        {"name": "Droogfontein Solar", "technology": "Solar", "capacity_mw": 50, "status": "Operating", "latitude": -28.63, "longitude": 24.17},
        {"name": "Letsatsi Solar", "technology": "Solar", "capacity_mw": 64, "status": "Operating", "latitude": -28.73, "longitude": 25.13},
        {"name": "Lesedi Solar", "technology": "Solar", "capacity_mw": 64, "status": "Operating", "latitude": -28.75, "longitude": 25.15},
        {"name": "Prieska Solar", "technology": "Solar", "capacity_mw": 75, "status": "Operating", "latitude": -29.67, "longitude": 22.74},

        # Wind
        {"name": "Sere Wind Farm", "technology": "Wind", "capacity_mw": 100, "status": "Operating", "latitude": -31.87, "longitude": 18.38},
        {"name": "Cookhouse Wind Farm", "technology": "Wind", "capacity_mw": 139, "status": "Operating", "latitude": -33.4, "longitude": 25.82},
        {"name": "Jeffreys Bay Wind Farm", "technology": "Wind", "capacity_mw": 138, "status": "Operating", "latitude": -34.0, "longitude": 24.95},
        {"name": "Hopefield Wind Farm", "technology": "Wind", "capacity_mw": 67, "status": "Operating", "latitude": -33.08, "longitude": 18.35},
        {"name": "West Coast One Wind Farm", "technology": "Wind", "capacity_mw": 94, "status": "Operating", "latitude": -32.82, "longitude": 18.02},
        {"name": "Gouda Wind Farm", "technology": "Wind", "capacity_mw": 138, "status": "Operating", "latitude": -33.32, "longitude": 19.05},
        {"name": "Loeriesfontein Wind Farm", "technology": "Wind", "capacity_mw": 140, "status": "Operating", "latitude": -30.95, "longitude": 19.43},
        {"name": "Khobab Wind Farm", "technology": "Wind", "capacity_mw": 140, "status": "Operating", "latitude": -31.15, "longitude": 19.03},
    ]

    df = pd.DataFrame(plants_data)
    df["country"] = "South Africa"

    return df


def generate_load_profiles_data(year: int = 2020) -> pd.DataFrame:
    """Generate sample hourly load profiles for South Africa."""
    np.random.seed(42)

    # Generate timestamps for full year (excluding Feb 29)
    full_year = pd.date_range(start=f"{year}-01-01", end=f"{year + 1}-01-01", freq="h", inclusive="left")
    timestamps = full_year[(full_year.month != 2) | (full_year.day != 29)]

    n_hours = len(timestamps)
    hours = np.arange(n_hours)
    hour_of_day = hours % 24
    day_of_year = hours // 24

    # South Africa load pattern characteristics:
    # - Morning peak around 7-9 AM
    # - Evening peak around 6-8 PM (higher in winter for heating)
    # - Lower load on weekends
    # - Winter (June-August) has higher evening demand

    # Daily pattern with morning and evening peaks
    morning_peak = np.exp(-0.5 * ((hour_of_day - 8) / 2) ** 2) * 0.3
    evening_peak = np.exp(-0.5 * ((hour_of_day - 19) / 2) ** 2) * 0.4
    base_load = 0.5

    daily_pattern = base_load + morning_peak + evening_peak

    # Weekly pattern (lower on weekends - Sat=5, Sun=6)
    day_of_week = (day_of_year + 2) % 7  # Assuming Jan 1, 2020 is Wednesday
    weekend_factor = np.where(day_of_week >= 5, 0.85, 1.0)
    weekly_factor = np.repeat(weekend_factor, 24)[:n_hours]

    # Seasonal pattern (South Africa: winter = June-August, higher heating demand)
    # Peak in winter evenings
    month = timestamps.month.to_numpy()
    is_winter = ((month >= 6) & (month <= 8))
    seasonal_factor = np.where(
        np.repeat(is_winter, 1),
        1.0 + 0.15 * np.exp(-0.5 * ((hour_of_day - 19) / 3) ** 2),  # Extra evening demand in winter
        1.0
    )

    # Combine patterns
    load = daily_pattern * weekly_factor * seasonal_factor

    # Add noise
    load = load + np.random.normal(0, 0.02, n_hours)
    load = np.clip(load, 0.3, 1.2)

    # Normalize to [0, 1]
    load = (load - load.min()) / (load.max() - load.min())

    df = pd.DataFrame({
        "zone": "South Africa",
        "month": timestamps.month,
        "day": timestamps.day,
        "hour": timestamps.hour,
        "value": load,
    })

    return df


def generate_re_profiles_data(year: int = 2020, technology: str = "solar") -> pd.DataFrame:
    """Generate sample RE capacity factor profiles for South Africa."""
    np.random.seed(42 if technology == "solar" else 43)

    full_year = pd.date_range(start=f"{year}-01-01", end=f"{year + 1}-01-01", freq="h", inclusive="left")
    timestamps = full_year[(full_year.month != 2) | (full_year.day != 29)]

    n_hours = len(timestamps)
    hours = np.arange(n_hours)
    hour_of_day = hours % 24
    day_of_year = hours // 24

    if technology == "solar":
        # Solar pattern for South Africa (good solar resource, ~-30 latitude)
        # Peak around noon, zero at night
        # Higher in summer (Dec-Feb), lower in winter (Jun-Aug)

        # Daily solar curve
        solar_angle = (hour_of_day - 12) * np.pi / 12
        solar_elevation = np.cos(solar_angle)
        solar_elevation = np.clip(solar_elevation, 0, 1)

        # Add early morning and late evening taper
        solar_elevation = np.where(hour_of_day < 6, 0, solar_elevation)
        solar_elevation = np.where(hour_of_day > 18, 0, solar_elevation)

        # Seasonal variation (summer = Dec-Feb for Southern Hemisphere)
        # Day 0 = Jan 1, so Dec 21 is around day 355
        seasonal = 0.85 + 0.15 * np.cos((day_of_year - 355) * 2 * np.pi / 365)
        seasonal = np.repeat(seasonal, 24)[:n_hours]

        # Cloud factor (random daily variation)
        cloud_factor = np.random.uniform(0.7, 1.0, n_hours // 24 + 1)
        cloud_factor = np.repeat(cloud_factor, 24)[:n_hours]

        cf = solar_elevation * seasonal * cloud_factor

        # Peak capacity factor around 0.25-0.30 for South Africa
        cf = cf * 0.3

    else:  # wind
        # Wind pattern for South Africa
        # Generally stronger in afternoon/evening
        # More variable day-to-day

        # Base wind pattern (slightly higher in afternoon)
        base_wind = 0.2 + 0.1 * np.sin((hour_of_day - 15) * np.pi / 12)

        # Random daily variation (wind is highly variable)
        daily_factor = np.random.uniform(0.2, 1.0, n_hours // 24 + 1)
        daily_factor = np.repeat(daily_factor, 24)[:n_hours]

        # Some seasonal pattern (windier in winter for some regions)
        month = timestamps.month.to_numpy()
        seasonal = np.where((month >= 5) & (month <= 9), 1.1, 0.95)
        seasonal = seasonal.astype(float)

        cf = base_wind * daily_factor * seasonal

        # Peak capacity factor around 0.35 for good wind sites
        cf = np.clip(cf * 0.35, 0, 0.9)

    cf = np.clip(cf, 0, 1)

    df = pd.DataFrame({
        "zone": "South Africa",
        "month": timestamps.month,
        "day": timestamps.day,
        "hour": timestamps.hour,
        "capacity_factor": cf,
    })

    return df


def main():
    """Generate and save sample data."""
    output_dir = Path(__file__).parents[1] / "data" / "local" / "south_africa"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating sample data for South Africa...")

    # Power plants
    print("  - Power plants...")
    plants_df = generate_power_plants_data()
    plants_df.to_parquet(output_dir / "power_plants.parquet", index=False)
    print(f"    Saved {len(plants_df)} plants to {output_dir / 'power_plants.parquet'}")

    # Load profiles
    print("  - Load profiles...")
    load_df = generate_load_profiles_data(year=2020)
    load_df.to_parquet(output_dir / "load_profiles.parquet", index=False)
    print(f"    Saved {len(load_df)} hourly records to {output_dir / 'load_profiles.parquet'}")

    # Solar profiles
    print("  - Solar profiles...")
    solar_df = generate_re_profiles_data(year=2020, technology="solar")
    solar_df.to_parquet(output_dir / "re_profiles_solar.parquet", index=False)
    print(f"    Saved {len(solar_df)} hourly records to {output_dir / 're_profiles_solar.parquet'}")

    # Wind profiles
    print("  - Wind profiles...")
    wind_df = generate_re_profiles_data(year=2020, technology="wind")
    wind_df.to_parquet(output_dir / "re_profiles_wind.parquet", index=False)
    print(f"    Saved {len(wind_df)} hourly records to {output_dir / 're_profiles_wind.parquet'}")

    print(f"\nDone! Sample data saved to {output_dir}")


if __name__ == "__main__":
    main()
