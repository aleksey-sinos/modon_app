from __future__ import annotations

from datetime import timedelta
from typing import Literal, Optional

import polars as pl
from fastapi import APIRouter, Depends, Query

from api.deps import AppState, get_state
from api.schemas import CompletionBandRow, LandTypeRow, LocationContextRow, PipelineByYearRow, SubTypeRow, SupplyKPIs

router = APIRouter(prefix="/supply", tags=["supply"])

MIN_LOCATION_AREA_SAMPLES = 20
MAX_ABS_LOCATION_PERFORMANCE_PCT = 200


@router.get("/kpis", response_model=SupplyKPIs)
def get_supply_kpis(state: AppState = Depends(get_state)) -> SupplyKPIs:
    lands = state.lands
    projects = state.projects
    total_area = lands["ACTUAL_AREA"].sum() if "ACTUAL_AREA" in lands.columns else None
    return SupplyKPIs(
        total_land_parcels=lands.height,
        total_land_area_sqm=_opt_float(total_area),
        active_projects=int((projects["PROJECT_STATUS"] == "ACTIVE").sum()),
        pending_projects=int((projects["PROJECT_STATUS"] == "PENDING").sum()),
        units_in_pipeline=int(projects["CNT_UNIT"].cast(pl.Float64, strict=False).fill_null(0).sum()),
    )


@router.get("/land-types", response_model=list[LandTypeRow])
def get_land_types(state: AppState = Depends(get_state)) -> list[LandTypeRow]:
    lands = state.lands
    if "LAND_TYPE_EN" not in lands.columns:
        return []
    by_type = (
        lands.filter(pl.col("LAND_TYPE_EN").is_not_null())
        .group_by("LAND_TYPE_EN")
        .agg(
            pl.len().alias("parcels"),
            pl.col("ACTUAL_AREA").sum().alias("total_area_sqm"),
        )
        .sort("parcels", descending=True)
    )
    return [
        LandTypeRow(
            land_type=str(row["LAND_TYPE_EN"]),
            parcels=int(row["parcels"]),
            total_area_sqm=_opt_float(row.get("total_area_sqm")),
        )
        for row in by_type.iter_rows(named=True)
    ]


@router.get("/sub-types", response_model=list[SubTypeRow])
def get_sub_types(
    top: int = Query(15, ge=1, le=100),
    state: AppState = Depends(get_state),
) -> list[SubTypeRow]:
    lands = state.lands
    if "PROP_SUB_TYPE_EN" not in lands.columns:
        return []
    by_sub = (
        lands.filter(pl.col("PROP_SUB_TYPE_EN").is_not_null())
        .group_by("PROP_SUB_TYPE_EN")
        .agg(pl.len().alias("parcels"))
        .sort("parcels", descending=True)
        .head(top)
    )
    return [
        SubTypeRow(sub_type=str(row["PROP_SUB_TYPE_EN"]), parcels=int(row["parcels"]))
        for row in by_sub.iter_rows(named=True)
    ]


def _get_location_context(
    frame: pl.DataFrame,
    column: str,
    top: int,
    *,
    date_column: str,
    value_column: str,
    price_column: str,
) -> list[LocationContextRow]:
    required_columns = {column, "AREA_EN", date_column, value_column, price_column}
    if not required_columns.issubset(set(frame.columns)):
        return []

    frame = frame.filter(
        pl.col(column).is_not_null()
        & (pl.col(column).cast(pl.Utf8).str.strip_chars() != "")
        & pl.col("AREA_EN").is_not_null()
        & (pl.col("AREA_EN").cast(pl.Utf8).str.strip_chars() != "")
        & pl.col(date_column).is_not_null()
    )
    if frame.height == 0:
        return []

    valid_area_pairs = (
        frame.group_by([column, "AREA_EN"])
        .agg(pl.len().alias("sample_count"))
        .filter(pl.col("sample_count") >= MIN_LOCATION_AREA_SAMPLES)
        .select([column, "AREA_EN"])
    )
    frame = frame.join(valid_area_pairs, on=[column, "AREA_EN"], how="inner")
    if frame.height == 0:
        return []

    anchor_date = frame[date_column].max()
    current_start = anchor_date - timedelta(days=29)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=29)

    current_window = pl.col(date_column).is_between(current_start, anchor_date, closed="both")
    previous_window = pl.col(date_column).is_between(previous_start, previous_end, closed="both")

    by_location = (
        frame.group_by(column)
        .agg(
            pl.len().alias("contract_count"),
            (pl.col(value_column).sum() / 1_000_000).alias("annual_rent_m"),
            pl.col(price_column).median().alias("median_rent_sqm"),
            pl.col("AREA_EN").n_unique().alias("unique_areas"),
            pl.col(price_column).filter(current_window).median().alias("current_median_rent_sqm"),
            pl.col(price_column).filter(previous_window).median().alias("previous_median_rent_sqm"),
            pl.col(price_column).filter(current_window).std().alias("current_std_rent_sqm"),
            pl.col(price_column).filter(current_window).mean().alias("current_mean_rent_sqm"),
        )
        .with_columns(
            pl.when(
                pl.col("current_median_rent_sqm").is_not_null()
                & pl.col("previous_median_rent_sqm").is_not_null()
                & (pl.col("previous_median_rent_sqm") != 0)
            )
            .then(
                ((pl.col("current_median_rent_sqm") - pl.col("previous_median_rent_sqm")) / pl.col("previous_median_rent_sqm")) * 100
            )
            .otherwise(None)
            .alias("performance_30d_pct"),
            pl.when(
                pl.col("current_mean_rent_sqm").is_not_null()
                & pl.col("current_std_rent_sqm").is_not_null()
                & (pl.col("current_mean_rent_sqm") != 0)
            )
            .then((pl.col("current_std_rent_sqm") / pl.col("current_mean_rent_sqm")) * 100)
            .otherwise(None)
            .alias("volatility_30d_pct"),
        )
        .filter(
            pl.col("performance_30d_pct").is_null()
            | (pl.col("performance_30d_pct").abs() <= MAX_ABS_LOCATION_PERFORMANCE_PCT)
        )
        .sort(["median_rent_sqm", "contract_count", column], descending=[True, True, False], nulls_last=True)
        .head(top)
    )

    return [
        LocationContextRow(
            name=str(row[column]),
            contract_count=int(row["contract_count"]),
            annual_rent_m=float(row["annual_rent_m"] or 0),
            median_rent_sqm=_opt_float(row.get("median_rent_sqm")),
            unique_areas=int(row["unique_areas"] or 0),
            current_median_rent_sqm=_opt_float(row.get("current_median_rent_sqm")),
            previous_median_rent_sqm=_opt_float(row.get("previous_median_rent_sqm")),
            performance_30d_pct=_opt_float(row.get("performance_30d_pct")),
            volatility_30d_pct=_opt_float(row.get("volatility_30d_pct")),
        )
        for row in by_location.iter_rows(named=True)
    ]


@router.get("/nearest-metros", response_model=list[LocationContextRow])
def get_nearest_metros(
    top: int = Query(12, ge=1, le=50),
    market: Literal["rent", "sale"] = Query("rent"),
    state: AppState = Depends(get_state),
) -> list[LocationContextRow]:
    if market == "sale":
        return _get_location_context(
            state.transactions,
            "NEAREST_METRO_EN",
            top,
            date_column="INSTANCE_DATE",
            value_column="TRANS_VALUE",
            price_column="PRICE_PER_SQM",
        )
    return _get_location_context(
        state.rents,
        "NEAREST_METRO_EN",
        top,
        date_column="REGISTRATION_DATE",
        value_column="ANNUAL_AMOUNT",
        price_column="RENT_PER_SQM",
    )


@router.get("/nearest-landmarks", response_model=list[LocationContextRow])
def get_nearest_landmarks(
    top: int = Query(12, ge=1, le=50),
    market: Literal["rent", "sale"] = Query("rent"),
    state: AppState = Depends(get_state),
) -> list[LocationContextRow]:
    if market == "sale":
        return _get_location_context(
            state.transactions,
            "NEAREST_LANDMARK_EN",
            top,
            date_column="INSTANCE_DATE",
            value_column="TRANS_VALUE",
            price_column="PRICE_PER_SQM",
        )
    return _get_location_context(
        state.rents,
        "NEAREST_LANDMARK_EN",
        top,
        date_column="REGISTRATION_DATE",
        value_column="ANNUAL_AMOUNT",
        price_column="RENT_PER_SQM",
    )


@router.get("/pipeline-by-year", response_model=list[PipelineByYearRow])
def get_pipeline_by_year(
    from_year: int = Query(2024),
    state: AppState = Depends(get_state),
) -> list[PipelineByYearRow]:
    projects = state.projects
    if "END_DATE" not in projects.columns:
        return []
    pipeline = (
        projects.filter(pl.col("END_DATE").is_not_null())
        .with_columns(pl.col("END_DATE").dt.year().alias("completion_year"))
        .group_by("completion_year")
        .agg(
            pl.col("CNT_UNIT").cast(pl.Float64, strict=False).sum().alias("units"),
            pl.len().alias("projects"),
        )
        .filter(pl.col("completion_year") >= from_year)
        .sort("completion_year")
    )
    return [
        PipelineByYearRow(
            completion_year=int(row["completion_year"]),
            units=float(row["units"] or 0),
            projects=int(row["projects"]),
        )
        for row in pipeline.iter_rows(named=True)
    ]


@router.get("/completion-bands", response_model=list[CompletionBandRow])
def get_completion_bands(state: AppState = Depends(get_state)) -> list[CompletionBandRow]:
    projects = state.projects
    if "PERCENT_COMPLETED" not in projects.columns:
        return []
    completed = projects.filter(pl.col("PERCENT_COMPLETED").is_not_null())
    if completed.height == 0:
        return []
    bands = (
        completed.with_columns(
            pl.when(pl.col("PERCENT_COMPLETED") == 0).then(pl.lit("0%"))
            .when(pl.col("PERCENT_COMPLETED") < 25).then(pl.lit("1-24%"))
            .when(pl.col("PERCENT_COMPLETED") < 50).then(pl.lit("25-49%"))
            .when(pl.col("PERCENT_COMPLETED") < 75).then(pl.lit("50-74%"))
            .when(pl.col("PERCENT_COMPLETED") < 100).then(pl.lit("75-99%"))
            .otherwise(pl.lit("100%"))
            .alias("band")
        )
        .group_by("band")
        .agg(pl.len().alias("projects"))
        .sort("band")
    )
    return [
        CompletionBandRow(band=str(row["band"]), projects=int(row["projects"]))
        for row in bands.iter_rows(named=True)
    ]


def _opt_float(v: object) -> Optional[float]:
    return float(v) if v is not None else None
