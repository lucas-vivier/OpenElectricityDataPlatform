"""Power plant data source adapter.

Handles loading and cleaning of power plant data from Global Integrated Power.
Adapted from EPM pre-analysis generators_pipeline.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from ...config.regions import resolve_country_name

# Column aliases to normalize Global Integrated Power headers into a consistent schema
COLUMN_ALIASES: Dict[str, str] = {
    # Name columns
    "Plant / Project name": "name",
    "Plant Name": "name",
    "Name": "name",
    "gppd_idnr": "name",
    # Technology columns (Global Integrated Power April 2025 has both Type and Technology)
    "Type": "type",  # General type: nuclear, solar, wind, etc.
    "Technology": "technology_detail",  # Specific: pressurized heavy water reactor
    "Fuel": "fuel",
    "primary_fuel": "fuel",
    # Capacity
    "Capacity (MW)": "capacity_mw",
    "Capacity_MW": "capacity_mw",
    "CapacityMW": "capacity_mw",
    # Status
    "Status": "status",
    "Start year": "start_year",
    "Retired year": "retired_year",
    # Location
    "Country/area": "country",
    "Country": "country",
    "country_long": "country",
    "country": "country",
    "Subregion": "subregion",
    "Region": "region",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Subnational unit (state, province)": "state",
    # Additional Global Integrated Power columns
    "Owner": "owner",
    "Parent": "parent",
    "Hydrogen production": "hydrogen_production",
    "Hydrogen capable": "hydrogen_capable",
    "CHP": "chp",
    "CCS": "ccs",
    "GEM unit/phase ID": "gem_id",
}

# Status category keywords for normalization
STATUS_CATEGORY_KEYWORDS: List[tuple] = [
    ("Pre-Construction", ("pre-construction", "pre construction", "planned", "permitted")),
    ("Announced", ("announced", "proposed")),
    ("Construction", ("under construction", "construction", "committed")),
    ("Operating", ("operating", "existing", "online", "mothballed")),
    ("Retired", ("retired", "cancelled", "shelved")),
]

# Technology normalization mapping (from Global Integrated Power "Type" column to standard names)
TECHNOLOGY_MAPPING: Dict[str, str] = {
    # Solar
    "solar": "Solar",
    "solar pv": "Solar",
    "solar photovoltaic": "Solar",
    "solar thermal": "Solar Thermal",
    "csp": "Solar Thermal",
    "concentrated solar power": "Solar Thermal",
    # Wind
    "wind": "Wind",
    "wind onshore": "Wind",
    "wind offshore": "Wind Offshore",
    "offshore wind": "Wind Offshore",
    # Hydro
    "hydro": "Hydro",
    "hydroelectric": "Hydro",
    "hydropower": "Hydro",
    "pumped storage": "Hydro Storage",
    "pumped hydro": "Hydro Storage",
    # Fossil fuels
    "gas": "Gas",
    "natural gas": "Gas",
    "gas/oil": "Gas",
    "coal": "Coal",
    "oil": "Oil",
    "diesel": "Oil",
    "oil/gas": "Oil",
    # Nuclear
    "nuclear": "Nuclear",
    # Renewables
    "biomass": "Biomass",
    "bioenergy": "Biomass",
    "biogas": "Biomass",
    "geothermal": "Geothermal",
    "waste": "Waste",
    "waste-to-energy": "Waste",
    # Storage
    "battery": "Battery",
    "battery storage": "Battery",
    "storage": "Storage",
}

# Default technology icons for maps
DEFAULT_TECH_ICONS: Dict[str, str] = {
    "Hydro": "tint",
    "Solar": "sun",
    "Wind": "wind",
    "Thermal": "fire",
    "Gas": "gas-pump",
    "Coal": "industry",
    "Oil": "oil-can",
    "Nuclear": "atom",
    "Geothermal": "temperature-high",
    "Biomass": "leaf",
}

# Status category colors for visualization
DEFAULT_STATUS_COLORS: Dict[str, str] = {
    "Operating": "#2e7d32",
    "Construction": "#ff8f00",
    "Pre-Construction": "#1f77b4",
    "Announced": "#8e44ad",
    "Other": "#7f8c8d",
}


def _collapse_duplicate_columns(df: pd.DataFrame, column_names: Iterable[str]) -> pd.DataFrame:
    """Collapse duplicated columns by taking the first non-null value."""
    df = df.copy()
    for name in column_names:
        mask = [col == name for col in df.columns]
        if sum(mask) > 1:
            collapsed = df.loc[:, mask].bfill(axis=1).iloc[:, 0]
            first_idx = mask.index(True)
            keep_cols = [col for col, is_dupe in zip(df.columns, mask) if not is_dupe]
            df = df.loc[:, keep_cols]
            df.insert(first_idx, name, collapsed)
    return df


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename common Global Integrated Power columns and coerce expected dtypes."""
    df = df.copy()
    rename = {col: COLUMN_ALIASES[col] for col in df.columns if col in COLUMN_ALIASES}
    df = df.rename(columns=rename)

    # Consolidate duplicated normalized columns
    df = _collapse_duplicate_columns(df, set(COLUMN_ALIASES.values()))

    # Create unified 'technology' column from 'type' (preferred) or 'technology_detail'
    if "type" in df.columns:
        df["technology"] = df["type"].fillna("").astype(str)
    elif "technology_detail" in df.columns:
        df["technology"] = df["technology_detail"].fillna("").astype(str)

    # Ensure string columns exist
    for col in ("name", "technology", "status", "country", "fuel", "subregion", "region"):
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    # Ensure numeric columns exist
    for col in ("capacity_mw", "latitude", "longitude", "start_year", "retired_year"):
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _status_category(value: Optional[str]) -> str:
    """Return a normalized status category based on known keywords."""
    normalized = (value or "").lower()
    for category, keywords in STATUS_CATEGORY_KEYWORDS:
        for keyword in keywords:
            if keyword in normalized:
                return category
    return "Other"


def load_global_integrated_power_data(
    xlsx_path: Path,
    countries: Optional[List[str]] = None,
    sheet_name: str = "Power facilities",
    verbose: bool = False,
) -> pd.DataFrame:
    """Load and standardize generation sites from Global Integrated Power Excel or CSV sources.

    Args:
        xlsx_path: Path to Global Integrated Power Excel file or CSV
        countries: List of countries to filter by (None = all countries)
        sheet_name: Excel sheet name (for .xlsx files)
        verbose: Whether to print progress messages

    Returns:
        DataFrame with standardized columns: name, technology, capacity_mw, status,
        status_category, country, latitude, longitude, fuel, start_year, retired_year
    """
    path = Path(xlsx_path)
    if not path.exists():
        raise FileNotFoundError(f"Global Integrated Power data file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df_raw = pd.read_csv(path)
        if "country_long" in df_raw.columns:
            df_raw["country"] = df_raw["country_long"].fillna(df_raw.get("country"))
        df = _normalize_columns(df_raw)
        if "status" in df.columns:
            df["status"] = df["status"].replace("", np.nan).fillna("Operating")
        else:
            df["status"] = "Operating"
    else:
        df_raw = pd.read_excel(path, sheet_name=sheet_name, header=0, index_col=None)
        df = _normalize_columns(df_raw)

    if verbose:
        print(f"Loaded {len(df_raw)} raw rows from {path}")

    # Filter by countries if provided
    if countries:
        df = filter_by_country(df, countries, verbose=verbose)

    # Clean up - normalize technology names
    df = clean_global_integrated_power_data(df)

    # Drop rows without coordinates
    df = df.dropna(subset=["latitude", "longitude"])

    # Remove duplicates
    df = df.drop_duplicates(subset=["country", "name", "technology", "latitude", "longitude"])

    # Fill missing values
    df["status"] = df["status"].replace("", "Unknown")
    df["technology"] = df["technology"].replace("", "Unknown")

    # Add status category
    df["status_category"] = df["status"].apply(_status_category)

    if verbose:
        print(f"{len(df)} rows remain after filtering and cleaning")

    # Select and order final columns
    output_columns = [
        "name", "technology", "capacity_mw", "status", "status_category",
        "country", "latitude", "longitude", "fuel", "start_year", "retired_year",
        "subregion", "region"
    ]
    # Only include columns that exist
    output_columns = [c for c in output_columns if c in df.columns]

    return df[output_columns].reset_index(drop=True)


def filter_by_country(
    df: pd.DataFrame,
    countries: List[str],
    verbose: bool = False,
) -> pd.DataFrame:
    """Filter power plant data by country names using fuzzy matching.

    Args:
        df: DataFrame with 'country' column
        countries: List of country names to include
        verbose: Whether to print matching info

    Returns:
        Filtered DataFrame
    """
    if not countries or "country" not in df.columns:
        return df

    available = df["country"].dropna().unique().tolist()
    resolved_map: Dict[str, str] = {}

    for country in countries:
        match = resolve_country_name(country, available, threshold=0.75)
        if match:
            resolved_map[country] = match
        elif verbose:
            print(f"No match found for '{country}'; skipping.")

    if not resolved_map:
        return pd.DataFrame(columns=df.columns)

    df = df[df["country"].isin(resolved_map.values())].copy()

    # Remap to original requested names
    reverse_map = {v: k for k, v in resolved_map.items()}
    df["country"] = df["country"].map(reverse_map).fillna(df["country"])

    return df


def clean_global_integrated_power_data(df: pd.DataFrame) -> pd.DataFrame:
    """Additional cleaning of Global Integrated Power data.

    Args:
        df: Raw Global Integrated Power DataFrame

    Returns:
        Cleaned DataFrame with normalized technology names
    """
    df = df.copy()

    # Normalize technology names using TECHNOLOGY_MAPPING
    def normalize_tech(tech: str) -> str:
        if not tech:
            return "Unknown"
        tech_lower = tech.lower().strip()
        if tech_lower in TECHNOLOGY_MAPPING:
            return TECHNOLOGY_MAPPING[tech_lower]
        # Try partial matching
        for key, value in TECHNOLOGY_MAPPING.items():
            if key in tech_lower:
                return value
        return tech.title() if tech else "Unknown"

    df["technology"] = df["technology"].apply(normalize_tech)

    return df


def load_gppd_data(
    csv_path: Path,
    countries: Optional[List[str]] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Load and standardize power plant data from Global Power Plant Database (WRI).

    Args:
        csv_path: Path to GPPD CSV file
        countries: List of countries to filter by (None = all countries)
        verbose: Whether to print progress messages

    Returns:
        DataFrame with standardized columns: name, technology, capacity_mw, status,
        status_category, country, latitude, longitude, fuel, start_year
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"GPPD data file not found: {path}")

    df_raw = pd.read_csv(path)

    if verbose:
        print(f"Loaded {len(df_raw)} raw rows from {path}")

    # Map GPPD columns to standard schema
    df = pd.DataFrame({
        "name": df_raw["name"].fillna(""),
        "technology": df_raw["primary_fuel"].fillna("Unknown"),
        "capacity_mw": pd.to_numeric(df_raw["capacity_mw"], errors="coerce").fillna(0),
        "status": "Operating",  # GPPD only contains operating plants
        "country": df_raw["country_long"].fillna(df_raw.get("country", "")),
        "latitude": pd.to_numeric(df_raw["latitude"], errors="coerce"),
        "longitude": pd.to_numeric(df_raw["longitude"], errors="coerce"),
        "fuel": df_raw["primary_fuel"].fillna(""),
        "start_year": pd.to_numeric(df_raw["commissioning_year"], errors="coerce"),
    })

    # Filter by countries if provided
    if countries:
        df = filter_by_country(df, countries, verbose=verbose)

    # Normalize technology names using TECHNOLOGY_MAPPING
    def normalize_tech(tech: str) -> str:
        if not tech:
            return "Unknown"
        tech_lower = tech.lower().strip()
        if tech_lower in TECHNOLOGY_MAPPING:
            return TECHNOLOGY_MAPPING[tech_lower]
        for key, value in TECHNOLOGY_MAPPING.items():
            if key in tech_lower:
                return value
        return tech.title() if tech else "Unknown"

    df["technology"] = df["technology"].apply(normalize_tech)

    # Add status category (all are Operating in GPPD)
    df["status_category"] = "Operating"

    # Drop rows without coordinates
    df = df.dropna(subset=["latitude", "longitude"])

    if verbose:
        print(f"{len(df)} rows remain after filtering and cleaning")

    return df.reset_index(drop=True)


def summarize_by_technology(df: pd.DataFrame, status: str = "Operating") -> pd.DataFrame:
    """Summarize capacity by technology.

    Args:
        df: Power plant DataFrame
        status: Status category to filter by (or 'all' for all statuses)

    Returns:
        Summary DataFrame with technology and total_capacity_mw columns
    """
    if df.empty:
        return pd.DataFrame(columns=["technology", "total_capacity_mw"])

    if status != "all":
        df["status_category"] = df["status"].apply(_status_category)
        df = df[df["status_category"] == status]

    if df.empty:
        return pd.DataFrame(columns=["technology", "total_capacity_mw"])

    summary = (
        df.groupby("technology", dropna=False)
        .agg(total_capacity_mw=("capacity_mw", "sum"))
        .reset_index()
        .sort_values("total_capacity_mw", ascending=False)
    )
    return summary
