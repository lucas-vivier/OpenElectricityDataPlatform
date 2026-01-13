"""Exports API router - download data in various formats."""

import io
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional

from ...data import load_power_plants, load_load_profiles, load_re_profiles
from ...export.geojson_export import export_plants_geojson_string

router = APIRouter()


@router.get("/power-plants/csv")
async def export_power_plants_csv(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by countries"),
    technology: Optional[str] = Query(None, description="Filter by technology"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Export power plants as CSV file."""
    df = load_power_plants(region, countries or [])

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No power plant data found")

    if technology:
        df = df[df["technology"].str.lower() == technology.lower()]

    if status:
        df = df[df["status"].str.lower().str.contains(status.lower(), na=False)]

    # Select columns for export
    export_cols = ["name", "technology", "capacity_mw", "status", "country", "latitude", "longitude"]
    export_cols = [c for c in export_cols if c in df.columns]

    # Create CSV in memory
    buffer = io.StringIO()
    df[export_cols].to_csv(buffer, index=False)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=power_plants_{region}.csv"},
    )


@router.get("/power-plants/geojson")
async def export_power_plants_geojson(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by countries"),
    technology: Optional[str] = Query(None, description="Filter by technology"),
):
    """Export power plants as GeoJSON file."""
    df = load_power_plants(region, countries or [])

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No power plant data found")

    if technology:
        df = df[df["technology"].str.lower() == technology.lower()]

    geojson_str = export_plants_geojson_string(df)

    return StreamingResponse(
        iter([geojson_str]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=power_plants_{region}.geojson"},
    )


@router.get("/load-profiles/csv")
async def export_load_profiles_csv(
    region: str = Query(..., description="Region ID"),
    countries: Optional[List[str]] = Query(None, description="Filter by countries"),
    year: int = Query(2020, description="Year"),
    format_type: str = Query("standard", description="Format: 'standard' or 'epm'"),
):
    """Export load profiles as CSV file.

    Formats:
    - standard: zone, month, day, hour, value
    - epm: zone, season, day, hour, value (requires seasonal conversion)
    """
    df = load_load_profiles(region, countries or [], year=year)

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No load profile data found")

    if format_type == "epm":
        from ...treatments import month_to_season
        df = month_to_season(df, other_columns=["zone"] if "zone" in df.columns else [])
        export_cols = ["zone", "season", "day", "hour", "value"]
    else:
        export_cols = ["zone", "month", "day", "hour", "value"]

    export_cols = [c for c in export_cols if c in df.columns]

    buffer = io.StringIO()
    df[export_cols].to_csv(buffer, index=False)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=load_profiles_{region}_{year}.csv"},
    )


@router.get("/re-profiles/csv")
async def export_re_profiles_csv(
    region: str = Query(..., description="Region ID"),
    technology: str = Query("solar", description="Technology: 'solar' or 'wind'"),
    countries: Optional[List[str]] = Query(None, description="Filter by countries"),
    year: int = Query(2020, description="Year"),
    format_type: str = Query("standard", description="Format: 'standard' or 'epm'"),
):
    """Export RE capacity factor profiles as CSV file."""
    df = load_re_profiles(region, countries or [], year=year, tech=technology)

    if df is None or df.empty:
        # Use mock data if no real data
        from ...data.sources.renewables import generate_mock_re_profiles
        zone = countries[0] if countries else region
        df = generate_mock_re_profiles([zone], year=year, technology=technology)

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No RE profile data found")

    # Rename capacity_factor to value for consistency
    if "capacity_factor" in df.columns:
        df = df.rename(columns={"capacity_factor": "value"})

    if format_type == "epm":
        from ...treatments import month_to_season
        df = month_to_season(df, other_columns=["zone"] if "zone" in df.columns else [])
        export_cols = ["zone", "season", "day", "hour", "value"]
    else:
        export_cols = ["zone", "month", "day", "hour", "value"]

    export_cols = [c for c in export_cols if c in df.columns]

    buffer = io.StringIO()
    df[export_cols].to_csv(buffer, index=False)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={technology}_profiles_{region}_{year}.csv"},
    )


@router.get("/formats")
async def list_export_formats():
    """List available export formats."""
    return {
        "formats": {
            "csv": {
                "description": "Comma-separated values",
                "use_case": "General purpose, Excel compatible",
            },
            "geojson": {
                "description": "GeoJSON FeatureCollection",
                "use_case": "GIS applications, web mapping",
            },
        },
        "data_types": {
            "power_plants": ["csv", "geojson"],
            "load_profiles": ["csv"],
            "re_profiles": ["csv"],
        },
        "csv_formats": {
            "standard": "zone, month, day, hour, value",
            "epm": "zone, season, day, hour, value (for capacity expansion models)",
        },
    }
