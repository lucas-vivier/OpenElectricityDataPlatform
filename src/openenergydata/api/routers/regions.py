"""Regions API router."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from ...config import get_regions, get_countries_for_region, get_region_bbox, get_country_centroid

router = APIRouter()


class RegionInfo(BaseModel):
    """Region information."""
    id: str
    name: str
    countries: List[str]
    bbox: Optional[List[float]] = None
    default_zoom: Optional[int] = None


class RegionListResponse(BaseModel):
    """List of regions."""
    regions: List[RegionInfo]


class CountryCentroidResponse(BaseModel):
    """Country centroid coordinates."""
    lat: float
    lon: float


@router.get("", response_model=RegionListResponse)
async def list_regions():
    """Get all available regions."""
    regions_data = get_regions()
    regions_list = [
        RegionInfo(
            id=region_id,
            name=info["name"],
            countries=info.get("countries", []),
            bbox=info.get("bbox"),
            default_zoom=info.get("default_zoom"),
        )
        for region_id, info in regions_data.items()
        if region_id != "country_centroids"
    ]
    return RegionListResponse(regions=regions_list)


@router.get("/country-centroid", response_model=CountryCentroidResponse)
async def get_centroid(country: str = Query(..., description="Country name")):
    """Get the centroid coordinates for a country."""
    centroid = get_country_centroid(country)

    if not centroid:
        raise HTTPException(status_code=404, detail=f"Centroid not found for country '{country}'")

    return CountryCentroidResponse(lat=centroid["lat"], lon=centroid["lon"])


@router.get("/{region_id}", response_model=RegionInfo)
async def get_region(region_id: str):
    """Get a specific region by ID."""
    regions_data = get_regions()

    if region_id not in regions_data or region_id == "country_centroids":
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found")

    info = regions_data[region_id]
    return RegionInfo(
        id=region_id,
        name=info["name"],
        countries=info.get("countries", []),
        bbox=info.get("bbox"),
        default_zoom=info.get("default_zoom"),
    )


@router.get("/{region_id}/countries", response_model=List[str])
async def get_region_countries(region_id: str):
    """Get countries for a specific region."""
    countries = get_countries_for_region(region_id)

    if not countries:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found")

    return countries
