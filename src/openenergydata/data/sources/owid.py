"""OWID (Our World in Data) energy dataset loader.

Provides access to global energy statistics including:
- Electricity demand and generation
- Energy consumption by source
- Population and GDP
- Per-capita metrics

Source: https://github.com/owid/energy-data
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd

from ...config.regions import resolve_country_name


# Key columns for energy modeling
OWID_COLUMNS = {
    # Core identifiers
    "country": "country",
    "year": "year",
    "iso_code": "iso_code",

    # Socio-economic
    "population": "population",
    "gdp": "gdp",

    # Electricity
    "electricity_demand": "electricity_demand",  # TWh
    "electricity_generation": "electricity_generation",  # TWh
    "electricity_demand_per_capita": "electricity_demand_per_capita",  # kWh

    # Energy
    "energy_per_capita": "energy_per_capita",  # kWh
    "energy_per_gdp": "energy_per_gdp",  # kWh per $

    # Fossil fuels
    "fossil_electricity": "fossil_electricity",  # TWh
    "coal_electricity": "coal_electricity",  # TWh
    "gas_electricity": "gas_electricity",  # TWh
    "oil_electricity": "oil_electricity",  # TWh

    # Renewables
    "renewables_electricity": "renewables_electricity",  # TWh
    "hydro_electricity": "hydro_electricity",  # TWh
    "solar_electricity": "solar_electricity",  # TWh
    "wind_electricity": "wind_electricity",  # TWh
    "nuclear_electricity": "nuclear_electricity",  # TWh

    # Shares
    "renewables_share_elec": "renewables_share_elec",  # %
    "fossil_share_elec": "fossil_share_elec",  # %
    "low_carbon_share_elec": "low_carbon_share_elec",  # %

    # Carbon
    "carbon_intensity_elec": "carbon_intensity_elec",  # gCO2/kWh
}


def load_owid_energy(
    csv_path: Path,
    countries: Optional[List[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    columns: Optional[List[str]] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Load OWID energy data for specified countries and years.

    Args:
        csv_path: Path to owid-energy-data.csv
        countries: List of country names to filter by (None = all)
        start_year: Start year for filtering (None = no limit)
        end_year: End year for filtering (None = no limit)
        columns: List of columns to include (None = key columns only)
        verbose: Whether to print progress messages

    Returns:
        DataFrame with energy statistics by country and year
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"OWID energy file not found: {path}")

    if verbose:
        print(f"Loading OWID energy data from {path}...")

    df = pd.read_csv(path, low_memory=False)

    if verbose:
        print(f"Loaded {len(df)} rows, {len(df['country'].unique())} countries")

    # Filter by countries
    if countries:
        available = df["country"].dropna().unique().tolist()
        resolved = []
        for country in countries:
            match = resolve_country_name(country, available, threshold=0.8)
            if match:
                resolved.append(match)
            elif verbose:
                print(f"No match found for '{country}' in OWID data")

        if resolved:
            df = df[df["country"].isin(resolved)]
        else:
            df = pd.DataFrame(columns=df.columns)

    # Filter by years
    if start_year is not None:
        df = df[df["year"] >= start_year]
    if end_year is not None:
        df = df[df["year"] <= end_year]

    # Select columns
    if columns is None:
        # Use key columns that exist in the data
        columns = [c for c in OWID_COLUMNS.keys() if c in df.columns]
    else:
        columns = [c for c in columns if c in df.columns]

    # Always include core identifiers
    core = ["country", "year", "iso_code"]
    columns = core + [c for c in columns if c not in core]

    if verbose:
        print(f"{len(df)} rows after filtering")

    return df[columns].reset_index(drop=True)


def get_latest_values(
    csv_path: Path,
    countries: Optional[List[str]] = None,
    columns: Optional[List[str]] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Get the most recent values for each country.

    Args:
        csv_path: Path to owid-energy-data.csv
        countries: List of country names to filter by
        columns: List of columns to include
        verbose: Whether to print progress messages

    Returns:
        DataFrame with latest values per country
    """
    df = load_owid_energy(csv_path, countries, columns=columns, verbose=verbose)

    if df.empty:
        return df

    # Get latest year for each country
    latest = (
        df.sort_values("year", ascending=False)
        .groupby("country", as_index=False)
        .first()
    )

    return latest


def get_time_series(
    csv_path: Path,
    countries: List[str],
    variable: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Get time series for a specific variable and countries.

    Args:
        csv_path: Path to owid-energy-data.csv
        countries: List of country names
        variable: Column name to extract
        start_year: Start year
        end_year: End year
        verbose: Whether to print progress messages

    Returns:
        DataFrame with columns: year, {country1}, {country2}, ...
    """
    df = load_owid_energy(
        csv_path,
        countries,
        start_year=start_year,
        end_year=end_year,
        columns=[variable],
        verbose=verbose,
    )

    if df.empty or variable not in df.columns:
        return pd.DataFrame()

    # Pivot to wide format
    pivot = df.pivot(index="year", columns="country", values=variable)
    pivot = pivot.reset_index()

    return pivot


def summarize_by_country(
    csv_path: Path,
    countries: Optional[List[str]] = None,
    year: Optional[int] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Get summary statistics for countries.

    Args:
        csv_path: Path to owid-energy-data.csv
        countries: List of country names (None = all)
        year: Specific year (None = latest available)
        verbose: Whether to print progress messages

    Returns:
        Summary DataFrame with key metrics per country
    """
    if year is not None:
        df = load_owid_energy(csv_path, countries, start_year=year, end_year=year, verbose=verbose)
    else:
        df = get_latest_values(csv_path, countries, verbose=verbose)

    if df.empty:
        return df

    # Select key summary columns
    summary_cols = [
        "country", "year", "population", "gdp",
        "electricity_demand", "electricity_generation",
        "renewables_share_elec", "fossil_share_elec",
        "carbon_intensity_elec",
    ]
    summary_cols = [c for c in summary_cols if c in df.columns]

    return df[summary_cols].sort_values("electricity_demand", ascending=False, na_position="last")
