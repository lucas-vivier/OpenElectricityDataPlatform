"""Power Plants API router."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from ...data import load_power_plants
from ...data.sources.power_plants import summarize_by_technology

router = APIRouter()


class PowerPlant(BaseModel):
    """Power plant data."""
    name: str
    technology: str
    capacity_mw: float
    status: str
    country: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PowerPlantsResponse(BaseModel):
    """Power plants response."""
    count: int
    total_capacity_mw: float
    plants: List[PowerPlant]


class TechnologySummary(BaseModel):
    """Technology capacity summary."""
    technology: str
    total_capacity_mw: float


class SummaryResponse(BaseModel):
    """Summary response."""
    count: int
    total_capacity_mw: float
    by_technology: List[TechnologySummary]


@router.get("", response_model=PowerPlantsResponse)
async def get_power_plants(
    region: str = Query(..., description="Region ID (e.g., 'south_africa')"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    technology: Optional[str] = Query(None, description="Filter by technology"),
    status: Optional[str] = Query(None, description="Filter by status (e.g., 'Operating')"),
    min_capacity: Optional[float] = Query(None, description="Minimum capacity in MW"),
    source: str = Query("gem", description="Data source: 'gem' (Global Energy Monitor) or 'gppd' (Global Power Plant Database)"),
):
    """Get power plants for a region."""
    # Load data
    df = load_power_plants(region, countries or [], source=source)

    if df is None or df.empty:
        return PowerPlantsResponse(count=0, total_capacity_mw=0, plants=[])

    # Apply filters
    if technology:
        df = df[df["technology"].str.lower() == technology.lower()]

    if status:
        df = df[df["status"].str.lower().str.contains(status.lower(), na=False)]

    if min_capacity:
        df = df[df["capacity_mw"] >= min_capacity]

    # Convert to response
    plants = [
        PowerPlant(
            name=row.get("name", ""),
            technology=row.get("technology", ""),
            capacity_mw=row.get("capacity_mw", 0),
            status=row.get("status", ""),
            country=row.get("country", ""),
            latitude=row.get("latitude") if row.get("latitude") and row.get("latitude") == row.get("latitude") else None,
            longitude=row.get("longitude") if row.get("longitude") and row.get("longitude") == row.get("longitude") else None,
        )
        for _, row in df.iterrows()
    ]

    return PowerPlantsResponse(
        count=len(plants),
        total_capacity_mw=df["capacity_mw"].sum(),
        plants=plants,
    )


@router.get("/summary", response_model=SummaryResponse)
async def get_power_plants_summary(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    status: Optional[str] = Query("Operating", description="Filter by status"),
    source: str = Query("gem", description="Data source: 'gem' or 'gppd'"),
):
    """Get summary statistics for power plants."""
    df = load_power_plants(region, countries or [], source=source)

    if df is None or df.empty:
        return SummaryResponse(count=0, total_capacity_mw=0, by_technology=[])

    # Get summary by technology
    summary_df = summarize_by_technology(df, status=status or "all")

    by_tech = [
        TechnologySummary(
            technology=row["technology"],
            total_capacity_mw=row["total_capacity_mw"],
        )
        for _, row in summary_df.iterrows()
    ]

    return SummaryResponse(
        count=len(df),
        total_capacity_mw=df["capacity_mw"].sum(),
        by_technology=by_tech,
    )


@router.get("/geojson")
async def get_power_plants_geojson(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    technology: Optional[str] = Query(None, description="Filter by technology"),
    source: str = Query("gem", description="Data source: 'gem' or 'gppd'"),
):
    """Get power plants as GeoJSON FeatureCollection."""
    df = load_power_plants(region, countries or [], source=source)

    if df is None or df.empty:
        return {"type": "FeatureCollection", "features": []}

    if technology:
        df = df[df["technology"].str.lower() == technology.lower()]

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
                "technology": row.get("technology", ""),
                "capacity_mw": float(row.get("capacity_mw", 0)),
                "status": row.get("status", ""),
                "country": row.get("country", ""),
            },
        })

    return {"type": "FeatureCollection", "features": features}
