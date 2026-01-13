"""Data quality validation and reporting module.

Provides functions to assess data quality across different data sources
and generate quality reports for countries and regions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

import pandas as pd

from ..config.regions import get_countries_for_region
from .loader import (
    load_power_plants,
    load_load_profiles,
    load_hydropower,
    load_resource_potential,
)


class QualityLevel(str, Enum):
    """Data quality level classification."""
    EXCELLENT = "excellent"  # >= 90% complete, all checks pass
    GOOD = "good"           # >= 70% complete, most checks pass
    FAIR = "fair"           # >= 50% complete, some issues
    POOR = "poor"           # < 50% complete or major issues
    NO_DATA = "no_data"     # No data available


@dataclass
class DatasetQuality:
    """Quality assessment for a single dataset."""
    dataset: str
    available: bool
    record_count: int
    completeness: float  # 0-100 percentage
    quality_level: QualityLevel
    issues: List[str]
    metrics: Dict[str, Any]


@dataclass
class CountryQuality:
    """Quality assessment for a country across all datasets."""
    country: str
    iso_code: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    overall_score: float  # 0-100
    quality_level: QualityLevel
    datasets: Dict[str, DatasetQuality]
    summary: str


def _get_completeness_score(df: pd.DataFrame, key_columns: List[str]) -> float:
    """Calculate completeness score based on non-null values in key columns."""
    if df is None or df.empty:
        return 0.0

    scores = []
    for col in key_columns:
        if col in df.columns:
            non_null = df[col].notna().sum()
            total = len(df)
            scores.append((non_null / total) * 100 if total > 0 else 0)

    return sum(scores) / len(scores) if scores else 0.0


def _classify_quality(completeness: float, issues: List[str]) -> QualityLevel:
    """Classify quality level based on completeness and issues."""
    critical_issues = sum(1 for i in issues if "missing" in i.lower() or "no data" in i.lower())

    if completeness >= 90 and critical_issues == 0:
        return QualityLevel.EXCELLENT
    elif completeness >= 70 and critical_issues <= 1:
        return QualityLevel.GOOD
    elif completeness >= 50 and critical_issues <= 2:
        return QualityLevel.FAIR
    else:
        return QualityLevel.POOR


def assess_power_plants(country: str, df: Optional[pd.DataFrame]) -> DatasetQuality:
    """Assess power plant data quality for a country."""
    issues = []
    metrics = {}

    if df is None or df.empty:
        return DatasetQuality(
            dataset="power_plants",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=["No power plant data available"],
            metrics={}
        )

    # Filter to country
    country_df = df[df["country"] == country] if "country" in df.columns else df

    if country_df.empty:
        return DatasetQuality(
            dataset="power_plants",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=[f"No power plants found for {country}"],
            metrics={}
        )

    record_count = len(country_df)

    # Key columns for completeness
    key_columns = ["name", "technology", "capacity_mw", "latitude", "longitude"]
    completeness = _get_completeness_score(country_df, key_columns)

    # Check for specific issues
    if "capacity_mw" in country_df.columns:
        missing_capacity = country_df["capacity_mw"].isna().sum()
        if missing_capacity > 0:
            issues.append(f"{missing_capacity} plants missing capacity")
        metrics["total_capacity_mw"] = country_df["capacity_mw"].sum()
        metrics["avg_capacity_mw"] = country_df["capacity_mw"].mean()

    if "latitude" in country_df.columns and "longitude" in country_df.columns:
        missing_coords = ((country_df["latitude"].isna()) | (country_df["longitude"].isna())).sum()
        if missing_coords > 0:
            issues.append(f"{missing_coords} plants missing coordinates")
        metrics["geo_coverage"] = ((record_count - missing_coords) / record_count * 100) if record_count > 0 else 0

    if "technology" in country_df.columns:
        tech_count = country_df["technology"].nunique()
        metrics["technology_count"] = tech_count
        metrics["technologies"] = country_df["technology"].value_counts().head(5).to_dict()

    if "status" in country_df.columns:
        status_counts = country_df["status"].value_counts().to_dict()
        metrics["status_distribution"] = status_counts

    quality_level = _classify_quality(completeness, issues)

    return DatasetQuality(
        dataset="power_plants",
        available=True,
        record_count=record_count,
        completeness=round(completeness, 1),
        quality_level=quality_level,
        issues=issues,
        metrics=metrics
    )


def assess_load_profiles(country: str, df: Optional[pd.DataFrame]) -> DatasetQuality:
    """Assess load profile data quality for a country."""
    issues = []
    metrics = {}

    if df is None or df.empty:
        return DatasetQuality(
            dataset="load_profiles",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=["No load profile data available"],
            metrics={}
        )

    # Filter to country/zone
    zone_col = "zone" if "zone" in df.columns else "country"
    country_df = df[df[zone_col] == country] if zone_col in df.columns else df

    if country_df.empty:
        return DatasetQuality(
            dataset="load_profiles",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=[f"No load profiles found for {country}"],
            metrics={}
        )

    record_count = len(country_df)

    # Expected 8760 hours for a full year
    expected_hours = 8760
    hour_coverage = (record_count / expected_hours) * 100
    completeness = min(hour_coverage, 100)

    if record_count < expected_hours:
        issues.append(f"Incomplete year coverage: {record_count}/{expected_hours} hours")

    if "value" in country_df.columns:
        missing_values = country_df["value"].isna().sum()
        if missing_values > 0:
            issues.append(f"{missing_values} hours missing load values")

        metrics["min_value"] = float(country_df["value"].min())
        metrics["max_value"] = float(country_df["value"].max())
        metrics["mean_value"] = float(country_df["value"].mean())

    metrics["hours_available"] = record_count
    metrics["year_coverage_pct"] = round(hour_coverage, 1)

    quality_level = _classify_quality(completeness, issues)

    return DatasetQuality(
        dataset="load_profiles",
        available=True,
        record_count=record_count,
        completeness=round(completeness, 1),
        quality_level=quality_level,
        issues=issues,
        metrics=metrics
    )


def assess_hydropower(country: str, df: Optional[pd.DataFrame]) -> DatasetQuality:
    """Assess hydropower data quality for a country."""
    issues = []
    metrics = {}

    if df is None or df.empty:
        return DatasetQuality(
            dataset="hydropower",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=["No hydropower data available"],
            metrics={}
        )

    # Filter to country
    country_df = df[df["country"] == country] if "country" in df.columns else df

    if country_df.empty:
        return DatasetQuality(
            dataset="hydropower",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=[f"No hydropower plants found for {country}"],
            metrics={}
        )

    record_count = len(country_df)

    key_columns = ["name", "capacity_mw", "latitude", "longitude", "river_name"]
    completeness = _get_completeness_score(country_df, key_columns)

    if "capacity_mw" in country_df.columns:
        missing_capacity = country_df["capacity_mw"].isna().sum()
        if missing_capacity > 0:
            issues.append(f"{missing_capacity} plants missing capacity")
        metrics["total_capacity_mw"] = float(country_df["capacity_mw"].sum())

    if "river_name" in country_df.columns:
        missing_river = country_df["river_name"].isna().sum()
        if missing_river > record_count * 0.5:
            issues.append(f"Most plants missing river information")

    quality_level = _classify_quality(completeness, issues)

    return DatasetQuality(
        dataset="hydropower",
        available=True,
        record_count=record_count,
        completeness=round(completeness, 1),
        quality_level=quality_level,
        issues=issues,
        metrics=metrics
    )


def assess_resource_potential(
    country: str,
    solar_df: Optional[pd.DataFrame],
    wind_df: Optional[pd.DataFrame]
) -> DatasetQuality:
    """Assess renewable resource potential data quality for a country."""
    issues = []
    metrics = {}

    solar_available = solar_df is not None and not solar_df.empty
    wind_available = wind_df is not None and not wind_df.empty

    if not solar_available and not wind_available:
        return DatasetQuality(
            dataset="resource_potential",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=["No resource potential data available"],
            metrics={}
        )

    total_records = 0
    completeness_scores = []

    if solar_available:
        solar_country = solar_df[solar_df["country"] == country] if "country" in solar_df.columns else solar_df
        solar_count = len(solar_country)
        total_records += solar_count
        if solar_count > 0:
            solar_completeness = _get_completeness_score(
                solar_country, ["latitude", "longitude", "capacity_mw", "capacity_factor"]
            )
            completeness_scores.append(solar_completeness)
            metrics["solar_sites"] = solar_count
            if "capacity_mw" in solar_country.columns:
                metrics["solar_capacity_mw"] = float(solar_country["capacity_mw"].sum())
            if "capacity_factor" in solar_country.columns:
                metrics["solar_avg_cf"] = float(solar_country["capacity_factor"].mean())
        else:
            issues.append(f"No solar resource data for {country}")
    else:
        issues.append("No solar resource data available")

    if wind_available:
        wind_country = wind_df[wind_df["country"] == country] if "country" in wind_df.columns else wind_df
        wind_count = len(wind_country)
        total_records += wind_count
        if wind_count > 0:
            wind_completeness = _get_completeness_score(
                wind_country, ["latitude", "longitude", "capacity_mw", "capacity_factor"]
            )
            completeness_scores.append(wind_completeness)
            metrics["wind_sites"] = wind_count
            if "capacity_mw" in wind_country.columns:
                metrics["wind_capacity_mw"] = float(wind_country["capacity_mw"].sum())
            if "capacity_factor" in wind_country.columns:
                metrics["wind_avg_cf"] = float(wind_country["capacity_factor"].mean())
        else:
            issues.append(f"No wind resource data for {country}")
    else:
        issues.append("No wind resource data available")

    completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
    quality_level = _classify_quality(completeness, issues)

    return DatasetQuality(
        dataset="resource_potential",
        available=True,
        record_count=total_records,
        completeness=round(completeness, 1),
        quality_level=quality_level,
        issues=issues,
        metrics=metrics
    )


# Country centroids for map display (approximate)
COUNTRY_CENTROIDS: Dict[str, tuple] = {
    "South Africa": (-29.0, 24.0),
    "Namibia": (-22.0, 17.0),
    "Botswana": (-22.0, 24.0),
    "Zimbabwe": (-19.0, 29.5),
    "Mozambique": (-18.0, 35.0),
    "Zambia": (-13.0, 28.0),
    "Malawi": (-13.5, 34.0),
    "Lesotho": (-29.5, 28.5),
    "Eswatini": (-26.5, 31.5),
    "Nigeria": (9.0, 8.0),
    "Ghana": (8.0, -2.0),
    "Kenya": (1.0, 38.0),
    "Tanzania": (-6.0, 35.0),
    "Ethiopia": (9.0, 40.0),
    "Egypt": (26.0, 30.0),
    "Morocco": (32.0, -5.0),
    "Algeria": (28.0, 3.0),
    "Democratic Republic of the Congo": (-4.0, 22.0),
    "Angola": (-12.5, 18.5),
    "Uganda": (1.0, 32.0),
    "Senegal": (14.5, -14.5),
    "Cote d'Ivoire": (7.5, -5.5),
    "Cameroon": (6.0, 12.0),
    "India": (21.0, 78.0),
    "Pakistan": (30.0, 70.0),
    "Bangladesh": (24.0, 90.0),
    "Indonesia": (-5.0, 120.0),
    "Thailand": (15.0, 100.0),
    "Vietnam": (16.0, 108.0),
    "Brazil": (-10.0, -55.0),
    "Argentina": (-34.0, -64.0),
    "Chile": (-33.0, -70.0),
    "Colombia": (4.0, -72.0),
    "Mexico": (23.0, -102.0),
    "Germany": (51.0, 10.0),
    "France": (46.0, 2.0),
    "United Kingdom": (54.0, -2.0),
    "Spain": (40.0, -4.0),
    "Italy": (42.0, 12.0),
    "Poland": (52.0, 19.0),
    "Turkey": (39.0, 35.0),
    "Saudi Arabia": (24.0, 45.0),
    "China": (35.0, 105.0),
    "Japan": (36.0, 138.0),
    "Australia": (-25.0, 135.0),
}


def get_country_centroid(country: str) -> tuple:
    """Get approximate centroid coordinates for a country."""
    return COUNTRY_CENTROIDS.get(country, (0.0, 0.0))


def assess_country_quality(
    country: str,
    region: str,
    verbose: bool = False
) -> CountryQuality:
    """Assess overall data quality for a country.

    Args:
        country: Country name
        region: Region identifier for data loading
        verbose: Whether to print progress

    Returns:
        CountryQuality with assessments for all datasets
    """
    if verbose:
        print(f"Assessing quality for {country}...")

    datasets: Dict[str, DatasetQuality] = {}

    # Load and assess power plants
    try:
        power_df = load_power_plants(region, [country])
        datasets["power_plants"] = assess_power_plants(country, power_df)
    except Exception as e:
        if verbose:
            print(f"  Error loading power plants: {e}")
        datasets["power_plants"] = DatasetQuality(
            dataset="power_plants",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=[f"Error loading data: {str(e)}"],
            metrics={}
        )

    # Load and assess load profiles
    try:
        load_df = load_load_profiles(region, [country])
        datasets["load_profiles"] = assess_load_profiles(country, load_df)
    except Exception as e:
        if verbose:
            print(f"  Error loading load profiles: {e}")
        datasets["load_profiles"] = DatasetQuality(
            dataset="load_profiles",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=[f"Error loading data: {str(e)}"],
            metrics={}
        )

    # Load and assess hydropower
    try:
        hydro_df = load_hydropower(region, [country], source="both")
        datasets["hydropower"] = assess_hydropower(country, hydro_df)
    except Exception as e:
        if verbose:
            print(f"  Error loading hydropower: {e}")
        datasets["hydropower"] = DatasetQuality(
            dataset="hydropower",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=[f"Error loading data: {str(e)}"],
            metrics={}
        )

    # Load and assess resource potential
    try:
        solar_df = load_resource_potential(region, [country], technology="solar")
        wind_df = load_resource_potential(region, [country], technology="wind")
        datasets["resource_potential"] = assess_resource_potential(country, solar_df, wind_df)
    except Exception as e:
        if verbose:
            print(f"  Error loading resource potential: {e}")
        datasets["resource_potential"] = DatasetQuality(
            dataset="resource_potential",
            available=False,
            record_count=0,
            completeness=0.0,
            quality_level=QualityLevel.NO_DATA,
            issues=[f"Error loading data: {str(e)}"],
            metrics={}
        )

    # Calculate overall score
    available_datasets = [d for d in datasets.values() if d.available]
    if available_datasets:
        overall_score = sum(d.completeness for d in available_datasets) / len(available_datasets)
    else:
        overall_score = 0.0

    # Classify overall quality
    all_issues = []
    for d in datasets.values():
        all_issues.extend(d.issues)

    overall_level = _classify_quality(overall_score, all_issues)

    # Generate summary
    available_count = len(available_datasets)
    total_count = len(datasets)
    summary = f"{available_count}/{total_count} datasets available, {overall_score:.0f}% overall completeness"

    # Get coordinates
    lat, lon = get_country_centroid(country)

    return CountryQuality(
        country=country,
        iso_code=None,  # Could be enhanced with ISO codes
        latitude=lat if lat != 0 else None,
        longitude=lon if lon != 0 else None,
        overall_score=round(overall_score, 1),
        quality_level=overall_level,
        datasets=datasets,
        summary=summary
    )


def assess_region_quality(
    region: str,
    verbose: bool = False
) -> Dict[str, CountryQuality]:
    """Assess data quality for all countries in a region.

    Args:
        region: Region identifier
        verbose: Whether to print progress

    Returns:
        Dictionary mapping country names to their quality assessments
    """
    countries = get_countries_for_region(region)

    if not countries:
        if verbose:
            print(f"No countries found for region: {region}")
        return {}

    if verbose:
        print(f"Assessing quality for {len(countries)} countries in {region}")

    results = {}
    for country in countries:
        results[country] = assess_country_quality(country, region, verbose=verbose)

    return results


def get_quality_summary(quality_results: Dict[str, CountryQuality]) -> Dict[str, Any]:
    """Generate a summary of quality results for a region.

    Args:
        quality_results: Results from assess_region_quality

    Returns:
        Summary dictionary with counts and statistics
    """
    if not quality_results:
        return {
            "total_countries": 0,
            "by_quality_level": {},
            "average_score": 0,
            "datasets_coverage": {}
        }

    # Count by quality level
    by_level = {}
    for level in QualityLevel:
        by_level[level.value] = sum(
            1 for q in quality_results.values() if q.quality_level == level
        )

    # Average score
    avg_score = sum(q.overall_score for q in quality_results.values()) / len(quality_results)

    # Dataset coverage
    datasets_coverage = {}
    for dataset_name in ["power_plants", "load_profiles", "hydropower", "resource_potential"]:
        available = sum(
            1 for q in quality_results.values()
            if q.datasets.get(dataset_name, DatasetQuality(
                dataset=dataset_name, available=False, record_count=0,
                completeness=0, quality_level=QualityLevel.NO_DATA, issues=[], metrics={}
            )).available
        )
        datasets_coverage[dataset_name] = {
            "countries_with_data": available,
            "coverage_pct": round(available / len(quality_results) * 100, 1)
        }

    return {
        "total_countries": len(quality_results),
        "by_quality_level": by_level,
        "average_score": round(avg_score, 1),
        "datasets_coverage": datasets_coverage
    }