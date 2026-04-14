from __future__ import annotations

from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_csvs_to_polars(data_dir: str | Path = "data") -> dict[str, pl.DataFrame]:
    """Load all CSV files from a directory into Polars DataFrames.

    Returns a dictionary keyed by each file stem, for example
    "projects-2026-04-13" -> DataFrame.
    """
    base_path = Path(data_dir)
    if not base_path.is_absolute():
        base_path = PROJECT_ROOT / base_path
    if not base_path.exists():
        raise FileNotFoundError(f"Data directory not found: {base_path}")

    csv_files = sorted(base_path.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {base_path}")

    dataframes: dict[str, pl.DataFrame] = {}
    for csv_file in csv_files:
        dataframes[csv_file.stem] = pl.read_csv(csv_file, infer_schema=False, null_values=[""])

    return dataframes


def get_df_by_prefix(dataframes: dict[str, pl.DataFrame], prefix: str) -> pl.DataFrame:
    for name, df in dataframes.items():
        if name.startswith(prefix):
            return df
    raise KeyError(f"Dataset not found for prefix '{prefix}'")
