from __future__ import annotations

from typing import Optional

import polars as pl
from fastapi import APIRouter, Depends, Query

from api.deps import AppState, get_state
from api.schemas import (
    MonthlyTrendPoint,
    PaginatedRents,
    RentAreaHeatmapPoint,
    RentByAreaRow,
    RentByTypeRow,
    RentKPIs,
    RentRow,
    RentTrendPoint,
)

router = APIRouter(prefix="/rents", tags=["rents"])

MAX_PAGE_SIZE = 500


def _apply_filters(
    df: pl.DataFrame,
    developer: Optional[str],
    area: Optional[str],
    prop_type: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> pl.DataFrame:
    date_column = "REGISTRATION_DATE" if "REGISTRATION_DATE" in df.columns else "MONTH"
    if developer:
        df = df.filter(pl.col("DEVELOPER_EN") == developer)
    if area and "AREA_EN" in df.columns:
        df = df.filter(pl.col("AREA_EN") == area)
    if prop_type:
        df = df.filter(pl.col("PROP_TYPE_EN") == prop_type)
    if date_from:
        df = df.filter(pl.col(date_column).cast(pl.Utf8) >= date_from)
    if date_to:
        df = df.filter(pl.col(date_column).cast(pl.Utf8) <= date_to)
    return df


@router.get("/kpis", response_model=RentKPIs)
def get_rent_kpis(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> RentKPIs:
    r = _apply_filters(state.rents, developer, area, prop_type, date_from, date_to)
    return RentKPIs(
        total_contracts=r.height,
        total_annual_rent=float(r["ANNUAL_AMOUNT"].sum() or 0),
        median_rent_sqm=_opt_float(r["RENT_PER_SQM"].median() if r.height > 0 else None),
        avg_annual_contract=_opt_float(r["ANNUAL_AMOUNT"].mean() if r.height > 0 else None),
    )


@router.get("/monthly", response_model=list[MonthlyTrendPoint])
def get_monthly_rent(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MonthlyTrendPoint]:
    r = _apply_filters(state.rents, developer, area, prop_type, date_from, date_to)
    agg = (
        r.group_by("MONTH")
        .agg((pl.col("ANNUAL_AMOUNT").sum() / 1_000_000).alias("value"))
        .sort("MONTH")
    )
    return [
        MonthlyTrendPoint(month=str(row["MONTH"]), value=float(row["value"] or 0))
        for row in agg.iter_rows(named=True)
    ]


@router.get("/monthly-count", response_model=list[MonthlyTrendPoint])
def get_monthly_count(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MonthlyTrendPoint]:
    r = _apply_filters(state.rents, developer, area, prop_type, date_from, date_to)
    agg = (
        r.group_by("MONTH")
        .agg(pl.len().cast(pl.Float64).alias("value"))
        .sort("MONTH")
    )
    return [
        MonthlyTrendPoint(month=str(row["MONTH"]), value=float(row["value"] or 0))
        for row in agg.iter_rows(named=True)
    ]


@router.get("/weekly", response_model=list[MonthlyTrendPoint])
def get_weekly_rent(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MonthlyTrendPoint]:
    r = _apply_filters(state.rents, developer, area, prop_type, date_from, date_to)
    agg = (
        r.with_columns(pl.col("REGISTRATION_DATE").dt.truncate("1w").alias("WEEK"))
        .group_by("WEEK")
        .agg((pl.col("ANNUAL_AMOUNT").sum() / 1_000_000).alias("value"))
        .sort("WEEK")
    )
    return [
        MonthlyTrendPoint(month=str(row["WEEK"]), value=float(row["value"] or 0))
        for row in agg.iter_rows(named=True)
    ]


@router.get("/weekly-count", response_model=list[MonthlyTrendPoint])
def get_weekly_count(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MonthlyTrendPoint]:
    r = _apply_filters(state.rents, developer, area, prop_type, date_from, date_to)
    agg = (
        r.with_columns(pl.col("REGISTRATION_DATE").dt.truncate("1w").alias("WEEK"))
        .group_by("WEEK")
        .agg(pl.len().cast(pl.Float64).alias("value"))
        .sort("WEEK")
    )
    return [
        MonthlyTrendPoint(month=str(row["WEEK"]), value=float(row["value"] or 0))
        for row in agg.iter_rows(named=True)
    ]


@router.get("/by-type", response_model=list[RentByTypeRow])
def get_rent_by_type(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[RentByTypeRow]:
    r = _apply_filters(state.rents, developer, area, None, date_from, date_to)
    if "PROP_TYPE_EN" not in r.columns or r.height == 0:
        return []
    by_type = (
        r.filter(pl.col("PROP_TYPE_EN").is_not_null())
        .group_by("PROP_TYPE_EN")
        .agg(
            pl.len().alias("contract_count"),
            (pl.col("ANNUAL_AMOUNT").sum() / 1_000_000).alias("annual_rent_m"),
            pl.col("RENT_PER_SQM").median().alias("median_rent_sqm"),
        )
        .sort("contract_count", descending=True)
    )
    return [
        RentByTypeRow(
            prop_type=str(row["PROP_TYPE_EN"]),
            contract_count=int(row["contract_count"]),
            annual_rent_m=float(row["annual_rent_m"] or 0),
            median_rent_sqm=_opt_float(row.get("median_rent_sqm")),
        )
        for row in by_type.iter_rows(named=True)
    ]


@router.get("/type-trend", response_model=list[RentTrendPoint])
def get_rent_type_trend(
    prop_types: Optional[str] = Query(None, description="Comma-separated property types"),
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    frequency: str = Query("monthly", pattern="^(monthly|weekly)$"),
    state: AppState = Depends(get_state),
) -> list[RentTrendPoint]:
    r = _apply_filters(state.rents, developer, area, None, date_from, date_to)
    if "PROP_TYPE_EN" not in r.columns or r.height == 0:
        return []
    if prop_types:
        selected = [p.strip() for p in prop_types.split(",") if p.strip()]
        r = r.filter(pl.col("PROP_TYPE_EN").is_in(selected))
    period_column = "MONTH"
    if frequency == "weekly":
        r = r.with_columns(pl.col("REGISTRATION_DATE").dt.truncate("1w").alias("WEEK"))
        period_column = "WEEK"
    trend = (
        r.filter(pl.col("PROP_TYPE_EN").is_not_null())
        .group_by([period_column, "PROP_TYPE_EN"])
        .agg(pl.col("RENT_PER_SQM").median().alias("median_rent_sqm"))
        .sort(period_column)
    )
    return [
        RentTrendPoint(
            month=str(row[period_column]),
            prop_type=str(row["PROP_TYPE_EN"]),
            median_rent_sqm=float(row["median_rent_sqm"] or 0),
        )
        for row in trend.iter_rows(named=True)
    ]


@router.get("/by-area", response_model=list[RentByAreaRow])
def get_rent_by_area(
    top: int = Query(20, ge=1, le=100),
    min_contracts: int = Query(5, ge=1),
    developer: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[RentByAreaRow]:
    r = _apply_filters(state.rents, developer, None, prop_type, date_from, date_to)
    if "AREA_EN" not in r.columns or r.height == 0:
        return []
    by_area = (
        r.filter(pl.col("AREA_EN").is_not_null())
        .group_by("AREA_EN")
        .agg(
            pl.col("RENT_PER_SQM").median().alias("median_rent_sqm"),
            pl.len().alias("contract_count"),
        )
        .filter(pl.col("contract_count") >= min_contracts)
        .sort("median_rent_sqm", descending=True)
        .head(top)
    )
    return [
        RentByAreaRow(
            area=str(row["AREA_EN"]),
            median_rent_sqm=float(row["median_rent_sqm"] or 0),
            contract_count=int(row["contract_count"]),
        )
        for row in by_area.iter_rows(named=True)
    ]


@router.get("/area-heatmap", response_model=list[RentAreaHeatmapPoint])
def get_rent_area_heatmap(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    top: int = Query(80, ge=1, le=200),
    state: AppState = Depends(get_state),
) -> list[RentAreaHeatmapPoint]:
    r = _apply_filters(state.rents, developer, area, prop_type, date_from, date_to)
    if "AREA_EN" not in r.columns or r.height == 0:
        return []

    area_col = pl.col("AREA_EN").cast(pl.Utf8)
    agg = (
        r.filter(area_col.is_not_null() & (area_col.str.strip_chars() != ""))
        .group_by("AREA_EN")
        .agg(
            pl.len().alias("contract_count"),
            (pl.col("ANNUAL_AMOUNT").sum() / 1_000_000).alias("annual_rent_m"),
        )
        .sort(["contract_count", "annual_rent_m", "AREA_EN"], descending=[True, True, False])
        .head(top)
    )

    return [
        RentAreaHeatmapPoint(
            area=str(row["AREA_EN"]),
            contract_count=int(row["contract_count"] or 0),
            annual_rent_m=float(row["annual_rent_m"] or 0),
        )
        for row in agg.iter_rows(named=True)
    ]


@router.get("", response_model=PaginatedRents)
def list_rents(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    state: AppState = Depends(get_state),
) -> PaginatedRents:
    r = _apply_filters(state.rents, developer, area, prop_type, date_from, date_to)
    total = r.height
    offset = (page - 1) * page_size
    page_df = r.slice(offset, page_size)

    items = [
        RentRow(
            registration_date=_opt_str(row.get("REGISTRATION_DATE")),
            developer=row.get("DEVELOPER_EN"),
            project=row.get("PROJECT_EN"),
            area=row.get("AREA_EN"),
            prop_type=row.get("PROP_TYPE_EN"),
            annual_amount=_opt_float(row.get("ANNUAL_AMOUNT")),
            effective_area=_opt_float(row.get("EFFECTIVE_AREA")),
            rent_per_sqm=_opt_float(row.get("RENT_PER_SQM")),
            rooms=row.get("ROOMS"),
        )
        for row in page_df.iter_rows(named=True)
    ]
    return PaginatedRents(total=total, page=page, page_size=page_size, items=items)


def _opt_float(v: object) -> Optional[float]:
    return float(v) if v is not None else None


def _opt_str(v: object) -> Optional[str]:
    return str(v) if v is not None else None
