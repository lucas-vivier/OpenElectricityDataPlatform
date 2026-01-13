"""Resource Potential API router.

Provides access to IRENA MSR (Model Solar/Wind Resource) data
showing optimal renewable energy sites for each country.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

from ...data import load_resource_potential, load_re_profiles_processed
from ...data.sources.irena import summarize_msr_by_country

router = APIRouter()


class ResourceSite(BaseModel):
    """Resource potential site."""
    country: str
    msr_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity_mw: Optional[float] = None
    capacity_factor: Optional[float] = None
    lcoe: Optional[float] = None
    technology: str


class ResourcePotentialResponse(BaseModel):
    """Resource potential response."""
    count: int
    total_capacity_mw: float
    avg_capacity_factor: Optional[float] = None
    sites: List[ResourceSite]


class CountryPotential(BaseModel):
    """Country resource potential summary."""
    country: str
    total_capacity_mw: float
    site_count: int
    avg_capacity_factor: Optional[float] = None
    avg_lcoe: Optional[float] = None


class PotentialSummaryResponse(BaseModel):
    """Summary response."""
    technology: str
    total_capacity_mw: float
    country_count: int
    by_country: List[CountryPotential]


@router.get("/solar", response_model=ResourcePotentialResponse)
async def get_solar_potential(
    region: str = Query(..., description="Region ID (e.g., 'southern_africa')"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    min_capacity_factor: Optional[float] = Query(None, description="Minimum capacity factor (0-1)"),
    max_lcoe: Optional[float] = Query(None, description="Maximum LCOE"),
    limit: int = Query(1000, description="Maximum sites to return"),
):
    """Get solar resource potential sites for a region."""
    df = load_resource_potential(region, countries, technology="solar")

    if df is None or df.empty:
        return ResourcePotentialResponse(count=0, total_capacity_mw=0, sites=[])

    # Apply filters
    if min_capacity_factor and "capacity_factor" in df.columns:
        df = df[df["capacity_factor"] >= min_capacity_factor]

    if max_lcoe and "lcoe" in df.columns:
        df = df[df["lcoe"] <= max_lcoe]

    # Limit results
    if len(df) > limit:
        df = df.head(limit)

    # Convert to response
    sites = [
        ResourceSite(
            country=row.get("country", ""),
            msr_id=str(row.get("msr_id", "")) if row.get("msr_id") else None,
            latitude=_safe_float(row.get("latitude")),
            longitude=_safe_float(row.get("longitude")),
            capacity_mw=_safe_float(row.get("capacity_mw")),
            capacity_factor=_safe_float(row.get("capacity_factor")),
            lcoe=_safe_float(row.get("lcoe")),
            technology="Solar PV",
        )
        for _, row in df.iterrows()
    ]

    avg_cf = df["capacity_factor"].mean() if "capacity_factor" in df.columns and len(df) > 0 else None

    return ResourcePotentialResponse(
        count=len(sites),
        total_capacity_mw=df["capacity_mw"].sum() if "capacity_mw" in df.columns else 0,
        avg_capacity_factor=_safe_float(avg_cf),
        sites=sites,
    )


@router.get("/wind", response_model=ResourcePotentialResponse)
async def get_wind_potential(
    region: str = Query(..., description="Region ID (e.g., 'southern_africa')"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    min_capacity_factor: Optional[float] = Query(None, description="Minimum capacity factor (0-1)"),
    max_lcoe: Optional[float] = Query(None, description="Maximum LCOE"),
    limit: int = Query(1000, description="Maximum sites to return"),
):
    """Get wind resource potential sites for a region."""
    df = load_resource_potential(region, countries, technology="wind")

    if df is None or df.empty:
        return ResourcePotentialResponse(count=0, total_capacity_mw=0, sites=[])

    # Apply filters
    cf_col = "capacity_factor_100m" if "capacity_factor_100m" in df.columns else "capacity_factor"

    if min_capacity_factor and cf_col in df.columns:
        df = df[df[cf_col] >= min_capacity_factor]

    if max_lcoe and "lcoe" in df.columns:
        df = df[df["lcoe"] <= max_lcoe]

    # Limit results
    if len(df) > limit:
        df = df.head(limit)

    # Convert to response
    sites = [
        ResourceSite(
            country=row.get("country", ""),
            msr_id=str(row.get("msr_id", "")) if row.get("msr_id") else None,
            latitude=_safe_float(row.get("latitude")),
            longitude=_safe_float(row.get("longitude")),
            capacity_mw=_safe_float(row.get("capacity_mw")),
            capacity_factor=_safe_float(row.get(cf_col)),
            lcoe=_safe_float(row.get("lcoe")),
            technology="Wind",
        )
        for _, row in df.iterrows()
    ]

    avg_cf = df[cf_col].mean() if cf_col in df.columns and len(df) > 0 else None

    return ResourcePotentialResponse(
        count=len(sites),
        total_capacity_mw=df["capacity_mw"].sum() if "capacity_mw" in df.columns else 0,
        avg_capacity_factor=_safe_float(avg_cf),
        sites=sites,
    )


@router.get("/solar/summary", response_model=PotentialSummaryResponse)
async def get_solar_potential_summary(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
):
    """Get summary of solar resource potential by country."""
    df = load_resource_potential(region, countries, technology="solar")

    if df is None or df.empty:
        return PotentialSummaryResponse(
            technology="Solar PV",
            total_capacity_mw=0,
            country_count=0,
            by_country=[],
        )

    summary_df = summarize_msr_by_country(df, technology="solar")

    by_country = [
        CountryPotential(
            country=row["country"],
            total_capacity_mw=row["total_capacity_mw"],
            site_count=row["site_count"],
            avg_capacity_factor=_safe_float(row.get("avg_capacity_factor")),
            avg_lcoe=_safe_float(row.get("avg_lcoe")),
        )
        for _, row in summary_df.iterrows()
    ]

    return PotentialSummaryResponse(
        technology="Solar PV",
        total_capacity_mw=df["capacity_mw"].sum() if "capacity_mw" in df.columns else 0,
        country_count=len(by_country),
        by_country=by_country,
    )


@router.get("/wind/summary", response_model=PotentialSummaryResponse)
async def get_wind_potential_summary(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
):
    """Get summary of wind resource potential by country."""
    df = load_resource_potential(region, countries, technology="wind")

    if df is None or df.empty:
        return PotentialSummaryResponse(
            technology="Wind",
            total_capacity_mw=0,
            country_count=0,
            by_country=[],
        )

    summary_df = summarize_msr_by_country(df, technology="wind")

    by_country = [
        CountryPotential(
            country=row["country"],
            total_capacity_mw=row["total_capacity_mw"],
            site_count=row["site_count"],
            avg_capacity_factor=_safe_float(row.get("avg_capacity_factor")),
            avg_lcoe=_safe_float(row.get("avg_lcoe")),
        )
        for _, row in summary_df.iterrows()
    ]

    return PotentialSummaryResponse(
        technology="Wind",
        total_capacity_mw=df["capacity_mw"].sum() if "capacity_mw" in df.columns else 0,
        country_count=len(by_country),
        by_country=by_country,
    )


@router.get("/solar/geojson")
async def get_solar_potential_geojson(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    limit: int = Query(500, description="Maximum sites to return"),
):
    """Get solar resource sites as GeoJSON FeatureCollection."""
    df = load_resource_potential(region, countries, technology="solar")

    if df is None or df.empty:
        return {"type": "FeatureCollection", "features": []}

    # Filter valid coordinates and limit
    df = df.dropna(subset=["latitude", "longitude"])
    if len(df) > limit:
        df = df.head(limit)

    features = []
    for _, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
            "properties": {
                "country": row.get("country", ""),
                "msr_id": str(row.get("msr_id", "")) if row.get("msr_id") else None,
                "capacity_mw": _safe_float(row.get("capacity_mw")) or 0,
                "capacity_factor": _safe_float(row.get("capacity_factor")),
                "lcoe": _safe_float(row.get("lcoe")),
                "technology": "Solar PV",
            },
        })

    return {"type": "FeatureCollection", "features": features}


@router.get("/wind/geojson")
async def get_wind_potential_geojson(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    limit: int = Query(500, description="Maximum sites to return"),
):
    """Get wind resource sites as GeoJSON FeatureCollection."""
    df = load_resource_potential(region, countries, technology="wind")

    if df is None or df.empty:
        return {"type": "FeatureCollection", "features": []}

    # Filter valid coordinates and limit
    df = df.dropna(subset=["latitude", "longitude"])
    if len(df) > limit:
        df = df.head(limit)

    cf_col = "capacity_factor_100m" if "capacity_factor_100m" in df.columns else "capacity_factor"

    features = []
    for _, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
            "properties": {
                "country": row.get("country", ""),
                "msr_id": str(row.get("msr_id", "")) if row.get("msr_id") else None,
                "capacity_mw": _safe_float(row.get("capacity_mw")) or 0,
                "capacity_factor": _safe_float(row.get(cf_col)),
                "lcoe": _safe_float(row.get("lcoe")),
                "technology": "Wind",
            },
        })

    return {"type": "FeatureCollection", "features": features}


@router.get("/profiles/{technology}")
async def get_re_profiles(
    technology: str,
    region: str = Query(..., description="Region ID"),
    zones: Optional[List[str]] = Query(None, description="Filter by zones"),
):
    """Get processed RE capacity factor profiles (representative days)."""
    if technology not in ["solar", "wind"]:
        return {"error": "Technology must be 'solar' or 'wind'"}

    df = load_re_profiles_processed(region, technology, zones)

    if df is None or df.empty:
        return {"technology": technology, "count": 0, "profiles": []}

    # Convert to list of dicts
    data = df.to_dict(orient="records")

    return {
        "technology": technology,
        "count": len(data),
        "profiles": data,
    }


def _safe_float(value) -> Optional[float]:
    """Convert value to float, handling NaN."""
    if value is None:
        return None
    try:
        f = float(value)
        return f if f == f else None  # NaN check
    except (ValueError, TypeError):
        return None
