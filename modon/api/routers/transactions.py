from __future__ import annotations

from typing import Optional

import polars as pl
from fastapi import APIRouter, Depends, Query

from api.deps import AppState, get_state
from api.schemas import (
    AreaPricePoint,
    MonthlyTrendPoint,
    PaginatedTransactions,
    TransactionAreaHeatmapPoint,
    TransactionKPIs,
    TransactionRow,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])

MAX_PAGE_SIZE = 500


def _apply_filters(
    df: pl.DataFrame,
    developer: Optional[str],
    area: Optional[str],
    prop_type: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> pl.DataFrame:
    if developer:
        df = df.filter(pl.col("DEVELOPER_EN") == developer)
    if area:
        df = df.filter(pl.col("AREA_EN") == area)
    if prop_type:
        df = df.filter(pl.col("PROP_TYPE_EN") == prop_type)
    if date_from:
        df = df.filter(pl.col("INSTANCE_DATE").cast(pl.Utf8) >= date_from)
    if date_to:
        df = df.filter(pl.col("INSTANCE_DATE").cast(pl.Utf8) <= date_to)
    return df


@router.get("/kpis", response_model=TransactionKPIs)
def get_transaction_kpis(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    state: AppState = Depends(get_state),
) -> TransactionKPIs:
    t = _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
    return TransactionKPIs(
        total_transactions=t.height,
        total_sales_value=float(t["TRANS_VALUE"].sum() or 0),
        median_price_sqm=_opt_float(t["PRICE_PER_SQM"].median() if t.height > 0 else None),
        avg_transaction_value=_opt_float(t["TRANS_VALUE"].mean() if t.height > 0 else None),
    )


@router.get("/monthly", response_model=list[MonthlyTrendPoint])
def get_monthly_sales(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MonthlyTrendPoint]:
    t = _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
    agg = (
        t.group_by("MONTH")
        .agg((pl.col("TRANS_VALUE").sum() / 1_000_000).alias("value"))
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
    t = _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
    agg = (
        t.group_by("MONTH")
        .agg(pl.len().cast(pl.Float64).alias("value"))
        .sort("MONTH")
    )
    return [
        MonthlyTrendPoint(month=str(row["MONTH"]), value=float(row["value"] or 0))
        for row in agg.iter_rows(named=True)
    ]


@router.get("/monthly-price", response_model=list[MonthlyTrendPoint])
def get_monthly_price(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MonthlyTrendPoint]:
    t = _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
    agg = (
        t.group_by("MONTH")
        .agg(pl.col("PRICE_PER_SQM").median().alias("value"))
        .sort("MONTH")
    )
    return [
        MonthlyTrendPoint(month=str(row["MONTH"]), value=float(row["value"] or 0))
        for row in agg.iter_rows(named=True)
    ]


@router.get("/weekly", response_model=list[MonthlyTrendPoint])
def get_weekly_sales(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MonthlyTrendPoint]:
    t = _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
    agg = (
        t.with_columns(pl.col("INSTANCE_DATE").dt.truncate("1w").alias("WEEK"))
        .group_by("WEEK")
        .agg((pl.col("TRANS_VALUE").sum() / 1_000_000).alias("value"))
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
    t = _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
    agg = (
        t.with_columns(pl.col("INSTANCE_DATE").dt.truncate("1w").alias("WEEK"))
        .group_by("WEEK")
        .agg(pl.len().cast(pl.Float64).alias("value"))
        .sort("WEEK")
    )
    return [
        MonthlyTrendPoint(month=str(row["WEEK"]), value=float(row["value"] or 0))
        for row in agg.iter_rows(named=True)
    ]


@router.get("/weekly-price", response_model=list[MonthlyTrendPoint])
def get_weekly_price(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MonthlyTrendPoint]:
    t = _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
    agg = (
        t.with_columns(pl.col("INSTANCE_DATE").dt.truncate("1w").alias("WEEK"))
        .group_by("WEEK")
        .agg(pl.col("PRICE_PER_SQM").median().alias("value"))
        .sort("WEEK")
    )
    return [
        MonthlyTrendPoint(month=str(row["WEEK"]), value=float(row["value"] or 0))
        for row in agg.iter_rows(named=True)
    ]


@router.get("/area-heatmap", response_model=list[TransactionAreaHeatmapPoint])
def get_area_heatmap(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    top: int = Query(80, ge=1, le=200),
    state: AppState = Depends(get_state),
) -> list[TransactionAreaHeatmapPoint]:
    t = _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
    if t.height == 0:
        return []

    area_col = pl.col("AREA_EN").cast(pl.Utf8)
    agg = (
        t.filter(area_col.is_not_null() & (area_col.str.strip_chars() != ""))
        .group_by("AREA_EN")
        .agg(
            pl.len().alias("transaction_count"),
            (pl.col("TRANS_VALUE").sum() / 1_000_000).alias("sales_value_m"),
        )
        .sort(["transaction_count", "sales_value_m", "AREA_EN"], descending=[True, True, False])
        .head(top)
    )
    return [
        TransactionAreaHeatmapPoint(
            area=str(row["AREA_EN"]),
            transaction_count=int(row["transaction_count"] or 0),
            sales_value_m=float(row["sales_value_m"] or 0),
        )
        for row in agg.iter_rows(named=True)
    ]


@router.get("/by-area", response_model=list[AreaPricePoint])
def get_transactions_by_area(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    top: int = Query(15, ge=1, le=100),
    state: AppState = Depends(get_state),
) -> list[AreaPricePoint]:
    t = _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
    if t.height == 0:
        return []

    area_col = pl.col("AREA_EN").cast(pl.Utf8)
    agg = (
        t.filter(area_col.is_not_null() & (area_col.str.strip_chars() != ""))
        .group_by("AREA_EN")
        .agg(
            pl.col("PRICE_PER_SQM").median().alias("median_price_sqm"),
            pl.len().alias("transaction_count"),
        )
        .sort(["median_price_sqm", "transaction_count", "AREA_EN"], descending=[True, True, False])
        .head(top)
    )
    return [
        AreaPricePoint(
            area=str(row["AREA_EN"]),
            median_price_sqm=float(row["median_price_sqm"] or 0),
            transaction_count=int(row["transaction_count"] or 0),
        )
        for row in agg.iter_rows(named=True)
    ]


@router.get("", response_model=PaginatedTransactions)
def list_transactions(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    prop_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    state: AppState = Depends(get_state),
) -> PaginatedTransactions:
    t = (
        _apply_filters(state.transactions, developer, area, prop_type, date_from, date_to)
        .sort(["INSTANCE_DATE", "TRANSACTION_NUMBER"], descending=[True, True], nulls_last=True)
    )
    total = t.height
    offset = (page - 1) * page_size
    page_df = t.slice(offset, page_size)

    items = [
        TransactionRow(
            transaction_number=row.get("TRANSACTION_NUMBER"),
            instance_date=_opt_str(row.get("INSTANCE_DATE")),
            developer=row.get("DEVELOPER_EN"),
            project=row.get("PROJECT_EN"),
            area=row.get("AREA_EN"),
            prop_type=row.get("PROP_TYPE_EN"),
            trans_value=_opt_float(row.get("TRANS_VALUE")),
            effective_area=_opt_float(row.get("EFFECTIVE_AREA")),
            price_per_sqm=_opt_float(row.get("PRICE_PER_SQM")),
            is_offplan=row.get("IS_OFFPLAN_EN"),
            rooms=row.get("ROOMS_EN"),
        )
        for row in page_df.iter_rows(named=True)
    ]
    return PaginatedTransactions(total=total, page=page, page_size=page_size, items=items)


def _opt_float(v: object) -> Optional[float]:
    return float(v) if v is not None else None


def _opt_str(v: object) -> Optional[str]:
    return str(v) if v is not None else None
