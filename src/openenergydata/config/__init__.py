"""Configuration module for OpenEnergyData."""

from .settings import Settings, get_settings
from .regions import get_regions, get_countries_for_region, get_region_bbox

__all__ = ["Settings", "get_settings", "get_regions", "get_countries_for_region", "get_region_bbox"]
