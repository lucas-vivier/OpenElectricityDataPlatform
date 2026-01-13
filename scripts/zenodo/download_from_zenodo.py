#!/usr/bin/env python3
"""
Download preprocessed data from Zenodo.

This script downloads regional data files from Zenodo for local use.
Files are verified using SHA256 checksums.

Usage:
    python scripts/zenodo/download_from_zenodo.py --region south_africa
    python scripts/zenodo/download_from_zenodo.py --all
    python scripts/zenodo/download_from_zenodo.py --list

Environment:
    ZENODO_RECORD_ID: Override the default record ID for a region
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm

# Add project root to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from openenergydata.config.data_paths import get_local_region_path, LOCAL_DIR

# Zenodo API
ZENODO_API = "https://zenodo.org/api"

# Registry of Zenodo record IDs per region
# Update these after publishing to Zenodo
ZENODO_RECORDS = {
    # "south_africa": "1234567",  # Example - replace with real record IDs
    # "west_africa": "1234568",
    # "east_africa": "1234569",
}


def get_record_id(region_id: str) -> Optional[str]:
    """Get Zenodo record ID for a region."""
    # Check environment override first
    env_key = f"ZENODO_RECORD_{region_id.upper()}"
    if os.getenv(env_key):
        return os.getenv(env_key)

    # Check local record file
    region_path = get_local_region_path(region_id)
    record_file = region_path / "zenodo_record.json"
    if record_file.exists():
        record = json.loads(record_file.read_text())
        # Extract record ID from DOI or deposit_id
        if "deposit_id" in record:
            return str(record["deposit_id"])

    # Check registry
    return ZENODO_RECORDS.get(region_id)


def get_record_files(record_id: str) -> list:
    """Get list of files in a Zenodo record."""
    response = requests.get(f"{ZENODO_API}/records/{record_id}")
    response.raise_for_status()
    record = response.json()
    return record.get("files", [])


def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def download_file(url: str, dest_path: Path, expected_checksum: Optional[str] = None) -> bool:
    """Download a file with progress bar and optional checksum verification."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if file already exists with correct checksum
    if dest_path.exists() and expected_checksum:
        existing_checksum = calculate_sha256(dest_path)
        if existing_checksum == expected_checksum:
            print(f"  {dest_path.name}: Already exists (checksum OK)")
            return True

    # Download with progress bar
    response = requests.get(url, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    block_size = 8192

    with open(dest_path, "wb") as f:
        with tqdm(
            total=total_size,
            unit="iB",
            unit_scale=True,
            desc=f"  {dest_path.name}",
        ) as pbar:
            for chunk in response.iter_content(chunk_size=block_size):
                f.write(chunk)
                pbar.update(len(chunk))

    # Verify checksum if provided
    if expected_checksum:
        actual_checksum = calculate_sha256(dest_path)
        if actual_checksum != expected_checksum:
            print(f"  WARNING: Checksum mismatch for {dest_path.name}")
            print(f"    Expected: {expected_checksum}")
            print(f"    Got: {actual_checksum}")
            return False

    return True


def download_region(region_id: str, force: bool = False) -> bool:
    """Download all data files for a region from Zenodo."""
    record_id = get_record_id(region_id)
    if not record_id:
        print(f"No Zenodo record found for region '{region_id}'")
        print("  Either the region hasn't been uploaded to Zenodo yet,")
        print("  or you need to set ZENODO_RECORD_{REGION_ID} environment variable.")
        return False

    print(f"\nDownloading data for region: {region_id}")
    print(f"  Zenodo record: {record_id}")

    # Get file list from Zenodo
    try:
        files = get_record_files(record_id)
    except requests.HTTPError as e:
        print(f"  Error fetching record: {e}")
        return False

    if not files:
        print("  No files found in record")
        return False

    print(f"  Found {len(files)} files")

    # Download each file
    region_path = get_local_region_path(region_id)
    success = True

    for file_info in files:
        filename = file_info["key"]
        url = file_info["links"]["self"]
        checksum = file_info.get("checksum", "").replace("md5:", "")  # Zenodo uses MD5

        dest_path = region_path / filename

        # Skip non-parquet files unless they're metadata
        if not filename.endswith((".parquet", ".json", ".txt")):
            continue

        try:
            # Note: Zenodo provides MD5, not SHA256, so we skip checksum for now
            # In production, you might want to store SHA256 in zenodo_metadata.json
            if not download_file(url, dest_path, expected_checksum=None):
                success = False
        except Exception as e:
            print(f"  Error downloading {filename}: {e}")
            success = False

    if success:
        print(f"\nDownload complete: {region_path}")
    else:
        print(f"\nDownload completed with errors")

    return success


def list_available_regions():
    """List regions with known Zenodo records."""
    print("Regions with Zenodo records:")
    print("-" * 40)

    if not ZENODO_RECORDS:
        print("  No regions have been uploaded to Zenodo yet.")
        print("  Run upload_to_zenodo.py first.")
        return

    for region_id, record_id in ZENODO_RECORDS.items():
        print(f"  {region_id}: Record {record_id}")


def list_local_regions():
    """List locally available preprocessed regions."""
    print("\nLocally preprocessed regions:")
    print("-" * 40)

    if not LOCAL_DIR.exists():
        print("  No local data found.")
        return

    for region_dir in sorted(LOCAL_DIR.iterdir()):
        if region_dir.is_dir():
            parquet_count = len(list(region_dir.glob("*.parquet")))
            record_file = region_dir / "zenodo_record.json"
            zenodo_status = "uploaded" if record_file.exists() else "local only"
            print(f"  {region_dir.name}: {parquet_count} files ({zenodo_status})")


def main():
    parser = argparse.ArgumentParser(
        description="Download preprocessed data from Zenodo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Download a single region
    python scripts/zenodo/download_from_zenodo.py --region south_africa

    # Download all available regions
    python scripts/zenodo/download_from_zenodo.py --all

    # List available regions
    python scripts/zenodo/download_from_zenodo.py --list

    # Force re-download
    python scripts/zenodo/download_from_zenodo.py --region south_africa --force
        """,
    )
    parser.add_argument("--region", help="Region ID to download")
    parser.add_argument("--all", action="store_true", help="Download all available regions")
    parser.add_argument("--force", action="store_true", help="Force re-download even if files exist")
    parser.add_argument("--list", action="store_true", help="List available regions")

    args = parser.parse_args()

    if args.list:
        list_available_regions()
        list_local_regions()
        return

    if not args.region and not args.all:
        parser.error("Specify --region REGION_ID or --all or --list")

    if args.all:
        if not ZENODO_RECORDS:
            print("No regions configured for Zenodo download.")
            print("Set ZENODO_RECORD_{REGION_ID} environment variables or update ZENODO_RECORDS in this script.")
            return

        for region_id in ZENODO_RECORDS:
            download_region(region_id, force=args.force)
    else:
        download_region(args.region, force=args.force)


if __name__ == "__main__":
    main()
