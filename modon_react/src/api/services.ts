import { apiFetch, filtersToParams } from './client';
import type {
  CommonFilters,
  OverviewKPIs,
  MonthlySalesItem,
  MonthlyProjectLaunchItem,
  SalesSegment,
  WeeklyRentItem,
  WeeklySalesItem,
  AreaPriceItem,
  AreaVolumeItem,
  ProjectStatusItem,
  TrendingDevelopmentAreaItem,
  DevelopmentActivitySnapshot,
  MarketActivitySnapshot,
  MarketNewsResponse,
  MarketSummaryResponse,
  FilterOptions,
  DeveloperRow,
  DeveloperDetail,
  TransactionKPIs,
  TransactionAreaHeatmapItem,
  MonthlyValueItem,
  PaginatedTransactions,
  MortgageFilters,
  MortgageKPIs,
  MortgageProcedureRow,
  PaginatedMortgages,
  PropertyTypeRow,
  PropertyTypeTrendItem,
  RentKPIs,
  RentByTypeRow,
  RentTypeTrendItem,
  RentByAreaRow,
  RentAreaHeatmapItem,
  PaginatedRents,
  SupplyKPIs,
  LandTypeRow,
  SubTypeRow,
  PipelineByYearRow,
  CompletionBandRow,
  SupplyAreaHeatmapItem,
  LocationContextRow,
} from './types';

// ─── Overview ─────────────────────────────────────────────────────────────────
export const getOverviewKPIs = () =>
  apiFetch<OverviewKPIs>('/overview/kpis');

export const getMonthlySales = () =>
  apiFetch<MonthlySalesItem[]>('/overview/monthly-sales');

export const getWeeklySales = (segment: SalesSegment = 'total') =>
  apiFetch<WeeklySalesItem[]>('/overview/weekly-sales', { segment });

export const getWeeklyRents = () =>
  apiFetch<WeeklyRentItem[]>('/overview/weekly-rents');

export const getMarketActivity = () =>
  apiFetch<MarketActivitySnapshot>('/overview/market-activity');

export const getMarketSummary = (refresh = false) =>
  apiFetch<MarketSummaryResponse>('/overview/market-summary', refresh ? { refresh: 'true' } : undefined);

export const getMarketNews = (refresh = false) =>
  apiFetch<MarketNewsResponse>('/overview/market-news', refresh ? { refresh: 'true' } : undefined);

export const getDevelopmentActivity = () =>
  apiFetch<DevelopmentActivitySnapshot>('/overview/development-activity');

export const getMonthlyProjectLaunches = () =>
  apiFetch<MonthlyProjectLaunchItem[]>('/overview/monthly-project-launches');

export const getTopAreasByPrice = (top = 10) =>
  apiFetch<AreaPriceItem[]>('/overview/top-areas-price', { top });

export const getTopAreasByVolume = (top = 10) =>
  apiFetch<AreaVolumeItem[]>('/overview/top-areas-volume', { top });

export const getProjectStatus = () =>
  apiFetch<ProjectStatusItem[]>('/overview/project-status');

export const getTrendingDevelopmentAreas = (top = 8, windowDays = 90) =>
  apiFetch<TrendingDevelopmentAreaItem[]>('/overview/trending-development-areas', { top, window_days: windowDays });

export const getFilterOptions = (filters?: CommonFilters) =>
  apiFetch<FilterOptions>('/overview/filter-options', filtersToParams(filters));

// ─── Developers ───────────────────────────────────────────────────────────────
export const getDevelopers = (area?: string) =>
  apiFetch<DeveloperRow[]>('/developers', { area });

export const getDeveloperDetail = (name: string) =>
  apiFetch<DeveloperDetail>(`/developers/${encodeURIComponent(name)}`);

// ─── Transactions ─────────────────────────────────────────────────────────────
export const getTransactionKPIs = (filters?: CommonFilters) =>
  apiFetch<TransactionKPIs>('/transactions/kpis', filtersToParams(filters));

export const getTransactionsMonthly = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/transactions/monthly', filtersToParams(filters));

export const getTransactionsWeekly = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/transactions/weekly', filtersToParams(filters));

export const getTransactionsMonthlyCount = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/transactions/monthly-count', filtersToParams(filters));

export const getTransactionsWeeklyCount = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/transactions/weekly-count', filtersToParams(filters));

export const getTransactionsMonthlyPrice = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/transactions/monthly-price', filtersToParams(filters));

export const getTransactionsWeeklyPrice = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/transactions/weekly-price', filtersToParams(filters));

export const getTransactionsAreaHeatmap = (top = 80, filters?: CommonFilters) =>
  apiFetch<TransactionAreaHeatmapItem[]>('/transactions/area-heatmap', {
    ...filtersToParams(filters),
    top,
  });

export const getTransactionsByArea = (top = 20, filters?: CommonFilters) =>
  apiFetch<AreaPriceItem[]>('/transactions/by-area', {
    ...filtersToParams(filters),
    top,
  });

export const getTransactions = (
  filters?: CommonFilters,
  page = 1,
  page_size = 50,
) =>
  apiFetch<PaginatedTransactions>('/transactions', {
    ...filtersToParams(filters),
    page,
    page_size,
  });

// ─── Mortgages ────────────────────────────────────────────────────────────────
function mortgageFiltersToParams(filters?: MortgageFilters): Record<string, string | undefined> {
  return {
    procedure: filters?.procedure,
    date_from: filters?.date_from,
    date_to: filters?.date_to,
  };
}

export const getMortgageKPIs = (filters?: MortgageFilters) =>
  apiFetch<MortgageKPIs>('/mortgages/kpis', mortgageFiltersToParams(filters));

export const getMortgagesMonthly = (filters?: MortgageFilters) =>
  apiFetch<MonthlyValueItem[]>('/mortgages/monthly', mortgageFiltersToParams(filters));

export const getMortgagesByProcedure = (filters?: Omit<MortgageFilters, 'procedure'>) =>
  apiFetch<MortgageProcedureRow[]>('/mortgages/by-procedure', mortgageFiltersToParams(filters));

export const getMortgages = (
  filters?: MortgageFilters,
  page = 1,
  page_size = 50,
) =>
  apiFetch<PaginatedMortgages>('/mortgages', {
    ...mortgageFiltersToParams(filters),
    page,
    page_size,
  });

// ─── Properties ───────────────────────────────────────────────────────────────
export const getPropertyTypes = (filters?: CommonFilters) =>
  apiFetch<PropertyTypeRow[]>('/properties/types', filtersToParams(filters));

export const getPropertyTypeTrend = (prop_types?: string, filters?: CommonFilters, frequency: 'monthly' | 'weekly' = 'monthly') =>
  apiFetch<PropertyTypeTrendItem[]>('/properties/type-trend', {
    ...filtersToParams(filters),
    prop_types,
    frequency,
  });

// ─── Rents ───────────────────────────────────────────────────────────────────
export const getRentKPIs = (filters?: CommonFilters) =>
  apiFetch<RentKPIs>('/rents/kpis', filtersToParams(filters));

export const getRentsMonthly = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/rents/monthly', filtersToParams(filters));

export const getRentsWeekly = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/rents/weekly', filtersToParams(filters));

export const getRentsMonthlyCount = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/rents/monthly-count', filtersToParams(filters));

export const getRentsWeeklyCount = (filters?: CommonFilters) =>
  apiFetch<MonthlyValueItem[]>('/rents/weekly-count', filtersToParams(filters));

export const getRentsByType = (filters?: CommonFilters) =>
  apiFetch<RentByTypeRow[]>('/rents/by-type', filtersToParams(filters));

export const getRentTypeTrend = (prop_types?: string, filters?: CommonFilters, frequency: 'monthly' | 'weekly' = 'monthly') =>
  apiFetch<RentTypeTrendItem[]>('/rents/type-trend', {
    ...filtersToParams(filters),
    prop_types,
    frequency,
  });

export const getRentsByArea = (top = 20, filters?: CommonFilters) =>
  apiFetch<RentByAreaRow[]>('/rents/by-area', { ...filtersToParams(filters), top });

export const getRentsAreaHeatmap = (top = 80, filters?: CommonFilters) =>
  apiFetch<RentAreaHeatmapItem[]>('/rents/area-heatmap', {
    ...filtersToParams(filters),
    top,
  });

export const getRents = (filters?: CommonFilters, page = 1, page_size = 50) =>
  apiFetch<PaginatedRents>('/rents', {
    ...filtersToParams(filters),
    page,
    page_size,
  });

// ─── Supply ───────────────────────────────────────────────────────────────────
export const getSupplyKPIs = () =>
  apiFetch<SupplyKPIs>('/supply/kpis');

export const getLandTypes = () =>
  apiFetch<LandTypeRow[]>('/supply/land-types');

export const getSubTypes = (top = 15) =>
  apiFetch<SubTypeRow[]>('/supply/sub-types', { top });

export const getPipelineByYear = (from_year?: number) =>
  apiFetch<PipelineByYearRow[]>('/supply/pipeline-by-year', { from_year });

export const getCompletionBands = () =>
  apiFetch<CompletionBandRow[]>('/supply/completion-bands');

export const getSupplyAreaHeatmap = (top = 80) =>
  apiFetch<SupplyAreaHeatmapItem[]>('/supply/area-heatmap', { top });

export const getNearestMetros = (top = 12, market: 'rent' | 'sale' = 'rent') =>
  apiFetch<LocationContextRow[]>('/supply/nearest-metros', { top, market });

export const getNearestLandmarks = (top = 12, market: 'rent' | 'sale' = 'rent') =>
  apiFetch<LocationContextRow[]>('/supply/nearest-landmarks', { top, market });
