#!/usr/bin/env python3
"""
Upload preprocessed data to Zenodo.

This script packages and uploads regional data files to Zenodo for public distribution.
Files are compressed and organized by region for efficient download.

Usage:
    python scripts/zenodo/upload_to_zenodo.py --region south_africa
    python scripts/zenodo/upload_to_zenodo.py --all
    python scripts/zenodo/upload_to_zenodo.py --region south_africa --publish

Environment:
    ZENODO_API_TOKEN: Your Zenodo API token (get from https://zenodo.org/account/settings/applications/)
    ZENODO_SANDBOX: Set to "true" to use sandbox.zenodo.org for testing

Output:
    Creates a new Zenodo deposit with:
    - Compressed parquet files for each dataset
    - metadata.json with processing info
    - README.txt with dataset description
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from openenergydata.config import get_regions
from openenergydata.config.data_paths import get_local_region_path

# Zenodo API endpoints
ZENODO_API = "https://zenodo.org/api"
ZENODO_SANDBOX_API = "https://sandbox.zenodo.org/api"


def get_api_base() -> str:
    """Get Zenodo API base URL (sandbox or production)."""
    if os.getenv("ZENODO_SANDBOX", "").lower() == "true":
        print("Using Zenodo SANDBOX (for testing)")
        return ZENODO_SANDBOX_API
    return ZENODO_API


def get_api_token() -> str:
    """Get Zenodo API token from environment."""
    token = os.getenv("ZENODO_API_TOKEN")
    if not token:
        raise ValueError(
            "ZENODO_API_TOKEN environment variable not set.\n"
            "Get your token from: https://zenodo.org/account/settings/applications/"
        )
    return token


def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def get_file_size_mb(filepath: Path) -> float:
    """Get file size in MB."""
    return filepath.stat().st_size / (1024 * 1024)


def create_deposit(token: str) -> dict:
    """Create a new Zenodo deposit."""
    api_base = get_api_base()
    response = requests.post(
        f"{api_base}/deposit/depositions",
        params={"access_token": token},
        json={},
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def upload_file(deposit_id: int, bucket_url: str, filepath: Path, token: str) -> dict:
    """Upload a file to a Zenodo deposit."""
    filename = filepath.name
    print(f"  Uploading {filename} ({get_file_size_mb(filepath):.2f} MB)...")

    with open(filepath, "rb") as f:
        response = requests.put(
            f"{bucket_url}/{filename}",
            data=f,
            params={"access_token": token},
        )
    response.raise_for_status()
    return response.json()


def set_metadata(deposit_id: int, metadata: dict, token: str) -> dict:
    """Set metadata for a Zenodo deposit."""
    api_base = get_api_base()
    response = requests.put(
        f"{api_base}/deposit/depositions/{deposit_id}",
        params={"access_token": token},
        json={"metadata": metadata},
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def publish_deposit(deposit_id: int, token: str) -> dict:
    """Publish a Zenodo deposit (makes it public and assigns DOI)."""
    api_base = get_api_base()
    response = requests.post(
        f"{api_base}/deposit/depositions/{deposit_id}/actions/publish",
        params={"access_token": token},
    )
    response.raise_for_status()
    return response.json()


def create_readme(region_id: str, region_name: str, files_info: list) -> str:
    """Create README content for the Zenodo deposit."""
    file_list = "\n".join(
        f"  - {f['name']}: {f['description']} ({f['size_mb']:.2f} MB)"
        for f in files_info
    )

    return f"""OpenEnergyData - {region_name}
{'=' * (len(region_name) + 18)}

Pre-processed energy data for capacity expansion modeling.

Region: {region_name} ({region_id})
Generated: {datetime.now().strftime('%Y-%m-%d')}

Files:
{file_list}

Format: Apache Parquet (compressed columnar format)
- Read with: pandas.read_parquet() or pyarrow

Usage:
    import pandas as pd
    df = pd.read_parquet("power_plants.parquet")

Data Sources:
- Power Plants: Global Energy Monitor - Global Integrated Power
- Hydropower: African Hydropower Atlas, Global Hydropower Tracker
- Load Profiles: Toktarova et al. (2019)
- Resource Potential: IRENA Modelled Suitable Regions
- Socioeconomic: Our World in Data

License: CC-BY 4.0
Project: https://github.com/your-org/OpenEnergyData
"""


def upload_region(region_id: str, token: str, publish: bool = False) -> dict:
    """Upload all data for a region to Zenodo."""
    # Get region info
    regions = get_regions()
    region = next((r for r in regions if r["id"] == region_id), None)
    if not region:
        raise ValueError(f"Region '{region_id}' not found")

    region_name = region["name"]
    region_path = get_local_region_path(region_id)

    if not region_path.exists():
        raise ValueError(
            f"No preprocessed data found for region '{region_id}'.\n"
            f"Run: python scripts/preprocess_data.py --region {region_id}"
        )

    # Find all parquet files
    parquet_files = list(region_path.glob("*.parquet"))
    if not parquet_files:
        raise ValueError(f"No parquet files found in {region_path}")

    print(f"\nUploading data for: {region_name} ({region_id})")
    print(f"Found {len(parquet_files)} files to upload")

    # Create deposit
    print("\nCreating Zenodo deposit...")
    deposit = create_deposit(token)
    deposit_id = deposit["id"]
    bucket_url = deposit["links"]["bucket"]
    print(f"  Deposit ID: {deposit_id}")

    # Upload files and track info
    files_info = []
    dataset_descriptions = {
        "power_plants": "Power plant locations and capacities",
        "hydropower": "Hydropower plant data",
        "load_profiles": "Hourly electricity demand profiles",
        "re_profiles_solar": "Solar capacity factor profiles",
        "re_profiles_wind": "Wind capacity factor profiles",
        "resource_potential_solar": "Solar PV technical potential",
        "resource_potential_wind": "Wind technical potential",
    }

    print("\nUploading files...")
    for filepath in sorted(parquet_files):
        upload_file(deposit_id, bucket_url, filepath, token)
        stem = filepath.stem
        files_info.append({
            "name": filepath.name,
            "description": dataset_descriptions.get(stem, stem.replace("_", " ").title()),
            "size_mb": get_file_size_mb(filepath),
            "sha256": calculate_sha256(filepath),
        })

    # Create and upload README
    readme_content = create_readme(region_id, region_name, files_info)
    readme_path = region_path / "README.txt"
    readme_path.write_text(readme_content)
    upload_file(deposit_id, bucket_url, readme_path, token)

    # Create and upload metadata
    metadata_info = {
        "region_id": region_id,
        "region_name": region_name,
        "countries": region.get("countries", []),
        "generated_at": datetime.now().isoformat(),
        "files": files_info,
    }
    metadata_path = region_path / "zenodo_metadata.json"
    metadata_path.write_text(json.dumps(metadata_info, indent=2))
    upload_file(deposit_id, bucket_url, metadata_path, token)

    # Set Zenodo metadata
    print("\nSetting deposit metadata...")
    zenodo_metadata = {
        "title": f"OpenEnergyData - {region_name}",
        "upload_type": "dataset",
        "description": f"""
            <p>Pre-processed energy data for capacity expansion modeling in {region_name}.</p>
            <p>Includes power plant data, hydropower, load profiles, renewable energy profiles,
            and resource potential data in Apache Parquet format.</p>
            <p>Part of the OpenEnergyData project for World Bank energy modelers.</p>
        """,
        "creators": [{"name": "OpenEnergyData Contributors"}],
        "keywords": [
            "energy",
            "power plants",
            "capacity expansion",
            "renewable energy",
            region_name,
        ],
        "license": "cc-by-4.0",
        "access_right": "open",
        "communities": [{"identifier": "energy"}] if not os.getenv("ZENODO_SANDBOX") else [],
    }
    set_metadata(deposit_id, zenodo_metadata, token)

    # Publish if requested
    if publish:
        print("\nPublishing deposit...")
        result = publish_deposit(deposit_id, token)
        doi = result.get("doi")
        print(f"  Published! DOI: {doi}")
        print(f"  URL: https://doi.org/{doi}")

        # Save record info locally
        record_info = {
            "deposit_id": deposit_id,
            "doi": doi,
            "url": f"https://doi.org/{doi}",
            "published_at": datetime.now().isoformat(),
        }
        record_path = region_path / "zenodo_record.json"
        record_path.write_text(json.dumps(record_info, indent=2))

        return result
    else:
        api_base = get_api_base()
        edit_url = f"{api_base.replace('/api', '')}/deposit/{deposit_id}"
        print(f"\nDeposit created (not published)")
        print(f"  Edit URL: {edit_url}")
        print(f"  Run with --publish to make it public")

        return deposit


def main():
    parser = argparse.ArgumentParser(
        description="Upload preprocessed data to Zenodo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Upload a single region (draft mode)
    python scripts/zenodo/upload_to_zenodo.py --region south_africa

    # Upload and publish
    python scripts/zenodo/upload_to_zenodo.py --region south_africa --publish

    # Upload all regions
    python scripts/zenodo/upload_to_zenodo.py --all

    # Test with sandbox
    ZENODO_SANDBOX=true python scripts/zenodo/upload_to_zenodo.py --region south_africa
        """,
    )
    parser.add_argument("--region", help="Region ID to upload")
    parser.add_argument("--all", action="store_true", help="Upload all regions")
    parser.add_argument("--publish", action="store_true", help="Publish after upload")
    parser.add_argument("--list", action="store_true", help="List available regions")

    args = parser.parse_args()

    if args.list:
        regions = get_regions()
        print("Available regions:")
        for r in regions:
            print(f"  {r['id']}: {r['name']}")
        return

    if not args.region and not args.all:
        parser.error("Specify --region REGION_ID or --all")

    token = get_api_token()

    if args.all:
        regions = get_regions()
        for region in regions:
            try:
                upload_region(region["id"], token, publish=args.publish)
            except Exception as e:
                print(f"Error uploading {region['id']}: {e}")
    else:
        upload_region(args.region, token, publish=args.publish)


if __name__ == "__main__":
    main()
