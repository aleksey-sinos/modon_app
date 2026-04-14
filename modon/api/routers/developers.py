from __future__ import annotations

from typing import Optional

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import AppState, get_state
from api.schemas import DeveloperDetail, DeveloperProject, DeveloperRow, MonthlySalesPoint

router = APIRouter(prefix="/developers", tags=["developers"])


def _build_leaderboard(state: AppState, area: Optional[str] = None) -> pl.DataFrame:
    projects = state.projects
    transactions = state.transactions
    rents = state.rents

    if area:
        if "AREA_EN" in projects.columns:
            projects = projects.filter(pl.col("AREA_EN") == area)
        if "AREA_EN" in transactions.columns:
            transactions = transactions.filter(pl.col("AREA_EN") == area)
        if "AREA_EN" in rents.columns:
            rents = rents.filter(pl.col("AREA_EN") == area)

    dev_projects = (
        projects.group_by("DEVELOPER_EN")
        .agg(
            pl.len().alias("total_projects"),
            (pl.col("PROJECT_STATUS") == "ACTIVE").sum().alias("active"),
            (pl.col("PROJECT_STATUS") == "PENDING").sum().alias("pending"),
            pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).sum().alias("portfolio_value"),
            pl.when(pl.col("PROJECT_STATUS") == "ACTIVE").then(pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False)).otherwise(0).sum().alias("active_portfolio_value"),
            pl.when(pl.col("PROJECT_STATUS") == "PENDING").then(pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False)).otherwise(0).sum().alias("pending_portfolio_value"),
            pl.col("CNT_UNIT").cast(pl.Float64, strict=False).sum().alias("total_units"),
            pl.when(pl.col("PROJECT_STATUS") == "ACTIVE").then(pl.col("CNT_UNIT").cast(pl.Float64, strict=False)).otherwise(0).sum().alias("active_units"),
            pl.when(pl.col("PROJECT_STATUS") == "PENDING").then(pl.col("CNT_UNIT").cast(pl.Float64, strict=False)).otherwise(0).sum().alias("pending_units"),
        )
    )
    dev_sales = (
        transactions.filter(pl.col("DEVELOPER_EN").is_not_null())
        .group_by("DEVELOPER_EN")
        .agg(
            pl.len().alias("sales_count"),
            pl.col("TRANS_VALUE").sum().alias("sales_value"),
            pl.col("PRICE_PER_SQM").median().alias("median_price_sqm"),
        )
    )
    dev_rents = (
        rents.filter(pl.col("DEVELOPER_EN").is_not_null())
        .group_by("DEVELOPER_EN")
        .agg(
            pl.len().alias("rent_count"),
            pl.col("ANNUAL_AMOUNT").sum().alias("rent_value"),
            pl.col("RENT_PER_SQM").median().alias("median_rent_sqm"),
        )
    )
    return (
        dev_projects.join(dev_sales, on="DEVELOPER_EN", how="left")
        .join(dev_rents, on="DEVELOPER_EN", how="left")
        .with_columns(
            [
                pl.col("sales_count").fill_null(0),
                pl.col("rent_count").fill_null(0),
                (pl.col("median_rent_sqm") / pl.col("median_price_sqm")).alias("gross_yield"),
            ]
        )
        .sort(by=["total_projects", "active", "DEVELOPER_EN"], descending=[True, True, False])
    )


def _row_to_model(row: dict) -> DeveloperRow:
    return DeveloperRow(
        developer=str(row["DEVELOPER_EN"] or ""),
        total_projects=int(row["total_projects"]),
        active=int(row["active"] or 0),
        pending=int(row["pending"] or 0),
        portfolio_value=_opt_float(row.get("portfolio_value")),
        active_portfolio_value=_opt_float(row.get("active_portfolio_value")),
        pending_portfolio_value=_opt_float(row.get("pending_portfolio_value")),
        total_units=_opt_float(row.get("total_units")),
        active_units=_opt_float(row.get("active_units")),
        pending_units=_opt_float(row.get("pending_units")),
        sales_count=int(row["sales_count"] or 0),
        sales_value=_opt_float(row.get("sales_value")),
        rent_count=int(row["rent_count"] or 0),
        rent_value=_opt_float(row.get("rent_value")),
        median_price_sqm=_opt_float(row.get("median_price_sqm")),
        median_rent_sqm=_opt_float(row.get("median_rent_sqm")),
        gross_yield=_opt_float(row.get("gross_yield")),
    )


@router.get("", response_model=list[DeveloperRow])
def list_developers(
    area: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> list[DeveloperRow]:
    leaderboard = _build_leaderboard(state, area=area)
    return [_row_to_model(row) for row in leaderboard.iter_rows(named=True)]


@router.get("/{developer_name}", response_model=DeveloperDetail)
def get_developer(developer_name: str, state: AppState = Depends(get_state)) -> DeveloperDetail:
    leaderboard = _build_leaderboard(state)
    match = leaderboard.filter(pl.col("DEVELOPER_EN") == developer_name)
    if match.height == 0:
        raise HTTPException(status_code=404, detail=f"Developer '{developer_name}' not found")

    kpis = _row_to_model(match.row(0, named=True))

    dev_projects = (
        state.projects.filter(pl.col("DEVELOPER_EN") == developer_name)
        .sort("START_DATE", descending=True, nulls_last=True)
    )
    projects_list = [
        DeveloperProject(
            project=str(row["PROJECT_EN"] or ""),
            status=row.get("PROJECT_STATUS"),
            percent_completed=_opt_float(row.get("PERCENT_COMPLETED")),
            start_date=_opt_date(row.get("START_DATE")),
            end_date=_opt_date(row.get("END_DATE")),
            project_value=_opt_float(row.get("PROJECT_VALUE")),
            units=_opt_float(row.get("CNT_UNIT")),
        )
        for row in dev_projects.iter_rows(named=True)
    ]

    monthly_sales_df = (
        state.transactions.filter(pl.col("DEVELOPER_EN") == developer_name)
        .group_by("MONTH")
        .agg(
            (pl.col("TRANS_VALUE").sum() / 1_000_000).alias("sales_value_m"),
            pl.len().alias("transaction_count"),
        )
        .sort("MONTH")
    )
    monthly_sales = [
        MonthlySalesPoint(
            month=str(row["MONTH"]),
            sales_value_m=float(row["sales_value_m"] or 0),
            transaction_count=int(row["transaction_count"]),
        )
        for row in monthly_sales_df.iter_rows(named=True)
    ]

    return DeveloperDetail(
        developer=developer_name,
        kpis=kpis,
        projects=projects_list,
        monthly_sales=monthly_sales,
    )


def _opt_float(v: object) -> Optional[float]:
    return float(v) if v is not None else None


def _opt_date(v: object) -> Optional[str]:
    return str(v) if v is not None else None
