"""Data Quality API router."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path

from ...data.quality import (
    assess_country_quality,
    assess_region_quality,
    get_quality_summary,
    QualityLevel,
)
from ...config.regions import get_countries_for_region, get_regions
from ...config.data_paths import get_data_source_path, data_source_exists

router = APIRouter()


class DatasetQualityResponse(BaseModel):
    """Quality assessment for a single dataset."""
    dataset: str
    available: bool
    record_count: int
    completeness: float
    quality_level: str
    issues: List[str]
    metrics: Dict[str, Any]


class CountryQualityResponse(BaseModel):
    """Quality assessment for a country."""
    country: str
    iso_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    overall_score: float
    quality_level: str
    datasets: Dict[str, DatasetQualityResponse]
    summary: str


class RegionQualitySummary(BaseModel):
    """Summary of quality for a region."""
    total_countries: int
    by_quality_level: Dict[str, int]
    average_score: float
    datasets_coverage: Dict[str, Dict[str, Any]]


class RegionQualityResponse(BaseModel):
    """Quality assessment for a region."""
    region: str
    summary: RegionQualitySummary
    countries: List[CountryQualityResponse]


class QualityGeoJSONProperties(BaseModel):
    """Properties for GeoJSON feature."""
    country: str
    overall_score: float
    quality_level: str
    summary: str
    power_plants_available: bool
    load_profiles_available: bool
    hydropower_available: bool
    resource_potential_available: bool


@router.get("/country", response_model=CountryQualityResponse)
async def get_country_quality(
    region: str = Query(..., description="Region ID (e.g., 'south_africa')"),
    country: str = Query(..., description="Country name"),
):
    """Get data quality assessment for a specific country."""
    result = assess_country_quality(country, region)

    datasets = {}
    for name, ds in result.datasets.items():
        datasets[name] = DatasetQualityResponse(
            dataset=ds.dataset,
            available=ds.available,
            record_count=ds.record_count,
            completeness=ds.completeness,
            quality_level=ds.quality_level.value,
            issues=ds.issues,
            metrics=ds.metrics,
        )

    return CountryQualityResponse(
        country=result.country,
        iso_code=result.iso_code,
        latitude=result.latitude,
        longitude=result.longitude,
        overall_score=result.overall_score,
        quality_level=result.quality_level.value,
        datasets=datasets,
        summary=result.summary,
    )


@router.get("/region", response_model=RegionQualityResponse)
async def get_region_quality(
    region: str = Query(..., description="Region ID (e.g., 'southern_africa')"),
):
    """Get data quality assessment for all countries in a region."""
    results = assess_region_quality(region)
    summary = get_quality_summary(results)

    countries = []
    for country_name, result in results.items():
        datasets = {}
        for name, ds in result.datasets.items():
            datasets[name] = DatasetQualityResponse(
                dataset=ds.dataset,
                available=ds.available,
                record_count=ds.record_count,
                completeness=ds.completeness,
                quality_level=ds.quality_level.value,
                issues=ds.issues,
                metrics=ds.metrics,
            )

        countries.append(CountryQualityResponse(
            country=result.country,
            iso_code=result.iso_code,
            latitude=result.latitude,
            longitude=result.longitude,
            overall_score=result.overall_score,
            quality_level=result.quality_level.value,
            datasets=datasets,
            summary=result.summary,
        ))

    return RegionQualityResponse(
        region=region,
        summary=RegionQualitySummary(
            total_countries=summary["total_countries"],
            by_quality_level=summary["by_quality_level"],
            average_score=summary["average_score"],
            datasets_coverage=summary["datasets_coverage"],
        ),
        countries=countries,
    )


@router.get("/region/geojson")
async def get_region_quality_geojson(
    region: str = Query(..., description="Region ID"),
):
    """Get data quality assessment as GeoJSON for map visualization."""
    results = assess_region_quality(region)

    features = []
    for country_name, result in results.items():
        # Skip countries without coordinates
        if result.latitude is None or result.longitude is None:
            continue

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [result.longitude, result.latitude],
            },
            "properties": {
                "country": result.country,
                "overall_score": result.overall_score,
                "quality_level": result.quality_level.value,
                "summary": result.summary,
                "power_plants_available": result.datasets.get("power_plants", None) is not None
                    and result.datasets["power_plants"].available,
                "load_profiles_available": result.datasets.get("load_profiles", None) is not None
                    and result.datasets["load_profiles"].available,
                "hydropower_available": result.datasets.get("hydropower", None) is not None
                    and result.datasets["hydropower"].available,
                "resource_potential_available": result.datasets.get("resource_potential", None) is not None
                    and result.datasets["resource_potential"].available,
                "power_plants_count": result.datasets.get("power_plants", None).record_count
                    if result.datasets.get("power_plants") else 0,
                "power_plants_completeness": result.datasets.get("power_plants", None).completeness
                    if result.datasets.get("power_plants") else 0,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/summary")
async def get_quality_overview(
    region: str = Query(..., description="Region ID"),
):
    """Get a quick summary of data quality for a region."""
    results = assess_region_quality(region)
    summary = get_quality_summary(results)

    # Add list of countries by quality level
    countries_by_level = {level.value: [] for level in QualityLevel}
    for country_name, result in results.items():
        countries_by_level[result.quality_level.value].append({
            "country": country_name,
            "score": result.overall_score,
        })

    return {
        "region": region,
        "total_countries": summary["total_countries"],
        "average_score": summary["average_score"],
        "by_quality_level": summary["by_quality_level"],
        "datasets_coverage": summary["datasets_coverage"],
        "countries_by_level": countries_by_level,
    }


class DatasetAvailability(BaseModel):
    """Lightweight availability check for a dataset."""
    available: bool
    source: str
    source_exists: bool


class CountryAvailability(BaseModel):
    """Lightweight availability check for a country."""
    country: str
    datasets: Dict[str, DatasetAvailability]


class RegionAvailabilityResponse(BaseModel):
    """Lightweight availability check for a region."""
    region: str
    total_countries: int
    data_sources: Dict[str, bool]
    countries: List[CountryAvailability]


@router.get("/availability", response_model=RegionAvailabilityResponse)
async def check_data_availability(
    region: str = Query(..., description="Region ID (e.g., 'southern_africa')"),
):
    """
    Quick check of data availability without loading full datasets.
    Much faster than full quality assessment - just checks if source files exist.
    """
    countries = get_countries_for_region(region)

    # Check which data sources exist
    data_sources = {
        "power_plants": data_source_exists("global_integrated_power_plants"),
        "load_profiles": True,  # Synthetic data always available
        "hydropower": data_source_exists("african_hydro_atlas") or data_source_exists("global_hydro_tracker"),
        "solar_potential": data_source_exists("irena_solar_msr"),
        "wind_potential": data_source_exists("irena_wind_msr"),
        "socioeconomic": data_source_exists("owid_energy"),
    }

    # For each country, indicate which datasets are potentially available
    # This is a quick check - actual data filtering happens when loading
    country_availability = []
    for country in countries:
        datasets = {}
        for ds_name, available in data_sources.items():
            source_path = ""
            if ds_name == "power_plants":
                source_path = "Global-Integrated-Power-April-2025.xlsx"
            elif ds_name == "hydropower":
                source_path = "African_Hydropower_Atlas_v2-0.xlsx"
            elif ds_name == "solar_potential":
                source_path = "SolarPV_BestMSRsToCover5%CountryArea.csv"
            elif ds_name == "wind_potential":
                source_path = "Wind_BestMSRsToCover5%CountryArea.csv"
            elif ds_name == "socioeconomic":
                source_path = "owid-energy-data.csv"
            elif ds_name == "load_profiles":
                source_path = "synthetic (generated)"

            datasets[ds_name] = DatasetAvailability(
                available=available,
                source=source_path,
                source_exists=available,
            )

        country_availability.append(CountryAvailability(
            country=country,
            datasets=datasets,
        ))

    return RegionAvailabilityResponse(
        region=region,
        total_countries=len(countries),
        data_sources=data_sources,
        countries=country_availability,
    )
