from __future__ import annotations

import logging
from dataclasses import dataclass

import polars as pl

from src.aggregation import (
    aggregate_mortgage_transactions,
    enrich_rents,
    enrich_transactions,
    make_project_dimension,
)
from src.cleaning import (
    make_mortgage_reporting_view,
    make_rent_reporting_view,
    make_sales_reporting_view,
    prepare_lands,
    prepare_projects,
    prepare_rents,
    prepare_transactions,
)
from src.escape_csv_newlines import preprocess_raw_csvs
from src.loading import get_df_by_prefix, load_csvs_to_polars

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    projects: pl.DataFrame
    lands: pl.DataFrame
    transactions: pl.DataFrame
    mortgages: pl.DataFrame
    rents: pl.DataFrame


_state: AppState | None = None


def load_state(data_dir: str = "data", preprocess_raw: bool = False) -> AppState:
    global _state
    if preprocess_raw:
        preprocess_raw_csvs()
    dfs = load_csvs_to_polars(data_dir)
    projects = prepare_projects(get_df_by_prefix(dfs, "projects-"))
    lands = prepare_lands(get_df_by_prefix(dfs, "lands-"))
    transactions_base = prepare_transactions(get_df_by_prefix(dfs, "transactions-"))
    rents_base = prepare_rents(get_df_by_prefix(dfs, "rents-"))
    dim = make_project_dimension(projects, lands)
    transactions_base = enrich_transactions(transactions_base, dim)
    rents_base = enrich_rents(rents_base, dim)

    transactions = make_sales_reporting_view(transactions_base)
    mortgages = aggregate_mortgage_transactions(make_mortgage_reporting_view(transactions_base))
    rents = make_rent_reporting_view(rents_base)

    _state = AppState(
        projects=projects,
        lands=lands,
        transactions=transactions,
        mortgages=mortgages,
        rents=rents,
    )
    logger.info(
        "Data loaded: %d projects, %d sales, %d mortgage tx, %d rents",
        projects.height,
        transactions.height,
        mortgages.height,
        rents.height,
    )
    return _state


def get_state() -> AppState:
    if _state is None:
        raise RuntimeError("App state not initialised. Call load_state() at startup.")
    return _state
