import { useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend,
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import PageHeader from '../components/ui/PageHeader';
import { LoadingSpinner, ErrorMessage } from '../components/ui/LoadingState';
import { useFetch } from '../hooks/useFetch';
import { useFilters } from '../context/AppContext';
import { getPropertyTypes, getPropertyTypeTrend } from '../api/services';

// ─── colour palette per prop type (cycles if more types than entries) ─────────
const TYPE_COLORS = ['#10b981','#3b82f6','#8b5cf6','#f59e0b','#ef4444','#06b6d4','#ec4899'];

function colorFor(i: number) { return TYPE_COLORS[i % TYPE_COLORS.length]; }

export default function Valuation() {
  const filters = useFilters();

  const typesFetcher = useCallback(() => getPropertyTypes(filters), [filters]);
  const trendFetcher = useCallback(() => getPropertyTypeTrend(undefined, filters), [filters]);

  const { data: types, loading: typesLoading, error: typesError } = useFetch(typesFetcher);
  const { data: trend, loading: trendLoading } = useFetch(trendFetcher);

  // Pivot trend data for multi-line chart
  const propTypeNames = [...new Set((trend ?? []).map((t) => t.prop_type))];
  const trendByMonth = Object.values(
    (trend ?? []).reduce<Record<string, Record<string, number | string>>>((acc, row) => {
      if (!acc[row.month]) acc[row.month] = { month: row.month.slice(0, 7) };
      acc[row.month][row.prop_type] = row.median_price_sqm;
      return acc;
    }, {}),
  );

  const totalTx = types?.reduce((s, t) => s + t.transaction_count, 0) ?? 0;
  const totalSalesM = types?.reduce((s, t) => s + t.sales_value_m, 0) ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader title="Property Types" subtitle="Sales analysis by property type" />

      {typesError && <ErrorMessage message={typesError} />}

      {typesLoading ? <LoadingSpinner /> : types ? (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Property Types" value={types.length} icon="🏠" color="blue" />
            <StatCard label="Total Transactions" value={totalTx.toLocaleString()} icon="🤝" color="emerald" />
            <StatCard label="Total Sales" value={`AED ${totalSalesM >= 1000 ? `${(totalSalesM / 1000).toFixed(1)}B` : `${totalSalesM.toFixed(0)}M`}`} icon="💰" color="amber" />
            <StatCard label="Types Tracked" value={types.length} icon="📊" color="violet" />
          </div>

          {/* By type bars */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
              <h3 className="mb-4 text-sm font-medium text-gray-600">Transactions by Type</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={types} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="prop_type" tick={{ fontSize: 10 }} width={80} />
                  <Tooltip formatter={(v: number) => v.toLocaleString()} />
                  <Bar dataKey="transaction_count" name="Transactions" fill="#10b981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
              <h3 className="mb-4 text-sm font-medium text-gray-600">Median Price/sqm by Type (AED)</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={types} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="prop_type" tick={{ fontSize: 10 }} width={80} />
                  <Tooltip formatter={(v: number) => `AED ${v.toLocaleString()}`} />
                  <Bar dataKey="median_price_sqm" name="Median AED/sqm" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Type cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {types.map((t, i) => (
              <div key={t.prop_type} className="rounded-xl border border-gray-200 bg-white p-4 shadow-card">
                <div className="flex items-center gap-2 mb-3">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: colorFor(i) }} />
                  <h3 className="font-semibold text-gray-900">{t.prop_type}</h3>
                </div>
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="rounded-lg bg-gray-50 py-2">
                    <p className="text-sm font-semibold text-gray-800">{t.transaction_count.toLocaleString()}</p>
                    <p className="text-[10px] text-gray-400 uppercase tracking-wide">Transactions</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 py-2">
                    <p className="text-sm font-semibold text-gray-800">{t.sales_value_m >= 1000 ? `${(t.sales_value_m / 1000).toFixed(1)}B` : `${t.sales_value_m.toFixed(0)}M`} AED</p>
                    <p className="text-[10px] text-gray-400 uppercase tracking-wide">Sales Value</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 py-2">
                    <p className="text-sm font-semibold text-gray-800">{t.median_price_sqm.toLocaleString()}</p>
                    <p className="text-[10px] text-gray-400 uppercase tracking-wide">Med AED/sqm</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 py-2">
                    <p className="text-sm font-semibold text-gray-800">{t.median_area_sqm.toLocaleString()}</p>
                    <p className="text-[10px] text-gray-400 uppercase tracking-wide">Med sqm</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}

      {/* Trend lines */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <h3 className="mb-4 text-sm font-medium text-gray-600">Median Price/sqm Trend by Type (AED)</h3>
        {trendLoading ? <LoadingSpinner /> : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trendByMonth} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: number) => `AED ${v.toLocaleString()}`} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              {propTypeNames.map((name, i) => (
                <Line key={name} type="monotone" dataKey={name} stroke={colorFor(i)} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
