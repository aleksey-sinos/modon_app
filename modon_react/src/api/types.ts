// ─── Common filter params ─────────────────────────────────────────────────────
export interface CommonFilters {
  developer?: string;
  area?: string;
  prop_type?: string;
  date_from?: string;
  date_to?: string;
}

// ─── Overview ─────────────────────────────────────────────────────────────────
export interface OverviewKPIs {
  total_projects: number;
  active_projects: number;
  units_in_pipeline: number;
  total_sales_value: number;
  median_price_sqm: number;
}

export interface MonthlySalesItem {
  month: string;
  sales_value_m: number;
  transaction_count: number;
}

export interface WeeklySalesItem {
  week: string;
  sales_value_m: number;
  transaction_count: number;
}

export type SalesSegment = 'total' | 'off-plan' | 'ready';

export interface WeeklyRentItem {
  week: string;
  annual_rent_m: number;
  contract_count: number;
}

export interface AreaPriceItem {
  area: string;
  median_price_sqm: number;
  transaction_count: number;
}

export interface AreaVolumeItem {
  area: string;
  sales_value_m: number;
}

export interface ProjectStatusItem {
  status: string;
  count: number;
}

export interface TrendingDevelopmentAreaItem {
  area: string;
  projects_started: number;
  active_projects: number;
  pending_projects: number;
  units_announced: number;
  active_units_announced: number;
  pending_units_announced: number;
  project_value_m: number;
  active_project_value_m: number;
  pending_project_value_m: number;
}

export interface RollingCountMetric {
  last_30d: number;
  previous_30d: number;
  delta: number;
  delta_pct: number | null;
}

export interface RollingFloatMetric {
  last_30d: number | null;
  previous_30d: number | null;
  delta: number | null;
  delta_pct: number | null;
}

export interface MarketActivitySnapshot {
  anchor_date: string;
  window_days: number;
  sales_count: RollingCountMetric;
  rent_count: RollingCountMetric;
  sales_price_per_sqm: RollingFloatMetric;
  rent_price_per_sqm: RollingFloatMetric;
}

export interface DevelopmentActivitySnapshot {
  anchor_date: string;
  window_days: number;
  projects_started: RollingCountMetric;
}

export interface MarketSummarySection {
  title: string;
  body: string;
}

export interface MarketSummarySource {
  title: string;
  url: string;
}

export interface MarketNewsItem {
  headline: string;
  summary: string;
}

export interface MarketNewsResponse {
  provider: string;
  model: string | null;
  generated_at: string;
  is_fallback: boolean;
  note: string | null;
  news_items: MarketNewsItem[];
  sources: MarketSummarySource[];
}

export interface MarketSummaryResponse {
  provider: string;
  model: string | null;
  generated_at: string;
  is_fallback: boolean;
  note: string | null;
  summary: string;
  sections: MarketSummarySection[];
  sources: MarketSummarySource[];
}

export interface MonthlyProjectLaunchItem {
  month: string;
  projects_started: number;
  project_value_m: number;
  units_announced: number;
}

export interface FilterOptions {
  developers: string[];
  areas: string[];
  prop_types: string[];
}

// ─── Developers ───────────────────────────────────────────────────────────────
export interface DeveloperRow {
  developer: string;
  total_projects: number;
  active: number;
  pending: number;
  portfolio_value: number;
  active_portfolio_value: number | null;
  pending_portfolio_value: number | null;
  total_units: number | null;
  active_units: number | null;
  pending_units: number | null;
  sales_count: number;
  sales_value: number;
  rent_count: number;
  rent_value: number;
  median_price_sqm: number | null;
  median_rent_sqm: number | null;
  gross_yield: number | null;
}

export interface DeveloperProject {
  project: string;
  status: string;
  percent_completed: number | null;
  start_date: string | null;
  end_date: string | null;
  project_value: number | null;
  units: number | null;
}

export interface DeveloperMonthlySales {
  month: string;
  sales_value_m: number;
  transaction_count: number;
}

export interface DeveloperDetail {
  developer: string;
  kpis: DeveloperRow;
  projects: DeveloperProject[];
  monthly_sales: DeveloperMonthlySales[];
}

// ─── Transactions ─────────────────────────────────────────────────────────────
export interface TransactionKPIs {
  total_transactions: number;
  total_sales_value: number;
  median_price_sqm: number;
  avg_transaction_value: number;
}

export interface TransactionAreaHeatmapItem {
  area: string;
  transaction_count: number;
  sales_value_m: number;
}

export interface MonthlyValueItem {
  month: string;
  value: number;
}

export interface TransactionItem {
  transaction_number: string;
  instance_date: string;
  developer: string | null;
  project: string | null;
  area: string | null;
  prop_type: string | null;
  trans_value: number;
  effective_area: number | null;
  price_per_sqm: number | null;
  is_offplan: string | null;
  rooms: string | null;
}

export interface PaginatedTransactions {
  total: number;
  page: number;
  page_size: number;
  items: TransactionItem[];
}

// ─── Mortgages ────────────────────────────────────────────────────────────────
export interface MortgageFilters {
  procedure?: string;
  date_from?: string;
  date_to?: string;
}

export interface MortgageKPIs {
  total_mortgage_transactions: number;
  total_mortgage_value: number;
  avg_mortgage_value: number | null;
}

export interface MortgageProcedureRow {
  procedure: string;
  transaction_count: number;
  total_value_m: number;
  avg_value: number | null;
}

export interface MortgageTransactionItem {
  transaction_number: string | null;
  instance_date: string | null;
  procedure: string | null;
  mortgage_value: number | null;
  row_count: number;
  area: string | null;
  prop_type: string | null;
  is_offplan: string | null;
}

export interface PaginatedMortgages {
  total: number;
  page: number;
  page_size: number;
  items: MortgageTransactionItem[];
}

// ─── Properties ───────────────────────────────────────────────────────────────
export interface PropertyTypeRow {
  prop_type: string;
  transaction_count: number;
  sales_value_m: number;
  median_price_sqm: number;
  median_area_sqm: number;
}

export interface PropertyTypeTrendItem {
  month: string;
  prop_type: string;
  median_price_sqm: number;
}

// ─── Rents ───────────────────────────────────────────────────────────────────
export interface RentKPIs {
  total_contracts: number;
  total_annual_rent: number;
  median_rent_sqm: number | null;
  avg_annual_contract: number | null;
}

export interface RentByTypeRow {
  prop_type: string;
  contract_count: number;
  annual_rent_m: number;
  median_rent_sqm: number;
}

export interface RentTypeTrendItem {
  month: string;
  prop_type: string;
  median_rent_sqm: number;
}

export interface RentByAreaRow {
  area: string;
  median_rent_sqm: number;
  contract_count: number;
}

export interface RentAreaHeatmapItem {
  area: string;
  contract_count: number;
  annual_rent_m: number;
}

export interface RentItem {
  registration_date: string;
  developer: string | null;
  project: string | null;
  area: string | null;
  prop_type: string | null;
  annual_amount: number;
  effective_area: number | null;
  rent_per_sqm: number | null;
  rooms: string | null;
}

export interface PaginatedRents {
  total: number;
  page: number;
  page_size: number;
  items: RentItem[];
}

// ─── Supply ───────────────────────────────────────────────────────────────────
export interface SupplyKPIs {
  total_land_parcels: number;
  total_land_area_sqm: number;
  active_projects: number;
  pending_projects: number;
  units_in_pipeline: number;
}

export interface LandTypeRow {
  land_type: string;
  parcels: number;
  total_area_sqm: number;
}

export interface SubTypeRow {
  sub_type: string;
  parcels: number;
}

export interface PipelineByYearRow {
  completion_year: number;
  units: number;
  projects: number;
}

export interface CompletionBandRow {
  band: string;
  projects: number;
}

export interface SupplyAreaHeatmapItem {
  area: string;
  year: number;
  project_count: number;
  units: number;
}

export interface LocationContextRow {
  name: string;
  contract_count: number;
  annual_rent_m: number;
  median_rent_sqm: number | null;
  unique_areas: number;
  current_median_rent_sqm: number | null;
  previous_median_rent_sqm: number | null;
  performance_30d_pct: number | null;
  volatility_30d_pct: number | null;
}
