# %%
from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)

from src.loading import get_df_by_prefix, load_csvs_to_polars
from src.cleaning import prepare_lands, prepare_projects, prepare_rents, prepare_transactions
from src.aggregation import (
    aggregate_rents,
    aggregate_sales,
    combine_sales_rents,
    enrich_rents,
    enrich_transactions,
    make_project_dimension,
)

data_dir = "data"
# %%
dataframes = load_csvs_to_polars(data_dir)

projects = prepare_projects(get_df_by_prefix(dataframes, "projects-"))
lands = prepare_lands(get_df_by_prefix(dataframes, "lands-"))
transactions = prepare_transactions(get_df_by_prefix(dataframes, "transactions-"))
rents = prepare_rents(get_df_by_prefix(dataframes, "rents-"))
# %%
project_land_dim = make_project_dimension(projects, lands)
transactions_enriched = enrich_transactions(transactions, project_land_dim)
rents_enriched = enrich_rents(rents, project_land_dim)

seg_property_cols = ["PROP_TYPE_EN"]
seg_developer_cols = ["DEVELOPER_EN"]
seg_land_cols = ["LAND_TYPE_EN"]

performance_by_property = combine_sales_rents(
    aggregate_sales(transactions_enriched, seg_property_cols),
    aggregate_rents(rents_enriched, seg_property_cols),
    seg_property_cols,
)
performance_by_developer = combine_sales_rents(
    aggregate_sales(transactions_enriched, seg_developer_cols),
    aggregate_rents(rents_enriched, seg_developer_cols),
    seg_developer_cols,
)
performance_by_land = combine_sales_rents(
    aggregate_sales(transactions_enriched, seg_land_cols),
    aggregate_rents(rents_enriched, seg_land_cols),
    seg_land_cols,
)

outputs = {
    "transactions_enriched": transactions_enriched,
    "rents_enriched": rents_enriched,
    "performance_by_property_type": performance_by_property,
    "performance_by_developer": performance_by_developer,
    "performance_by_land_type": performance_by_land,
}

output_path = Path(output_dir)
output_path.mkdir(parents=True, exist_ok=True)
for name, df in outputs.items():
    df.write_csv(output_path / f"{name}.csv")


