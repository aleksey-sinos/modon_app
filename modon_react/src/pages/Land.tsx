import { useCallback, useState } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import type { TooltipProps } from 'recharts';
import StatCard from '../components/ui/StatCard';
import PageHeader from '../components/ui/PageHeader';
import { LoadingSpinner, ErrorMessage } from '../components/ui/LoadingState';
import { useFetch } from '../hooks/useFetch';
import {
  getSupplyKPIs, getLandTypes, getSubTypes, getNearestMetros, getNearestLandmarks,
} from '../api/services';
import type { LocationContextRow } from '../api/types';

const ZONING_COLORS = ['#10b981','#3b82f6','#8b5cf6','#f59e0b','#ef4444','#06b6d4','#ec4899'];
function colorFor(i: number) { return ZONING_COLORS[i % ZONING_COLORS.length]; }

function fmtArea(n: number) {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B sqm`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M sqm`;
  return `${n.toLocaleString()} sqm`;
}

function fmtPercent(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '—';
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
}

function buildPerformanceChartData(rows: LocationContextRow[] | null | undefined) {
  const ranked = [...(rows ?? [])]
    .filter((row) => row.performance_30d_pct != null)
    .sort((left, right) => (left.performance_30d_pct ?? Number.POSITIVE_INFINITY) - (right.performance_30d_pct ?? Number.POSITIVE_INFINITY));

  const biggestFalls = ranked.slice(0, 3).map((row) => ({
    ...row,
    bucket: 'Top Fall',
  }));
  const biggestRises = ranked.slice(-3).reverse().map((row) => ({
    ...row,
    bucket: 'Top Rise',
  }));

  return [...biggestRises, ...biggestFalls];
}

export default function Land() {
  const [locationMarket, setLocationMarket] = useState<'rent' | 'sale'>('rent');
  const kpiFetcher        = useCallback(() => getSupplyKPIs(), []);
  const landTypesFetcher  = useCallback(() => getLandTypes(), []);
  const subTypesFetcher   = useCallback(() => getSubTypes(15), []);
  const metrosFetcher     = useCallback(() => getNearestMetros(10, locationMarket), [locationMarket]);
  const landmarksFetcher  = useCallback(() => getNearestLandmarks(10, locationMarket), [locationMarket]);

  const { data: kpis,      loading: kpisLoading,  error: kpisError } = useFetch(kpiFetcher);
  const { data: landTypes, loading: ltLoading  } = useFetch(landTypesFetcher);
  const { data: subTypes,  loading: stLoading  } = useFetch(subTypesFetcher);
  const { data: metros,    loading: metrosLoading } = useFetch(metrosFetcher);
  const { data: landmarks, loading: landmarksLoading } = useFetch(landmarksFetcher);

  const metroPerformance = buildPerformanceChartData(metros);
  const landmarkPerformance = buildPerformanceChartData(landmarks);

  const leadLandType = landTypes?.[0]?.land_type ?? '—';
  const leadSubType = subTypes?.[0]?.sub_type ?? '—';
  const marketLabel = locationMarket === 'sale' ? 'sales' : 'rental';
  const countLabel = locationMarket === 'sale' ? 'Transactions' : 'Contracts';
  const valueLabel = locationMarket === 'sale' ? 'Total Sales Value' : 'Total Annual Rent';
  const medianLabel = locationMarket === 'sale' ? 'Median Price/sqm' : 'Median Rent/sqm/yr';

  function truncateSingleLine(value: string, maxLength = 24) {
    const clean = value.replace(/\s+/g, ' ').trim();
    if (clean.length <= maxLength) return clean;
    return `${clean.slice(0, maxLength - 1)}…`;
  }

  function LocationContextTooltip({ active, payload }: TooltipProps<number, string>) {
    const row = payload?.[0]?.payload as LocationContextRow | undefined;
    if (!active || !row) return null;
    return (
      <div className="rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-lg">
        <div className="text-sm font-medium text-gray-900">{row.name}</div>
        <div className="mt-2 space-y-1 text-xs text-gray-600">
          <div>{countLabel}: {row.contract_count.toLocaleString()}</div>
          <div>{valueLabel}: AED {row.annual_rent_m.toFixed(1)}M</div>
          <div>{medianLabel}: {row.median_rent_sqm ? `AED ${row.median_rent_sqm.toLocaleString()}` : '—'}</div>
          <div>Current 30D Median: {row.current_median_rent_sqm ? `AED ${row.current_median_rent_sqm.toLocaleString()}` : '—'}</div>
          <div>Previous 30D Median: {row.previous_median_rent_sqm ? `AED ${row.previous_median_rent_sqm.toLocaleString()}` : '—'}</div>
          <div>30D Performance: {fmtPercent(row.performance_30d_pct)}</div>
          <div>30D Volatility: {fmtPercent(row.volatility_30d_pct)}</div>
          <div>Areas Covered: {row.unique_areas.toLocaleString()}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Land" subtitle={`Land parcels with ${marketLabel}-based location context`} />

      {kpisError && <ErrorMessage message={kpisError} />}

      {kpisLoading ? <LoadingSpinner /> : kpis ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Land Parcels"    value={kpis.total_land_parcels.toLocaleString()} icon="🗺"  color="blue" />
          <StatCard label="Total Land Area" value={fmtArea(kpis.total_land_area_sqm)}        icon="📐"  color="emerald" />
          <StatCard label="Top Land Type" value={leadLandType} icon="🌍" color="amber" />
          <StatCard label="Top Sub-type" value={leadSubType} icon="📍" color="violet" />
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Land by Type</h3>
          {ltLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={landTypes ?? []} cx="50%" cy="50%" outerRadius={80} dataKey="parcels" nameKey="land_type">
                  {(landTypes ?? []).map((_, i) => <Cell key={i} fill={colorFor(i)} />)}
                </Pie>
                <Tooltip formatter={(v: number) => v.toLocaleString()} />
                <Legend iconType="circle" iconSize={10} wrapperStyle={{ fontSize: 11 }} formatter={(_v, entry) => (entry.payload as {land_type?: string}).land_type ?? ''} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Top Sub-types by Parcel Count</h3>
          {stLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={subTypes ?? []} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
                <YAxis type="category" dataKey="sub_type" tick={{ fontSize: 10 }} width={80} />
                <Tooltip formatter={(v: number) => v.toLocaleString()} />
                <Bar dataKey="parcels" name="Parcels" fill="#10b981" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-sky-100 bg-sky-50/60 p-4 text-sm text-sky-900">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <p>
            Nearest metro station and landmark views use the selected {marketLabel} registry as location context. The land parcel file does not include proximity fields for metro or landmarks. Location metrics exclude underlying areas with fewer than 20 {locationMarket === 'sale' ? 'sales' : 'rent'} samples.
          </p>
          <div className="inline-flex rounded-lg border border-sky-200 bg-white p-1">
            <button
              type="button"
              onClick={() => setLocationMarket('rent')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${locationMarket === 'rent' ? 'bg-sky-100 text-sky-900' : 'text-sky-700 hover:text-sky-900'}`}
            >
              Rent
            </button>
            <button
              type="button"
              onClick={() => setLocationMarket('sale')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${locationMarket === 'sale' ? 'bg-sky-100 text-sky-900' : 'text-sky-700 hover:text-sky-900'}`}
            >
              Sell
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Metro Locations — Top 3 Rise and Fall</h3>
          <p className="mb-4 text-xs text-gray-400">Largest 30-day increases first, followed by the steepest declines.</p>
          {metrosLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={metroPerformance} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 150 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(value: number) => `${value.toFixed(0)}%`} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={150} tickFormatter={(value: string) => truncateSingleLine(value, 24)} />
                <Tooltip formatter={(value: number, _name: string, payload) => [`${value.toFixed(1)}%`, (payload?.payload as { bucket?: string } | undefined)?.bucket ?? '30D Performance']} />
                <Bar dataKey="performance_30d_pct" name="30D Performance" radius={[0, 4, 4, 0]}>
                  {metroPerformance.map((row) => (
                    <Cell key={`${row.bucket}-${row.name}`} fill={row.bucket === 'Top Rise' ? '#10b981' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Landmark Locations — Top 3 Rise and Fall</h3>
          <p className="mb-4 text-xs text-gray-400">Largest 30-day increases first, followed by the steepest declines.</p>
          {landmarksLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={landmarkPerformance} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 170 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(value: number) => `${value.toFixed(0)}%`} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={170} tickFormatter={(value: string) => truncateSingleLine(value, 28)} />
                <Tooltip formatter={(value: number, _name: string, payload) => [`${value.toFixed(1)}%`, (payload?.payload as { bucket?: string } | undefined)?.bucket ?? '30D Performance']} />
                <Bar dataKey="performance_30d_pct" name="30D Performance" radius={[0, 4, 4, 0]}>
                  {landmarkPerformance.map((row) => (
                    <Cell key={`${row.bucket}-${row.name}`} fill={row.bucket === 'Top Rise' ? '#10b981' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Nearest Metro Station Context</h3>
          {metrosLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={metros ?? []} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 130 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={130} tickFormatter={(value: string) => truncateSingleLine(value, 20)} />
                <Tooltip content={<LocationContextTooltip />} />
                <Bar dataKey="median_rent_sqm" name={medianLabel} fill="#0f766e" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Nearest Landmark Context</h3>
          {landmarksLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={landmarks ?? []} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 150 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={150} tickFormatter={(value: string) => truncateSingleLine(value, 24)} />
                <Tooltip content={<LocationContextTooltip />} />
                <Bar dataKey="median_rent_sqm" name={medianLabel} fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
