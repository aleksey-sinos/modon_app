from __future__ import annotations

import logging
import re
from typing import Iterable

import polars as pl

logger = logging.getLogger(__name__)

RENT_AREA_REPORTING_MIN_SQM = 15.0
RENT_AREA_REPORTING_MAX_SQM = 10_000.0
RENT_RATE_MAX_AED_PER_SQM = 10_000.0


def _log_null_stats(df: pl.DataFrame, columns: list[str], stage: str) -> None:
    total = df.height
    for col in columns:
        if col not in df.columns:
            continue
        null_count = df[col].null_count()
        if null_count:
            pct = null_count / total * 100
            logger.warning("%s | %s: %d nulls / %d rows (%.1f%%)", stage, col, null_count, total, pct)
        else:
            logger.info("%s | %s: no nulls", stage, col)


def _log_conversion_failures(
    df_before: pl.DataFrame, df_after: pl.DataFrame, columns: list[str], stage: str
) -> None:
    total = df_before.height
    for col in columns:
        if col not in df_before.columns or col not in df_after.columns:
            continue
        orig_nulls = df_before[col].null_count()
        new_nulls = df_after[col].null_count()
        failed = new_nulls - orig_nulls
        if failed > 0:
            pct = failed / total * 100
            logger.warning(
                "%s | %s: %d values failed conversion (%.1f%% of rows)", stage, col, failed, pct
            )
        else:
            logger.info("%s | %s: all non-null values converted successfully", stage, col)


def cast_date_columns(df: pl.DataFrame, columns: Iterable[str], stage: str = "") -> pl.DataFrame:
    existing = [c for c in columns if c in df.columns]
    if not existing:
        return df
    df = df.with_columns([pl.col(c).replace("", None).alias(c) for c in existing])
    result = df.with_columns(
        [
            pl.coalesce(
                [
                    pl.col(c)
                    .str.strptime(pl.Datetime, format="%Y-%m-%d %H:%M:%S", strict=False)
                    .dt.date(),
                    pl.col(c).str.strptime(pl.Date, format="%Y-%m-%d", strict=False),
                ]
            ).alias(c)
            for c in existing
        ]
    )
    _log_conversion_failures(df, result, existing, stage or "cast_date_columns")
    return result


def cast_numeric_columns(df: pl.DataFrame, columns: Iterable[str], stage: str = "") -> pl.DataFrame:
    existing = [c for c in columns if c in df.columns]
    if not existing:
        return df
    df = df.with_columns([pl.col(c).replace("", None).alias(c) for c in existing])
    result = df.with_columns(
        [pl.col(c).cast(pl.Float64, strict=False).alias(c) for c in existing]
    )
    _log_conversion_failures(df, result, existing, stage or "cast_numeric_columns")
    return result


def normalize_text_keys(df: pl.DataFrame, columns: Iterable[str]) -> pl.DataFrame:
    existing = [c for c in columns if c in df.columns]
    if not existing:
        return df
    return df.with_columns(
        [
            pl.col(c).cast(pl.Utf8, strict=False).str.strip_chars().replace("", None).alias(c)
            for c in existing
        ]
    )


def normalize_developer_names(df: pl.DataFrame, columns: Iterable[str]) -> pl.DataFrame:
    existing = [c for c in columns if c in df.columns]
    if not existing:
        return df
    return df.with_columns(
        [
            pl.when(pl.col(c).is_not_null())
            .then(pl.col(c).map_elements(_to_capital_case_name, return_dtype=pl.Utf8))
            .otherwise(None)
            .alias(c)
            for c in existing
        ]
    )


def _to_capital_case_name(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    words = [word for word in re.split(r"\s+", text) if word]
    collapsed_words = _collapse_initial_runs(words)
    normalized_words = [_normalize_name_word(word) for word in collapsed_words]
    return " ".join(normalized_words)


def _collapse_initial_runs(words: list[str]) -> list[str]:
    collapsed: list[str] = []
    run: list[str] = []

    def flush_run() -> None:
        nonlocal run
        if not run:
            return
        if len(run) > 1:
            collapsed.append("".join(run))
        else:
            collapsed.extend(run)
        run = []

    for word in words:
        if len(word) == 1 and word.isalpha() and word.isupper():
            run.append(word)
            continue
        flush_run()
        collapsed.append(word)

    flush_run()
    return collapsed


def _normalize_name_word(word: str) -> str:
    slash_parts = word.split("/")
    return "/".join(_normalize_name_token(part) for part in slash_parts)


def _normalize_name_token(token: str) -> str:
    if not token:
        return token
    abbreviation_key = token.replace(".", "").upper()
    if abbreviation_key in {"LLC", "FZE", "SPV", "DWC", "PJSC", "PLC", "INC", "LTD", "LLP", "AMIS", "ADE"}:
        return token
    if "." in token:
        parts = token.split(".")
        normalized = [_normalize_name_token(part) if part else "" for part in parts]
        return ".".join(normalized)

    pieces = re.split(r"([-'])", token)
    normalized_pieces: list[str] = []
    for piece in pieces:
        if piece in {"-", "'"}:
            normalized_pieces.append(piece)
            continue
        if not piece:
            normalized_pieces.append(piece)
            continue
        if piece.isnumeric():
            normalized_pieces.append(piece)
            continue
        normalized_pieces.append(piece[:1].upper() + piece[1:].lower())
    return "".join(normalized_pieces)


def add_join_keys(df: pl.DataFrame) -> pl.DataFrame:
    exprs: list[pl.Expr] = []
    if "PROJECT_EN" in df.columns:
        exprs.append(pl.col("PROJECT_EN").str.to_lowercase().alias("PROJECT_EN_KEY"))
    if "MASTER_PROJECT_EN" in df.columns:
        exprs.append(pl.col("MASTER_PROJECT_EN").str.to_lowercase().alias("MASTER_PROJECT_EN_KEY"))
    if not exprs:
        return df
    return df.with_columns(exprs)


def drop_join_suffix_columns(df: pl.DataFrame, suffix: str = "_right") -> pl.DataFrame:
    columns_to_drop = [c for c in df.columns if c.endswith(suffix)]
    if not columns_to_drop:
        return df
    return df.drop(columns_to_drop)


def prepare_projects(projects: pl.DataFrame) -> pl.DataFrame:
    stage = "projects"
    logger.info("%s: starting cleaning (%d rows)", stage, projects.height)
    projects = normalize_text_keys(
        projects,
        ["PROJECT_NUMBER", "PROJECT_EN", "DEVELOPER_NUMBER", "DEVELOPER_EN", "MASTER_PROJECT_EN"],
    )
    projects = normalize_developer_names(projects, ["DEVELOPER_EN"])
    projects = cast_date_columns(
        projects,
        ["START_DATE", "END_DATE", "ADOPTION_DATE", "INSPECTION_DATE", "COMPLETION_DATE"],
        stage=stage,
    )
    projects = cast_numeric_columns(
        projects,
        ["PROJECT_VALUE", "PERCENT_COMPLETED", "CNT_LAND", "CNT_BUILDING", "CNT_VILLA", "CNT_UNIT"],
        stage=stage,
    )
    _log_null_stats(
        projects,
        ["PROJECT_NUMBER", "PROJECT_EN", "DEVELOPER_NUMBER", "DEVELOPER_EN",
         "START_DATE", "END_DATE", "PROJECT_VALUE", "PERCENT_COMPLETED"],
        stage,
    )
    return add_join_keys(projects)


def prepare_lands(lands: pl.DataFrame) -> pl.DataFrame:
    stage = "lands"
    logger.info("%s: starting cleaning (%d rows)", stage, lands.height)
    lands = normalize_text_keys(
        lands,
        ["PROJECT_NUMBER", "PROJECT_EN", "MASTER_PROJECT_EN", "LAND_TYPE_EN", "PROP_SUB_TYPE_EN"],
    )
    lands = cast_numeric_columns(lands, ["ACTUAL_AREA"], stage=stage)
    _log_null_stats(lands, ["LAND_TYPE_EN", "PROP_SUB_TYPE_EN", "ACTUAL_AREA", "PROJECT_EN"], stage)
    return add_join_keys(lands)


def prepare_transactions(transactions: pl.DataFrame) -> pl.DataFrame:
    stage = "transactions"
    logger.info("%s: starting cleaning (%d rows)", stage, transactions.height)
    transactions = normalize_text_keys(
        transactions,
        ["GROUP_EN", "PROJECT_EN", "MASTER_PROJECT_EN", "PROP_TYPE_EN", "PROP_SB_TYPE_EN", "DEVELOPER_EN"],
    )
    transactions = normalize_developer_names(transactions, ["DEVELOPER_EN"])
    transactions = cast_date_columns(transactions, ["INSTANCE_DATE"], stage=stage)
    transactions = cast_numeric_columns(
        transactions, ["TRANS_VALUE", "ACTUAL_AREA", "PROCEDURE_AREA"], stage=stage
    )
    _log_null_stats(
        transactions,
        ["INSTANCE_DATE", "TRANS_VALUE", "ACTUAL_AREA", "PROCEDURE_AREA", "PROP_TYPE_EN", "PROJECT_EN"],
        stage,
    )
    transactions = add_join_keys(transactions)

    is_sales = pl.col("GROUP_EN") == "Sales"
    is_mortgage = (pl.col("GROUP_EN") == "Mortgage") | (
        pl.col("PROCEDURE_EN").cast(pl.Utf8, strict=False).str.contains("Mortgage", literal=True)
    )
    valid_area = pl.col("EFFECTIVE_AREA") > 0
    valid_value = pl.col("TRANS_VALUE") > 0

    return transactions.with_columns(
        [
            pl.coalesce([pl.col("ACTUAL_AREA"), pl.col("PROCEDURE_AREA")]).alias("EFFECTIVE_AREA"),
            pl.col("INSTANCE_DATE").dt.truncate("1mo").alias("MONTH"),
        ]
    ).with_columns(
        [
            is_sales.alias("IS_SALES"),
            is_mortgage.alias("IS_MORTGAGE"),
            (pl.col("GROUP_EN") == "Gifts").alias("IS_GIFT"),
            (valid_value & valid_area).alias("IS_VALID_VALUE_AREA"),
            pl.when(valid_value & valid_area)
            .then(pl.col("TRANS_VALUE") / pl.col("EFFECTIVE_AREA"))
            .otherwise(None)
            .alias("PRICE_PER_SQM"),
        ]
    )


def make_sales_reporting_view(transactions: pl.DataFrame) -> pl.DataFrame:
    return transactions.filter(pl.col("IS_SALES") & pl.col("IS_VALID_VALUE_AREA"))


def make_mortgage_reporting_view(transactions: pl.DataFrame) -> pl.DataFrame:
    return transactions.filter(pl.col("IS_MORTGAGE") & (pl.col("TRANS_VALUE") > 0))


def prepare_rents(rents: pl.DataFrame) -> pl.DataFrame:
    stage = "rents"
    logger.info("%s: starting cleaning (%d rows)", stage, rents.height)
    rents = normalize_text_keys(
        rents,
        ["PROJECT_EN", "MASTER_PROJECT_EN", "PROP_TYPE_EN", "PROP_SUB_TYPE_EN", "DEVELOPER_EN"],
    )
    rents = normalize_developer_names(rents, ["DEVELOPER_EN"])
    rents = cast_date_columns(rents, ["REGISTRATION_DATE", "START_DATE", "END_DATE"], stage=stage)
    rents = cast_numeric_columns(
        rents, ["ANNUAL_AMOUNT", "CONTRACT_AMOUNT", "ACTUAL_AREA"], stage=stage
    )
    _log_null_stats(
        rents,
        ["REGISTRATION_DATE", "ANNUAL_AMOUNT", "CONTRACT_AMOUNT", "ACTUAL_AREA", "PROP_TYPE_EN", "PROJECT_EN"],
        stage,
    )
    rents = add_join_keys(rents)

    valid_area_for_rate = (
        (pl.col("EFFECTIVE_AREA") >= RENT_AREA_REPORTING_MIN_SQM) &
        (pl.col("EFFECTIVE_AREA") < RENT_AREA_REPORTING_MAX_SQM)
    )
    valid_amount = pl.col("ANNUAL_AMOUNT") > 0

    return (
        rents.with_columns(
            [
                pl.col("ACTUAL_AREA").alias("EFFECTIVE_AREA"),
                pl.col("REGISTRATION_DATE").dt.truncate("1mo").alias("MONTH"),
            ]
        )
        .with_columns(
            [
                (valid_amount & (pl.col("EFFECTIVE_AREA") > 0)).alias("IS_VALID_RENT_RECORD"),
                pl.when(valid_amount & (pl.col("EFFECTIVE_AREA") > 0))
                .then(pl.col("ANNUAL_AMOUNT") / pl.col("EFFECTIVE_AREA"))
                .otherwise(None)
                .alias("RENT_PER_SQM"),
            ]
        )
        .with_columns(
            (
                valid_area_for_rate &
                (pl.col("RENT_PER_SQM") <= RENT_RATE_MAX_AED_PER_SQM)
            ).alias("IS_VALID_AREA_FOR_RATE")
        )
        .with_columns(
            pl.when(pl.col("IS_VALID_AREA_FOR_RATE"))
            .then(pl.col("RENT_PER_SQM"))
            .otherwise(None)
            .alias("RENT_PER_SQM")
        )
    )


def make_rent_reporting_view(rents: pl.DataFrame) -> pl.DataFrame:
    return rents.filter(pl.col("IS_VALID_RENT_RECORD"))
