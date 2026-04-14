import { useCallback, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, Cell,
  Line,
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import DubaiMap from '../components/map/DubaiMap';
import { LoadingSpinner, ErrorMessage } from '../components/ui/LoadingState';
import { useFetch } from '../hooks/useFetch';
import {
  getDevelopmentActivity,
  getDevelopers,
  getMarketNews,
  getMarketSummary,
  getMonthlyProjectLaunches,
  getOverviewKPIs,
  getMarketActivity,
  getWeeklyRents,
  getWeeklySales,
  getTopAreasByPrice,
  getTopAreasByVolume,
  getTrendingDevelopmentAreas,
  getTransactionsAreaHeatmap,
} from '../api/services';
import type {
  DeveloperRow,
  RollingCountMetric,
  RollingFloatMetric,
  SalesSegment,
  TransactionAreaHeatmapItem,
  TrendingDevelopmentAreaItem,
} from '../api/types';

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;

const SALES_SEGMENT_OPTIONS: Array<{ value: SalesSegment; label: string }> = [
  { value: 'total', label: 'Total' },
  { value: 'off-plan', label: 'Off-Plan' },
  { value: 'ready', label: 'Ready' },
];

type TrendingAreaMetric = 'projects_started' | 'units_announced' | 'project_value_m';

type DeveloperLeaderboardMetric = 'active' | 'total_units_value' | 'portfolio_value_value';

const TRENDING_AREA_METRIC_OPTIONS: Array<{ value: TrendingAreaMetric; label: string; activeKey: keyof TrendingDevelopmentAreaItem; pendingKey: keyof TrendingDevelopmentAreaItem }> = [
  { value: 'projects_started', label: 'By projects', activeKey: 'active_projects', pendingKey: 'pending_projects' },
  { value: 'units_announced', label: 'By units', activeKey: 'active_units_announced', pendingKey: 'pending_units_announced' },
  { value: 'project_value_m', label: 'By investment', activeKey: 'active_project_value_m', pendingKey: 'pending_project_value_m' },
];

const DEVELOPER_LEADERBOARD_METRIC_OPTIONS: Array<{ value: DeveloperLeaderboardMetric; label: string; activeKey: string; pendingKey: string }> = [
  { value: 'active', label: 'By projects', activeKey: 'active', pendingKey: 'pending' },
  { value: 'total_units_value', label: 'By units', activeKey: 'active_units_value', pendingKey: 'pending_units_value' },
  { value: 'portfolio_value_value', label: 'By investment', activeKey: 'active_portfolio_value_value', pendingKey: 'pending_portfolio_value_value' },
];

function fmt(n: number) {
  if (n >= 1_000_000_000) return `AED ${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `AED ${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `AED ${(n / 1_000).toFixed(0)}K`;
  return `AED ${n}`;
}

function fmtMillionsValue(value: number) {
  if (Math.abs(value) >= 1000) return `AED ${(value / 1000).toFixed(1)}B`;
  return `AED ${value.toFixed(1)}M`;
}

function fmtCountMetric(metric: RollingCountMetric) {
  return metric.last_30d.toLocaleString();
}

function fmtPriceMetric(metric: RollingFloatMetric) {
  if (metric.last_30d == null) return '—';
  return `AED ${metric.last_30d.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtPreviousCount(metric: RollingCountMetric) {
  return `Prev 30d period: ${metric.previous_30d.toLocaleString()}`;
}

function fmtPreviousPrice(metric: RollingFloatMetric) {
  if (metric.previous_30d == null) return 'Prev 30d period: —';
  return `Prev 30d period: AED ${metric.previous_30d.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtChartTooltip(value: number, name: string) {
  if (name.includes('AED')) {
    return fmtMillionsValue(value);
  }
  return value.toLocaleString();
}

function truncateSingleLine(value: string, maxLength = 24) {
  const clean = value.replace(/\s+/g, ' ').trim();
  if (clean.length <= maxLength) return clean;
  return `${clean.slice(0, maxLength - 1)}…`;
}

export default function Dashboard() {
  const [salesSegment, setSalesSegment] = useState<SalesSegment>('total');
  const [trendingAreaMetric, setTrendingAreaMetric] = useState<TrendingAreaMetric>('projects_started');
  const [developerLeaderboardMetric, setDeveloperLeaderboardMetric] = useState<DeveloperLeaderboardMetric>('active');
  const [selectedDevelopmentArea, setSelectedDevelopmentArea] = useState<string | null>(null);
  const [showLatestNews, setShowLatestNews] = useState(false);
  const [newsRefreshVersion, setNewsRefreshVersion] = useState(0);
  const developersFetcher = useCallback(() => getDevelopers(selectedDevelopmentArea ?? undefined), [selectedDevelopmentArea]);
  const developmentFetcher = useCallback(() => getDevelopmentActivity(), []);
  const developmentMonthlyFetcher = useCallback(() => getMonthlyProjectLaunches(), []);
  const kpisFetcher = useCallback(() => getOverviewKPIs(), []);
  const activityFetcher = useCallback(() => getMarketActivity(), []);
  const summaryFetcher = useCallback(() => getMarketSummary(), []);
  const newsFetcher = useCallback(() => getMarketNews(newsRefreshVersion > 0), [newsRefreshVersion]);
  const rentsFetcher = useCallback(() => getWeeklyRents(), []);
  const salesFetcher = useCallback(() => getWeeklySales(salesSegment), [salesSegment]);
  const areasFetcher = useCallback(() => getTopAreasByPrice(10), []);
  const volumeFetcher = useCallback(() => getTopAreasByVolume(10), []);
  const trendingAreasFetcher = useCallback(() => getTrendingDevelopmentAreas(8, 90), []);
  const transactionHeatmapFetcher = useCallback(() => getTransactionsAreaHeatmap(80), []);

  const { data: developers, loading: developersLoading, error: developersError } = useFetch(developersFetcher);
  const { data: development, loading: developmentLoading, error: developmentError } = useFetch(developmentFetcher);
  const { data: monthlyProjectLaunches, loading: monthlyProjectLaunchesLoading, error: monthlyProjectLaunchesError } = useFetch(developmentMonthlyFetcher);
  const { data: kpis, error: kpisError } = useFetch(kpisFetcher);
  const { data: activity, loading: activityLoading, error: activityError } = useFetch(activityFetcher);
  const { data: marketSummary, loading: summaryLoading, error: summaryError } = useFetch(summaryFetcher);
  const { data: marketNews, loading: newsLoading, error: newsError } = useFetch(newsFetcher);
  const { data: weeklyRents, loading: rentsLoading } = useFetch(rentsFetcher);
  const { data: weeklySales, loading: salesLoading } = useFetch(salesFetcher);
  useFetch(areasFetcher);
  useFetch(volumeFetcher);
  const { data: trendingAreas, loading: trendingAreasLoading, error: trendingAreasError } = useFetch(trendingAreasFetcher);
  const { data: transactionHeatmap, loading: transactionHeatmapLoading, error: transactionHeatmapError } = useFetch(transactionHeatmapFetcher);
  const selectedTrendingAreaMetric = TRENDING_AREA_METRIC_OPTIONS.find((option) => option.value === trendingAreaMetric) ?? TRENDING_AREA_METRIC_OPTIONS[0];
  const selectedDeveloperLeaderboardMetric = DEVELOPER_LEADERBOARD_METRIC_OPTIONS.find((option) => option.value === developerLeaderboardMetric) ?? DEVELOPER_LEADERBOARD_METRIC_OPTIONS[0];
  const topActiveDevelopers = [...(developers ?? [])]
    .map((developer) => ({
      ...developer,
      total_units_value: developer.total_units ?? 0,
      active_units_value: developer.active_units ?? 0,
      pending_units_value: developer.pending_units ?? 0,
      portfolio_value_value: developer.portfolio_value ?? 0,
      active_portfolio_value_value: developer.active_portfolio_value ?? 0,
      pending_portfolio_value_value: developer.pending_portfolio_value ?? 0,
    }))
    .sort((a, b) => {
      if (developerLeaderboardMetric === 'total_units_value') {
        return ((b.active_units_value + b.pending_units_value) - (a.active_units_value + a.pending_units_value)) || (b.active - a.active) || (b.total_projects - a.total_projects);
      }
      if (developerLeaderboardMetric === 'portfolio_value_value') {
        return ((b.active_portfolio_value_value + b.pending_portfolio_value_value) - (a.active_portfolio_value_value + a.pending_portfolio_value_value)) || (b.active - a.active) || (b.total_projects - a.total_projects);
      }
      return ((b.active + b.pending) - (a.active + a.pending)) || (b.active - a.active) || (b.total_projects - a.total_projects);
    })
    .slice(0, 10);
  const salesValueLabel = salesSegment === 'off-plan'
    ? 'Off-Plan Sales (M AED)'
    : salesSegment === 'ready'
      ? 'Ready Sales (M AED)'
      : 'Sales (M AED)';
  const salesDealsLabel = salesSegment === 'off-plan'
    ? 'Off-Plan Deals'
    : salesSegment === 'ready'
      ? 'Ready Deals'
      : 'Sale Deals';
  const recentUnitsAnnounced = [...(monthlyProjectLaunches ?? [])]
    .sort((a, b) => a.month.localeCompare(b.month))
    .slice(-3)
    .map((item) => ({
      ...item,
      monthLabel: item.month.slice(0, 7),
    }));
  const trendingAreasChartData = [...(trendingAreas ?? [])]
    .sort((a, b) => {
      const aValue = Number(a[selectedTrendingAreaMetric.activeKey] ?? 0) + Number(a[selectedTrendingAreaMetric.pendingKey] ?? 0);
      const bValue = Number(b[selectedTrendingAreaMetric.activeKey] ?? 0) + Number(b[selectedTrendingAreaMetric.pendingKey] ?? 0);
      return bValue - aValue || a.area.localeCompare(b.area);
    })
    .map((item: TrendingDevelopmentAreaItem) => ({
      ...item,
      areaLabel: truncateSingleLine(item.area, 22),
      isSelected: item.area === selectedDevelopmentArea,
    }));
  const heatmapAreas = (transactionHeatmap ?? []).map((item: TransactionAreaHeatmapItem) => ({
    id: item.area,
    area: item.area,
    transactionCount: item.transaction_count,
    salesValueM: item.sales_value_m,
  }));

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-xl border border-sky-200 bg-[linear-gradient(135deg,#eff6ff_0%,#ffffff_55%,#ecfdf5_100%)] p-5 shadow-card">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className={`mb-2 inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${marketSummary?.provider === 'gemini' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
              {marketSummary?.provider === 'gemini' ? 'AI Summary' : 'Automated Summary'}
            </div>
            <h2 className="text-base font-semibold text-gray-900">Market Briefing</h2>
            <p className="mt-1 text-sm text-gray-500">{marketSummary?.summary ?? 'Live narrative built from current sales, rental, and development signals.'}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {marketNews && (marketNews.news_items.length > 0 || marketNews.sources.length > 0) ? (
              <button
                type="button"
                onClick={() => setShowLatestNews((value) => !value)}
                className="rounded-full border border-sky-200 bg-white/80 px-3 py-1 text-xs font-medium text-sky-700 transition hover:border-sky-300 hover:text-sky-900"
              >
                {showLatestNews ? 'Hide latest market news' : 'Latest market news'}
              </button>
            ) : null}
            {marketSummary?.model ? (
              <div className="rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-xs text-emerald-700">
                {marketSummary.model}
              </div>
            ) : null}
          </div>
        </div>

        {summaryLoading && !marketSummary ? <LoadingSpinner /> : marketSummary ? (
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
            {marketSummary.sections.map((section) => (
              <div key={section.title} className="rounded-xl border border-white/70 bg-white/80 p-4 backdrop-blur-sm">
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">{section.title}</div>
                <p className="text-sm leading-6 text-gray-700">{section.body}</p>
              </div>
            ))}
          </div>
        ) : null}

        {marketSummary && showLatestNews ? (
          <div className="mt-4 rounded-xl border border-sky-100 bg-white/70 p-4 backdrop-blur-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-gray-900">Latest Market News</h3>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setNewsRefreshVersion((value) => value + 1)}
                  disabled={newsLoading}
                  className="rounded-full border border-gray-200 bg-white/80 px-3 py-1 text-xs font-medium text-gray-700 transition hover:border-gray-300 hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {newsLoading ? 'Refreshing...' : 'Refresh latest news'}
                </button>
                <div className="text-xs uppercase tracking-[0.16em] text-gray-400">Grounded sources</div>
              </div>
            </div>
            {newsLoading && !marketNews ? <LoadingSpinner /> : marketNews && marketNews.news_items.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                {marketNews.news_items.map((item, index) => {
                  const source = marketNews.sources[index] ?? null;
                  return (
                    <div key={`${item.headline}-${index}`} className="rounded-xl border border-gray-200 bg-white px-4 py-3">
                      <div className="text-sm font-medium text-gray-900">{item.headline}</div>
                      <p className="mt-2 text-sm leading-6 text-gray-600">{item.summary}</p>
                      {source ? (
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-3 inline-flex text-xs font-medium text-sky-700 transition hover:text-sky-900"
                        >
                          {source.title}
                        </a>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No grounded market news was returned for this briefing.</p>
            )}
            {marketNews?.note ? <p className="mt-3 text-xs text-amber-700">{marketNews.note}</p> : null}
          </div>
        ) : null}

        {marketSummary?.note ? <p className="mt-4 text-xs text-amber-700">{marketSummary.note}</p> : null}
      </div>

      {kpisError && <ErrorMessage message={kpisError} />}
      {activityError && <ErrorMessage message={activityError} />}
      {summaryError && <ErrorMessage message={summaryError} />}
      {newsError && <ErrorMessage message={newsError} />}
      {developersError && <ErrorMessage message={developersError} />}
      {developmentError && <ErrorMessage message={developmentError} />}
      {monthlyProjectLaunchesError && <ErrorMessage message={monthlyProjectLaunchesError} />}
      {trendingAreasError && <ErrorMessage message={trendingAreasError} />}
      {transactionHeatmapError && <ErrorMessage message={transactionHeatmapError} />}

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Property Market Pulse</h2>

          </div>
        </div>

        {activityLoading ? (
          <LoadingSpinner />
        ) : activity ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Sales in Last 30 Days"
                value={fmtCountMetric(activity.sales_count)}
                sub={fmtPreviousCount(activity.sales_count)}
                trend={activity.sales_count.delta_pct ?? undefined}
                icon="🏷"
                color="emerald"
              />
              <StatCard
                label="Sale Price / sqm"
                value={fmtPriceMetric(activity.sales_price_per_sqm)}
                sub={fmtPreviousPrice(activity.sales_price_per_sqm)}
                trend={activity.sales_price_per_sqm.delta_pct ?? undefined}
                icon="📐"
                color="amber"
              />
              <StatCard
                label="Rentals in Last 30 Days"
                value={fmtCountMetric(activity.rent_count)}
                sub={fmtPreviousCount(activity.rent_count)}
                trend={activity.rent_count.delta_pct ?? undefined}
                icon="🔑"
                color="blue"
              />
              <StatCard
                label="Rent Price / sqm"
                value={fmtPriceMetric(activity.rent_price_per_sqm)}
                sub={fmtPreviousPrice(activity.rent_price_per_sqm)}
                trend={activity.rent_price_per_sqm.delta_pct ?? undefined}
                icon="🏠"
                color="violet"
              />
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-sm font-medium text-gray-600">Weekly Sales Volume (AED M)</h3>
                  <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-1">
                    {SALES_SEGMENT_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setSalesSegment(option.value)}
                        className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${salesSegment === option.value ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
                {weeklySales && weeklySales.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <ComposedChart data={weeklySales ?? []} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="week" tick={{ fontSize: 11 }} tickFormatter={(v: string) => v.slice(5)} />
                      <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number, name: string) => fmtChartTooltip(v, name)} labelFormatter={(l: string) => `Week of ${l}`} />
                      <Bar yAxisId="left" dataKey="sales_value_m" name={salesValueLabel} fill="#10b981" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                      <Line yAxisId="right" type="linear" dataKey="transaction_count" name={salesDealsLabel} stroke="#111827a8" strokeWidth={3} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : salesLoading ? (
                  <LoadingSpinner />
                ) : null}
              </div>

              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
                <h3 className="mb-4 text-sm font-medium text-gray-600">Weekly Rental Volume (AED M)</h3>
                {rentsLoading ? <LoadingSpinner /> : (
                  <ResponsiveContainer width="100%" height={220}>
                    <ComposedChart data={weeklyRents ?? []} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="week" tick={{ fontSize: 11 }} tickFormatter={(v: string) => v.slice(5)} />
                      <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number, name: string) => fmtChartTooltip(v, name)} labelFormatter={(l: string) => `Week of ${l}`} />
                      <Bar yAxisId="left" dataKey="annual_rent_m" name="Rent (M AED)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      <Line yAxisId="right" type="linear" dataKey="contract_count" name="Rental Deals" stroke="#111827a8" strokeWidth={3} dot={false} activeDot={{ r: 4 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Development Pulse</h2>
          </div>
        </div>

        {developmentLoading ? (
          <LoadingSpinner />
        ) : development && kpis ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
              <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-card hover:shadow-card-hover transition-shadow">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-gray-500 truncate">Projects Started</p>
                    <p className="mt-1 text-xl font-semibold text-gray-900 truncate tracking-tight">{fmtCountMetric(development.projects_started)}</p>
                    <p className="mt-0.5 text-xs text-gray-400 truncate">{fmtPreviousCount(development.projects_started)}</p>
                    {development.projects_started.delta_pct !== null && (
                      <p className={`mt-1.5 inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-xs font-medium ${development.projects_started.delta_pct >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                        {development.projects_started.delta_pct >= 0 ? '↑' : '↓'} {Math.abs(development.projects_started.delta_pct).toFixed(1)}%
                      </p>
                    )}
                  </div>
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-amber-50 text-base text-amber-600">
                    🚧
                  </div>
                </div>

                <div className="mt-4 border-t border-gray-100 pt-4">
                  <h3 className="mb-3 text-sm font-medium text-gray-600">Units Announced, Last 3 Months</h3>
                  {monthlyProjectLaunchesLoading ? <LoadingSpinner /> : recentUnitsAnnounced.length > 0 ? (
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={recentUnitsAnnounced} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                        <XAxis dataKey="monthLabel" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip
                          formatter={(value: number) => value.toLocaleString()}
                          labelFormatter={(label: string) => `Month of ${label}`}
                        />
                        <Bar dataKey="units_announced" name="Units Announced" fill="#8b5cf6" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-gray-500">No monthly launch data available.</p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card xl:col-span-2">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-sm font-medium text-gray-600">Trending Development Areas</h3>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-1">
                      {TRENDING_AREA_METRIC_OPTIONS.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => setTrendingAreaMetric(option.value)}
                          className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${trendingAreaMetric === option.value ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                    <div className="text-xs uppercase tracking-[0.16em] text-gray-400">Last 90 days</div>
                  </div>
                </div>
                <p className="mb-3 text-xs text-gray-400">Click an area to filter the developer leaderboard.</p>
                {trendingAreasLoading ? <LoadingSpinner /> : trendingAreasChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={trendingAreasChartData} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 140 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 11 }}
                        tickFormatter={(value: number) => (trendingAreaMetric === 'project_value_m' ? `${value.toFixed(0)}M` : value.toLocaleString())}
                      />
                      <YAxis type="category" dataKey="areaLabel" tick={{ fontSize: 11 }} width={140} />
                      <Tooltip
                        content={({ active, payload }) => {
                          const row = payload?.[0]?.payload as TrendingDevelopmentAreaItem | undefined;
                          if (!active || !row) return null;
                          return (
                            <div className="rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-lg">
                              <div className="text-sm font-medium text-gray-900">{row.area}</div>
                              <div className="mt-2 space-y-1 text-xs text-gray-600">
                                <div>Active Projects: {row.active_projects.toLocaleString()}</div>
                                <div>Pending Projects: {row.pending_projects.toLocaleString()}</div>
                                <div>Active Units: {row.active_units_announced.toLocaleString()}</div>
                                <div>Pending Units: {row.pending_units_announced.toLocaleString()}</div>
                                <div>Active Investment: {fmtMillionsValue(row.active_project_value_m)}</div>
                                <div>Pending Investment: {fmtMillionsValue(row.pending_project_value_m)}</div>
                              </div>
                            </div>
                          );
                        }}
                      />
                      <Bar
                        dataKey={selectedTrendingAreaMetric.activeKey}
                        name="Active"
                        stackId="status"
                        fill="#0f766e"
                        radius={[0, 4, 4, 0]}
                        isAnimationActive={false}
                        background={({ x, y, width, height, index }: { x?: number; y?: number; width?: number; height?: number; index?: number }) => {
                          const entry = trendingAreasChartData[index ?? -1];
                          if (!entry) return <g />;
                          return <rect x={x} y={y} width={width} height={height} fill="transparent" cursor="pointer" onClick={() => setSelectedDevelopmentArea((current) => (current === entry.area ? null : entry.area))} />;
                        }}
                      >
                        {trendingAreasChartData.map((entry) => (
                          <Cell
                            key={`${entry.area}-active`}
                            fill={entry.isSelected ? '#0b5d56' : '#0f766e'}
                            style={{ cursor: 'pointer' }}
                            onClick={() => setSelectedDevelopmentArea((current) => (current === entry.area ? null : entry.area))}
                          />
                        ))}
                      </Bar>
                      <Bar
                        dataKey={selectedTrendingAreaMetric.pendingKey}
                        name="Pending"
                        stackId="status"
                        fill="#86efac"
                        radius={[0, 4, 4, 0]}
                        isAnimationActive={false}
                      >
                        {trendingAreasChartData.map((entry) => (
                          <Cell
                            key={`${entry.area}-pending`}
                            fill={entry.isSelected ? '#4ade80' : '#86efac'}
                            style={{ cursor: 'pointer' }}
                            onClick={() => setSelectedDevelopmentArea((current) => (current === entry.area ? null : entry.area))}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-gray-500">No recent development area activity available.</p>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-sm font-medium text-gray-600">Most Active Developers</h3>
                <div className="flex flex-wrap items-center gap-3">
                  <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-1">
                    {DEVELOPER_LEADERBOARD_METRIC_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setDeveloperLeaderboardMetric(option.value)}
                        className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${developerLeaderboardMetric === option.value ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                  {selectedDevelopmentArea ? (
                    <div className="flex items-center gap-2">
                      <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                        Area: {selectedDevelopmentArea}
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedDevelopmentArea(null)}
                        className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-700 transition hover:border-gray-300 hover:text-gray-900"
                      >
                        Clear
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
              {developersLoading ? <LoadingSpinner /> : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={topActiveDevelopers} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 180 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11 }}
                      tickFormatter={(value: number) => (developerLeaderboardMetric === 'portfolio_value_value' ? fmt(value).replace('AED ', '') : value.toLocaleString())}
                    />
                    <YAxis type="category" dataKey="developer" tick={{ fontSize: 11 }} width={180} tickFormatter={(value: string) => truncateSingleLine(value, 22)} />
                    <Tooltip
                      content={({ active, payload }) => {
                        const row = payload?.[0]?.payload as (DeveloperRow & {
                          total_units_value: number;
                          active_units_value: number;
                          pending_units_value: number;
                          portfolio_value_value: number;
                          active_portfolio_value_value: number;
                          pending_portfolio_value_value: number;
                        }) | undefined;
                        if (!active || !row) return null;
                        return (
                          <div className="rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-lg">
                            <div className="text-sm font-medium text-gray-900">{row.developer}</div>
                            <div className="mt-2 space-y-1 text-xs text-gray-600">
                              <div>Active Projects: {row.active.toLocaleString()}</div>
                              <div>Pending Projects: {row.pending.toLocaleString()}</div>
                              <div>Active Units: {row.active_units_value.toLocaleString()}</div>
                              <div>Pending Units: {row.pending_units_value.toLocaleString()}</div>
                              <div>Active Investment: {fmt(row.active_portfolio_value_value)}</div>
                              <div>Pending Investment: {fmt(row.pending_portfolio_value_value)}</div>
                            </div>
                          </div>
                        );
                      }}
                    />
                    <Bar dataKey={selectedDeveloperLeaderboardMetric.activeKey} name="Active" stackId="status" fill="#0f766e" radius={[0, 4, 4, 0]} />
                    <Bar dataKey={selectedDeveloperLeaderboardMetric.pendingKey} name="Pending" stackId="status" fill="#86efac" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        ) : null}
      </div>

      {/* Map */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium text-gray-600">Pulse Map</h3>
            <p className="mt-1 text-xs text-gray-400">Transaction intensity by area, weighted by transaction count.</p>
          </div>
          {transactionHeatmap ? (
            <div className="rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
              {transactionHeatmap.length.toLocaleString()} areas
            </div>
          ) : null}
        </div>
        {transactionHeatmapLoading && !transactionHeatmap ? <LoadingSpinner /> : (
          <DubaiMap apiKey={MAPS_KEY} markers={[]} heatmapAreas={heatmapAreas} height="460px" />
        )}
      </div>
    </div>
  );
}

