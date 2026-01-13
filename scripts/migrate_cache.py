#!/usr/bin/env python3
"""Migrate existing region-based cache to country-based structure.

This script converts the old cache structure:
    data/local/{region}/power_plants.parquet

To the new country-based structure:
    data/local/power_plants/{country}.parquet

Usage:
    python scripts/migrate_cache.py [--dry-run] [--remove-old]

Options:
    --dry-run      Show what would be done without making changes
    --remove-old   Remove old region directories after migration
"""

import argparse
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
LOCAL_DIR = PROJECT_ROOT / "data" / "local"

# Data types and their country/zone columns
DATA_TYPE_CONFIG = {
    "power_plants": {"column": "country", "filename": "power_plants.parquet"},
    "load_profiles": {"column": "zone", "filename": "load_profiles.parquet"},
    "hydropower": {"column": "country", "filename": "hydropower.parquet"},
    "resource_potential_solar": {"column": "country", "filename": "resource_potential_solar.parquet"},
    "resource_potential_wind": {"column": "country", "filename": "resource_potential_wind.parquet"},
    "re_profiles_solar": {"column": "zone", "filename": "re_profiles_solar.parquet"},
    "re_profiles_wind": {"column": "zone", "filename": "re_profiles_wind.parquet"},
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def normalize_country_name(country: str) -> str:
    """Convert country name to safe filename."""
    import re
    normalized = country.lower()
    normalized = normalized.replace(" ", "_")
    normalized = normalized.replace("'", "")
    normalized = normalized.replace("-", "_")
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    return normalized


def get_region_directories() -> list[Path]:
    """Find all region directories (old structure)."""
    if not LOCAL_DIR.exists():
        return []

    # Exclude directories that are data types (new structure)
    data_type_names = set(DATA_TYPE_CONFIG.keys())

    return [
        d for d in LOCAL_DIR.iterdir()
        if d.is_dir()
        and d.name not in data_type_names
        and not d.name.startswith(".")
    ]


def migrate_region_file(
    region_path: Path,
    data_type: str,
    config: dict,
    dry_run: bool = False,
) -> int:
    """Migrate a single region parquet file to country-based files.

    Returns:
        Number of countries migrated
    """
    source_file = region_path / config["filename"]
    if not source_file.exists():
        return 0

    country_col = config["column"]

    try:
        df = pd.read_parquet(source_file)
    except Exception as e:
        logger.error(f"Failed to read {source_file}: {e}")
        return 0

    if country_col not in df.columns:
        logger.warning(f"Column '{country_col}' not found in {source_file}")
        return 0

    countries = df[country_col].unique()
    migrated = 0

    # Target directory
    target_dir = LOCAL_DIR / data_type

    for country in countries:
        if pd.isna(country):
            continue

        country_df = df[df[country_col] == country]
        normalized = normalize_country_name(str(country))
        target_path = target_dir / f"{normalized}.parquet"

        if dry_run:
            logger.info(f"  [DRY-RUN] Would write {len(country_df)} rows to {target_path.name}")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            country_df.to_parquet(target_path, index=False)
            logger.info(f"  Wrote {len(country_df)} rows to {target_path.name}")

        migrated += 1

    return migrated


def create_metadata(data_type: str, region_name: str, dry_run: bool = False) -> None:
    """Create metadata file for migrated data."""
    target_dir = LOCAL_DIR / data_type
    metadata_path = target_dir / "_metadata.json"

    if not target_dir.exists():
        return

    # Load existing metadata if present
    existing_metadata = {}
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                existing_metadata = json.load(f)
        except Exception:
            pass

    # Add metadata for new files
    for parquet_file in target_dir.glob("*.parquet"):
        country_name = parquet_file.stem
        if country_name in existing_metadata:
            continue  # Don't overwrite existing metadata

        try:
            df = pd.read_parquet(parquet_file)
            existing_metadata[country_name] = {
                "source": "migrated",
                "source_file": f"{region_name}_cache",
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "row_count": len(df),
            }
        except Exception as e:
            logger.warning(f"Failed to read {parquet_file}: {e}")

    if dry_run:
        logger.info(f"  [DRY-RUN] Would update metadata with {len(existing_metadata)} countries")
    else:
        with open(metadata_path, "w") as f:
            json.dump(existing_metadata, f, indent=2)
        logger.info(f"  Updated metadata for {len(existing_metadata)} countries")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate cache from region-based to country-based structure"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--remove-old",
        action="store_true",
        help="Remove old region directories after migration",
    )
    args = parser.parse_args()

    logger.info("=== Cache Migration: Region-based to Country-based ===")
    logger.info(f"Local data directory: {LOCAL_DIR}")

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Find region directories
    region_dirs = get_region_directories()

    if not region_dirs:
        logger.info("No region directories found to migrate")
        return

    logger.info(f"Found {len(region_dirs)} region directories: {[d.name for d in region_dirs]}")

    total_migrated = 0

    for region_dir in region_dirs:
        logger.info(f"\nProcessing region: {region_dir.name}")

        for data_type, config in DATA_TYPE_CONFIG.items():
            migrated = migrate_region_file(region_dir, data_type, config, args.dry_run)
            if migrated > 0:
                total_migrated += migrated
                logger.info(f"  {data_type}: migrated {migrated} countries")
                create_metadata(data_type, region_dir.name, args.dry_run)

    # Remove old directories if requested
    if args.remove_old and not args.dry_run:
        logger.info("\nRemoving old region directories...")
        for region_dir in region_dirs:
            logger.info(f"  Removing: {region_dir}")
            shutil.rmtree(region_dir)
    elif args.remove_old and args.dry_run:
        logger.info("\n[DRY-RUN] Would remove old region directories:")
        for region_dir in region_dirs:
            logger.info(f"  [DRY-RUN] Would remove: {region_dir}")

    logger.info(f"\n=== Migration complete. Total countries migrated: {total_migrated} ===")


if __name__ == "__main__":
    main()
