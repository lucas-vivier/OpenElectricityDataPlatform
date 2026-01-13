"""Country-based data caching with metadata tracking.

Provides unified caching for all data types with:
- Per-country parquet files
- Metadata tracking (source, timestamp, row count)
- Cache validation and management
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from ..config.data_paths import (
    VALID_DATA_TYPES,
    get_country_cache_dir,
    get_country_cache_path,
    get_cache_metadata_path,
    normalize_country_name_for_path,
)

logger = logging.getLogger(__name__)


class CacheMetadata:
    """Manages metadata for cached country data.

    Metadata is stored in _metadata.json per data type and tracks:
    - source: Data source identifier (e.g., 'gem', 'toktarova')
    - source_file: Name of the source file processed
    - processed_at: ISO timestamp of when data was cached
    - row_count: Number of rows in the cached file
    """

    def __init__(self, data_type: str):
        """Initialize metadata manager for a data type.

        Args:
            data_type: One of the valid data types (e.g., 'power_plants')

        Raises:
            ValueError: If data_type is not valid
        """
        if data_type not in VALID_DATA_TYPES:
            raise ValueError(f"Invalid data type: {data_type}")
        self.data_type = data_type
        self._metadata: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load metadata from disk."""
        path = get_cache_metadata_path(self.data_type)
        if path.exists():
            try:
                with open(path) as f:
                    self._metadata = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load metadata for {self.data_type}: {e}")
                self._metadata = {}

    def _save(self) -> None:
        """Save metadata to disk."""
        path = get_cache_metadata_path(self.data_type)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._metadata, f, indent=2)

    def get(self, country: str) -> Optional[dict]:
        """Get metadata for a country.

        Args:
            country: Country name (will be normalized)

        Returns:
            Metadata dict or None if not cached
        """
        normalized = normalize_country_name_for_path(country)
        return self._metadata.get(normalized)

    def set(
        self,
        country: str,
        source: str,
        source_file: str,
        row_count: int,
    ) -> None:
        """Set metadata for a country.

        Args:
            country: Country name (will be normalized)
            source: Data source identifier
            source_file: Source file name
            row_count: Number of rows cached
        """
        normalized = normalize_country_name_for_path(country)
        self._metadata[normalized] = {
            "source": source,
            "source_file": source_file,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "row_count": row_count,
        }
        self._save()

    def remove(self, country: str) -> None:
        """Remove metadata for a country.

        Args:
            country: Country name (will be normalized)
        """
        normalized = normalize_country_name_for_path(country)
        if normalized in self._metadata:
            del self._metadata[normalized]
            self._save()

    def list_cached_countries(self) -> List[str]:
        """List all cached countries (normalized names).

        Returns:
            List of normalized country names
        """
        return list(self._metadata.keys())

    def get_all(self) -> Dict[str, dict]:
        """Get all metadata.

        Returns:
            Dict mapping normalized country names to metadata
        """
        return self._metadata.copy()


def cache_country_data(
    df: pd.DataFrame,
    data_type: str,
    country: str,
    source: str,
    source_file: str,
) -> bool:
    """Cache data for a single country.

    Args:
        df: DataFrame to cache (should be filtered to single country)
        data_type: Type of data (e.g., 'power_plants')
        country: Country name
        source: Data source identifier (e.g., 'gem', 'toktarova')
        source_file: Source file name

    Returns:
        True if caching succeeded
    """
    if data_type not in VALID_DATA_TYPES:
        logger.error(f"Invalid data type: {data_type}")
        return False

    try:
        path = get_country_cache_path(data_type, country)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write parquet file
        df.to_parquet(path, index=False)

        # Update metadata
        metadata = CacheMetadata(data_type)
        metadata.set(country, source, source_file, len(df))

        logger.info(f"Cached {len(df)} rows for {country} ({data_type})")
        return True

    except Exception as e:
        logger.error(f"Failed to cache {data_type} for {country}: {e}")
        return False


def load_cached_country(data_type: str, country: str) -> Optional[pd.DataFrame]:
    """Load cached data for a single country.

    Args:
        data_type: Type of data
        country: Country name

    Returns:
        DataFrame or None if not cached
    """
    path = get_country_cache_path(data_type, country)
    if not path.exists():
        return None

    try:
        return pd.read_parquet(path)
    except Exception as e:
        logger.warning(f"Failed to read cache for {country} ({data_type}): {e}")
        return None


def load_cached_countries(
    data_type: str,
    countries: List[str],
) -> Tuple[pd.DataFrame, List[str]]:
    """Load cached data for multiple countries.

    Args:
        data_type: Type of data
        countries: List of country names

    Returns:
        Tuple of (concatenated DataFrame, list of missing countries)
    """
    cached_dfs = []
    missing = []

    for country in countries:
        df = load_cached_country(data_type, country)
        if df is not None and not df.empty:
            cached_dfs.append(df)
        else:
            missing.append(country)

    if cached_dfs:
        combined = pd.concat(cached_dfs, ignore_index=True)
    else:
        combined = pd.DataFrame()

    return combined, missing


def get_cached_countries(data_type: str) -> Set[str]:
    """Get set of countries that have cached data.

    Args:
        data_type: Type of data

    Returns:
        Set of normalized country names
    """
    cache_dir = get_country_cache_dir(data_type)
    if not cache_dir.exists():
        return set()

    return {p.stem for p in cache_dir.glob("*.parquet") if p.stem != "_metadata"}


def clear_country_cache(data_type: str, country: str) -> bool:
    """Remove cached data for a country.

    Args:
        data_type: Type of data
        country: Country name

    Returns:
        True if successful
    """
    path = get_country_cache_path(data_type, country)
    try:
        if path.exists():
            path.unlink()
        metadata = CacheMetadata(data_type)
        metadata.remove(country)
        logger.info(f"Cleared cache for {country} ({data_type})")
        return True
    except Exception as e:
        logger.error(f"Failed to clear cache for {country}: {e}")
        return False


def clear_data_type_cache(data_type: str) -> bool:
    """Remove all cached data for a data type.

    Args:
        data_type: Type of data

    Returns:
        True if successful
    """
    cache_dir = get_country_cache_dir(data_type)
    try:
        if cache_dir.exists():
            for f in cache_dir.glob("*"):
                f.unlink()
            cache_dir.rmdir()
        logger.info(f"Cleared all cache for {data_type}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear {data_type} cache: {e}")
        return False


def get_cache_info(data_type: str) -> Dict[str, dict]:
    """Get cache information for a data type.

    Args:
        data_type: Type of data

    Returns:
        Dict with metadata for all cached countries
    """
    metadata = CacheMetadata(data_type)
    return metadata.get_all()
