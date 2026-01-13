"""Map visualization components using Folium.

Adapted from EPM pre-analysis generators_pipeline.py.
"""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

try:
    import folium
    from folium.plugins import MarkerCluster
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False


# Default technology icons for Font Awesome
DEFAULT_TECH_ICONS: Dict[str, str] = {
    "Hydro": "tint",
    "Solar": "sun",
    "Wind": "wind",
    "Thermal": "fire",
    "Gas": "gas-pump",
    "Coal": "industry",
    "Oil": "oil-can",
    "Nuclear": "atom",
    "Geothermal": "temperature-high",
    "Biomass": "leaf",
    "Unknown": "question",
}

# Default technology colors
DEFAULT_TECH_COLORS: Dict[str, str] = {
    "Hydro": "#1f77b4",
    "Solar": "#ff7f0e",
    "Wind": "#2ca02c",
    "Thermal": "#d62728",
    "Gas": "#9467bd",
    "Coal": "#8c564b",
    "Oil": "#e377c2",
    "Nuclear": "#7f7f7f",
    "Geothermal": "#bcbd22",
    "Biomass": "#17becf",
    "Unknown": "#aaaaaa",
}

# Status colors
DEFAULT_STATUS_COLORS: Dict[str, str] = {
    "Operating": "#2e7d32",
    "Construction": "#ff8f00",
    "Pre-Construction": "#1f77b4",
    "Announced": "#8e44ad",
    "Other": "#7f8c8d",
}


def create_power_plant_map(
    df: pd.DataFrame,
    center: Optional[tuple] = None,
    zoom_start: int = 5,
    use_clusters: bool = True,
    tech_colors: Optional[Dict[str, str]] = None,
    tile_layer: str = "CartoDB positron",
) -> "folium.Map":
    """Create an interactive Folium map of power plants.

    Args:
        df: DataFrame with columns: name, technology, capacity_mw, status, latitude, longitude
        center: Map center as (lat, lon). Auto-calculated if None.
        zoom_start: Initial zoom level
        use_clusters: Whether to use marker clustering
        tech_colors: Custom technology color mapping
        tile_layer: Tile layer name

    Returns:
        Folium Map object
    """
    if not HAS_FOLIUM:
        raise ImportError("Folium is required for map visualization. Install with: pip install folium")

    tech_colors = tech_colors or DEFAULT_TECH_COLORS

    # Filter to valid coordinates
    df_valid = df.dropna(subset=["latitude", "longitude"]).copy()

    if df_valid.empty:
        # Return empty map
        return folium.Map(location=[0, 0], zoom_start=2, tiles=tile_layer)

    # Auto-calculate center if not provided
    if center is None:
        center = (df_valid["latitude"].mean(), df_valid["longitude"].mean())

    # Create map
    m = folium.Map(location=center, zoom_start=zoom_start, tiles=tile_layer)

    # Add markers
    if use_clusters:
        marker_cluster = MarkerCluster().add_to(m)
        marker_parent = marker_cluster
    else:
        marker_parent = m

    for _, row in df_valid.iterrows():
        popup_html = _build_popup(row)
        tech = row.get("technology", "Unknown")
        color = tech_colors.get(tech, tech_colors.get("Unknown", "#aaaaaa"))
        icon = DEFAULT_TECH_ICONS.get(tech, "bolt")

        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row.get("name", "Power Plant"),
            icon=folium.Icon(color=_to_folium_color(color), icon=icon, prefix="fa"),
        ).add_to(marker_parent)

    # Add legend
    _add_legend(m, df_valid, tech_colors)

    return m


def _build_popup(row: pd.Series) -> str:
    """Build HTML popup content for a plant marker."""
    fields = [
        ("Name", row.get("name", "")),
        ("Technology", row.get("technology", "")),
        ("Capacity (MW)", f"{row.get('capacity_mw', 0):,.1f}" if pd.notna(row.get("capacity_mw")) else ""),
        ("Status", row.get("status", "")),
        ("Country", row.get("country", "")),
    ]
    lines = [f"<b>{label}:</b> {val}" for label, val in fields if val]
    return "<br>".join(lines)


def _to_folium_color(hex_color: str) -> str:
    """Convert hex color to nearest Folium color name."""
    # Folium has limited color options, map to closest
    color_map = {
        "#1f77b4": "blue",
        "#ff7f0e": "orange",
        "#2ca02c": "green",
        "#d62728": "red",
        "#9467bd": "purple",
        "#8c564b": "darkred",
        "#e377c2": "pink",
        "#7f7f7f": "gray",
        "#bcbd22": "beige",
        "#17becf": "lightblue",
        "#2e7d32": "darkgreen",
        "#ff8f00": "orange",
        "#8e44ad": "purple",
    }
    return color_map.get(hex_color, "blue")


def _add_legend(m: "folium.Map", df: pd.DataFrame, tech_colors: Dict[str, str]) -> None:
    """Add a legend to the map showing technology colors."""
    if "technology" not in df.columns:
        return

    techs = df["technology"].value_counts().head(10).index.tolist()

    legend_html = """
    <div style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        width: 150px;
        background-color: white;
        border: 2px solid grey;
        border-radius: 5px;
        padding: 10px;
        font-size: 12px;
        z-index: 1000;
    ">
    <b>Technology</b><br>
    """

    for tech in techs:
        color = tech_colors.get(tech, "#aaaaaa")
        legend_html += f'<i style="background:{color};width:12px;height:12px;display:inline-block;margin-right:5px;"></i>{tech}<br>'

    legend_html += "</div>"

    m.get_root().html.add_child(folium.Element(legend_html))


def create_region_map(
    bbox: list,
    countries: list,
    zoom_start: int = 5,
) -> "folium.Map":
    """Create a map showing a region boundary.

    Args:
        bbox: Bounding box as [min_lon, min_lat, max_lon, max_lat]
        countries: List of country names to highlight
        zoom_start: Initial zoom level

    Returns:
        Folium Map object
    """
    if not HAS_FOLIUM:
        raise ImportError("Folium is required. Install with: pip install folium")

    # Calculate center from bbox
    center_lat = (bbox[1] + bbox[3]) / 2
    center_lon = (bbox[0] + bbox[2]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, tiles="CartoDB positron")

    # Add rectangle for bbox
    folium.Rectangle(
        bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
        color="blue",
        weight=2,
        fill=True,
        fill_opacity=0.1,
    ).add_to(m)

    return m
