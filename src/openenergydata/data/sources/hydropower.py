"""Hydropower data source adapter.

Handles loading and cleaning of hydropower data from:
- African Hydropower Atlas v2.0
- Global Energy Monitor (filtered from Global Integrated Power)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ...config.regions import resolve_country_name


# Status normalization mapping
STATUS_MAPPING: Dict[str, str] = {
    "existing": "Operating",
    "operating": "Operating",
    "committed": "Construction",
    "construction": "Construction",
    "candidate": "Planned",
    "planned": "Planned",
    "announced": "Announced",
    "mothballed": "Mothballed",
    "retired": "Retired",
    "cancelled": "Cancelled",
}


def load_african_hydro_atlas(
    xlsx_path: Path,
    countries: Optional[List[str]] = None,
    sheet_name: str = "1 - Spatial and technical data",
    verbose: bool = False,
) -> pd.DataFrame:
    """Load hydropower data from African Hydropower Atlas.

    Args:
        xlsx_path: Path to the African Hydropower Atlas Excel file
        countries: List of countries to filter by (None = all)
        sheet_name: Sheet name containing spatial/technical data
        verbose: Whether to print progress messages

    Returns:
        DataFrame with standardized columns: name, technology, capacity_mw, status,
        country, latitude, longitude, river_name, river_basin, reservoir_size_mcm
    """
    path = Path(xlsx_path)
    if not path.exists():
        raise FileNotFoundError(f"African Hydropower Atlas file not found: {path}")

    # Read with header on row 2 (0-indexed)
    df = pd.read_excel(path, sheet_name=sheet_name, header=2)

    if verbose:
        print(f"Loaded {len(df)} rows from {path}")

    # Normalize column names
    column_mapping = {
        "Country": "country",
        "Unit Name": "name",
        "Status": "status",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "River Name": "river_name",
        "River Basin": "river_basin",
        "Capacity": "capacity_mw",
        "Reservoir Size": "reservoir_size_mcm",
        "Mean Annual Discharge": "mean_annual_discharge",
        "Design Discharge": "design_discharge",
        "First Year": "start_year",
        "Size Type": "size_type",
    }

    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    # Normalize country names (uppercase in source)
    if "country" in df.columns:
        df["country"] = df["country"].str.title()

    # Normalize status
    if "status" in df.columns:
        df["status_original"] = df["status"]
        df["status"] = df["status"].str.lower().map(
            lambda x: STATUS_MAPPING.get(x, "Unknown") if pd.notna(x) else "Unknown"
        )

    # Add technology column
    df["technology"] = "Hydro"

    # Filter by countries if provided
    if countries:
        available = df["country"].dropna().unique().tolist()
        resolved = []
        for country in countries:
            match = resolve_country_name(country, available, threshold=0.75)
            if match:
                resolved.append(match)
            elif verbose:
                print(f"No match found for '{country}'")

        if resolved:
            df = df[df["country"].isin(resolved)]
        else:
            df = pd.DataFrame(columns=df.columns)

    # Convert numeric columns
    for col in ["capacity_mw", "latitude", "longitude", "reservoir_size_mcm",
                "mean_annual_discharge", "design_discharge", "start_year"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Select output columns
    output_columns = [
        "name", "technology", "capacity_mw", "status", "country",
        "latitude", "longitude", "river_name", "river_basin",
        "reservoir_size_mcm", "start_year", "size_type"
    ]
    output_columns = [c for c in output_columns if c in df.columns]

    if verbose:
        print(f"{len(df)} rows after filtering")

    return df[output_columns].reset_index(drop=True)


def load_hydro_climate_scenarios(
    xlsx_path: Path,
    scenario: str = "SSP1-RCP26",
    countries: Optional[List[str]] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Load hydropower fleet projections under climate scenarios.

    Args:
        xlsx_path: Path to the African Hydropower Atlas Excel file
        scenario: Climate scenario (SSP1-RCP26, SSP4-RCP60, SSP5-RCP85)
        countries: List of countries to filter by
        verbose: Whether to print progress messages

    Returns:
        DataFrame with hydropower projections including capacity factors
    """
    path = Path(xlsx_path)
    if not path.exists():
        raise FileNotFoundError(f"African Hydropower Atlas file not found: {path}")

    # Map scenario to sheet name
    scenario_sheets = {
        "SSP1-RCP26": "4b - HydrofleetAll SSP1-RCP26",
        "SSP4-RCP60": "4c - HydrofleetAll SSP4-RCP60",
        "SSP5-RCP85": "4d - HydrofleetAll SSP5-RCP85",
    }

    if scenario not in scenario_sheets:
        raise ValueError(f"Unknown scenario: {scenario}. Options: {list(scenario_sheets.keys())}")

    sheet_name = scenario_sheets[scenario]
    df = pd.read_excel(path, sheet_name=sheet_name, header=0)

    if verbose:
        print(f"Loaded {len(df)} rows for scenario {scenario}")

    # Filter by countries if provided
    if countries and "Country" in df.columns:
        available = df["Country"].dropna().unique().tolist()
        resolved = []
        for country in countries:
            match = resolve_country_name(country, available, threshold=0.75)
            if match:
                resolved.append(match)

        if resolved:
            df = df[df["Country"].isin(resolved)]

    return df


def summarize_hydro_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize hydropower capacity by country.

    Args:
        df: Hydropower DataFrame with 'country' and 'capacity_mw' columns

    Returns:
        Summary DataFrame with country, total_capacity_mw, plant_count
    """
    if df.empty or "country" not in df.columns:
        return pd.DataFrame(columns=["country", "total_capacity_mw", "plant_count"])

    summary = (
        df.groupby("country", dropna=False)
        .agg(
            total_capacity_mw=("capacity_mw", "sum"),
            plant_count=("name", "count"),
        )
        .reset_index()
        .sort_values("total_capacity_mw", ascending=False)
    )

    return summary
