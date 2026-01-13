"""Treatments API router - data processing operations."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from ...data import load_load_profiles, load_re_profiles
from ...treatments import compute_representative_days, month_to_season

router = APIRouter()


class RepDayWeight(BaseModel):
    """Representative day weight."""
    rep_day: int
    original_month: int
    original_day: int
    weight: float


class RepDayProfile(BaseModel):
    """Representative day profile."""
    rep_day: int
    hour: int
    value: float
    weight: float


class RepresentativeDaysResponse(BaseModel):
    """Representative days computation result."""
    n_days: int
    total_weight: float
    weights: List[RepDayWeight]
    load_profiles: List[RepDayProfile]
    re_profiles: Optional[List[RepDayProfile]] = None


class SeasonalProfile(BaseModel):
    """Profile converted to seasonal format."""
    zone: str
    season: str
    day: int
    hour: int
    value: float


class SeasonalConversionResponse(BaseModel):
    """Seasonal conversion result."""
    zone: str
    n_seasons: int
    count: int
    data: List[SeasonalProfile]


@router.post("/representative-days", response_model=RepresentativeDaysResponse)
async def compute_rep_days(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Countries to include"),
    year: int = Query(2020, description="Year for profiles"),
    n_days: int = Query(12, ge=4, le=52, description="Number of representative days"),
    n_clusters: int = Query(20, ge=4, le=100, description="Number of clusters for K-means"),
    include_re: bool = Query(False, description="Include RE profiles in clustering"),
    re_technology: str = Query("solar", description="RE technology if include_re=True"),
):
    """Compute representative days using K-means clustering.

    This reduces a full year of hourly data to a smaller set of
    representative days with associated weights.
    """
    # Load data
    load_df = load_load_profiles(region, countries or [], year=year)

    if load_df is None or load_df.empty:
        raise HTTPException(status_code=404, detail="No load profile data found")

    re_df = None
    if include_re:
        re_df = load_re_profiles(region, countries or [], year=year, tech=re_technology)
        if re_df is not None and "capacity_factor" in re_df.columns:
            re_df = re_df.rename(columns={"capacity_factor": "value"})

    # Compute representative days
    try:
        rep_load, rep_re, weights_df = compute_representative_days(
            load_profiles=load_df,
            re_profiles=re_df,
            n_days=n_days,
            n_clusters=n_clusters,
            verbose=False,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")

    # Build response
    weights = [
        RepDayWeight(
            rep_day=int(row["rep_day"]),
            original_month=int(row["original_month"]),
            original_day=int(row["original_day"]),
            weight=float(row["weight"]),
        )
        for _, row in weights_df.iterrows()
    ]

    load_profiles = [
        RepDayProfile(
            rep_day=int(row["rep_day"]),
            hour=int(row["hour"]),
            value=float(row["value"]),
            weight=float(row["weight"]),
        )
        for _, row in rep_load.iterrows()
    ]

    re_profiles = None
    if rep_re is not None and not rep_re.empty:
        re_profiles = [
            RepDayProfile(
                rep_day=int(row["rep_day"]),
                hour=int(row["hour"]),
                value=float(row["value"]),
                weight=float(row["weight"]),
            )
            for _, row in rep_re.iterrows()
        ]

    return RepresentativeDaysResponse(
        n_days=len(weights),
        total_weight=float(weights_df["weight"].sum()),
        weights=weights,
        load_profiles=load_profiles,
        re_profiles=re_profiles,
    )


@router.post("/seasonal-conversion", response_model=SeasonalConversionResponse)
async def convert_to_seasonal(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Countries to include"),
    year: int = Query(2020, description="Year for profiles"),
    data_type: str = Query("load", description="Data type: 'load' or 'solar' or 'wind'"),
):
    """Convert monthly data to seasonal format (DJF, MAM, JJA, SON).

    This groups months into meteorological seasons and renumbers days
    sequentially within each season.
    """
    # Load data
    if data_type == "load":
        df = load_load_profiles(region, countries or [], year=year)
    else:
        df = load_re_profiles(region, countries or [], year=year, tech=data_type)
        if df is not None and "capacity_factor" in df.columns:
            df = df.rename(columns={"capacity_factor": "value"})

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No {data_type} data found")

    # Convert to seasonal
    try:
        seasonal_df = month_to_season(df, other_columns=["zone"] if "zone" in df.columns else [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

    zone = df["zone"].iloc[0] if "zone" in df.columns else region
    seasons = seasonal_df["season"].unique().tolist()

    data = [
        SeasonalProfile(
            zone=row.get("zone", zone),
            season=row["season"],
            day=int(row["day"]),
            hour=int(row["hour"]),
            value=float(row["value"]),
        )
        for _, row in seasonal_df.head(1000).iterrows()  # Limit response size
    ]

    return SeasonalConversionResponse(
        zone=zone,
        n_seasons=len(seasons),
        count=len(seasonal_df),
        data=data,
    )


@router.get("/methods")
async def list_treatment_methods():
    """List available treatment methods and their parameters."""
    return {
        "representative_days": {
            "description": "Reduce time series to representative days using K-means clustering",
            "endpoint": "POST /api/treatments/representative-days",
            "parameters": {
                "n_days": "Number of representative days (default: 12)",
                "n_clusters": "Number of clusters for K-means (default: 20)",
                "include_re": "Include RE profiles in clustering (default: False)",
            },
        },
        "seasonal_conversion": {
            "description": "Convert monthly data to seasonal format (DJF, MAM, JJA, SON)",
            "endpoint": "POST /api/treatments/seasonal-conversion",
            "parameters": {
                "data_type": "Type of data to convert: 'load', 'solar', or 'wind'",
            },
        },
    }
