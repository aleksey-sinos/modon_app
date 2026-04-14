import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend,
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import PageHeader from '../components/ui/PageHeader';
import DataTable from '../components/ui/DataTable';
import type { Column } from '../components/ui/DataTable';
import DubaiMap from '../components/map/DubaiMap';
import { LoadingSpinner, ErrorMessage } from '../components/ui/LoadingState';
import { useFetch } from '../hooks/useFetch';
import { useApp, useFilters } from '../context/AppContext';
import {
  getTransactionKPIs, getTransactionsWeekly, getTransactionsWeeklyCount, getTransactions, getTransactionsAreaHeatmap, getTransactionsByArea, getPropertyTypes, getPropertyTypeTrend,
} from '../api/services';
import type { PropertyTypeTrendItem, PropertyTypeRow, TransactionAreaHeatmapItem, TransactionItem } from '../api/types';

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;
const INITIAL_TRANSACTION_LIMIT = 15;
const TRANSACTION_LOAD_STEP = 15;
type MapMetric = 'count' | 'amount';
const TYPE_COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899'];

function formatDateInput(date: Date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getDefaultSalesDateRange() {
  const today = new Date();
  const dateTo = formatDateInput(today);
  const dateFrom = new Date(today);
  dateFrom.setDate(dateFrom.getDate() - 90);
  return {
    date_from: formatDateInput(dateFrom),
    date_to: dateTo,
  };
}

function fmtVal(n: number) {
  if (n >= 1e9) return `AED ${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `AED ${(n / 1e6).toFixed(1)}M`;
  return `AED ${n.toLocaleString()}`;
}

function fmtNullableValue(n: number | null | undefined) {
  if (n == null) return '—';
  return fmtVal(n);
}

function fmtCompactMoneyFromMillions(value: number) {
  const amount = value * 1_000_000;
  if (amount >= 1e9) return `AED ${(amount / 1e9).toFixed(1)}B`;
  return `AED ${(amount / 1e6).toFixed(1)}M`;
}

function fmtWeekLabel(value: string) {
  return `Week of ${value}`;
}

function colorFor(index: number) {
  return TYPE_COLORS[index % TYPE_COLORS.length];
}

export default function Deals() {
  const { state, setFilterArea, setFilterDateFrom, setFilterDateTo } = useApp();
  const filters = useFilters();
  const [mapMetric, setMapMetric] = useState<MapMetric>('count');
  const [selectedPropType, setSelectedPropType] = useState<string | null>(null);
  const [visibleTransactions, setVisibleTransactions] = useState(INITIAL_TRANSACTION_LIMIT);
  const defaultDateRange = useMemo(() => getDefaultSalesDateRange(), []);
  const baseFilters = useMemo(() => ({
    ...filters,
    date_from: filters.date_from ?? defaultDateRange.date_from,
    date_to: filters.date_to ?? defaultDateRange.date_to,
  }), [defaultDateRange.date_from, defaultDateRange.date_to, filters]);
  const effectiveFilters = useMemo(() => ({
    ...baseFilters,
    prop_type: selectedPropType ?? undefined,
  }), [baseFilters, selectedPropType]);
  const areaSelectorFilters = useMemo(() => ({
    ...effectiveFilters,
    area: undefined,
  }), [effectiveFilters]);

  useEffect(() => {
    if (!state.filterDateFrom) {
      setFilterDateFrom(defaultDateRange.date_from);
    }
    if (!state.filterDateTo) {
      setFilterDateTo(defaultDateRange.date_to);
    }
  }, [defaultDateRange.date_from, defaultDateRange.date_to, setFilterDateFrom, setFilterDateTo, state.filterDateFrom, state.filterDateTo]);

  useEffect(() => {
    setVisibleTransactions(INITIAL_TRANSACTION_LIMIT);
  }, [effectiveFilters.area, effectiveFilters.date_from, effectiveFilters.date_to, effectiveFilters.developer, effectiveFilters.prop_type]);

  const kpiFetcher = useCallback(() => getTransactionKPIs(effectiveFilters), [effectiveFilters]);
  const weeklyFetcher = useCallback(() => getTransactionsWeekly(effectiveFilters), [effectiveFilters]);
  const countFetcher = useCallback(() => getTransactionsWeeklyCount(effectiveFilters), [effectiveFilters]);
  const byTypeFetcher = useCallback(() => getPropertyTypes(baseFilters), [baseFilters]);
  const trendFetcher = useCallback(
    () => getPropertyTypeTrend(selectedPropType ?? undefined, baseFilters, 'weekly'),
    [baseFilters, selectedPropType],
  );
  const byAreaFetcher = useCallback(() => getTransactionsByArea(15, areaSelectorFilters), [areaSelectorFilters]);
  const tableFetcher = useCallback(
    () => getTransactions(effectiveFilters, 1, visibleTransactions),
    [effectiveFilters, visibleTransactions],
  );
  const heatmapFetcher = useCallback(() => getTransactionsAreaHeatmap(80, effectiveFilters), [effectiveFilters]);

  const { data: kpis, loading: kpisLoading, error: kpisError } = useFetch(kpiFetcher);
  const { data: weekly, loading: weeklyLoading } = useFetch(weeklyFetcher);
  const { data: weeklyCount, loading: countLoading } = useFetch(countFetcher);
  const { data: byType, loading: byTypeLoading } = useFetch(byTypeFetcher);
  const { data: trend, loading: trendLoading } = useFetch(trendFetcher);
  const { data: byArea, loading: areaLoading } = useFetch(byAreaFetcher);
  const { data: paginated, loading: tableLoading } = useFetch(tableFetcher);
  const { data: heatmap, loading: heatmapLoading, error: heatmapError } = useFetch(heatmapFetcher);

  const propTypeNames = [...new Set((trend ?? []).map((item) => item.prop_type))];
  const trendByWeek = Object.values(
    (trend ?? []).reduce<Record<string, Record<string, number | string>>>((acc, row: PropertyTypeTrendItem) => {
      if (!acc[row.month]) acc[row.month] = { month: row.month };
      acc[row.month][row.prop_type] = row.median_price_sqm;
      return acc;
    }, {}),
  );

  const heatmapAreas = (heatmap ?? []).map((item: TransactionAreaHeatmapItem) => ({
    id: item.area,
    area: item.area,
    transactionCount: item.transaction_count,
    salesValueM: item.sales_value_m,
    weight: mapMetric === 'amount' ? item.sales_value_m : item.transaction_count,
  }));

  const columns: Column<TransactionItem>[] = [
    { key: 'instance_date',      header: 'Date',      className: 'hidden md:table-cell' },
    { key: 'developer',          header: 'Developer', render: (d) => d.developer ?? '—' },
    { key: 'project',            header: 'Project',   render: (d) => d.project ?? '—' },
    { key: 'area',               header: 'Area',      render: (d) => d.area ?? '—', className: 'hidden lg:table-cell' },
    { key: 'prop_type',          header: 'Type',      render: (d) => d.prop_type ?? '—' },
    { key: 'trans_value',        header: 'Value',     render: (d) => fmtVal(d.trans_value) },
    { key: 'price_per_sqm',      header: 'AED/sqm',   render: (d) => d.price_per_sqm ? d.price_per_sqm.toLocaleString() : '—', className: 'hidden xl:table-cell' },
    { key: 'is_offplan',         header: 'Off-plan',  render: (d) => d.is_offplan ?? '—', className: 'hidden xl:table-cell' },
  ];
  const canLoadMoreTransactions = paginated ? paginated.items.length < paginated.total : false;
  const topAreasChartHeight = Math.max(220, (byArea?.length ?? 0) * 28);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Transactions"
        subtitle={kpis ? `${kpis.total_transactions.toLocaleString()} transactions · ${fmtVal(kpis.total_sales_value)} · ${effectiveFilters.date_from} to ${effectiveFilters.date_to}` : 'Loading…'}
      />

      {kpisError && <ErrorMessage message={kpisError} />}
      {heatmapError && <ErrorMessage message={heatmapError} />}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-medium text-gray-600">Sales by Property Type</h3>
              <p className="mt-1 text-xs text-gray-400">Click a bar to filter the rest of the page.</p>
            </div>
            {selectedPropType ? (
              <button
                type="button"
                onClick={() => setSelectedPropType(null)}
                className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 transition hover:bg-blue-100"
              >
                Clear: {selectedPropType}
              </button>
            ) : null}
          </div>
          {byTypeLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={byType ?? []} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="prop_type" tick={{ fontSize: 10 }} width={80} />
                <Tooltip formatter={(value: number, _name: string, payload: { payload?: PropertyTypeRow }) => {
                  if (payload?.payload) {
                    return [`${value.toLocaleString()} transactions`, payload.payload.prop_type];
                  }
                  return value.toLocaleString();
                }} />
                <Bar
                  dataKey="transaction_count"
                  name="Transactions"
                  radius={[0, 4, 4, 0]}
                  background={({ x, y, width, height, index }: { x?: number; y?: number; width?: number; height?: number; index?: number }) => {
                    const item = (byType ?? [])[index ?? -1];
                    if (!item) return <g />;
                    return <rect x={x} y={y} width={width} height={height} fill="transparent" cursor="pointer" onClick={() => setSelectedPropType((current) => current === item.prop_type ? null : item.prop_type)} />;
                  }}
                >
                  {(byType ?? []).map((item) => {
                    const isSelected = item.prop_type === selectedPropType;
                    const isMuted = selectedPropType !== null && !isSelected;
                    return (
                      <Cell
                        key={item.prop_type}
                        fill={isSelected ? '#1d4ed8' : isMuted ? '#bfdbfe' : '#3b82f6'}
                        cursor="pointer"
                        onClick={() => setSelectedPropType((current) => current === item.prop_type ? null : item.prop_type)}
                      />
                    );
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Weekly Sales Value (AED M)</h3>
          {weeklyLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={weekly ?? []} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: number) => fmtCompactMoneyFromMillions(v)} labelFormatter={fmtWeekLabel} />
                <Bar dataKey="value" name="Sales Value" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Weekly Transaction Count</h3>
          {countLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={weeklyCount ?? []} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: number) => v.toLocaleString()} labelFormatter={fmtWeekLabel} />
                <Bar dataKey="value" name="Transactions" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* KPIs */}
      {kpisLoading ? <LoadingSpinner /> : kpis ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Transactions" value={kpis.total_transactions.toLocaleString()} icon="🤝" color="blue" />
          <StatCard label="Attributed Sales Value" value={fmtVal(kpis.total_sales_value)} icon="💰" color="emerald" />
          <StatCard label="Avg. Transaction" value={fmtNullableValue(kpis.avg_transaction_value)} icon="📈" color="amber" />
          <StatCard label="Median AED/sqm" value={kpis.median_price_sqm != null ? kpis.median_price_sqm.toLocaleString() : '—'} icon="📐" color="violet" />
        </div>
      ) : null}

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <h3 className="mb-4 text-sm font-medium text-gray-600">Median Price/sqm Trend by Type (AED)</h3>
        {trendLoading ? <LoadingSpinner /> : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={trendByWeek} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(value: string) => value.slice(5)} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
              <Tooltip formatter={(value: number) => `AED ${value.toLocaleString()}`} labelFormatter={fmtWeekLabel} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              {propTypeNames.map((name, index) => (
                <Line key={name} type="monotone" dataKey={name} stroke={colorFor(index)} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium text-gray-600">Top Areas — Median Price/sqm (AED)</h3>
            <p className="mt-1 text-xs text-gray-400">Click a bar to filter the rest of the page by area.</p>
          </div>
          {state.filterArea ? (
            <button
              type="button"
              onClick={() => setFilterArea('')}
              className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 transition hover:bg-blue-100"
            >
              Clear: {state.filterArea}
            </button>
          ) : null}
        </div>
        {areaLoading ? <LoadingSpinner /> : (
          <ResponsiveContainer width="100%" height={topAreasChartHeight}>
            <BarChart data={byArea ?? []} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 140 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="area" tick={{ fontSize: 10 }} width={140} interval={0} tickMargin={8} />
              <Tooltip formatter={(value: number) => `AED ${value.toLocaleString()}`} />
              <Bar
                dataKey="median_price_sqm"
                name="Median Price/sqm"
                radius={[0, 4, 4, 0]}
                background={({ x, y, width, height, index }: { x?: number; y?: number; width?: number; height?: number; index?: number }) => {
                  const item = (byArea ?? [])[index ?? -1];
                  if (!item) return <g />;
                  return <rect x={x} y={y} width={width} height={height} fill="transparent" cursor="pointer" onClick={() => setFilterArea(state.filterArea === item.area ? '' : item.area)} />;
                }}
              >
                {(byArea ?? []).map((item) => {
                  const isSelected = item.area === state.filterArea;
                  const isMuted = Boolean(state.filterArea) && !isSelected;
                  return (
                    <Cell
                      key={item.area}
                      fill={isSelected ? '#1d4ed8' : isMuted ? '#a7f3d0' : '#10b981'}
                      cursor="pointer"
                      onClick={() => setFilterArea(state.filterArea === item.area ? '' : item.area)}
                    />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Map */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium text-gray-600">Sales Map</h3>
            <p className="mt-1 text-xs text-gray-400">Heatmap by area using {mapMetric === 'amount' ? 'sales value' : 'transaction count'}.</p>
          </div>
          <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-1">
            <button
              type="button"
              onClick={() => setMapMetric('count')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${mapMetric === 'count' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
            >
              By count
            </button>
            <button
              type="button"
              onClick={() => setMapMetric('amount')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${mapMetric === 'amount' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
            >
              By amount
            </button>
          </div>
        </div>
        {heatmapLoading && !heatmap ? <LoadingSpinner /> : (
          <DubaiMap apiKey={MAPS_KEY} markers={[]} heatmapAreas={heatmapAreas} height="420px" />
        )}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-600">Transactions</h3>
          {paginated && (
            <span className="text-xs text-gray-400">
              Latest {Math.min(paginated.items.length, visibleTransactions)} of {paginated.total.toLocaleString()} in range
            </span>
          )}
        </div>
        {tableLoading ? <LoadingSpinner /> : (
          <DataTable<TransactionItem>
            columns={columns}
            data={paginated?.items ?? []}
            rowKey={(d) => d.transaction_number}
          />
        )}
        {paginated && canLoadMoreTransactions ? (
          <div className="flex justify-center border-t border-gray-100 px-5 py-3">
            <button
              type="button"
              onClick={() => setVisibleTransactions((current) => current + TRANSACTION_LOAD_STEP)}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50"
            >
              Load more transactions
            </button>
          </div>
        ) : null}
      </div>

    </div>
  );
}
