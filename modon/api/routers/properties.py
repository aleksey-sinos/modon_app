from __future__ import annotations

from typing import Optional

import polars as pl
from fastapi import APIRouter, Depends, Query

from api.deps import AppState, get_state
from api.schemas import PropertyTypeRow, PropertyTypeTrendPoint

router = APIRouter(prefix="/properties", tags=["properties"])


def _apply_filters(
    df: pl.DataFrame,
    developer: Optional[str],
    area: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    is_offplan: Optional[str],
) -> pl.DataFrame:
    if developer:
        df = df.filter(pl.col("DEVELOPER_EN") == developer)
    if area:
        df = df.filter(pl.col("AREA_EN") == area)
    if date_from:
        df = df.filter(pl.col("INSTANCE_DATE").cast(pl.Utf8) >= date_from)
    if date_to:
        df = df.filter(pl.col("INSTANCE_DATE").cast(pl.Utf8) <= date_to)
    if is_offplan and "IS_OFFPLAN_EN" in df.columns:
        df = df.filter(pl.col("IS_OFFPLAN_EN") == is_offplan)
    return df


@router.get("/types", response_model=list[PropertyTypeRow])
def get_property_types(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    is_offplan: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[PropertyTypeRow]:
    t = _apply_filters(state.transactions, developer, area, date_from, date_to, is_offplan)
    if "PROP_TYPE_EN" not in t.columns or t.height == 0:
        return []
    by_type = (
        t.filter(pl.col("PROP_TYPE_EN").is_not_null())
        .group_by("PROP_TYPE_EN")
        .agg(
            pl.len().alias("transaction_count"),
            (pl.col("TRANS_VALUE").sum() / 1_000_000).alias("sales_value_m"),
            pl.col("PRICE_PER_SQM").median().alias("median_price_sqm"),
            pl.col("EFFECTIVE_AREA").median().alias("median_area_sqm"),
        )
        .sort("transaction_count", descending=True)
    )
    return [
        PropertyTypeRow(
            prop_type=str(row["PROP_TYPE_EN"]),
            transaction_count=int(row["transaction_count"]),
            sales_value_m=float(row["sales_value_m"] or 0),
            median_price_sqm=_opt_float(row.get("median_price_sqm")),
            median_area_sqm=_opt_float(row.get("median_area_sqm")),
        )
        for row in by_type.iter_rows(named=True)
    ]


@router.get("/type-trend", response_model=list[PropertyTypeTrendPoint])
def get_property_type_trend(
    prop_types: Optional[str] = Query(None, description="Comma-separated property types"),
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    frequency: str = Query("monthly", pattern="^(monthly|weekly)$"),
    state: AppState = Depends(get_state),
) -> list[PropertyTypeTrendPoint]:
    t = _apply_filters(state.transactions, developer, area, date_from, date_to, None)
    if "PROP_TYPE_EN" not in t.columns or t.height == 0:
        return []
    if prop_types:
        selected = [p.strip() for p in prop_types.split(",") if p.strip()]
        t = t.filter(pl.col("PROP_TYPE_EN").is_in(selected))
    period_column = "MONTH"
    if frequency == "weekly":
        t = t.with_columns(pl.col("INSTANCE_DATE").dt.truncate("1w").alias("WEEK"))
        period_column = "WEEK"
    trend = (
        t.filter(pl.col("PROP_TYPE_EN").is_not_null())
        .group_by([period_column, "PROP_TYPE_EN"])
        .agg(pl.col("PRICE_PER_SQM").median().alias("median_price_sqm"))
        .sort(period_column)
    )
    return [
        PropertyTypeTrendPoint(
            month=str(row[period_column]),
            prop_type=str(row["PROP_TYPE_EN"]),
            median_price_sqm=float(row["median_price_sqm"] or 0),
        )
        for row in trend.iter_rows(named=True)
    ]


def _opt_float(v: object) -> Optional[float]:
    return float(v) if v is not None else None
