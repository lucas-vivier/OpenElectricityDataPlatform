"""Data loading and source handling module.

Provides unified data loading with country-based caching.
"""

from .loader import (
    load_power_plants,
    load_load_profiles,
    load_re_profiles,
    load_hydropower,
    load_hydro_scenarios,
    load_resource_potential,
    load_re_profiles_processed,
)
from .cache import (
    CacheMetadata,
    cache_country_data,
    load_cached_country,
    load_cached_countries,
    get_cached_countries,
    clear_country_cache,
    clear_data_type_cache,
    get_cache_info,
)

__all__ = [
    # Loaders
    "load_power_plants",
    "load_load_profiles",
    "load_re_profiles",
    "load_hydropower",
    "load_hydro_scenarios",
    "load_resource_potential",
    "load_re_profiles_processed",
    # Cache management
    "CacheMetadata",
    "cache_country_data",
    "load_cached_country",
    "load_cached_countries",
    "get_cached_countries",
    "clear_country_cache",
    "clear_data_type_cache",
    "get_cache_info",
]
