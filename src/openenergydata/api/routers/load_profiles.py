"""Load Profiles API router."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from ...data import load_load_profiles

router = APIRouter()


class HourlyValue(BaseModel):
    """Single hourly value."""
    zone: str
    month: int
    day: int
    hour: int
    value: float


class LoadProfilesResponse(BaseModel):
    """Load profiles response."""
    zone: str
    year: int
    count: int
    data: List[HourlyValue]


class LoadProfilesSummary(BaseModel):
    """Summary statistics for load profiles."""
    zone: str
    year: int
    count: int
    min_value: float
    max_value: float
    mean_value: float


@router.get("", response_model=LoadProfilesResponse)
async def get_load_profiles(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    year: int = Query(2020, description="Year for profiles"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month"),
    day: Optional[int] = Query(None, ge=1, le=31, description="Filter by day"),
    limit: int = Query(1000, le=10000, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get hourly load profiles for a region."""
    df = load_load_profiles(region, countries or [], year=year)

    if df is None or df.empty:
        return LoadProfilesResponse(
            zone=countries[0] if countries else region,
            year=year,
            count=0,
            data=[],
        )

    # Apply filters
    if month is not None:
        df = df[df["month"] == month]

    if day is not None:
        df = df[df["day"] == day]

    # Get zone name
    zone = df["zone"].iloc[0] if "zone" in df.columns else region

    # Apply pagination
    total_count = len(df)
    df = df.iloc[offset:offset + limit]

    # Convert to response
    data = [
        HourlyValue(
            zone=row.get("zone", zone),
            month=int(row["month"]),
            day=int(row["day"]),
            hour=int(row["hour"]),
            value=float(row["value"]),
        )
        for _, row in df.iterrows()
    ]

    return LoadProfilesResponse(
        zone=zone,
        year=year,
        count=total_count,
        data=data,
    )


@router.get("/summary", response_model=LoadProfilesSummary)
async def get_load_profiles_summary(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    year: int = Query(2020, description="Year for profiles"),
):
    """Get summary statistics for load profiles."""
    df = load_load_profiles(region, countries or [], year=year)

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No load profile data found")

    zone = df["zone"].iloc[0] if "zone" in df.columns else region

    return LoadProfilesSummary(
        zone=zone,
        year=year,
        count=len(df),
        min_value=float(df["value"].min()),
        max_value=float(df["value"].max()),
        mean_value=float(df["value"].mean()),
    )


@router.get("/daily")
async def get_daily_profile(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    year: int = Query(2020, description="Year"),
    month: int = Query(1, ge=1, le=12, description="Month"),
    day: int = Query(1, ge=1, le=31, description="Day"),
):
    """Get a single day's hourly profile."""
    df = load_load_profiles(region, countries or [], year=year)

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No load profile data found")

    df = df[(df["month"] == month) & (df["day"] == day)]

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {year}-{month:02d}-{day:02d}")

    df = df.sort_values("hour")

    return {
        "zone": df["zone"].iloc[0] if "zone" in df.columns else region,
        "date": f"{year}-{month:02d}-{day:02d}",
        "hours": df["hour"].tolist(),
        "values": df["value"].tolist(),
    }


@router.get("/monthly-average")
async def get_monthly_average(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by specific countries"),
    year: int = Query(2020, description="Year"),
):
    """Get average daily profile for each month, grouped by country/zone."""
    df = load_load_profiles(region, countries or [], year=year)

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No load profile data found")

    # Get unique zones/countries
    zones = df["zone"].unique().tolist() if "zone" in df.columns else [region]

    # Build per-country monthly profiles
    profiles_by_country = {}
    for zone in zones:
        zone_df = df[df["zone"] == zone] if "zone" in df.columns else df

        # Group by month and hour, calculate mean for this zone
        monthly = zone_df.groupby(["month", "hour"])["value"].mean().reset_index()

        zone_monthly = {}
        for month in range(1, 13):
            month_data = monthly[monthly["month"] == month].sort_values("hour")
            if not month_data.empty:
                zone_monthly[month] = {
                    "hours": month_data["hour"].tolist(),
                    "values": month_data["value"].tolist(),
                }

        if zone_monthly:
            profiles_by_country[zone] = zone_monthly

    # Also compute aggregate monthly profiles (backward compatibility)
    monthly_all = df.groupby(["month", "hour"])["value"].mean().reset_index()
    aggregate_monthly = {}
    for month in range(1, 13):
        month_data = monthly_all[monthly_all["month"] == month].sort_values("hour")
        if not month_data.empty:
            aggregate_monthly[month] = {
                "hours": month_data["hour"].tolist(),
                "values": month_data["value"].tolist(),
            }

    return {
        "zone": zones[0] if len(zones) == 1 else region,
        "year": year,
        "monthly_profiles": aggregate_monthly,  # Backward compatible
        "profiles_by_country": profiles_by_country,  # New per-country data
        "countries": zones,
    }
