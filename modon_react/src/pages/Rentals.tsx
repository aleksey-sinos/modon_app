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
  getRentKPIs, getRentsWeekly, getRentsWeeklyCount, getRentsByType, getRentTypeTrend, getRentsByArea, getRents, getRentsAreaHeatmap,
} from '../api/services';
import type { RentAreaHeatmapItem, RentByTypeRow, RentItem } from '../api/types';

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;
const INITIAL_RENT_LIMIT = 15;
const RENT_LOAD_STEP = 15;
type MapMetric = 'count' | 'amount';

function fmtVal(n: number) {
  if (n >= 1e9) return `AED ${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `AED ${(n / 1e6).toFixed(1)}M`;
  return `AED ${n.toLocaleString()}`;
}

function fmtWeekLabel(value: string) {
  return `Week of ${value}`;
}

export default function Rentals() {
  const { state, setFilterArea } = useApp();
  const filters = useFilters();
  const [visibleRents, setVisibleRents] = useState(INITIAL_RENT_LIMIT);
  const [mapMetric, setMapMetric] = useState<MapMetric>('count');
  const [selectedPropType, setSelectedPropType] = useState<string | null>(null);
  const baseFilters = useMemo(() => ({ ...filters }), [filters]);
  const effectiveFilters = useMemo(() => ({
    ...baseFilters,
    prop_type: selectedPropType ?? undefined,
  }), [baseFilters, selectedPropType]);
  const areaSelectorFilters = useMemo(() => ({
    ...effectiveFilters,
    area: undefined,
  }), [effectiveFilters]);

  const kpiFetcher = useCallback(() => getRentKPIs(effectiveFilters), [effectiveFilters]);
  const weeklyFetcher = useCallback(() => getRentsWeekly(effectiveFilters), [effectiveFilters]);
  const countFetcher = useCallback(() => getRentsWeeklyCount(effectiveFilters), [effectiveFilters]);
  const byTypeFetcher = useCallback(() => getRentsByType(baseFilters), [baseFilters]);
  const trendFetcher = useCallback(
    () => getRentTypeTrend(selectedPropType ?? undefined, baseFilters, 'weekly'),
    [baseFilters, selectedPropType],
  );
  const byAreaFetcher = useCallback(() => getRentsByArea(15, areaSelectorFilters), [areaSelectorFilters]);
  const tableFetcher = useCallback(() => getRents(effectiveFilters, 1, visibleRents), [effectiveFilters, visibleRents]);
  const heatmapFetcher = useCallback(() => getRentsAreaHeatmap(80, effectiveFilters), [effectiveFilters]);

  useEffect(() => {
    setVisibleRents(INITIAL_RENT_LIMIT);
  }, [effectiveFilters.area, effectiveFilters.date_from, effectiveFilters.date_to, effectiveFilters.developer, effectiveFilters.prop_type]);

  const { data: kpis, loading: kpisLoading, error: kpisError } = useFetch(kpiFetcher);
  const { data: weekly, loading: weeklyLoading } = useFetch(weeklyFetcher);
  const { data: weeklyCount, loading: countLoading } = useFetch(countFetcher);
  const { data: byType } = useFetch(byTypeFetcher);
  const { data: trend, loading: trendLoading } = useFetch(trendFetcher);
  const { data: byArea, loading: areaLoading } = useFetch(byAreaFetcher);
  const { data: paginated, loading: tableLoading } = useFetch(tableFetcher);
  const { data: heatmap, loading: heatmapLoading, error: heatmapError } = useFetch(heatmapFetcher);

  // Pivot trend data for multi-line chart
  const trendTypeNames = [...new Set((trend ?? []).map((t) => t.prop_type))];
  const trendByWeek = Object.values(
    (trend ?? []).reduce<Record<string, Record<string, number | string>>>((acc, row) => {
      if (!acc[row.month]) acc[row.month] = { month: row.month };
      acc[row.month][row.prop_type] = row.median_rent_sqm;
      return acc;
    }, {}),
  );

  const TREND_COLORS = ['#10b981','#3b82f6','#8b5cf6','#f59e0b','#ef4444','#06b6d4','#ec4899'];
  function colorFor(i: number) { return TREND_COLORS[i % TREND_COLORS.length]; }

  const heatmapAreas = (heatmap ?? []).map((item: RentAreaHeatmapItem) => ({
    id: item.area,
    area: item.area,
    transactionCount: item.contract_count,
    salesValueM: item.annual_rent_m,
    weight: mapMetric === 'amount' ? item.annual_rent_m : item.contract_count,
  }));

  const columns: Column<RentItem>[] = [
    { key: 'registration_date', header: 'Date',      className: 'hidden md:table-cell' },
    { key: 'developer',         header: 'Developer', render: (d) => d.developer ?? '—' },
    { key: 'project',           header: 'Project',   render: (d) => d.project ?? '—' },
    { key: 'area',              header: 'Area',      render: (d) => d.area ?? '—', className: 'hidden lg:table-cell' },
    { key: 'prop_type',         header: 'Type',      render: (d) => d.prop_type ?? '—' },
    { key: 'annual_amount',     header: 'Annual Rent', render: (d) => fmtVal(d.annual_amount) },
    { key: 'rent_per_sqm',      header: 'AED/sqm/yr', render: (d) => d.rent_per_sqm ? d.rent_per_sqm.toFixed(0) : '—', className: 'hidden xl:table-cell' },
  ];
  const canLoadMoreRents = paginated ? paginated.items.length < paginated.total : false;
  const topAreasChartHeight = Math.max(220, (byArea?.length ?? 0) * 28);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Rent Market"
        subtitle={kpis ? `${kpis.total_contracts.toLocaleString()} contracts · ${fmtVal(kpis.total_annual_rent)}` : 'Loading…'}
      />

      {kpisError && <ErrorMessage message={kpisError} />}
      {heatmapError && <ErrorMessage message={heatmapError} />}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-medium text-gray-600">Rent by Property Type</h3>
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
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={byType ?? []} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
              <YAxis type="category" dataKey="prop_type" tick={{ fontSize: 10 }} width={80} />
              <Tooltip formatter={(value: number, _name: string, payload: { payload?: RentByTypeRow }) => {
                if (payload?.payload) {
                  return [`${value.toLocaleString()} contracts`, payload.payload.prop_type];
                }
                return value.toLocaleString();
              }} />
              <Bar dataKey="contract_count" name="Contracts" radius={[0, 4, 4, 0]}>
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
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Median Rent/sqm/yr Trend by Type (AED)</h3>
          {trendLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={trendByWeek} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(value: string) => value.slice(5)} />
                <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                <Tooltip formatter={(v: number) => `AED ${v.toLocaleString()}`} labelFormatter={fmtWeekLabel} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                {trendTypeNames.map((name, i) => (
                  <Line key={name} type="monotone" dataKey={name} stroke={colorFor(i)} strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {kpisLoading ? <LoadingSpinner /> : kpis ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Total Contracts" value={kpis.total_contracts.toLocaleString()} icon="📋" color="blue" />
          <StatCard label="Total Annual Rent" value={fmtVal(kpis.total_annual_rent)} icon="💵" color="emerald" />
          <StatCard label="Median Rent/sqm" value={`AED ${kpis.median_rent_sqm.toLocaleString()}`} icon="📐" color="amber" />
          <StatCard label="Avg. Contract" value={fmtVal(kpis.avg_annual_contract)} icon="📄" color="violet" />
        </div>
      ) : null}

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Weekly Rent Value (AED M)</h3>
          {weeklyLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={weekly ?? []} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: number) => `AED ${v.toFixed(1)}M`} labelFormatter={fmtWeekLabel} />
                <Bar dataKey="value" name="Rent Value" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Weekly Contract Count</h3>
          {countLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={weeklyCount ?? []} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: number) => v.toLocaleString()} labelFormatter={fmtWeekLabel} />
                <Bar dataKey="value" name="Contracts" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Top areas by rent */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium text-gray-600">Top Areas — Median Rent/sqm/yr (AED)</h3>
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
              <Tooltip formatter={(v: number) => `AED ${v.toLocaleString()}`} />
              <Bar dataKey="median_rent_sqm" name="Median Rent/sqm" radius={[0, 4, 4, 0]}>
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
            <h3 className="text-sm font-medium text-gray-600">Rental Market Map</h3>
            <p className="mt-1 text-xs text-gray-400">Heatmap by area using {mapMetric === 'amount' ? 'annual rent amount' : 'contract count'}.</p>
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
          <h3 className="text-sm font-medium text-gray-600">Rent Contracts</h3>
          {paginated && <span className="text-xs text-gray-400">Showing {paginated.items.length.toLocaleString()} of {paginated.total.toLocaleString()}</span>}
        </div>
        {tableLoading ? <LoadingSpinner /> : (
          <DataTable<RentItem> columns={columns} data={paginated?.items ?? []} rowKey={(d) => `${d.registration_date}-${d.annual_amount}-${d.area}`} />
        )}
        {paginated && canLoadMoreRents ? (
          <div className="flex justify-center border-t border-gray-100 px-5 py-3">
            <button
              type="button"
              onClick={() => setVisibleRents((current) => current + RENT_LOAD_STEP)}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50"
            >
              Load more contracts
            </button>
          </div>
        ) : null}
      </div>

    </div>
  );
}

