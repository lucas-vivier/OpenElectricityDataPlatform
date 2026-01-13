"""Representative days computation using K-means clustering.

Adapted from EPM pre-analysis representative_days/representativedays_pipeline.py.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from .timeseries_utils import (
    validate_time_columns,
    drop_feb29,
    normalize_series,
    DEFAULT_SEASONS_MAP,
)


def compute_representative_days(
    load_profiles: pd.DataFrame,
    re_profiles: Optional[pd.DataFrame] = None,
    n_days: int = 12,
    n_clusters: int = 20,
    method: str = "kmeans",
    random_state: int = 42,
    seasons_map: Optional[Dict[int, str]] = None,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], pd.DataFrame]:
    """Compute representative days using clustering.

    This function reduces a full year of hourly data to a smaller set of
    representative days with associated weights.

    Args:
        load_profiles: DataFrame with zone, month, day, hour, value columns
        re_profiles: Optional DataFrame with renewable profiles (same format)
        n_days: Number of representative days to select (must be <= n_clusters)
        n_clusters: Number of clusters for initial grouping
        method: Clustering method ('kmeans' only for now)
        random_state: Random seed for reproducibility
        seasons_map: Month to season mapping (uses default if None)
        verbose: Whether to print progress

    Returns:
        Tuple of (rep_load_profiles, rep_re_profiles, weights_df)
        - rep_load_profiles: Representative load profiles
        - rep_re_profiles: Representative RE profiles (or None)
        - weights_df: DataFrame with day weights (sum to 365)
    """
    if method != "kmeans":
        raise NotImplementedError(f"Method '{method}' not implemented. Use 'kmeans'.")

    if n_days > n_clusters:
        n_clusters = n_days
        if verbose:
            print(f"Adjusted n_clusters to {n_clusters} to match n_days")

    seasons_map = seasons_map or DEFAULT_SEASONS_MAP

    # Validate and prepare load profiles
    load_df = _prepare_profiles(load_profiles, "load", verbose)

    # Optionally prepare RE profiles
    re_df = None
    if re_profiles is not None and not re_profiles.empty:
        re_df = _prepare_profiles(re_profiles, "re", verbose)

    # Build feature matrix for clustering
    features, day_index = _build_feature_matrix(load_df, re_df, verbose)

    if verbose:
        print(f"Clustering {len(day_index)} days into {n_clusters} clusters...")

    # Perform K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    cluster_labels = kmeans.fit_predict(features)

    # Select representative days (closest to cluster centers)
    rep_day_indices, weights = _select_representative_days(
        features, cluster_labels, kmeans.cluster_centers_, n_days
    )

    if verbose:
        print(f"Selected {len(rep_day_indices)} representative days")
        print(f"Weights sum: {weights.sum():.1f} (should be ~365)")

    # Extract representative day profiles
    rep_days = [day_index[i] for i in rep_day_indices]
    rep_load = _extract_representative_profiles(load_df, rep_days, weights)

    rep_re = None
    if re_df is not None:
        rep_re = _extract_representative_profiles(re_df, rep_days, weights)

    # Build weights DataFrame
    weights_df = pd.DataFrame({
        "rep_day": range(1, len(rep_days) + 1),
        "original_month": [d[0] for d in rep_days],
        "original_day": [d[1] for d in rep_days],
        "weight": weights,
    })

    return rep_load, rep_re, weights_df


def _prepare_profiles(
    df: pd.DataFrame,
    name: str,
    verbose: bool,
) -> pd.DataFrame:
    """Validate and prepare profile DataFrame."""
    df = df.copy()

    # Validate time columns
    df = validate_time_columns(df, time_cols=("month", "day", "hour"), name=name, verbose=verbose)

    # Drop Feb 29
    df = drop_feb29(df, name=name, verbose=verbose)

    # Detect value column
    value_cols = [c for c in df.columns if c not in ("zone", "month", "day", "hour")]
    if not value_cols:
        raise ValueError(f"No value column found in {name} profiles")

    value_col = value_cols[0]

    # Normalize
    df = normalize_series(df, value_col=value_col, name=name, verbose=verbose)

    # Rename value column for consistency
    if value_col != "value":
        df = df.rename(columns={value_col: "value"})

    return df


def _build_feature_matrix(
    load_df: pd.DataFrame,
    re_df: Optional[pd.DataFrame],
    verbose: bool,
) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
    """Build feature matrix for clustering (one row per day).

    Features are the 24 hourly values for each zone, concatenated.

    Returns:
        Tuple of (feature_matrix, day_index)
        - feature_matrix: numpy array of shape (n_days, n_features)
        - day_index: list of (month, day) tuples
    """
    zones = load_df["zone"].unique()

    # Get unique days
    days = load_df.groupby(["month", "day"]).size().reset_index()[["month", "day"]]
    day_index = [(row["month"], row["day"]) for _, row in days.iterrows()]

    features_list = []

    for month, day in day_index:
        day_features = []

        # Load features
        for zone in zones:
            mask = (load_df["zone"] == zone) & (load_df["month"] == month) & (load_df["day"] == day)
            hourly = load_df.loc[mask].sort_values("hour")["value"].values

            if len(hourly) != 24:
                # Pad or truncate to 24 hours
                hourly = np.pad(hourly, (0, max(0, 24 - len(hourly))), mode="edge")[:24]

            day_features.extend(hourly)

        # RE features (if provided)
        if re_df is not None:
            for zone in re_df["zone"].unique():
                mask = (re_df["zone"] == zone) & (re_df["month"] == month) & (re_df["day"] == day)
                hourly = re_df.loc[mask].sort_values("hour")["value"].values

                if len(hourly) != 24:
                    hourly = np.pad(hourly, (0, max(0, 24 - len(hourly))), mode="edge")[:24]

                day_features.extend(hourly)

        features_list.append(day_features)

    features = np.array(features_list)

    if verbose:
        print(f"Built feature matrix: {features.shape[0]} days x {features.shape[1]} features")

    return features, day_index


def _select_representative_days(
    features: np.ndarray,
    labels: np.ndarray,
    centers: np.ndarray,
    n_days: int,
) -> Tuple[List[int], np.ndarray]:
    """Select representative days closest to cluster centers.

    Args:
        features: Feature matrix
        labels: Cluster labels for each day
        centers: Cluster centers
        n_days: Number of representative days to select

    Returns:
        Tuple of (rep_day_indices, weights)
    """
    n_clusters = len(centers)

    # Find the day closest to each cluster center
    cluster_reps = {}
    cluster_sizes = {}

    for cluster_id in range(n_clusters):
        mask = labels == cluster_id
        cluster_indices = np.where(mask)[0]
        cluster_sizes[cluster_id] = len(cluster_indices)

        if len(cluster_indices) == 0:
            continue

        # Find closest day to center
        cluster_features = features[mask]
        distances = np.linalg.norm(cluster_features - centers[cluster_id], axis=1)
        closest_idx = cluster_indices[np.argmin(distances)]
        cluster_reps[cluster_id] = closest_idx

    # Select top n_days clusters by size
    sorted_clusters = sorted(cluster_sizes.keys(), key=lambda x: cluster_sizes[x], reverse=True)
    selected_clusters = sorted_clusters[:n_days]

    rep_day_indices = [cluster_reps[c] for c in selected_clusters if c in cluster_reps]

    # Calculate weights (proportional to cluster size)
    total_days = len(features)
    weights = np.array([cluster_sizes[c] * total_days / sum(cluster_sizes[c] for c in selected_clusters)
                        for c in selected_clusters if c in cluster_reps])

    # Normalize weights to sum to 365
    weights = weights * 365 / weights.sum()

    return rep_day_indices, weights


def _extract_representative_profiles(
    df: pd.DataFrame,
    rep_days: List[Tuple[int, int]],
    weights: np.ndarray,
) -> pd.DataFrame:
    """Extract profiles for representative days.

    Args:
        df: Full profile DataFrame
        rep_days: List of (month, day) tuples for representative days
        weights: Weight for each representative day

    Returns:
        DataFrame with representative day profiles, with 'rep_day' column
    """
    profiles = []

    for i, (month, day) in enumerate(rep_days):
        mask = (df["month"] == month) & (df["day"] == day)
        day_profile = df.loc[mask].copy()
        day_profile["rep_day"] = i + 1
        day_profile["weight"] = weights[i]
        profiles.append(day_profile)

    result = pd.concat(profiles, ignore_index=True)

    # Reorder columns
    cols = ["zone", "rep_day", "hour", "value", "weight"]
    cols = [c for c in cols if c in result.columns]
    other_cols = [c for c in result.columns if c not in cols]
    result = result[cols + other_cols]

    return result
