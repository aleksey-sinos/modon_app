from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


# ── Overview ──────────────────────────────────────────────────────────────────

class MarketKPIs(BaseModel):
    total_projects: int
    active_projects: int
    units_in_pipeline: int
    total_sales_value: float
    median_price_sqm: Optional[float]


class MonthlySalesPoint(BaseModel):
    month: str
    sales_value_m: float
    transaction_count: int


class WeeklySalesPoint(BaseModel):
    week: str
    sales_value_m: float
    transaction_count: int


class WeeklyRentPoint(BaseModel):
    week: str
    annual_rent_m: float
    contract_count: int


class AreaPricePoint(BaseModel):
    area: str
    median_price_sqm: float
    transaction_count: int


class ProjectStatusCount(BaseModel):
    status: str
    count: int


class TrendingDevelopmentArea(BaseModel):
    area: str
    projects_started: int
    active_projects: int
    pending_projects: int
    units_announced: float
    active_units_announced: float
    pending_units_announced: float
    project_value_m: float
    active_project_value_m: float
    pending_project_value_m: float


class TopAreaVolume(BaseModel):
    area: str
    sales_value_m: float


class RollingCountMetric(BaseModel):
    last_30d: int
    previous_30d: int
    delta: int
    delta_pct: Optional[float]


class RollingFloatMetric(BaseModel):
    last_30d: Optional[float]
    previous_30d: Optional[float]
    delta: Optional[float]
    delta_pct: Optional[float]


class MarketActivitySnapshot(BaseModel):
    anchor_date: str
    window_days: int
    sales_count: RollingCountMetric
    rent_count: RollingCountMetric
    sales_price_per_sqm: RollingFloatMetric
    rent_price_per_sqm: RollingFloatMetric


class DevelopmentActivitySnapshot(BaseModel):
    anchor_date: str
    window_days: int
    projects_started: RollingCountMetric


class MarketSummarySection(BaseModel):
    title: str
    body: str


class MarketSummarySource(BaseModel):
    title: str
    url: str


class MarketNewsItem(BaseModel):
    headline: str
    summary: str


class MarketNewsResponse(BaseModel):
    provider: str
    model: Optional[str]
    generated_at: str
    is_fallback: bool
    note: Optional[str]
    news_items: list[MarketNewsItem]
    sources: list[MarketSummarySource]


class MarketSummaryResponse(BaseModel):
    provider: str
    model: Optional[str]
    generated_at: str
    is_fallback: bool
    note: Optional[str]
    summary: str
    sections: list[MarketSummarySection]
    sources: list[MarketSummarySource]


class MonthlyProjectLaunchPoint(BaseModel):
    month: str
    projects_started: int
    project_value_m: float
    units_announced: float


# ── Developers ────────────────────────────────────────────────────────────────

class DeveloperRow(BaseModel):
    developer: str
    total_projects: int
    active: int
    pending: int
    portfolio_value: Optional[float]
    active_portfolio_value: Optional[float]
    pending_portfolio_value: Optional[float]
    total_units: Optional[float]
    active_units: Optional[float]
    pending_units: Optional[float]
    sales_count: int
    sales_value: Optional[float]
    rent_count: int
    rent_value: Optional[float]
    median_price_sqm: Optional[float]
    median_rent_sqm: Optional[float]
    gross_yield: Optional[float]


class DeveloperProject(BaseModel):
    project: str
    status: Optional[str]
    percent_completed: Optional[float]
    start_date: Optional[str]
    end_date: Optional[str]
    project_value: Optional[float]
    units: Optional[float]


class DeveloperDetail(BaseModel):
    developer: str
    kpis: DeveloperRow
    projects: list[DeveloperProject]
    monthly_sales: list[MonthlySalesPoint]


# ── Transactions ──────────────────────────────────────────────────────────────

class TransactionKPIs(BaseModel):
    total_transactions: int
    total_sales_value: float
    median_price_sqm: Optional[float]
    avg_transaction_value: Optional[float]


class TransactionRow(BaseModel):
    transaction_number: Optional[str]
    instance_date: Optional[str]
    developer: Optional[str]
    project: Optional[str]
    area: Optional[str]
    prop_type: Optional[str]
    trans_value: Optional[float]
    effective_area: Optional[float]
    price_per_sqm: Optional[float]
    is_offplan: Optional[str]
    rooms: Optional[str]


class PaginatedTransactions(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TransactionRow]


class MonthlyTrendPoint(BaseModel):
    month: str
    value: float


class TransactionAreaHeatmapPoint(BaseModel):
    area: str
    transaction_count: int
    sales_value_m: float


class MortgageKPIs(BaseModel):
    total_mortgage_transactions: int
    total_mortgage_value: float
    avg_mortgage_value: Optional[float]


class MortgageProcedureRow(BaseModel):
    procedure: str
    transaction_count: int
    total_value_m: float
    avg_value: Optional[float]


class MortgageTransactionRow(BaseModel):
    transaction_number: Optional[str]
    instance_date: Optional[str]
    procedure: Optional[str]
    mortgage_value: Optional[float]
    row_count: int
    area: Optional[str]
    prop_type: Optional[str]
    is_offplan: Optional[str]


class PaginatedMortgageTransactions(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[MortgageTransactionRow]


# ── Properties ────────────────────────────────────────────────────────────────

class PropertyTypeRow(BaseModel):
    prop_type: str
    transaction_count: int
    sales_value_m: float
    median_price_sqm: Optional[float]
    median_area_sqm: Optional[float]


class PropertyTypeTrendPoint(BaseModel):
    month: str
    prop_type: str
    median_price_sqm: float


# ── Rents ─────────────────────────────────────────────────────────────────────

class RentKPIs(BaseModel):
    total_contracts: int
    total_annual_rent: float
    median_rent_sqm: Optional[float]
    avg_annual_contract: Optional[float]


class RentRow(BaseModel):
    registration_date: Optional[str]
    developer: Optional[str]
    project: Optional[str]
    area: Optional[str]
    prop_type: Optional[str]
    annual_amount: Optional[float]
    effective_area: Optional[float]
    rent_per_sqm: Optional[float]
    rooms: Optional[str]


class PaginatedRents(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RentRow]


class RentByTypeRow(BaseModel):
    prop_type: str
    contract_count: int
    annual_rent_m: float
    median_rent_sqm: Optional[float]


class RentTrendPoint(BaseModel):
    month: str
    prop_type: str
    median_rent_sqm: float


class RentByAreaRow(BaseModel):
    area: str
    median_rent_sqm: float
    contract_count: int


class RentAreaHeatmapPoint(BaseModel):
    area: str
    contract_count: int
    annual_rent_m: float


# ── Supply ────────────────────────────────────────────────────────────────────

class SupplyKPIs(BaseModel):
    total_land_parcels: int
    total_land_area_sqm: Optional[float]
    active_projects: int
    pending_projects: int
    units_in_pipeline: int


class LandTypeRow(BaseModel):
    land_type: str
    parcels: int
    total_area_sqm: Optional[float]


class SubTypeRow(BaseModel):
    sub_type: str
    parcels: int


class PipelineByYearRow(BaseModel):
    completion_year: int
    units: float
    projects: int


class CompletionBandRow(BaseModel):
    band: str
    projects: int


class SupplyAreaHeatmapPoint(BaseModel):
    area: str
    year: int
    project_count: int
    units: float


class LocationContextRow(BaseModel):
    name: str
    contract_count: int
    annual_rent_m: float
    median_rent_sqm: Optional[float]
    unique_areas: int
    current_median_rent_sqm: Optional[float]
    previous_median_rent_sqm: Optional[float]
    performance_30d_pct: Optional[float]
    volatility_30d_pct: Optional[float]


# ── Shared ────────────────────────────────────────────────────────────────────

class FilterOptions(BaseModel):
    developers: list[str]
    areas: list[str]
    prop_types: list[str]
