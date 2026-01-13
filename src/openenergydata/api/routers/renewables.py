"""Renewables (RE Profiles) API router."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from ...data import load_re_profiles
from ...data.sources.renewables import fetch_renewables_ninja, generate_mock_re_profiles

router = APIRouter()


class REProfileValue(BaseModel):
    """Single RE profile value."""
    zone: str
    month: int
    day: int
    hour: int
    capacity_factor: float


class REProfilesResponse(BaseModel):
    """RE profiles response."""
    zone: str
    technology: str
    year: int
    count: int
    mean_cf: float
    data: List[REProfileValue]


@router.get("", response_model=REProfilesResponse)
async def get_re_profiles(
    region: str = Query(..., description="Region ID"),
    technology: str = Query("solar", description="Technology: 'solar' or 'wind'"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    year: int = Query(2020, description="Year for profiles"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month"),
    limit: int = Query(1000, le=10000, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get renewable energy capacity factor profiles."""
    df = load_re_profiles(region, countries or [], year=year, tech=technology)

    # If no local data, use mock data for demo
    if df is None or df.empty:
        zone = countries[0] if countries else region
        df = generate_mock_re_profiles([zone], year=year, technology=technology)

    if df is None or df.empty:
        return REProfilesResponse(
            zone=countries[0] if countries else region,
            technology=technology,
            year=year,
            count=0,
            mean_cf=0,
            data=[],
        )

    # Apply filters
    if month is not None:
        df = df[df["month"] == month]

    zone = df["zone"].iloc[0] if "zone" in df.columns else region
    mean_cf = float(df["capacity_factor"].mean())

    # Apply pagination
    total_count = len(df)
    df = df.iloc[offset:offset + limit]

    data = [
        REProfileValue(
            zone=row.get("zone", zone),
            month=int(row["month"]),
            day=int(row["day"]),
            hour=int(row["hour"]),
            capacity_factor=float(row["capacity_factor"]),
        )
        for _, row in df.iterrows()
    ]

    return REProfilesResponse(
        zone=zone,
        technology=technology,
        year=year,
        count=total_count,
        mean_cf=mean_cf,
        data=data,
    )


@router.get("/fetch")
async def fetch_from_ninja(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    year: int = Query(2019, description="Year (2000-2023 available)"),
    technology: str = Query("solar", description="Technology: 'solar' or 'wind'"),
    api_key: str = Query(..., description="Renewables.ninja API key"),
):
    """Fetch fresh RE profiles from Renewables.ninja API.

    Requires a valid API key from https://renewables.ninja/
    """
    df = fetch_renewables_ninja(
        api_key=api_key,
        lat=lat,
        lon=lon,
        year=year,
        technology=technology,
        verbose=False,
    )

    if df is None or df.empty:
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch data from Renewables.ninja. Check your API key and parameters.",
        )

    return {
        "location": {"lat": lat, "lon": lon},
        "technology": technology,
        "year": year,
        "count": len(df),
        "mean_cf": float(df["capacity_factor"].mean()),
        "data": df.to_dict(orient="records"),
    }


@router.get("/daily")
async def get_daily_re_profile(
    region: str = Query(..., description="Region ID"),
    technology: str = Query("solar", description="Technology: 'solar' or 'wind'"),
    countries: Optional[List[str]] = Query(None, description="Filter by countries"),
    year: int = Query(2020, description="Year"),
    month: int = Query(1, ge=1, le=12, description="Month"),
    day: int = Query(1, ge=1, le=31, description="Day"),
):
    """Get a single day's RE capacity factor profile."""
    df = load_re_profiles(region, countries or [], year=year, tech=technology)

    if df is None or df.empty:
        zone = countries[0] if countries else region
        df = generate_mock_re_profiles([zone], year=year, technology=technology)

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No RE profile data found")

    df = df[(df["month"] == month) & (df["day"] == day)]

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {year}-{month:02d}-{day:02d}")

    df = df.sort_values("hour")

    return {
        "zone": df["zone"].iloc[0] if "zone" in df.columns else region,
        "technology": technology,
        "date": f"{year}-{month:02d}-{day:02d}",
        "hours": df["hour"].tolist(),
        "capacity_factors": df["capacity_factor"].tolist(),
    }
