from __future__ import annotations

import json
import logging
import os
from threading import Lock
from datetime import datetime
from datetime import date, timedelta
from typing import Literal, Optional

import polars as pl
from fastapi import APIRouter, Depends, Query
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from api.deps import AppState, get_state
from api.schemas import (
    AreaPricePoint,
    DevelopmentActivitySnapshot,
    FilterOptions,
    MarketActivitySnapshot,
    MarketKPIs,
    MarketNewsItem,
    MarketNewsResponse,
    MarketSummaryResponse,
    MarketSummarySection,
    MarketSummarySource,
    MonthlyProjectLaunchPoint,
    MonthlySalesPoint,
    ProjectStatusCount,
    RollingCountMetric,
    RollingFloatMetric,
    TrendingDevelopmentArea,
    TopAreaVolume,
    WeeklyRentPoint,
    WeeklySalesPoint,
)

router = APIRouter(prefix="/overview", tags=["overview"])

WEEKLY_POINTS_LIMIT = 12

logger = logging.getLogger(__name__)

_MARKET_SUMMARY_CACHE: Optional[MarketSummaryResponse] = None
_MARKET_SUMMARY_CACHE_AT: Optional[datetime] = None
_MARKET_SUMMARY_CACHE_LOCK = Lock()
_MARKET_NEWS_CACHE: Optional[MarketNewsResponse] = None
_MARKET_NEWS_CACHE_LOCK = Lock()

MARKET_SUMMARY_CACHE_TTL = timedelta(days=7)


@router.get("/kpis", response_model=MarketKPIs)
def get_kpis(state: AppState = Depends(get_state)) -> MarketKPIs:
    projects = state.projects
    transactions = state.transactions
    return MarketKPIs(
        total_projects=projects.height,
        active_projects=int((projects["PROJECT_STATUS"] == "ACTIVE").sum()),
        units_in_pipeline=int(projects["CNT_UNIT"].cast(pl.Float64, strict=False).fill_null(0).sum()),
        total_sales_value=float(transactions["TRANS_VALUE"].sum() or 0),
        median_price_sqm=_opt_float(transactions["PRICE_PER_SQM"].median()),
    )


@router.get("/monthly-sales", response_model=list[MonthlySalesPoint])
def get_monthly_sales(state: AppState = Depends(get_state)) -> list[MonthlySalesPoint]:
    tx = state.transactions
    sales = (
        tx.group_by("MONTH")
        .agg(
            (pl.col("TRANS_VALUE").sum() / 1_000_000).alias("sales_value_m"),
            pl.len().alias("transaction_count"),
        )
        .sort("MONTH")
    )
    return [
        MonthlySalesPoint(
            month=str(row["MONTH"]),
            sales_value_m=float(row["sales_value_m"] or 0),
            transaction_count=int(row["transaction_count"]),
        )
        for row in sales.iter_rows(named=True)
    ]


@router.get("/weekly-sales", response_model=list[WeeklySalesPoint])
def get_weekly_sales(
    segment: Literal["total", "off-plan", "ready"] = Query("total"),
    state: AppState = Depends(get_state),
) -> list[WeeklySalesPoint]:
    tx = state.transactions
    if segment != "total" and "IS_OFFPLAN_EN" in tx.columns:
        target = "Off-Plan" if segment == "off-plan" else "Ready"
        tx = tx.filter(pl.col("IS_OFFPLAN_EN") == target)
    cutoff_date = _last_completed_sunday()
    sales = (
        tx.filter(pl.col("INSTANCE_DATE") <= cutoff_date)
        .with_columns(pl.col("INSTANCE_DATE").dt.truncate("1w").alias("WEEK"))
        .group_by("WEEK")
        .agg(
            (pl.col("TRANS_VALUE").sum() / 1_000_000).alias("sales_value_m"),
            pl.len().alias("transaction_count"),
        )
        .sort("WEEK")
        .tail(WEEKLY_POINTS_LIMIT)
    )
    return [
        WeeklySalesPoint(
            week=str(row["WEEK"]),
            sales_value_m=float(row["sales_value_m"] or 0),
            transaction_count=int(row["transaction_count"]),
        )
        for row in sales.iter_rows(named=True)
    ]


@router.get("/weekly-rents", response_model=list[WeeklyRentPoint])
def get_weekly_rents(state: AppState = Depends(get_state)) -> list[WeeklyRentPoint]:
    rents = state.rents
    cutoff_date = _last_completed_sunday()
    weekly = (
        rents.filter(pl.col("REGISTRATION_DATE") <= cutoff_date)
        .with_columns(pl.col("REGISTRATION_DATE").dt.truncate("1w").alias("WEEK"))
        .group_by("WEEK")
        .agg(
            (pl.col("ANNUAL_AMOUNT").sum() / 1_000_000).alias("annual_rent_m"),
            pl.len().alias("contract_count"),
        )
        .sort("WEEK")
        .tail(WEEKLY_POINTS_LIMIT)
    )
    return [
        WeeklyRentPoint(
            week=str(row["WEEK"]),
            annual_rent_m=float(row["annual_rent_m"] or 0),
            contract_count=int(row["contract_count"]),
        )
        for row in weekly.iter_rows(named=True)
    ]


@router.get("/market-activity", response_model=MarketActivitySnapshot)
def get_market_activity(state: AppState = Depends(get_state)) -> MarketActivitySnapshot:
    anchor_date = _get_anchor_date(state)
    current_start = anchor_date - timedelta(days=29)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=29)

    tx = state.transactions
    rents = state.rents

    sales_current = _between_dates(tx, "INSTANCE_DATE", current_start, anchor_date)
    sales_previous = _between_dates(tx, "INSTANCE_DATE", previous_start, previous_end)
    rents_current = _between_dates(rents, "REGISTRATION_DATE", current_start, anchor_date)
    rents_previous = _between_dates(rents, "REGISTRATION_DATE", previous_start, previous_end)

    return MarketActivitySnapshot(
        anchor_date=anchor_date.isoformat(),
        window_days=30,
        sales_count=_count_metric(sales_current.height, sales_previous.height),
        rent_count=_count_metric(rents_current.height, rents_previous.height),
        sales_price_per_sqm=_float_metric(
            _mean_or_none(sales_current, "PRICE_PER_SQM"),
            _mean_or_none(sales_previous, "PRICE_PER_SQM"),
        ),
        rent_price_per_sqm=_float_metric(
            _mean_or_none(rents_current.filter(pl.col("IS_VALID_AREA_FOR_RATE")), "RENT_PER_SQM"),
            _mean_or_none(rents_previous.filter(pl.col("IS_VALID_AREA_FOR_RATE")), "RENT_PER_SQM"),
        ),
    )


@router.get("/development-activity", response_model=DevelopmentActivitySnapshot)
def get_development_activity(state: AppState = Depends(get_state)) -> DevelopmentActivitySnapshot:
    projects = state.projects.filter(pl.col("START_DATE").is_not_null())
    anchor_date = _get_latest_date(projects, "START_DATE")
    current_start = anchor_date - timedelta(days=29)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=29)

    current_projects = _between_dates(projects, "START_DATE", current_start, anchor_date)
    previous_projects = _between_dates(projects, "START_DATE", previous_start, previous_end)

    return DevelopmentActivitySnapshot(
        anchor_date=anchor_date.isoformat(),
        window_days=30,
        projects_started=_count_metric(current_projects.height, previous_projects.height),
    )


@router.get("/market-summary", response_model=MarketSummaryResponse)
def get_market_summary(state: AppState = Depends(get_state)) -> MarketSummaryResponse:
    cached = _get_cached_market_summary()
    if cached is not None:
        return cached

    activity = get_market_activity(state)
    development = get_development_activity(state)
    kpis = get_kpis(state)
    project_status = get_project_status(state)
    monthly_launches = get_monthly_project_launches(state)

    facts = _build_market_summary_facts(
        state=state,
        activity=activity,
        development=development,
        kpis=kpis,
        project_status=project_status,
        monthly_launches=monthly_launches,
    )
    fallback = _build_fallback_market_summary(facts)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = _get_gemini_model()

    if not api_key:
        fallback.note = "Set GEMINI_API_KEY on the backend to enable Gemini-generated copy."
        return _store_market_summary_cache(fallback)

    prompt = _build_gemini_market_summary_prompt(facts)
    generated = _generate_market_summary_with_gemini(api_key=api_key, model=model_name, prompt=prompt)
    if generated is None:
        fallback.note = "Gemini was unavailable, so the summary is using deterministic dashboard copy."
        return _store_market_summary_cache(fallback)

    response = MarketSummaryResponse(
        provider="gemini",
        model=generated["model"],
        generated_at=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        is_fallback=False,
        note=None,
        summary=generated["summary"],
        sections=[
            MarketSummarySection(title=section["title"], body=section["body"])
            for section in generated["sections"]
        ],
        sources=[
            MarketSummarySource(title=source["title"], url=source["url"])
            for source in generated["sources"]
        ],
    )
    return _store_market_summary_cache(response)


@router.get("/market-news", response_model=MarketNewsResponse)
def get_market_news(
    refresh: bool = Query(False),
    state: AppState = Depends(get_state),
) -> MarketNewsResponse:
    if not refresh:
        cached = _get_cached_market_news()
        if cached is not None:
            return cached

    activity = get_market_activity(state)
    development = get_development_activity(state)
    kpis = get_kpis(state)
    project_status = get_project_status(state)
    monthly_launches = get_monthly_project_launches(state)

    facts = _build_market_summary_facts(
        state=state,
        activity=activity,
        development=development,
        kpis=kpis,
        project_status=project_status,
        monthly_launches=monthly_launches,
    )
    fallback = _build_fallback_market_news()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = _get_gemini_model()

    if not api_key:
        fallback.note = "Set GEMINI_API_KEY on the backend to enable Gemini-generated market news."
        return _store_market_news_cache(fallback)

    prompt = _build_market_news_prompt(facts)
    generated = _generate_market_news_with_gemini(api_key=api_key, model=model_name, prompt=prompt)
    if generated is None:
        cached = _get_cached_market_news()
        if cached is not None:
            return cached.model_copy(update={"note": "Refresh failed, showing the previously cached market news."})

        fallback.note = "Gemini was unavailable, so market news could not be refreshed."
        return _store_market_news_cache(fallback)

    response = MarketNewsResponse(
        provider="gemini",
        model=generated["model"],
        generated_at=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        is_fallback=False,
        note=None,
        news_items=[
            MarketNewsItem(headline=item["headline"], summary=item["summary"])
            for item in generated["news_items"]
        ],
        sources=[
            MarketSummarySource(title=source["title"], url=source["url"])
            for source in generated["sources"]
        ],
    )
    return _store_market_news_cache(response)


@router.get("/monthly-project-launches", response_model=list[MonthlyProjectLaunchPoint])
def get_monthly_project_launches(state: AppState = Depends(get_state)) -> list[MonthlyProjectLaunchPoint]:
    projects = state.projects.filter(pl.col("START_DATE").is_not_null())
    latest_start_date = _get_latest_date(projects, "START_DATE")
    if not _is_last_day_of_month(latest_start_date):
        cutoff_date = latest_start_date.replace(day=1) - timedelta(days=1)
        projects = projects.filter(pl.col("START_DATE") <= cutoff_date)
    monthly = (
        projects.with_columns(pl.col("START_DATE").dt.truncate("1mo").alias("MONTH"))
        .group_by("MONTH")
        .agg(
            pl.len().alias("projects_started"),
            (pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).fill_null(0).sum() / 1_000_000).alias("project_value_m"),
            pl.col("CNT_UNIT").cast(pl.Float64, strict=False).fill_null(0).sum().alias("units_announced"),
        )
        .sort("MONTH")
        .tail(WEEKLY_POINTS_LIMIT)
    )
    return [
        MonthlyProjectLaunchPoint(
            month=str(row["MONTH"]),
            projects_started=int(row["projects_started"]),
            project_value_m=float(row["project_value_m"] or 0),
            units_announced=float(row["units_announced"] or 0),
        )
        for row in monthly.iter_rows(named=True)
    ]


@router.get("/top-areas-price", response_model=list[AreaPricePoint])
def get_top_areas_price(
    min_transactions: int = 10,
    top: int = 20,
    state: AppState = Depends(get_state),
) -> list[AreaPricePoint]:
    tx = state.transactions
    if "AREA_EN" not in tx.columns:
        return []
    by_area = (
        tx.filter(pl.col("AREA_EN").is_not_null())
        .group_by("AREA_EN")
        .agg(
            pl.col("PRICE_PER_SQM").median().alias("median_price_sqm"),
            pl.len().alias("transaction_count"),
        )
        .filter(pl.col("transaction_count") >= min_transactions)
        .sort("median_price_sqm", descending=True)
        .head(top)
    )
    return [
        AreaPricePoint(
            area=row["AREA_EN"],
            median_price_sqm=float(row["median_price_sqm"] or 0),
            transaction_count=int(row["transaction_count"]),
        )
        for row in by_area.iter_rows(named=True)
    ]


@router.get("/top-areas-volume", response_model=list[TopAreaVolume])
def get_top_areas_volume(
    top: int = 10,
    state: AppState = Depends(get_state),
) -> list[TopAreaVolume]:
    tx = state.transactions
    if "AREA_EN" not in tx.columns:
        return []
    by_area = (
        tx.filter(pl.col("AREA_EN").is_not_null())
        .group_by("AREA_EN")
        .agg((pl.col("TRANS_VALUE").sum() / 1_000_000).alias("sales_value_m"))
        .sort("sales_value_m", descending=True)
        .head(top)
    )
    return [
        TopAreaVolume(area=row["AREA_EN"], sales_value_m=float(row["sales_value_m"] or 0))
        for row in by_area.iter_rows(named=True)
    ]


@router.get("/project-status", response_model=list[ProjectStatusCount])
def get_project_status(state: AppState = Depends(get_state)) -> list[ProjectStatusCount]:
    counts = (
        state.projects
        .group_by("PROJECT_STATUS")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    return [
        ProjectStatusCount(status=str(row["PROJECT_STATUS"] or "Unknown"), count=int(row["count"]))
        for row in counts.iter_rows(named=True)
    ]


@router.get("/trending-development-areas", response_model=list[TrendingDevelopmentArea])
def get_trending_development_areas(
    top: int = 8,
    window_days: int = 90,
    state: AppState = Depends(get_state),
) -> list[TrendingDevelopmentArea]:
    projects = state.projects
    if "AREA_EN" not in projects.columns or "START_DATE" not in projects.columns:
        return []

    projects = projects.filter(
        pl.col("AREA_EN").is_not_null()
        & (pl.col("AREA_EN").cast(pl.Utf8).str.strip_chars() != "")
        & pl.col("START_DATE").is_not_null()
    )
    if projects.height == 0:
        return []

    anchor_date = _get_latest_date(projects, "START_DATE")
    recent_projects = _between_dates(
        projects,
        "START_DATE",
        anchor_date - timedelta(days=max(window_days - 1, 0)),
        anchor_date,
    )

    by_area = (
        recent_projects.group_by("AREA_EN")
        .agg(
            pl.len().alias("projects_started"),
            (pl.col("PROJECT_STATUS") == "ACTIVE").sum().alias("active_projects"),
            (pl.col("PROJECT_STATUS") == "PENDING").sum().alias("pending_projects"),
            pl.col("CNT_UNIT").cast(pl.Float64, strict=False).fill_null(0).sum().alias("units_announced"),
            pl.when(pl.col("PROJECT_STATUS") == "ACTIVE").then(pl.col("CNT_UNIT").cast(pl.Float64, strict=False).fill_null(0)).otherwise(0).sum().alias("active_units_announced"),
            pl.when(pl.col("PROJECT_STATUS") == "PENDING").then(pl.col("CNT_UNIT").cast(pl.Float64, strict=False).fill_null(0)).otherwise(0).sum().alias("pending_units_announced"),
            (pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).fill_null(0).sum() / 1_000_000).alias("project_value_m"),
            (pl.when(pl.col("PROJECT_STATUS") == "ACTIVE").then(pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).fill_null(0)).otherwise(0).sum() / 1_000_000).alias("active_project_value_m"),
            (pl.when(pl.col("PROJECT_STATUS") == "PENDING").then(pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).fill_null(0)).otherwise(0).sum() / 1_000_000).alias("pending_project_value_m"),
        )
        .sort(
            by=["projects_started", "units_announced", "project_value_m", "AREA_EN"],
            descending=[True, True, True, False],
        )
        .head(top)
    )
    return [
        TrendingDevelopmentArea(
            area=str(row["AREA_EN"]),
            projects_started=int(row["projects_started"]),
            active_projects=int(row["active_projects"] or 0),
            pending_projects=int(row["pending_projects"] or 0),
            units_announced=float(row["units_announced"] or 0),
            active_units_announced=float(row["active_units_announced"] or 0),
            pending_units_announced=float(row["pending_units_announced"] or 0),
            project_value_m=float(row["project_value_m"] or 0),
            active_project_value_m=float(row["active_project_value_m"] or 0),
            pending_project_value_m=float(row["pending_project_value_m"] or 0),
        )
        for row in by_area.iter_rows(named=True)
    ]


@router.get("/filter-options", response_model=FilterOptions)
def get_filter_options(
    developer: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    state: AppState = Depends(get_state),
) -> FilterOptions:
    tx = state.transactions

    if date_from:
        tx = tx.filter(pl.col("INSTANCE_DATE").cast(pl.Utf8) >= date_from)
    if date_to:
        tx = tx.filter(pl.col("INSTANCE_DATE").cast(pl.Utf8) <= date_to)

    developers_tx = tx.filter(pl.col("AREA_EN") == area) if area and "AREA_EN" in tx.columns else tx
    areas_tx = tx.filter(pl.col("DEVELOPER_EN") == developer) if developer else tx
    prop_types_tx = tx
    if developer:
        prop_types_tx = prop_types_tx.filter(pl.col("DEVELOPER_EN") == developer)
    if area and "AREA_EN" in prop_types_tx.columns:
        prop_types_tx = prop_types_tx.filter(pl.col("AREA_EN") == area)

    developers = sorted(developers_tx["DEVELOPER_EN"].drop_nulls().unique().to_list())
    areas = sorted(areas_tx["AREA_EN"].drop_nulls().unique().to_list()) if "AREA_EN" in areas_tx.columns else []
    prop_types = sorted(prop_types_tx["PROP_TYPE_EN"].drop_nulls().unique().to_list()) if "PROP_TYPE_EN" in prop_types_tx.columns else []
    return FilterOptions(developers=developers, areas=areas, prop_types=prop_types)


def _opt_float(v: object) -> Optional[float]:
    return float(v) if v is not None else None


def _get_cached_market_summary() -> Optional[MarketSummaryResponse]:
    with _MARKET_SUMMARY_CACHE_LOCK:
        if _MARKET_SUMMARY_CACHE is None or _MARKET_SUMMARY_CACHE_AT is None:
            return None
        if datetime.utcnow() - _MARKET_SUMMARY_CACHE_AT >= MARKET_SUMMARY_CACHE_TTL:
            return None
        return _MARKET_SUMMARY_CACHE.model_copy(deep=True)


def _store_market_summary_cache(response: MarketSummaryResponse) -> MarketSummaryResponse:
    with _MARKET_SUMMARY_CACHE_LOCK:
        global _MARKET_SUMMARY_CACHE, _MARKET_SUMMARY_CACHE_AT
        _MARKET_SUMMARY_CACHE = response.model_copy(deep=True)
        _MARKET_SUMMARY_CACHE_AT = datetime.utcnow()
        return _MARKET_SUMMARY_CACHE.model_copy(deep=True)


def _get_cached_market_news() -> Optional[MarketNewsResponse]:
    with _MARKET_NEWS_CACHE_LOCK:
        if _MARKET_NEWS_CACHE is None:
            return None
        return _MARKET_NEWS_CACHE.model_copy(deep=True)


def _store_market_news_cache(response: MarketNewsResponse) -> MarketNewsResponse:
    with _MARKET_NEWS_CACHE_LOCK:
        global _MARKET_NEWS_CACHE
        _MARKET_NEWS_CACHE = response.model_copy(deep=True)
        return _MARKET_NEWS_CACHE.model_copy(deep=True)


def _build_market_summary_facts(
    state: AppState,
    activity: MarketActivitySnapshot,
    development: DevelopmentActivitySnapshot,
    kpis: MarketKPIs,
    project_status: list[ProjectStatusCount],
    monthly_launches: list[MonthlyProjectLaunchPoint],
) -> dict:
    status_counts = {item.status.upper(): item.count for item in project_status}
    lead_developer = _get_lead_active_developer(state)
    latest_launch = monthly_launches[-1] if monthly_launches else None
    return {
        "anchor_date": activity.anchor_date,
        "window_days": activity.window_days,
        "sales_count": activity.sales_count.model_dump(),
        "rent_count": activity.rent_count.model_dump(),
        "sales_price_per_sqm": activity.sales_price_per_sqm.model_dump(),
        "rent_price_per_sqm": activity.rent_price_per_sqm.model_dump(),
        "projects_started": development.projects_started.model_dump(),
        "total_projects": kpis.total_projects,
        "active_projects": status_counts.get("ACTIVE", 0),
        "pending_projects": status_counts.get("PENDING", 0),
        "units_in_pipeline": kpis.units_in_pipeline,
        "latest_monthly_launch": None
        if latest_launch is None
        else {
            "month": latest_launch.month,
            "projects_started": latest_launch.projects_started,
            "project_value_m": latest_launch.project_value_m,
            "units_announced": latest_launch.units_announced,
        },
        "lead_developer": lead_developer,
    }


def _build_fallback_market_summary(facts: dict) -> MarketSummaryResponse:
    sales_metric = facts["sales_count"]
    rent_metric = facts["rent_count"]
    sale_price_metric = facts["sales_price_per_sqm"]
    rent_price_metric = facts["rent_price_per_sqm"]
    projects_metric = facts["projects_started"]
    latest_launch = facts["latest_monthly_launch"]
    lead_developer = facts["lead_developer"]

    development_bits = [
        f"The pipeline logged {int(projects_metric['last_30d']):,} project starts in the latest {facts['window_days']}-day window, {_fmt_delta_phrase(projects_metric.get('delta_pct'))} versus the prior period.",
        f"{int(facts['active_projects']):,} projects are active, {int(facts['pending_projects']):,} are pending, and the pipeline now covers {int(facts['units_in_pipeline']):,} units.",
    ]
    if latest_launch is not None:
        development_bits.append(
            f"In {_fmt_month_label(latest_launch['month'])}, launches accounted for AED {latest_launch['project_value_m']:.1f}M across {int(latest_launch['units_announced']):,} units."
        )
    if lead_developer is not None:
        development_bits.append(
            f"{lead_developer['developer']} leads on active pipeline with {int(lead_developer['active']):,} active projects."
        )

    return MarketSummaryResponse(
        provider="fallback",
        model=None,
        generated_at=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        is_fallback=True,
        note=None,
        summary=f"Market windows ending {facts['anchor_date']} show current sales, rental, and development momentum across Dubai.",
        sections=[
            MarketSummarySection(
                title="Market Activity",
                body=(
                    f"Sales closed at {int(sales_metric['last_30d']):,} deals, {_fmt_delta_phrase(sales_metric.get('delta_pct'))} versus the prior 30-day window. "
                    f"Rentals reached {int(rent_metric['last_30d']):,} contracts, {_fmt_delta_phrase(rent_metric.get('delta_pct'))}."
                ),
            ),
            MarketSummarySection(
                title="Pricing",
                body=(
                    f"Sale pricing is averaging {_fmt_price_per_sqm(sale_price_metric)}, {_fmt_delta_phrase(sale_price_metric.get('delta_pct'))}. "
                    f"Rental pricing is at {_fmt_price_per_sqm(rent_price_metric)}, {_fmt_delta_phrase(rent_price_metric.get('delta_pct'))}."
                ),
            ),
            MarketSummarySection(
                title="Development",
                body=" ".join(development_bits),
            ),
        ],
        sources=[],
    )


def _build_fallback_market_news() -> MarketNewsResponse:
    return MarketNewsResponse(
        provider="fallback",
        model=None,
        generated_at=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        is_fallback=True,
        note=None,
        news_items=[],
        sources=[],
    )


def _build_gemini_market_summary_prompt(facts: dict) -> str:
    return (
        "You are writing a concise executive market brief for a Dubai real-estate dashboard. "
        "First, use Google Search to gather at least one current external signal about Dubai property-market performance from a reputable source. "
        "Then write the brief using the supplied facts as the primary numeric basis and the search results only for broader market context. "
        "Do not invent statistics, causes, forecasts, or area-level detail that is not present in the facts or grounding sources. "
        "Return valid JSON only with this exact shape: "
        '{"summary":"string","sections":[{"title":"Market Activity","body":"string"},{"title":"Pricing","body":"string"},{"title":"Development","body":"string"}]}'
        " The summary should be one sentence under 160 characters. "
        "Each body should be 1-2 sentences and read like analyst copy, not bullet fragments. "
        "If a delta percentage is null, avoid percentage language. "
        "If search does not return useful context, stay close to the facts instead of speculating. "
        "Do not mention source names in the prose. Grounding sources will be surfaced separately. "
        "Facts: "
        f"{json.dumps(facts, ensure_ascii=True)}"
    )


def _build_market_news_prompt(facts: dict) -> str:
    return (
        "You are curating latest Dubai property market news for a dashboard. "
        "Use Google Search to find recent, relevant external coverage about Dubai real-estate market performance. "
        "Use the supplied facts only as context for relevance, not as the main content of the news feed. "
        "Return valid JSON only with this exact shape: "
        '{"news_items":[{"headline":"string","summary":"string"}]}'
        " Include 2 or 3 items. "
        "Each headline should be short and specific. "
        "Each summary should be one sentence, concise, and reflect the article's core takeaway. "
        "Do not invent articles or cite unnamed sources. "
        "Facts: "
        f"{json.dumps(facts, ensure_ascii=True)}"
    )


def _get_gemini_model() -> str:
    configured = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    return configured.removeprefix("models/") or "gemini-2.0-flash"


def _extract_json_payload(text: str) -> Optional[dict]:
    candidates = [text.strip()]

    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            candidates.append("\n".join(lines[1:-1]).strip())

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(stripped[start:end + 1])

    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return None


def _generate_gemini_json_response(
    client: genai.Client,
    model: str,
    prompt: str,
    *,
    use_search: bool,
) -> Optional[tuple[dict, list[dict[str, str]]]]:
    config_kwargs: dict[str, object] = {
        "temperature": 0.4,
    }
    if use_search:
        config_kwargs["tools"] = [genai_types.Tool(google_search=genai_types.GoogleSearch())]
    else:
        config_kwargs["response_mime_type"] = "application/json"

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=genai_types.GenerateContentConfig(**config_kwargs),
    )
    text = (response.text or "").strip()
    if not text:
        logger.warning("Gemini response did not include text candidates for model %s", model)
        return None

    parsed = _extract_json_payload(text)
    if parsed is None:
        logger.warning("Gemini returned non-JSON content for model %s", model)
        return None

    sources = _extract_grounding_sources(response) if use_search else []
    return parsed, sources


def _generate_market_summary_with_gemini(api_key: str, model: str, prompt: str) -> Optional[dict]:
    client = genai.Client(api_key=api_key)
    models_to_try = [model]
    if model != "gemini-2.0-flash":
        models_to_try.append("gemini-2.0-flash")

    for candidate_model in models_to_try:
        for use_search in (True, False):
            try:
                generated = _generate_gemini_json_response(
                    client,
                    candidate_model,
                    prompt,
                    use_search=use_search,
                )
            except (genai_errors.APIError, ValueError, TimeoutError) as exc:
                logger.warning(
                    "Gemini market summary request failed for model %s (search=%s): %s",
                    candidate_model,
                    use_search,
                    exc,
                )
                continue

            if generated is None:
                continue

            parsed, sources = generated
            normalized = _normalize_market_summary_payload(parsed)
            if normalized is None:
                logger.warning(
                    "Gemini market summary normalization failed for model %s (search=%s)",
                    candidate_model,
                    use_search,
                )
                continue

            normalized["model"] = candidate_model
            normalized["sources"] = sources
            return normalized

    return None


def _generate_market_news_with_gemini(api_key: str, model: str, prompt: str) -> Optional[dict]:
    client = genai.Client(api_key=api_key)
    models_to_try = [model]
    if model != "gemini-2.0-flash":
        models_to_try.append("gemini-2.0-flash")

    for candidate_model in models_to_try:
        for use_search in (True, False):
            try:
                generated = _generate_gemini_json_response(
                    client,
                    candidate_model,
                    prompt,
                    use_search=use_search,
                )
            except (genai_errors.APIError, ValueError, TimeoutError) as exc:
                logger.warning(
                    "Gemini market news request failed for model %s (search=%s): %s",
                    candidate_model,
                    use_search,
                    exc,
                )
                continue

            if generated is None:
                continue

            parsed, sources = generated
            normalized = _normalize_market_news_payload(parsed)
            if normalized is None:
                continue

            normalized["model"] = candidate_model
            normalized["sources"] = sources
            return normalized

    return None


def _normalize_market_summary_payload(parsed: object) -> Optional[dict]:
    if not isinstance(parsed, dict):
        logger.warning("Gemini market summary: payload is not a dict: %r", type(parsed))
        return None

    summary = parsed.get("summary")
    sections = parsed.get("sections")
    if not isinstance(summary, str) or not isinstance(sections, list) or len(sections) == 0:
        logger.warning(
            "Gemini market summary: unexpected shape — summary=%r, sections=%r",
            type(summary),
            [type(s) for s in sections] if isinstance(sections, list) else sections,
        )
        return None

    normalized_sections = []
    for section in sections:
        if not isinstance(section, dict):
            return None
        title = section.get("title")
        body = section.get("body")
        if not isinstance(title, str) or not isinstance(body, str):
            return None
        normalized_sections.append({"title": title.strip(), "body": body.strip()})

    cleaned_summary = summary.strip()
    if not cleaned_summary:
        return None

    return {"summary": cleaned_summary, "sections": normalized_sections}


def _normalize_market_news_payload(parsed: object) -> Optional[dict]:
    if not isinstance(parsed, dict):
        return None

    news_items = parsed.get("news_items")
    if not isinstance(news_items, list):
        return None

    normalized_items = []
    for item in news_items[:3]:
        if not isinstance(item, dict):
            return None
        headline = item.get("headline")
        summary = item.get("summary")
        if not isinstance(headline, str) or not isinstance(summary, str):
            return None
        cleaned_headline = headline.strip()
        cleaned_summary = summary.strip()
        if not cleaned_headline or not cleaned_summary:
            continue
        normalized_items.append({"headline": cleaned_headline, "summary": cleaned_summary})

    return {"news_items": normalized_items}


def _extract_grounding_sources(response: object) -> list[dict]:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []

    grounding = getattr(candidates[0], "grounding_metadata", None)
    chunks = getattr(grounding, "grounding_chunks", None) or []
    sources = []
    seen = set()
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        title = getattr(web, "title", None)
        url = getattr(web, "uri", None)
        if not title or not url or url in seen:
            continue
        seen.add(url)
        sources.append({"title": title, "url": url})
    return sources


def _get_lead_active_developer(state: AppState) -> Optional[dict]:
    projects = state.projects
    if projects.height == 0 or "DEVELOPER_EN" not in projects.columns:
        return None
    leaderboard = (
        projects.filter(pl.col("DEVELOPER_EN").is_not_null())
        .group_by("DEVELOPER_EN")
        .agg(
            (pl.col("PROJECT_STATUS") == "ACTIVE").sum().alias("active"),
            pl.len().alias("total_projects"),
        )
        .sort(["active", "total_projects"], descending=[True, True])
    )
    if leaderboard.height == 0:
        return None
    row = leaderboard.row(0, named=True)
    return {
        "developer": str(row["DEVELOPER_EN"] or ""),
        "active": int(row["active"] or 0),
        "total_projects": int(row["total_projects"] or 0),
    }


def _get_anchor_date(state: AppState) -> date:
    candidates = [
        state.transactions["INSTANCE_DATE"].max() if state.transactions.height > 0 else None,
        state.rents["REGISTRATION_DATE"].max() if state.rents.height > 0 else None,
    ]
    valid_dates = [value for value in candidates if value is not None]
    if not valid_dates:
        raise ValueError("No dated records available for overview market activity")
    return max(valid_dates)


def _get_latest_date(df: pl.DataFrame, col: str) -> date:
    if df.height == 0 or col not in df.columns:
        raise ValueError(f"No dated records available for {col}")
    latest = df[col].max()
    if latest is None:
        raise ValueError(f"No dated records available for {col}")
    return latest


def _between_dates(df: pl.DataFrame, date_col: str, start_date: date, end_date: date) -> pl.DataFrame:
    return df.filter(pl.col(date_col).is_between(start_date, end_date, closed="both"))


def _count_metric(current: int, previous: int) -> RollingCountMetric:
    delta = current - previous
    return RollingCountMetric(
        last_30d=current,
        previous_30d=previous,
        delta=delta,
        delta_pct=_delta_pct(current, previous),
    )


def _float_metric(current: Optional[float], previous: Optional[float]) -> RollingFloatMetric:
    delta = None if current is None or previous is None else current - previous
    return RollingFloatMetric(
        last_30d=current,
        previous_30d=previous,
        delta=delta,
        delta_pct=_delta_pct(current, previous),
    )


def _mean_or_none(df: pl.DataFrame, col: str) -> Optional[float]:
    if df.height == 0 or col not in df.columns:
        return None
    return _opt_float(df[col].mean())


def _fmt_delta_phrase(delta_pct: Optional[float]) -> str:
    if delta_pct is None or abs(delta_pct) < 0.1:
        return "holding roughly steady"
    direction = "up" if delta_pct > 0 else "down"
    return f"{direction} {abs(delta_pct):.1f}%"


def _fmt_price_per_sqm(metric: dict) -> str:
    value = metric.get("last_30d")
    if value is None:
        return "an unavailable level per sqm"
    return f"AED {float(value):,.0f}/sqm"


def _fmt_month_label(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%b %Y")
    except ValueError:
        return value[:7]


def _delta_pct(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous in (None, 0):
        return None
    return float(((current - previous) / previous) * 100)


def _last_completed_sunday(today: Optional[date] = None) -> date:
    reference = today or date.today()
    current_week_start = reference - timedelta(days=reference.weekday())
    return current_week_start - timedelta(days=1)


def _is_last_day_of_month(value: date) -> bool:
    return (value + timedelta(days=1)).day == 1
