"""Hydropower API router."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

from ...data import load_hydropower, load_hydro_scenarios
from ...data.sources.hydropower import summarize_hydro_by_country

router = APIRouter()


class HydropowerPlant(BaseModel):
    """Hydropower plant data."""
    name: str
    technology: str
    capacity_mw: Optional[float] = None
    status: str
    country: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    river_name: Optional[str] = None
    river_basin: Optional[str] = None
    reservoir_size_mcm: Optional[float] = None
    start_year: Optional[int] = None


class HydropowerResponse(BaseModel):
    """Hydropower plants response."""
    count: int
    total_capacity_mw: float
    plants: List[HydropowerPlant]


class CountrySummary(BaseModel):
    """Country capacity summary."""
    country: str
    total_capacity_mw: float
    plant_count: int


class HydroSummaryResponse(BaseModel):
    """Summary response."""
    count: int
    total_capacity_mw: float
    by_country: List[CountrySummary]


@router.get("", response_model=HydropowerResponse)
async def get_hydropower(
    region: str = Query(..., description="Region ID (e.g., 'southern_africa')"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    source: str = Query("both", description="Data source: 'african_atlas', 'gem' (filtered from Global Integrated Power), or 'both'"),
    status: Optional[str] = Query(None, description="Filter by status (e.g., 'Operating')"),
    min_capacity: Optional[float] = Query(None, description="Minimum capacity in MW"),
):
    """Get hydropower plants for a region."""
    df = load_hydropower(region, countries, source=source)

    if df is None or df.empty:
        return HydropowerResponse(count=0, total_capacity_mw=0, plants=[])

    # Apply filters
    if status:
        df = df[df["status"].str.lower().str.contains(status.lower(), na=False)]

    if min_capacity and "capacity_mw" in df.columns:
        df = df[df["capacity_mw"] >= min_capacity]

    # Convert to response
    plants = []
    for _, row in df.iterrows():
        plants.append(
            HydropowerPlant(
                name=row.get("name", ""),
                technology=row.get("technology", "Hydro"),
                capacity_mw=_safe_float(row.get("capacity_mw")),
                status=row.get("status", ""),
                country=row.get("country", ""),
                latitude=_safe_float(row.get("latitude")),
                longitude=_safe_float(row.get("longitude")),
                river_name=row.get("river_name") if row.get("river_name") == row.get("river_name") else None,
                river_basin=row.get("river_basin") if row.get("river_basin") == row.get("river_basin") else None,
                reservoir_size_mcm=_safe_float(row.get("reservoir_size_mcm")),
                start_year=_safe_int(row.get("start_year")),
            )
        )

    total_cap = df["capacity_mw"].sum() if "capacity_mw" in df.columns else 0

    return HydropowerResponse(
        count=len(plants),
        total_capacity_mw=total_cap,
        plants=plants,
    )


@router.get("/summary", response_model=HydroSummaryResponse)
async def get_hydropower_summary(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    source: str = Query("both", description="Data source: 'african_atlas', 'gem', or 'both'"),
):
    """Get summary statistics for hydropower by country."""
    df = load_hydropower(region, countries, source=source)

    if df is None or df.empty:
        return HydroSummaryResponse(count=0, total_capacity_mw=0, by_country=[])

    summary_df = summarize_hydro_by_country(df)

    by_country = [
        CountrySummary(
            country=row["country"],
            total_capacity_mw=row["total_capacity_mw"],
            plant_count=row["plant_count"],
        )
        for _, row in summary_df.iterrows()
    ]

    return HydroSummaryResponse(
        count=len(df),
        total_capacity_mw=df["capacity_mw"].sum() if "capacity_mw" in df.columns else 0,
        by_country=by_country,
    )


@router.get("/climate-scenarios")
async def get_hydro_climate_scenarios(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    scenario: str = Query("SSP1-RCP26", description="Climate scenario: SSP1-RCP26, SSP4-RCP60, SSP5-RCP85"),
):
    """Get hydropower projections under climate scenarios."""
    df = load_hydro_scenarios(region, countries, scenario=scenario)

    if df is None or df.empty:
        return {"scenario": scenario, "count": 0, "data": []}

    # Convert to list of dicts for JSON response
    data = df.to_dict(orient="records")

    return {
        "scenario": scenario,
        "count": len(data),
        "data": data,
    }


@router.get("/geojson")
async def get_hydropower_geojson(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    source: str = Query("both", description="Data source: 'african_atlas', 'gem', or 'both'"),
):
    """Get hydropower plants as GeoJSON FeatureCollection."""
    df = load_hydropower(region, countries, source=source)

    if df is None or df.empty:
        return {"type": "FeatureCollection", "features": []}

    # Filter valid coordinates
    df = df.dropna(subset=["latitude", "longitude"])

    features = []
    for _, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
            "properties": {
                "name": row.get("name", ""),
                "technology": row.get("technology", "Hydro"),
                "capacity_mw": _safe_float(row.get("capacity_mw")) or 0,
                "status": row.get("status", ""),
                "country": row.get("country", ""),
                "river_name": row.get("river_name") if row.get("river_name") == row.get("river_name") else None,
            },
        })

    return {"type": "FeatureCollection", "features": features}


def _safe_float(value) -> Optional[float]:
    """Convert value to float, handling NaN."""
    if value is None:
        return None
    try:
        f = float(value)
        return f if f == f else None  # NaN check
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> Optional[int]:
    """Convert value to int, handling NaN."""
    if value is None:
        return None
    try:
        f = float(value)
        if f != f:  # NaN check
            return None
        return int(f)
    except (ValueError, TypeError):
        return None
