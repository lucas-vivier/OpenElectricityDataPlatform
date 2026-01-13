"""Application settings and configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Settings:
    """Application configuration settings."""

    # Data paths
    data_dir: Path = field(default_factory=lambda: Path(__file__).parents[4] / "data")
    local_data_dir: Path = field(default_factory=lambda: Path(__file__).parents[4] / "data" / "local")
    metadata_dir: Path = field(default_factory=lambda: Path(__file__).parents[4] / "data" / "metadata")

    # API keys (loaded from environment or config)
    renewables_ninja_api_key: Optional[str] = None
    entsoe_api_key: Optional[str] = None
    cds_api_key: Optional[str] = None
    cds_api_url: str = "https://cds.climate.copernicus.eu/api/v2"

    # Zenodo settings
    zenodo_enabled: bool = True
    zenodo_api_url: str = "https://zenodo.org/api"
    zenodo_sandbox_url: str = "https://sandbox.zenodo.org/api"
    zenodo_use_sandbox: bool = False
    zenodo_api_token: Optional[str] = None

    # Default settings
    default_year: int = 2020
    default_n_representative_days: int = 12

    # Map settings
    default_map_zoom: int = 5
    map_tile_provider: str = "CartoDB positron"

    def __post_init__(self):
        """Load API keys from environment variables if not set."""
        if self.renewables_ninja_api_key is None:
            self.renewables_ninja_api_key = os.getenv("API_TOKEN_RENEWABLES_NINJA")
        if self.entsoe_api_key is None:
            self.entsoe_api_key = os.getenv("API_TOKEN_ENTSOE")
        if self.cds_api_key is None:
            self.cds_api_key = os.getenv("CDS_API_KEY")
        if self.cds_api_url == "https://cds.climate.copernicus.eu/api/v2":
            env_url = os.getenv("CDS_API_URL")
            if env_url:
                self.cds_api_url = env_url

        # Zenodo settings
        if self.zenodo_api_token is None:
            self.zenodo_api_token = os.getenv("ZENODO_API_TOKEN")
        zenodo_enabled_env = os.getenv("ZENODO_ENABLED")
        if zenodo_enabled_env is not None:
            self.zenodo_enabled = zenodo_enabled_env.lower() in ("true", "1", "yes")
        zenodo_sandbox_env = os.getenv("ZENODO_USE_SANDBOX")
        if zenodo_sandbox_env is not None:
            self.zenodo_use_sandbox = zenodo_sandbox_env.lower() in ("true", "1", "yes")

    @classmethod
    def from_yaml(cls, config_path: Path) -> "Settings":
        """Load settings from a YAML config file."""
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            config = yaml.safe_load(f)

        if config is None:
            return cls()

        return cls(
            data_dir=Path(config.get("data_dir", cls.data_dir)),
            local_data_dir=Path(config.get("local_data_dir", cls.local_data_dir)),
            renewables_ninja_api_key=config.get("renewables_ninja_api_key"),
            entsoe_api_key=config.get("entsoe_api_key"),
            cds_api_key=config.get("cds_api_key"),
            cds_api_url=config.get("cds_api_url", "https://cds.climate.copernicus.eu/api/v2"),
            zenodo_enabled=config.get("zenodo_enabled", True),
            zenodo_api_token=config.get("zenodo_api_token"),
            zenodo_use_sandbox=config.get("zenodo_use_sandbox", False),
            default_year=config.get("default_year", 2020),
            default_n_representative_days=config.get("default_n_representative_days", 12),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings."""
    # Try to load from config file first
    config_paths = [
        Path.cwd() / "config.yaml",
        Path.cwd() / "config.yml",
        Path(__file__).parents[4] / "config.yaml",
    ]

    for config_path in config_paths:
        if config_path.exists():
            return Settings.from_yaml(config_path)

    return Settings()
