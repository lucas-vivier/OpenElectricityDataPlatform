#!/usr/bin/env python3
"""Preprocessing pipeline for OpenEnergyData.

This script processes source data files into regional datasets ready for
Zenodo hosting or local caching.

Usage:
    # Preprocess single region
    python scripts/preprocess_data.py --region south_africa --output data/processed/

    # Preprocess all regions
    python scripts/preprocess_data.py --all --output data/processed/

    # Generate Zenodo package
    python scripts/preprocess_data.py --package zenodo --version 1.0.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openenergydata.config.data_paths import get_data_source_path, data_source_exists
from openenergydata.config.regions import get_regions, get_countries_for_region
from openenergydata.data.sources.power_plants import load_global_integrated_power_data
from openenergydata.data.sources.hydropower import load_african_hydro_atlas, load_global_hydro_tracker
from openenergydata.data.sources.irena import load_irena_solar_msr, load_irena_wind_msr, summarize_msr_by_country
from openenergydata.data.sources.owid import load_owid_energy, get_latest_values


# Typical daily capacity factor curves (normalized to peak = 1.0)
# Hour 0 = midnight, Hour 12 = noon
SOLAR_DAILY_CURVE = np.array([
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0,      # 00:00 - 05:00 (night)
    0.05, 0.15, 0.35, 0.60, 0.80, 0.95, # 06:00 - 11:00 (morning ramp)
    1.0, 0.98, 0.90, 0.75, 0.55, 0.30,  # 12:00 - 17:00 (afternoon)
    0.10, 0.0, 0.0, 0.0, 0.0, 0.0       # 18:00 - 23:00 (evening/night)
])

WIND_DAILY_CURVE = np.array([
    1.05, 1.08, 1.10, 1.10, 1.08, 1.05,  # 00:00 - 05:00 (night - higher)
    1.0, 0.95, 0.90, 0.88, 0.85, 0.85,   # 06:00 - 11:00 (morning - drops)
    0.85, 0.88, 0.90, 0.92, 0.95, 0.98,  # 12:00 - 17:00 (afternoon)
    1.0, 1.02, 1.03, 1.04, 1.05, 1.05    # 18:00 - 23:00 (evening - rises)
])


def expand_daily_to_hourly(
    daily_values: np.ndarray,
    technology: str = "solar",
) -> np.ndarray:
    """Expand daily capacity factor values to hourly (8760) values.

    IRENA H1-H366 provides one capacity factor per day of year.
    This function expands each daily value across 24 hours using
    a typical diurnal curve for the technology.

    Args:
        daily_values: Array of 365 or 366 daily capacity factors
        technology: 'solar' or 'wind' (determines daily curve shape)

    Returns:
        Array of 8760 hourly capacity factors (365 days × 24 hours)
    """
    # Use 365 days (skip leap day if present)
    daily = daily_values[:365] if len(daily_values) > 365 else daily_values

    # Pad if we have fewer than 365 days
    if len(daily) < 365:
        daily = np.pad(daily, (0, 365 - len(daily)), mode='edge')

    # Get the appropriate daily curve
    curve = SOLAR_DAILY_CURVE if technology == "solar" else WIND_DAILY_CURVE

    # Normalize curve to integrate to 1 (so daily average is preserved)
    curve_normalized = curve / curve.mean()

    # Expand: each daily value × 24 hourly weights
    hourly = np.zeros(365 * 24)
    for day_idx, daily_cf in enumerate(daily):
        start_hour = day_idx * 24
        end_hour = start_hour + 24
        hourly[start_hour:end_hour] = daily_cf * curve_normalized

    # Clip to valid range
    hourly = np.clip(hourly, 0, 1)

    return hourly


def generate_country_re_profiles(
    countries: list[str],
    technology: str = "solar",
    year: int = 2023,
    verbose: bool = False,
) -> pd.DataFrame:
    """Generate country-level RE capacity factor profiles.

    Loads IRENA MSR data for countries, extracts H1-H8760 hourly profiles,
    and aggregates by capacity-weighting to country level.

    Args:
        countries: List of country names
        technology: 'solar' or 'wind'
        year: Year for the profiles (used in output metadata)
        verbose: Print progress

    Returns:
        DataFrame with columns: country, month, day, hour, capacity_factor
    """
    # Load IRENA data with hourly profiles
    if technology == "solar":
        source_path = get_data_source_path("irena_solar_msr")
        if not source_path or not source_path.exists():
            if verbose:
                print(f"IRENA solar MSR file not found")
            return pd.DataFrame()
        df = load_irena_solar_msr(source_path, countries, include_hourly=True, verbose=verbose)
        cf_col = "capacity_factor"
    else:
        source_path = get_data_source_path("irena_wind_msr")
        if not source_path or not source_path.exists():
            if verbose:
                print(f"IRENA wind MSR file not found")
            return pd.DataFrame()
        df = load_irena_wind_msr(source_path, countries, include_hourly=True, verbose=verbose)
        cf_col = "capacity_factor_100m"

    if df.empty:
        if verbose:
            print(f"No {technology} data for countries: {countries}")
        return pd.DataFrame()

    # Get hourly columns (H1-H8760 for full year hourly data)
    hourly_cols = sorted(
        [c for c in df.columns if c.startswith("H") and c[1:].isdigit()],
        key=lambda x: int(x[1:])
    )

    if not hourly_cols:
        if verbose:
            print(f"No hourly columns (H1-H8760) found in {technology} data")
        return pd.DataFrame()

    # Determine if data is 8760 (hourly) or 366 (daily representative)
    n_hours = len(hourly_cols)
    is_full_hourly = n_hours >= 8760

    if verbose:
        print(f"  Found {n_hours} hourly columns ({'full year' if is_full_hourly else 'representative days'})")

    results = []

    for country in df["country"].unique():
        country_df = df[df["country"] == country]

        if country_df.empty:
            continue

        # Get capacity weights
        if "capacity_mw" in country_df.columns:
            weights = country_df["capacity_mw"].fillna(1).values
        else:
            weights = np.ones(len(country_df))

        weights = weights / weights.sum()  # Normalize

        # Capacity-weighted average of hourly profiles
        hourly_profiles = country_df[hourly_cols].values  # shape: (n_sites, n_hours)
        weighted_hourly = np.average(hourly_profiles, axis=0, weights=weights)

        # Handle data format
        if is_full_hourly:
            # Use first 8760 hours directly (skip leap day hour if present)
            hourly_cf = weighted_hourly[:8760]
        else:
            # Expand daily values to 8760 hours
            hourly_cf = expand_daily_to_hourly(weighted_hourly, technology)

        # Create DataFrame with time columns
        hours = pd.date_range(f"{year}-01-01", periods=8760, freq="h")
        country_result = pd.DataFrame({
            "country": country,
            "month": hours.month,
            "day": hours.day,
            "hour": hours.hour,
            "capacity_factor": hourly_cf,
        })

        # Add metadata
        country_result["technology"] = technology.title()
        country_result["year"] = year

        # Add aggregate stats
        summary = summarize_msr_by_country(country_df, technology)
        if not summary.empty:
            row = summary.iloc[0]
            country_result["total_capacity_mw"] = row.get("total_capacity_mw", 0)
            country_result["avg_lcoe"] = row.get("avg_lcoe", np.nan)

        results.append(country_result)

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)


def preprocess_region(
    region_id: str,
    output_dir: Path,
    year: int = 2023,
    verbose: bool = False,
) -> dict:
    """Process all data for a region and save to output directory.

    Creates:
        {output_dir}/{region_id}/
        ├── power_plants.parquet
        ├── hydropower.parquet
        ├── re_profiles_solar.parquet
        ├── re_profiles_wind.parquet
        ├── resource_potential_solar.parquet
        ├── resource_potential_wind.parquet
        ├── socioeconomic.parquet
        └── metadata.json

    Args:
        region_id: Region identifier (e.g., 'south_africa')
        output_dir: Base output directory
        year: Year for time-series data
        verbose: Print progress

    Returns:
        Dictionary with processing statistics
    """
    regions = get_regions()
    if region_id not in regions:
        raise ValueError(f"Unknown region: {region_id}. Available: {list(regions.keys())}")

    region_config = regions[region_id]
    countries = get_countries_for_region(region_id)

    if verbose:
        print(f"\n{'='*60}")
        print(f"Processing region: {region_id}")
        print(f"Countries: {countries}")
        print(f"{'='*60}")

    # Create output directory
    region_output = output_dir / region_id
    region_output.mkdir(parents=True, exist_ok=True)

    stats = {
        "region_id": region_id,
        "countries": countries,
        "processed_at": datetime.now().isoformat(),
        "files": {},
    }

    # 1. Power Plants
    if verbose:
        print("\n[1/7] Processing power plants...")
    try:
        gip_path = get_data_source_path("global_integrated_power_plants")
        if gip_path and gip_path.exists():
            plants_df = load_global_integrated_power_data(gip_path, countries, verbose=verbose)
            if not plants_df.empty:
                output_path = region_output / "power_plants.parquet"
                plants_df.to_parquet(output_path, index=False)
                stats["files"]["power_plants"] = {
                    "rows": len(plants_df),
                    "size_mb": round(output_path.stat().st_size / 1e6, 2),
                }
                if verbose:
                    print(f"  Saved {len(plants_df)} plants to {output_path}")
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")

    # 2. Hydropower
    if verbose:
        print("\n[2/7] Processing hydropower...")
    try:
        hydro_dfs = []

        african_path = get_data_source_path("african_hydro_atlas")
        if african_path and african_path.exists():
            african_df = load_african_hydro_atlas(african_path, countries, verbose=verbose)
            if not african_df.empty:
                hydro_dfs.append(african_df)

        global_path = get_data_source_path("global_hydro_tracker")
        if global_path and global_path.exists():
            global_df = load_global_hydro_tracker(global_path, countries, verbose=verbose)
            if not global_df.empty:
                hydro_dfs.append(global_df)

        if hydro_dfs:
            hydro_df = pd.concat(hydro_dfs, ignore_index=True)
            # Deduplicate by name and country
            hydro_df = hydro_df.drop_duplicates(subset=["name", "country"], keep="first")
            output_path = region_output / "hydropower.parquet"
            hydro_df.to_parquet(output_path, index=False)
            stats["files"]["hydropower"] = {
                "rows": len(hydro_df),
                "size_mb": round(output_path.stat().st_size / 1e6, 2),
            }
            if verbose:
                print(f"  Saved {len(hydro_df)} hydro plants to {output_path}")
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")

    # 3. Solar RE Profiles
    if verbose:
        print("\n[3/7] Processing solar RE profiles...")
    try:
        solar_profiles = generate_country_re_profiles(countries, "solar", year, verbose)
        if not solar_profiles.empty:
            output_path = region_output / "re_profiles_solar.parquet"
            solar_profiles.to_parquet(output_path, index=False)
            stats["files"]["re_profiles_solar"] = {
                "rows": len(solar_profiles),
                "countries": solar_profiles["country"].nunique(),
                "size_mb": round(output_path.stat().st_size / 1e6, 2),
            }
            if verbose:
                print(f"  Saved {len(solar_profiles)} solar profile rows to {output_path}")
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")

    # 4. Wind RE Profiles
    if verbose:
        print("\n[4/7] Processing wind RE profiles...")
    try:
        wind_profiles = generate_country_re_profiles(countries, "wind", year, verbose)
        if not wind_profiles.empty:
            output_path = region_output / "re_profiles_wind.parquet"
            wind_profiles.to_parquet(output_path, index=False)
            stats["files"]["re_profiles_wind"] = {
                "rows": len(wind_profiles),
                "countries": wind_profiles["country"].nunique(),
                "size_mb": round(output_path.stat().st_size / 1e6, 2),
            }
            if verbose:
                print(f"  Saved {len(wind_profiles)} wind profile rows to {output_path}")
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")

    # 5. Solar Resource Potential (IRENA sites)
    if verbose:
        print("\n[5/7] Processing solar resource potential...")
    try:
        solar_path = get_data_source_path("irena_solar_msr")
        if solar_path and solar_path.exists():
            solar_potential = load_irena_solar_msr(solar_path, countries, include_hourly=False, verbose=verbose)
            if not solar_potential.empty:
                output_path = region_output / "resource_potential_solar.parquet"
                solar_potential.to_parquet(output_path, index=False)
                stats["files"]["resource_potential_solar"] = {
                    "rows": len(solar_potential),
                    "size_mb": round(output_path.stat().st_size / 1e6, 2),
                }
                if verbose:
                    print(f"  Saved {len(solar_potential)} solar sites to {output_path}")
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")

    # 6. Wind Resource Potential (IRENA sites)
    if verbose:
        print("\n[6/7] Processing wind resource potential...")
    try:
        wind_path = get_data_source_path("irena_wind_msr")
        if wind_path and wind_path.exists():
            wind_potential = load_irena_wind_msr(wind_path, countries, include_hourly=False, verbose=verbose)
            if not wind_potential.empty:
                output_path = region_output / "resource_potential_wind.parquet"
                wind_potential.to_parquet(output_path, index=False)
                stats["files"]["resource_potential_wind"] = {
                    "rows": len(wind_potential),
                    "size_mb": round(output_path.stat().st_size / 1e6, 2),
                }
                if verbose:
                    print(f"  Saved {len(wind_potential)} wind sites to {output_path}")
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")

    # 7. Socioeconomic Data
    if verbose:
        print("\n[7/7] Processing socioeconomic data...")
    try:
        owid_path = get_data_source_path("owid_energy")
        if owid_path and owid_path.exists():
            socio_df = get_latest_values(owid_path, countries, verbose=verbose)
            if not socio_df.empty:
                output_path = region_output / "socioeconomic.parquet"
                socio_df.to_parquet(output_path, index=False)
                stats["files"]["socioeconomic"] = {
                    "rows": len(socio_df),
                    "size_mb": round(output_path.stat().st_size / 1e6, 2),
                }
                if verbose:
                    print(f"  Saved {len(socio_df)} socioeconomic rows to {output_path}")
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")

    # Save metadata
    metadata_path = region_output / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(stats, f, indent=2)

    if verbose:
        print(f"\n{'='*60}")
        print(f"Completed: {region_id}")
        print(f"Files created: {len(stats['files'])}")
        total_size = sum(f.get("size_mb", 0) for f in stats["files"].values())
        print(f"Total size: {total_size:.2f} MB")
        print(f"{'='*60}")

    return stats


def preprocess_all_regions(
    output_dir: Path,
    year: int = 2023,
    verbose: bool = False,
) -> dict:
    """Process all available regions.

    Args:
        output_dir: Base output directory
        year: Year for time-series data
        verbose: Print progress

    Returns:
        Dictionary with all region statistics
    """
    regions = get_regions()
    all_stats = {}

    for region_id in regions:
        try:
            stats = preprocess_region(region_id, output_dir, year, verbose)
            all_stats[region_id] = stats
        except Exception as e:
            print(f"Error processing {region_id}: {e}")
            all_stats[region_id] = {"error": str(e)}

    # Save index
    index_path = output_dir / "index.json"
    with open(index_path, "w") as f:
        json.dump(all_stats, f, indent=2)

    return all_stats


def generate_zenodo_package(
    output_dir: Path,
    version: str = "1.0.0",
    verbose: bool = False,
) -> Path:
    """Generate a Zenodo-ready package from processed data.

    Args:
        output_dir: Directory with processed region data
        version: Version string for the package
        verbose: Print progress

    Returns:
        Path to the generated package directory
    """
    package_dir = output_dir / f"openenergydata-v{version}"
    package_dir.mkdir(parents=True, exist_ok=True)

    # Copy processed data and generate checksums
    checksums = {}

    for region_dir in output_dir.iterdir():
        if not region_dir.is_dir() or region_dir.name.startswith("openenergydata"):
            continue

        dest_dir = package_dir / region_dir.name
        dest_dir.mkdir(exist_ok=True)

        for file in region_dir.glob("*.parquet"):
            dest_file = dest_dir / file.name
            dest_file.write_bytes(file.read_bytes())

            # Calculate checksum
            sha256 = hashlib.sha256(file.read_bytes()).hexdigest()
            checksums[f"{region_dir.name}/{file.name}"] = sha256

    # Write checksums
    checksums_path = package_dir / "checksums.json"
    with open(checksums_path, "w") as f:
        json.dump(checksums, f, indent=2)

    # Write README
    readme_path = package_dir / "README.md"
    readme_path.write_text(f"""# OpenEnergyData v{version}

Preprocessed energy data for capacity expansion modeling.

## Contents

This package contains regional datasets with:
- Power plants (from Global Integrated Power / Global Energy Monitor)
- Hydropower plants (African Hydropower Atlas, Global Hydropower Tracker)
- Solar/Wind RE profiles (hourly capacity factors from IRENA MSR)
- Resource potential sites (IRENA Model Solar/Wind Resource)
- Socioeconomic data (OWID Energy Dataset)

## Format

All data files are in Apache Parquet format for efficient reading.

## License

Data sources retain their original licenses:
- Global Energy Monitor: CC-BY
- IRENA Global Atlas: IRENA terms
- OWID: CC-BY

## Citation

Please cite the original data sources when using this data.

Generated: {datetime.now().isoformat()}
""")

    if verbose:
        print(f"Created Zenodo package at: {package_dir}")

    return package_dir


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess OpenEnergyData for regional datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process South Africa
    python scripts/preprocess_data.py --region south_africa --output data/processed/

    # Process all regions
    python scripts/preprocess_data.py --all --output data/processed/

    # Create Zenodo package
    python scripts/preprocess_data.py --package zenodo --version 1.0.0 --output data/processed/
        """,
    )

    parser.add_argument(
        "--region",
        type=str,
        help="Region to process (e.g., south_africa, central_africa)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all available regions",
    )
    parser.add_argument(
        "--package",
        type=str,
        choices=["zenodo"],
        help="Generate package for hosting",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed"),
        help="Output directory (default: data/processed)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2023,
        help="Year for time-series data (default: 2023)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="1.0.0",
        help="Version for package generation (default: 1.0.0)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed progress",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.region and not args.all and not args.package:
        parser.error("Must specify --region, --all, or --package")

    # Run preprocessing
    if args.region:
        preprocess_region(args.region, args.output, args.year, args.verbose)
    elif args.all:
        preprocess_all_regions(args.output, args.year, args.verbose)

    # Generate package if requested
    if args.package == "zenodo":
        generate_zenodo_package(args.output, args.version, args.verbose)


if __name__ == "__main__":
    main()
