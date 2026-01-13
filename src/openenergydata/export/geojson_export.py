"""GeoJSON export functions for spatial data.

Exports power plants and grid data as GeoJSON for use in GIS applications.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

import pandas as pd


def export_plants_geojson(
    df: pd.DataFrame,
    output_path: Union[str, Path],
    properties: Optional[list] = None,
) -> Path:
    """Export power plant data to GeoJSON format.

    Args:
        df: DataFrame with latitude, longitude columns
        output_path: Output file path
        properties: Columns to include as feature properties (uses all if None)

    Returns:
        Path to the exported file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Filter to valid coordinates
    df_valid = df.dropna(subset=["latitude", "longitude"]).copy()

    if df_valid.empty:
        # Write empty FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": [],
        }
        with open(output_path, "w") as f:
            json.dump(geojson, f, indent=2)
        return output_path

    # Determine properties to include
    if properties is None:
        properties = [c for c in df_valid.columns if c not in ("latitude", "longitude")]

    features = []
    for _, row in df_valid.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
            "properties": {
                prop: _to_json_serializable(row.get(prop))
                for prop in properties
                if prop in row
            },
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(output_path, "w") as f:
        json.dump(geojson, f, indent=2)

    return output_path


def export_plants_geojson_string(
    df: pd.DataFrame,
    properties: Optional[list] = None,
) -> str:
    """Export power plant data to GeoJSON string.

    Args:
        df: DataFrame with latitude, longitude columns
        properties: Columns to include as feature properties

    Returns:
        GeoJSON string
    """
    df_valid = df.dropna(subset=["latitude", "longitude"]).copy()

    if df_valid.empty:
        return json.dumps({"type": "FeatureCollection", "features": []})

    if properties is None:
        properties = [c for c in df_valid.columns if c not in ("latitude", "longitude")]

    features = []
    for _, row in df_valid.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
            "properties": {
                prop: _to_json_serializable(row.get(prop))
                for prop in properties
                if prop in row
            },
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    return json.dumps(geojson)


def export_grid_geojson(
    nodes_df: pd.DataFrame,
    lines_df: pd.DataFrame,
    output_path: Union[str, Path],
) -> Path:
    """Export grid data (nodes and lines) to GeoJSON format.

    Args:
        nodes_df: DataFrame with node data (latitude, longitude)
        lines_df: DataFrame with line data (from_lat, from_lon, to_lat, to_lon)
        output_path: Output file path

    Returns:
        Path to the exported file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    features = []

    # Add node features (points)
    if nodes_df is not None and not nodes_df.empty:
        nodes_valid = nodes_df.dropna(subset=["latitude", "longitude"])
        for _, row in nodes_valid.iterrows():
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["longitude"]), float(row["latitude"])],
                },
                "properties": {
                    "feature_type": "node",
                    **{k: _to_json_serializable(v) for k, v in row.items()
                       if k not in ("latitude", "longitude")},
                },
            }
            features.append(feature)

    # Add line features (LineStrings)
    if lines_df is not None and not lines_df.empty:
        required_cols = ["from_lat", "from_lon", "to_lat", "to_lon"]
        if all(c in lines_df.columns for c in required_cols):
            lines_valid = lines_df.dropna(subset=required_cols)
            for _, row in lines_valid.iterrows():
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [float(row["from_lon"]), float(row["from_lat"])],
                            [float(row["to_lon"]), float(row["to_lat"])],
                        ],
                    },
                    "properties": {
                        "feature_type": "line",
                        **{k: _to_json_serializable(v) for k, v in row.items()
                           if k not in required_cols},
                    },
                }
                features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(output_path, "w") as f:
        json.dump(geojson, f, indent=2)

    return output_path


def _to_json_serializable(value):
    """Convert a value to a JSON-serializable type."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float, str, bool, type(None))):
        return value
    return str(value)
