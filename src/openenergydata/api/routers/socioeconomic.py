"""Socio-Economic Data API router.

Provides access to OWID energy dataset with GDP, population,
electricity demand, and energy statistics by country.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ...config.data_paths import get_data_source_path
from ...data.sources.owid import (
    load_owid_energy,
    get_latest_values,
    get_time_series,
    summarize_by_country,
)

router = APIRouter()


class CountryStats(BaseModel):
    """Country statistics."""
    country: str
    year: int
    population: Optional[float] = None
    gdp: Optional[float] = None
    electricity_demand: Optional[float] = None
    electricity_generation: Optional[float] = None
    renewables_share_elec: Optional[float] = None
    fossil_share_elec: Optional[float] = None
    carbon_intensity_elec: Optional[float] = None


class SocioEconomicResponse(BaseModel):
    """Socio-economic data response."""
    count: int
    data: List[CountryStats]


class TimeSeriesPoint(BaseModel):
    """Time series data point."""
    year: int
    values: Dict[str, Optional[float]]


class TimeSeriesResponse(BaseModel):
    """Time series response."""
    variable: str
    countries: List[str]
    data: List[TimeSeriesPoint]


@router.get("/summary", response_model=SocioEconomicResponse)
async def get_summary(
    countries: Optional[List[str]] = Query(None, description="Filter by countries"),
    year: Optional[int] = Query(None, description="Specific year (default: latest)"),
):
    """Get summary statistics for countries."""
    owid_path = get_data_source_path("owid_energy")

    if not owid_path or not owid_path.exists():
        return SocioEconomicResponse(count=0, data=[])

    df = summarize_by_country(owid_path, countries, year)

    if df.empty:
        return SocioEconomicResponse(count=0, data=[])

    data = [
        CountryStats(
            country=row.get("country", ""),
            year=int(row.get("year", 0)),
            population=_safe_float(row.get("population")),
            gdp=_safe_float(row.get("gdp")),
            electricity_demand=_safe_float(row.get("electricity_demand")),
            electricity_generation=_safe_float(row.get("electricity_generation")),
            renewables_share_elec=_safe_float(row.get("renewables_share_elec")),
            fossil_share_elec=_safe_float(row.get("fossil_share_elec")),
            carbon_intensity_elec=_safe_float(row.get("carbon_intensity_elec")),
        )
        for _, row in df.iterrows()
    ]

    return SocioEconomicResponse(count=len(data), data=data)


@router.get("/countries")
async def list_countries():
    """List all available countries in OWID dataset."""
    owid_path = get_data_source_path("owid_energy")

    if not owid_path or not owid_path.exists():
        return {"count": 0, "countries": []}

    df = load_owid_energy(owid_path)
    countries = sorted(df["country"].dropna().unique().tolist())

    return {"count": len(countries), "countries": countries}


@router.get("/timeseries/{variable}")
async def get_timeseries(
    variable: str,
    countries: List[str] = Query(..., description="Countries to include"),
    start_year: Optional[int] = Query(None, description="Start year"),
    end_year: Optional[int] = Query(None, description="End year"),
):
    """Get time series for a variable across countries.

    Available variables:
    - population, gdp
    - electricity_demand, electricity_generation
    - renewables_electricity, fossil_electricity
    - renewables_share_elec, fossil_share_elec
    - carbon_intensity_elec
    """
    owid_path = get_data_source_path("owid_energy")

    if not owid_path or not owid_path.exists():
        return TimeSeriesResponse(variable=variable, countries=[], data=[])

    df = get_time_series(
        owid_path,
        countries=countries,
        variable=variable,
        start_year=start_year,
        end_year=end_year,
    )

    if df.empty:
        return TimeSeriesResponse(variable=variable, countries=countries, data=[])

    # Convert to response format
    country_cols = [c for c in df.columns if c != "year"]
    data = []
    for _, row in df.iterrows():
        values = {c: _safe_float(row.get(c)) for c in country_cols}
        data.append(TimeSeriesPoint(year=int(row["year"]), values=values))

    return TimeSeriesResponse(
        variable=variable,
        countries=country_cols,
        data=data,
    )


@router.get("/electricity")
async def get_electricity_stats(
    countries: Optional[List[str]] = Query(None, description="Filter by countries"),
    start_year: int = Query(2000, description="Start year"),
    end_year: Optional[int] = Query(None, description="End year"),
):
    """Get electricity statistics by country and year."""
    owid_path = get_data_source_path("owid_energy")

    if not owid_path or not owid_path.exists():
        return {"count": 0, "data": []}

    columns = [
        "electricity_demand", "electricity_generation",
        "renewables_electricity", "fossil_electricity",
        "hydro_electricity", "solar_electricity", "wind_electricity",
        "nuclear_electricity", "coal_electricity", "gas_electricity",
    ]

    df = load_owid_energy(
        owid_path,
        countries=countries,
        start_year=start_year,
        end_year=end_year,
        columns=columns,
    )

    if df.empty:
        return {"count": 0, "data": []}

    data = df.to_dict(orient="records")
    return {"count": len(data), "data": data}


@router.get("/renewables-share")
async def get_renewables_share(
    countries: Optional[List[str]] = Query(None, description="Filter by countries"),
    year: Optional[int] = Query(None, description="Specific year (default: latest)"),
):
    """Get renewable energy share in electricity by country."""
    owid_path = get_data_source_path("owid_energy")

    if not owid_path or not owid_path.exists():
        return {"count": 0, "data": []}

    columns = [
        "renewables_share_elec", "fossil_share_elec",
        "hydro_share_elec", "solar_share_elec", "wind_share_elec",
        "nuclear_share_elec", "low_carbon_share_elec",
    ]

    if year:
        df = load_owid_energy(owid_path, countries, start_year=year, end_year=year, columns=columns)
    else:
        df = get_latest_values(owid_path, countries, columns=columns)

    if df.empty:
        return {"count": 0, "data": []}

    data = df.to_dict(orient="records")
    return {"count": len(data), "data": data}


def _safe_float(value) -> Optional[float]:
    """Convert value to float, handling NaN."""
    if value is None:
        return None
    try:
        f = float(value)
        return f if f == f else None  # NaN check
    except (ValueError, TypeError):
        return None
