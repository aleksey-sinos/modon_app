from __future__ import annotations

import polars as pl

from src.cleaning import drop_join_suffix_columns


def make_project_dimension(projects: pl.DataFrame, lands: pl.DataFrame) -> pl.DataFrame:
    project_dim = projects.select(
        [
            "PROJECT_NUMBER",
            "PROJECT_EN",
            "PROJECT_EN_KEY",
            "DEVELOPER_NUMBER",
            "DEVELOPER_EN",
            "AREA_EN",
            "ZONE_EN",
            "MASTER_PROJECT_EN",
            "MASTER_PROJECT_EN_KEY",
        ]
    )

    land_dim = lands.select(
        [
            "PROJECT_NUMBER",
            "PROJECT_EN",
            "PROJECT_EN_KEY",
            "LAND_TYPE_EN",
            "PROP_SUB_TYPE_EN",
            "AREA_EN",
            "ZONE_EN",
            "MASTER_PROJECT_EN",
            "MASTER_PROJECT_EN_KEY",
        ]
    )

    return drop_join_suffix_columns(
        project_dim.join(land_dim, on=["PROJECT_NUMBER", "PROJECT_EN_KEY"], how="left")
    )


def build_lookup_by_key(project_land_dim: pl.DataFrame, key_col: str) -> pl.DataFrame:
    return (
        project_land_dim.filter(pl.col(key_col).is_not_null())
        .group_by(key_col)
        .agg(
            [
                pl.col("DEVELOPER_NUMBER").drop_nulls().first().alias("DEVELOPER_NUMBER"),
                pl.col("DEVELOPER_EN").drop_nulls().first().alias("DEVELOPER_EN"),
                pl.col("LAND_TYPE_EN").drop_nulls().first().alias("LAND_TYPE_EN"),
                pl.col("PROP_SUB_TYPE_EN").drop_nulls().first().alias("PROP_SUB_TYPE_EN"),
                pl.col("PROJECT_NUMBER").drop_nulls().first().alias("PROJECT_NUMBER"),
            ]
        )
    )


def _apply_fallback_enrichment(
    df: pl.DataFrame,
    by_project: pl.DataFrame,
    by_master: pl.DataFrame,
) -> pl.DataFrame:
    return (
        df.join(by_project, on="PROJECT_EN_KEY", how="left")
        .pipe(drop_join_suffix_columns)
        .join(by_master, on="MASTER_PROJECT_EN_KEY", how="left", suffix="_master")
        .pipe(drop_join_suffix_columns)
        .with_columns(
            [
                pl.coalesce([pl.col("DEVELOPER_NUMBER"), pl.col("DEVELOPER_NUMBER_master")]).alias(
                    "DEVELOPER_NUMBER"
                ),
                pl.coalesce([pl.col("DEVELOPER_EN"), pl.col("DEVELOPER_EN_master")]).alias("DEVELOPER_EN"),
                pl.coalesce([pl.col("LAND_TYPE_EN"), pl.col("LAND_TYPE_EN_master")]).alias("LAND_TYPE_EN"),
                pl.coalesce([pl.col("PROP_SUB_TYPE_EN"), pl.col("PROP_SUB_TYPE_EN_master")]).alias(
                    "PROP_SUB_TYPE_EN"
                ),
                pl.coalesce([pl.col("PROJECT_NUMBER"), pl.col("PROJECT_NUMBER_master")]).alias(
                    "PROJECT_NUMBER"
                ),
            ]
        )
        .drop(
            [
                "DEVELOPER_NUMBER_master",
                "DEVELOPER_EN_master",
                "LAND_TYPE_EN_master",
                "PROP_SUB_TYPE_EN_master",
                "PROJECT_NUMBER_master",
            ]
        )
    )


def enrich_transactions(transactions: pl.DataFrame, project_land_dim: pl.DataFrame) -> pl.DataFrame:
    by_project = build_lookup_by_key(project_land_dim, "PROJECT_EN_KEY")
    by_master = build_lookup_by_key(project_land_dim, "MASTER_PROJECT_EN_KEY")
    return _apply_fallback_enrichment(transactions, by_project, by_master)


def enrich_rents(rents: pl.DataFrame, project_land_dim: pl.DataFrame) -> pl.DataFrame:
    by_project = build_lookup_by_key(project_land_dim, "PROJECT_EN_KEY")
    by_master = build_lookup_by_key(project_land_dim, "MASTER_PROJECT_EN_KEY")
    return _apply_fallback_enrichment(rents, by_project, by_master)


def aggregate_mortgage_transactions(transactions: pl.DataFrame) -> pl.DataFrame:
    return (
        transactions.filter(pl.col("TRANSACTION_NUMBER").is_not_null())
        .group_by("TRANSACTION_NUMBER")
        .agg(
            [
                pl.col("INSTANCE_DATE").drop_nulls().first().alias("INSTANCE_DATE"),
                pl.col("MONTH").drop_nulls().first().alias("MONTH"),
                pl.col("GROUP_EN").drop_nulls().first().alias("GROUP_EN"),
                pl.col("PROCEDURE_EN").drop_nulls().first().alias("PROCEDURE_EN"),
                pl.col("TRANS_VALUE").sum().alias("MORTGAGE_VALUE"),
                pl.len().alias("ROW_COUNT"),
                pl.col("AREA_EN").drop_nulls().first().alias("AREA_EN"),
                pl.col("PROP_TYPE_EN").drop_nulls().first().alias("PROP_TYPE_EN"),
                pl.col("IS_OFFPLAN_EN").drop_nulls().first().alias("IS_OFFPLAN_EN"),
            ]
        )
    )


def aggregate_sales(transactions_enriched: pl.DataFrame, group_cols: list[str]) -> pl.DataFrame:
    return (
        transactions_enriched.group_by(group_cols)
        .agg(
            [
                pl.len().alias("sales_count"),
                pl.col("TRANS_VALUE").sum().alias("sales_value"),
                pl.col("PRICE_PER_SQM").median().alias("median_price_per_sqm"),
                pl.col("PRICE_PER_SQM").mean().alias("avg_price_per_sqm"),
            ]
        )
        .sort(group_cols)
    )


def aggregate_rents(rents_enriched: pl.DataFrame, group_cols: list[str]) -> pl.DataFrame:
    return (
        rents_enriched.group_by(group_cols)
        .agg(
            [
                pl.len().alias("rent_count"),
                pl.col("ANNUAL_AMOUNT").sum().alias("annual_rent_value"),
                pl.col("RENT_PER_SQM").median().alias("median_rent_per_sqm"),
                pl.col("RENT_PER_SQM").mean().alias("avg_rent_per_sqm"),
            ]
        )
        .sort(group_cols)
    )


def combine_sales_rents(sales: pl.DataFrame, rents: pl.DataFrame, join_cols: list[str]) -> pl.DataFrame:
    return (
        drop_join_suffix_columns(sales.join(rents, on=join_cols, how="full"))
        .with_columns(
            [
                (pl.col("median_rent_per_sqm") / pl.col("median_price_per_sqm")).alias(
                    "gross_rental_yield"
                ),
                (pl.col("sales_count").fill_null(0) + pl.col("rent_count").fill_null(0)).alias(
                    "liquidity_score"
                ),
            ]
        )
        .sort(join_cols)
    )
