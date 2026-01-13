"""Region definitions and country mappings."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from difflib import SequenceMatcher


def _get_metadata_dir() -> Path:
    """Get the metadata directory path."""
    # __file__ = src/openenergydata/config/regions.py
    # parents[3] = project root
    return Path(__file__).parents[3] / "data" / "metadata"


@lru_cache(maxsize=1)
def get_regions() -> Dict[str, dict]:
    """Load region definitions from metadata file.

    Returns:
        Dictionary mapping region IDs to region info (name, countries, bbox).
    """
    regions_file = _get_metadata_dir() / "regions.json"

    if not regions_file.exists():
        # Return default if file doesn't exist
        return {
            "south_africa": {
                "name": "South Africa",
                "countries": ["South Africa"],
                "bbox": [16.4, -35.0, 33.0, -22.0],
                "default_zoom": 5,
            }
        }

    with open(regions_file) as f:
        return json.load(f)


def get_countries_for_region(region_id: str) -> List[str]:
    """Get the list of countries for a region.

    Args:
        region_id: Region identifier (e.g., 'south_africa', 'west_africa')

    Returns:
        List of country names in the region.
    """
    regions = get_regions()

    if region_id not in regions:
        return []

    return regions[region_id].get("countries", [])


def get_region_bbox(region_id: str) -> Optional[List[float]]:
    """Get the bounding box for a region.

    Args:
        region_id: Region identifier

    Returns:
        Bounding box as [min_lon, min_lat, max_lon, max_lat] or None.
    """
    regions = get_regions()

    if region_id not in regions:
        return None

    return regions[region_id].get("bbox")


def resolve_country_name(
    input_name: str,
    available_names: List[str],
    threshold: float = 0.75,
) -> Optional[str]:
    """Resolve a country name using fuzzy matching.

    Adapted from EPM pre-analysis snakemake_helpers.py.

    Args:
        input_name: The country name to resolve
        available_names: List of valid country names to match against
        threshold: Minimum similarity ratio (0-1) for a match

    Returns:
        The best matching country name, or None if no match above threshold.
    """
    if not input_name or not available_names:
        return None

    # Normalize input
    input_normalized = input_name.strip().lower()
    # Also create version without spaces (for matching CamelCase names like "DemocraticRepublicoftheCongo")
    input_no_spaces = input_normalized.replace(" ", "").replace("-", "").replace("'", "")

    # Try exact match first (case-insensitive)
    for name in available_names:
        name_lower = name.lower()
        if name_lower == input_normalized:
            return name
        # Also try matching without spaces
        name_no_spaces = name_lower.replace(" ", "").replace("-", "").replace("'", "")
        if name_no_spaces == input_no_spaces:
            return name

    # Fuzzy matching - try both with and without spaces
    best_match = None
    best_ratio = 0.0

    for name in available_names:
        name_lower = name.lower()
        name_no_spaces = name_lower.replace(" ", "").replace("-", "").replace("'", "")

        # Try regular match
        ratio = SequenceMatcher(None, input_normalized, name_lower).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = name

        # Try without spaces match
        ratio_no_spaces = SequenceMatcher(None, input_no_spaces, name_no_spaces).ratio()
        if ratio_no_spaces > best_ratio and ratio_no_spaces >= threshold:
            best_ratio = ratio_no_spaces
            best_match = name

    return best_match


def get_all_countries() -> List[str]:
    """Get a deduplicated list of all countries across all regions.

    Returns:
        Sorted list of unique country names.
    """
    regions = get_regions()
    all_countries = set()

    for region_info in regions.values():
        all_countries.update(region_info.get("countries", []))

    return sorted(all_countries)


def get_country_centroid(country: str) -> Optional[Dict[str, float]]:
    """Get the centroid coordinates for a country.

    Args:
        country: Country name

    Returns:
        Dict with 'lat' and 'lon' keys, or None if not found.
    """
    regions = get_regions()
    centroids = regions.get("country_centroids", {})

    if country in centroids:
        return centroids[country]

    # Try fuzzy matching
    available_countries = list(centroids.keys())
    resolved = resolve_country_name(country, available_countries)
    if resolved:
        return centroids[resolved]

    return None
