"""Time-series utilities for data processing.

Adapted from EPM pre-analysis representative_days/utils.py.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

import pandas as pd

logger = logging.getLogger(__name__)

# Days in each month (non-leap year)
NB_DAYS = pd.Series([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], index=range(1, 13))

# Default season mapping (month -> season code)
DEFAULT_SEASONS_MAP = {
    1: "DJF", 2: "DJF",
    3: "MAM", 4: "MAM", 5: "MAM",
    6: "JJA", 7: "JJA", 8: "JJA",
    9: "SON", 10: "SON", 11: "SON",
    12: "DJF",
}


def validate_time_columns(
    df: pd.DataFrame,
    time_cols: Iterable[str] = ("month", "day", "hour"),
    name: str = "",
    verbose: bool = True,
) -> pd.DataFrame:
    """Ensure time columns are numeric integers and in plausible ranges.

    Args:
        df: DataFrame to validate
        time_cols: Column names to check
        name: Label for error messages
        verbose: Whether to print warnings

    Returns:
        Copy of DataFrame with integer time columns

    Raises:
        ValueError: If columns are missing or have invalid values
    """
    df_checked = df.copy()
    label = f"[{name}] " if name else ""

    for col in time_cols:
        if col not in df_checked.columns:
            raise ValueError(f"{label}Missing required column '{col}'")

        numeric = pd.to_numeric(df_checked[col], errors="coerce")
        non_numeric = df_checked[numeric.isna()]
        if not non_numeric.empty:
            raise ValueError(f"{label}Non-numeric values in '{col}' (showing first 5):\n{non_numeric.head()}")

        non_int = df_checked[(numeric % 1 != 0)]
        if not non_int.empty:
            raise ValueError(f"{label}Non-integer values in '{col}' (showing first 5):\n{non_int.head()}")

        df_checked[col] = numeric.astype(int)

    # Range checks
    if "month" in df_checked.columns:
        bad = df_checked[(df_checked["month"] < 1) | (df_checked["month"] > 12)]
        if not bad.empty:
            raise ValueError(f"{label}Month values out of range 1-12 (showing first 5):\n{bad.head()}")

    if "day" in df_checked.columns:
        bad = df_checked[(df_checked["day"] < 1) | (df_checked["day"] > 31)]
        if not bad.empty:
            raise ValueError(f"{label}Day values out of range 1-31 (showing first 5):\n{bad.head()}")

    if "hour" in df_checked.columns:
        bad = df_checked[(df_checked["hour"] < 0) | (df_checked["hour"] > 23)]
        if not bad.empty:
            raise ValueError(f"{label}Hour values out of range 0-23 (showing first 5):\n{bad.head()}")

    return df_checked


def month_to_season(
    data: pd.DataFrame,
    seasons_map: Optional[dict] = None,
    other_columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Convert month numbers to season identifiers and renumber days within each season.

    Args:
        data: DataFrame with month, day, hour columns
        seasons_map: Mapping of month (1-12) to season code (e.g., 'DJF', 'MAM')
        other_columns: Additional grouping columns (e.g., 'zone')

    Returns:
        DataFrame with season column instead of month, days renumbered within season
    """
    seasons_map = seasons_map or DEFAULT_SEASONS_MAP
    other_columns = other_columns or []

    df = data.copy()

    # Allow "season" column to be treated as "month" for compatibility
    if "season" in df.columns and "month" not in df.columns:
        df = df.rename(columns={"season": "month"})

    required_cols = {"month", "day", "hour"}
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Map months to seasons
    df["season"] = df["month"].map(seasons_map)
    if df["season"].isna().any():
        missing_months = df.loc[df["season"].isna(), "month"].unique()
        raise ValueError(f"Months {missing_months} not found in seasons_map")

    # Remove Feb 29 if present
    df = df[~((df["month"] == 2) & (df["day"] == 29))]

    # Renumber days sequentially within each season (1, 2, 3, ...) based on 24-hour blocks
    group_cols = other_columns + ["season"]
    df["season_day"] = df.groupby(group_cols).cumcount() // 24 + 1

    # Clean up columns
    df = df.drop(columns=["day"]).rename(columns={"season_day": "day"})
    df = df.drop(columns=["month"])

    # Reorder and sort
    output_cols = other_columns + ["season", "day", "hour"] + [
        c for c in df.columns if c not in other_columns + ["season", "day", "hour"]
    ]
    df = df[output_cols].sort_values(by=other_columns + ["season", "day", "hour"])

    return df.reset_index(drop=True)


def drop_feb29(
    df: pd.DataFrame,
    name: str = "",
    verbose: bool = True,
) -> pd.DataFrame:
    """Remove Feb 29 entries if present.

    Args:
        df: DataFrame with month and day columns
        name: Label for messages
        verbose: Whether to print info about dropped rows

    Returns:
        DataFrame with Feb 29 entries removed
    """
    if {"month", "day"}.issubset(df.columns):
        mask = (df["month"] == 2) & (df["day"] == 29)
        if mask.any():
            count = int(mask.sum())
            if verbose:
                zones = df.loc[mask, "zone"].unique() if "zone" in df.columns else None
                zone_msg = f" for zones {', '.join(map(str, zones))}" if zones is not None else ""
                label = f"[{name}] " if name else ""
                print(f"{label}Dropping {count} Feb 29 entries{zone_msg}.")
            df = df.loc[~mask].copy()
    return df


def normalize_series(
    df: pd.DataFrame,
    value_col: str,
    name: str = "",
    verbose: bool = True,
) -> pd.DataFrame:
    """Normalize a value column to [0, 1] if not already normalized.

    Args:
        df: DataFrame to normalize
        value_col: Column name to normalize
        name: Label for messages
        verbose: Whether to print info about scaling

    Returns:
        DataFrame with normalized values
    """
    df_checked = df.copy()
    label = f"[{name}] " if name else ""

    max_val = df_checked[value_col].max(skipna=True)
    min_val = df_checked[value_col].min(skipna=True)

    if pd.isna(max_val) or max_val == 0:
        if verbose:
            print(f"{label}Cannot normalize '{value_col}' because max is 0 or NaN.")
        return df_checked

    if max_val <= 1 and min_val >= 0:
        # Already normalized
        return df_checked

    if verbose:
        print(f"{label}Normalizing '{value_col}' to [0,1] (max={max_val:.4g}).")

    df_checked[value_col] = df_checked[value_col] / max_val
    return df_checked


def check_complete_year(
    df: pd.DataFrame,
    name: str = "",
    verbose: bool = True,
    raise_on_missing: bool = False,
) -> bool:
    """Check if a DataFrame contains a complete year of hourly data.

    Args:
        df: DataFrame with zone, month, day, hour columns
        name: Label for messages
        verbose: Whether to print warnings
        raise_on_missing: Whether to raise an error if incomplete

    Returns:
        True if complete, False otherwise
    """
    required = {"zone", "month", "day", "hour"}
    if not required.issubset(df.columns):
        return True  # Can't check without required columns

    label = f"[{name}] " if name else ""
    expected_hours = set(range(24))
    is_complete = True

    for zone, g_zone in df.groupby("zone"):
        missing = []
        for month in range(1, 13):
            days_in_month = int(NB_DAYS.get(month, 0))
            g_month = g_zone[g_zone["month"] == month]

            if g_month.empty:
                for day in range(1, days_in_month + 1):
                    missing.extend((month, day, h) for h in expected_hours)
                continue

            for day in range(1, days_in_month + 1):
                g_day = g_month[g_month["day"] == day]
                if g_day.empty:
                    missing.extend((month, day, h) for h in expected_hours)
                    continue
                hours = set(g_day["hour"])
                if hours != expected_hours:
                    missing.extend((month, day, h) for h in sorted(expected_hours - hours))

        if missing:
            is_complete = False
            sample = missing[:6]
            formatted = "; ".join(f"m{m} d{d} h{h}" for m, d, h in sample)
            extra = "" if len(missing) <= len(sample) else f" ... (+{len(missing) - len(sample)} more)"
            message = f"{label}Incomplete year for zone {zone}: missing {len(missing)} entries: {formatted}{extra}"

            if raise_on_missing:
                raise ValueError(message + " Please clean the input data.")
            if verbose:
                print(message)

    return is_complete


def load_and_clean_timeseries(
    input_path: Union[str, Path],
    zones_to_exclude: Optional[List[str]] = None,
    value_column: str = "value",
    rename_value_to: Optional[Union[int, str]] = None,
    normalize: bool = True,
    drop_feb_29: bool = True,
    check_complete_year_flag: bool = False,
    verbose: bool = True,
    require_zone: bool = True,
) -> Tuple[pd.DataFrame, Union[str, int]]:
    """Load and standardize a raw month/day/hour time-series CSV.

    Args:
        input_path: Path to CSV file
        zones_to_exclude: List of zones to remove
        value_column: Name of value column (or will auto-detect)
        rename_value_to: New name for value column
        normalize: Whether to normalize values to [0, 1]
        drop_feb_29: Whether to remove Feb 29 entries
        check_complete_year_flag: Whether to check for complete year
        verbose: Whether to print progress messages
        require_zone: Whether zone column is required

    Returns:
        Tuple of (cleaned DataFrame, value column name)
    """
    zones_to_exclude = zones_to_exclude or []
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)

    # Handle season vs month naming
    if "month" not in df.columns and "season" in df.columns:
        df = df.rename(columns={"season": "month"})

    df = validate_time_columns(df, time_cols=("month", "day", "hour"), name=str(input_path), verbose=False)

    required_columns = {"month", "day", "hour"}
    if require_zone:
        required_columns.add("zone")

    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {input_path}: {missing}")

    # Detect value column
    candidate_value_cols = [c for c in df.columns if c not in required_columns]
    if value_column in df.columns:
        value_col = value_column
    elif len(candidate_value_cols) == 1:
        value_col = candidate_value_cols[0]
    else:
        # Heuristic: if columns look like years, pick the latest one
        year_like = []
        for col in candidate_value_cols:
            try:
                year_like.append(int(col))
            except (ValueError, TypeError):
                year_like.append(None)

        if any(y is not None for y in year_like):
            max_year = max(y for y in year_like if y is not None)
            value_col = candidate_value_cols[year_like.index(max_year)]
        else:
            value_col = candidate_value_cols[0] if candidate_value_cols else "value"

    if rename_value_to is not None:
        df = df.rename(columns={value_col: rename_value_to})
        value_col = rename_value_to

    # Filter zones
    if "zone" in df.columns and zones_to_exclude:
        df = df[~df["zone"].isin(zones_to_exclude)]

    # Fix hour indexing (1-24 -> 0-23)
    if df["hour"].min() == 1 and df["hour"].max() <= 24:
        df["hour"] = df["hour"] - 1

    if drop_feb_29:
        df = drop_feb29(df, name=str(input_path), verbose=verbose)

    if normalize:
        df = normalize_series(df, value_col=value_col, name=str(input_path), verbose=verbose)

    if check_complete_year_flag:
        check_complete_year(df, name=str(input_path), verbose=verbose)

    return df, value_col
