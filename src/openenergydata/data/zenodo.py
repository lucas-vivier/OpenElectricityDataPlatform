"""
Zenodo data client for downloading preprocessed datasets.

This module provides automatic downloading of preprocessed data from Zenodo
when local files are not available.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests

from ..config.data_paths import get_local_region_path, LOCAL_DIR

logger = logging.getLogger(__name__)

# Zenodo API
ZENODO_API = "https://zenodo.org/api"

# Registry of Zenodo record IDs per region
# These are updated after publishing datasets to Zenodo
# Format: region_id -> record_id
ZENODO_RECORDS: dict[str, str] = {
    # Populate after uploading to Zenodo:
    # "south_africa": "1234567",
    # "southern_africa": "1234568",
    # "west_africa": "1234569",
    # "east_africa": "1234570",
    # "central_africa": "1234571",
}


def get_zenodo_record_id(region_id: str) -> Optional[str]:
    """
    Get Zenodo record ID for a region.

    Checks in order:
    1. Environment variable ZENODO_RECORD_{REGION_ID}
    2. Local zenodo_record.json file
    3. Built-in registry
    """
    # Environment override
    env_key = f"ZENODO_RECORD_{region_id.upper()}"
    if os.getenv(env_key):
        return os.getenv(env_key)

    # Local record file (from previous upload)
    region_path = get_local_region_path(region_id)
    record_file = region_path / "zenodo_record.json"
    if record_file.exists():
        try:
            record = json.loads(record_file.read_text())
            if "deposit_id" in record:
                return str(record["deposit_id"])
        except (json.JSONDecodeError, KeyError):
            pass

    # Built-in registry
    return ZENODO_RECORDS.get(region_id)


def fetch_record_metadata(record_id: str) -> Optional[dict]:
    """Fetch metadata for a Zenodo record."""
    try:
        response = requests.get(
            f"{ZENODO_API}/records/{record_id}",
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Zenodo record {record_id}: {e}")
        return None


def download_file_from_zenodo(
    url: str,
    dest_path: Path,
    expected_size: Optional[int] = None,
    show_progress: bool = True,
) -> bool:
    """
    Download a single file from Zenodo.

    Args:
        url: Direct download URL
        dest_path: Local destination path
        expected_size: Expected file size in bytes (for progress)
        show_progress: Whether to show download progress

    Returns:
        True if download successful, False otherwise
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", expected_size or 0))

        # Simple progress tracking
        downloaded = 0
        block_size = 8192

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=block_size):
                f.write(chunk)
                downloaded += len(chunk)

                if show_progress and total_size > 0:
                    pct = (downloaded / total_size) * 100
                    if downloaded % (block_size * 100) == 0:  # Log every ~800KB
                        logger.info(f"  Downloading {dest_path.name}: {pct:.0f}%")

        logger.info(f"  Downloaded: {dest_path.name}")
        return True

    except requests.RequestException as e:
        logger.error(f"Failed to download {url}: {e}")
        if dest_path.exists():
            dest_path.unlink()  # Clean up partial download
        return False


def download_region_from_zenodo(
    region_id: str,
    datasets: Optional[list[str]] = None,
    force: bool = False,
) -> bool:
    """
    Download preprocessed data for a region from Zenodo.

    Args:
        region_id: Region identifier (e.g., "south_africa")
        datasets: Specific datasets to download (e.g., ["power_plants", "hydropower"])
                  If None, downloads all available datasets
        force: Force re-download even if files exist

    Returns:
        True if all requested downloads succeeded, False otherwise
    """
    record_id = get_zenodo_record_id(region_id)
    if not record_id:
        logger.warning(f"No Zenodo record found for region '{region_id}'")
        return False

    logger.info(f"Fetching Zenodo record {record_id} for region {region_id}")

    # Get record metadata
    record = fetch_record_metadata(record_id)
    if not record:
        return False

    files = record.get("files", [])
    if not files:
        logger.warning(f"No files found in Zenodo record {record_id}")
        return False

    # Filter to parquet files (skip README, metadata)
    parquet_files = [f for f in files if f["key"].endswith(".parquet")]

    # Filter to requested datasets if specified
    if datasets:
        dataset_filenames = [f"{d}.parquet" for d in datasets]
        parquet_files = [f for f in parquet_files if f["key"] in dataset_filenames]

    if not parquet_files:
        logger.warning(f"No matching files found for region {region_id}")
        return False

    region_path = get_local_region_path(region_id)
    success = True

    for file_info in parquet_files:
        filename = file_info["key"]
        url = file_info["links"]["self"]
        size = file_info.get("size", 0)

        dest_path = region_path / filename

        # Skip if file exists (unless force)
        if dest_path.exists() and not force:
            logger.debug(f"  {filename}: Already exists (skipping)")
            continue

        if not download_file_from_zenodo(url, dest_path, expected_size=size):
            success = False

    return success


def ensure_region_data(
    region_id: str,
    dataset: Optional[str] = None,
    files: Optional[list[str]] = None,
) -> bool:
    """
    Ensure dataset(s) are available locally, downloading from Zenodo if needed.

    This is the main entry point for the loader to use.

    Args:
        region_id: Region identifier
        dataset: Single dataset name (e.g., "power_plants", "hydropower")
        files: List of file names to download (e.g., ["power_plants.parquet"])
               Takes precedence over dataset if both provided

    Returns:
        True if all requested data is available, False otherwise
    """
    region_path = get_local_region_path(region_id)

    # Convert files to datasets
    if files:
        datasets = [f.replace(".parquet", "") for f in files if f.endswith(".parquet")]
    elif dataset:
        datasets = [dataset]
    else:
        datasets = None  # Download all

    # Check if files already exist
    if datasets:
        all_exist = all(
            (region_path / f"{d}.parquet").exists()
            for d in datasets
        )
        if all_exist:
            return True

    # Try to download from Zenodo
    logger.info(f"Local data not found for {region_id}, checking Zenodo...")

    if download_region_from_zenodo(region_id, datasets=datasets):
        # Verify files exist after download
        if datasets:
            return all(
                (region_path / f"{d}.parquet").exists()
                for d in datasets
            )
        return True

    return False


def list_available_regions() -> list[str]:
    """List regions that have Zenodo records available."""
    return list(ZENODO_RECORDS.keys())


def get_region_datasets(region_id: str) -> list[str]:
    """Get list of available datasets for a region from Zenodo."""
    record_id = get_zenodo_record_id(region_id)
    if not record_id:
        return []

    record = fetch_record_metadata(record_id)
    if not record:
        return []

    files = record.get("files", [])
    datasets = []
    for f in files:
        if f["key"].endswith(".parquet"):
            # Remove .parquet extension
            datasets.append(f["key"][:-8])

    return datasets
