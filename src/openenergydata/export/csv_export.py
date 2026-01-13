"""CSV export functions for model-ready data formats.

Exports data in formats compatible with capacity expansion models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd


def export_power_plants_csv(
    df: pd.DataFrame,
    output_path: Union[str, Path],
    include_columns: Optional[list] = None,
) -> Path:
    """Export power plant data to CSV.

    Args:
        df: DataFrame with power plant data
        output_path: Output file path
        include_columns: Columns to include (uses defaults if None)

    Returns:
        Path to the exported file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Default columns for model input
    default_cols = ["name", "technology", "capacity_mw", "status", "country", "latitude", "longitude"]
    if include_columns is None:
        include_columns = [c for c in default_cols if c in df.columns]

    df_export = df[include_columns].copy()
    df_export.to_csv(output_path, index=False)

    return output_path


def export_load_profiles_csv(
    df: pd.DataFrame,
    output_path: Union[str, Path],
    format_type: str = "standard",
) -> Path:
    """Export load profiles to CSV.

    Args:
        df: DataFrame with zone, month, day, hour, value columns
        output_path: Output file path
        format_type: 'standard' (zone, month, day, hour, value) or 'epm' (EPM format)

    Returns:
        Path to the exported file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df_export = df.copy()

    if format_type == "epm":
        # EPM format: zone, season, day, hour, value
        # Assumes data has already been converted to seasons
        expected_cols = ["zone", "season", "day", "hour", "value"]
        available_cols = [c for c in expected_cols if c in df_export.columns]
        df_export = df_export[available_cols]
    else:
        # Standard format
        expected_cols = ["zone", "month", "day", "hour", "value"]
        available_cols = [c for c in expected_cols if c in df_export.columns]
        df_export = df_export[available_cols]

    df_export.to_csv(output_path, index=False)
    return output_path


def export_re_profiles_csv(
    df: pd.DataFrame,
    output_path: Union[str, Path],
    format_type: str = "standard",
) -> Path:
    """Export renewable energy profiles to CSV.

    Args:
        df: DataFrame with zone, month, day, hour, capacity_factor columns
        output_path: Output file path
        format_type: 'standard' or 'epm'

    Returns:
        Path to the exported file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df_export = df.copy()

    # Rename capacity_factor to value if needed
    if "capacity_factor" in df_export.columns and "value" not in df_export.columns:
        df_export = df_export.rename(columns={"capacity_factor": "value"})

    if format_type == "epm":
        expected_cols = ["zone", "season", "day", "hour", "value"]
    else:
        expected_cols = ["zone", "month", "day", "hour", "value"]

    available_cols = [c for c in expected_cols if c in df_export.columns]
    df_export = df_export[available_cols]
    df_export.to_csv(output_path, index=False)

    return output_path


def export_representative_days_csv(
    profiles_df: pd.DataFrame,
    weights_df: pd.DataFrame,
    output_dir: Union[str, Path],
    profile_name: str = "load",
) -> dict:
    """Export representative day profiles and weights to CSV.

    Args:
        profiles_df: DataFrame with rep_day, hour, value columns
        weights_df: DataFrame with rep_day, weight columns
        output_dir: Output directory
        profile_name: Name for the profile files (e.g., 'load', 'solar', 'wind')

    Returns:
        Dict with paths to exported files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export profiles
    profile_path = output_dir / f"rep_days_{profile_name}.csv"
    profiles_df.to_csv(profile_path, index=False)

    # Export weights
    weights_path = output_dir / "rep_days_weights.csv"
    weights_df.to_csv(weights_path, index=False)

    return {
        "profiles": profile_path,
        "weights": weights_path,
    }


def export_all_data(
    power_plants: Optional[pd.DataFrame],
    load_profiles: Optional[pd.DataFrame],
    re_profiles: Optional[pd.DataFrame],
    output_dir: Union[str, Path],
    region_name: str = "export",
) -> dict:
    """Export all data types to a directory.

    Args:
        power_plants: Power plant DataFrame
        load_profiles: Load profile DataFrame
        re_profiles: RE profile DataFrame
        output_dir: Output directory
        region_name: Name for the export (used in filenames)

    Returns:
        Dict with paths to all exported files
    """
    output_dir = Path(output_dir) / region_name
    output_dir.mkdir(parents=True, exist_ok=True)

    exported = {}

    if power_plants is not None and not power_plants.empty:
        exported["power_plants"] = export_power_plants_csv(
            power_plants,
            output_dir / "power_plants.csv"
        )

    if load_profiles is not None and not load_profiles.empty:
        exported["load_profiles"] = export_load_profiles_csv(
            load_profiles,
            output_dir / "load_profiles.csv"
        )

    if re_profiles is not None and not re_profiles.empty:
        exported["re_profiles"] = export_re_profiles_csv(
            re_profiles,
            output_dir / "re_profiles.csv"
        )

    return exported
