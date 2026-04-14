from __future__ import annotations

from typing import Optional

import polars as pl
from fastapi import APIRouter, Depends, Query

from api.deps import AppState, get_state
from api.schemas import (
    MortgageKPIs,
    MortgageProcedureRow,
    MortgageTransactionRow,
    MonthlyTrendPoint,
    PaginatedMortgageTransactions,
)

router = APIRouter(prefix="/mortgages", tags=["mortgages"])

MAX_PAGE_SIZE = 500


def _apply_filters(
    df: pl.DataFrame,
    procedure: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> pl.DataFrame:
    if procedure:
        df = df.filter(pl.col("PROCEDURE_EN") == procedure)
    if date_from:
        df = df.filter(pl.col("INSTANCE_DATE").cast(pl.Utf8) >= date_from)
    if date_to:
        df = df.filter(pl.col("INSTANCE_DATE").cast(pl.Utf8) <= date_to)
    return df


@router.get("/kpis", response_model=MortgageKPIs)
def get_mortgage_kpis(
    procedure: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> MortgageKPIs:
    m = _apply_filters(state.mortgages, procedure, date_from, date_to)
    return MortgageKPIs(
        total_mortgage_transactions=m.height,
        total_mortgage_value=float(m["MORTGAGE_VALUE"].sum() or 0),
        avg_mortgage_value=_opt_float(m["MORTGAGE_VALUE"].mean() if m.height > 0 else None),
    )


@router.get("/monthly", response_model=list[MonthlyTrendPoint])
def get_monthly_mortgage_value(
    procedure: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MonthlyTrendPoint]:
    m = _apply_filters(state.mortgages, procedure, date_from, date_to)
    agg = (
        m.group_by("MONTH")
        .agg((pl.col("MORTGAGE_VALUE").sum() / 1_000_000).alias("value"))
        .sort("MONTH")
    )
    return [
        MonthlyTrendPoint(month=str(row["MONTH"]), value=float(row["value"] or 0))
        for row in agg.iter_rows(named=True)
    ]


@router.get("/by-procedure", response_model=list[MortgageProcedureRow])
def get_mortgages_by_procedure(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[MortgageProcedureRow]:
    m = _apply_filters(state.mortgages, None, date_from, date_to)
    agg = (
        m.group_by("PROCEDURE_EN")
        .agg(
            pl.len().alias("transaction_count"),
            (pl.col("MORTGAGE_VALUE").sum() / 1_000_000).alias("total_value_m"),
            pl.col("MORTGAGE_VALUE").mean().alias("avg_value"),
        )
        .sort("transaction_count", descending=True)
    )
    return [
        MortgageProcedureRow(
            procedure=str(row["PROCEDURE_EN"] or "Unknown"),
            transaction_count=int(row["transaction_count"]),
            total_value_m=float(row["total_value_m"] or 0),
            avg_value=_opt_float(row.get("avg_value")),
        )
        for row in agg.iter_rows(named=True)
    ]


@router.get("", response_model=PaginatedMortgageTransactions)
def list_mortgages(
    procedure: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    state: AppState = Depends(get_state),
) -> PaginatedMortgageTransactions:
    m = _apply_filters(state.mortgages, procedure, date_from, date_to)
    total = m.height
    offset = (page - 1) * page_size
    page_df = m.slice(offset, page_size)
    items = [
        MortgageTransactionRow(
            transaction_number=row.get("TRANSACTION_NUMBER"),
            instance_date=_opt_str(row.get("INSTANCE_DATE")),
            procedure=row.get("PROCEDURE_EN"),
            mortgage_value=_opt_float(row.get("MORTGAGE_VALUE")),
            row_count=int(row.get("ROW_COUNT") or 0),
            area=row.get("AREA_EN"),
            prop_type=row.get("PROP_TYPE_EN"),
            is_offplan=row.get("IS_OFFPLAN_EN"),
        )
        for row in page_df.iter_rows(named=True)
    ]
    return PaginatedMortgageTransactions(total=total, page=page, page_size=page_size, items=items)


def _opt_float(v: object) -> Optional[float]:
    return float(v) if v is not None else None


def _opt_str(v: object) -> Optional[str]:
    return str(v) if v is not None else None
