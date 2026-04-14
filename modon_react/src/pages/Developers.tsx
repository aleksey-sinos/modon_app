import { useCallback, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import StatCard from '../components/ui/StatCard';
import PageHeader from '../components/ui/PageHeader';
import Badge from '../components/ui/Badge';
import DataTable from '../components/ui/DataTable';
import type { Column } from '../components/ui/DataTable';
import { LoadingSpinner, ErrorMessage } from '../components/ui/LoadingState';
import { useFetch } from '../hooks/useFetch';
import { getDevelopers, getDeveloperDetail } from '../api/services';
import type { DeveloperRow, DeveloperDetail } from '../api/types';

function fmtB(n: number | null | undefined) {
  if (n == null) return '—';
  if (n >= 1e9) return `AED ${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `AED ${(n / 1e6).toFixed(0)}M`;
  return `AED ${n.toLocaleString()}`;
}

function truncateSingleLine(value: string, maxLength = 22) {
  const clean = value.replace(/\s+/g, ' ').trim();
  if (clean.length <= maxLength) return clean;
  return `${clean.slice(0, maxLength - 1)}…`;
}

const AVATAR_COLORS = [
  '#10b981','#3b82f6','#8b5cf6','#f59e0b','#ef4444','#06b6d4','#ec4899',
];

export default function Developers() {
  const [selected, setSelected] = useState<string | null>(null);

  const listFetcher = useCallback(() => getDevelopers(), []);
  const { data: devs, loading, error } = useFetch(listFetcher);

  const detailFetcher = useCallback(
    () => (selected ? getDeveloperDetail(selected) : Promise.resolve(null)),
    [selected],
  );
  const { data: detail, loading: detailLoading } = useFetch(detailFetcher);

  const columns: Column<DeveloperRow>[] = [
    { key: 'developer',       header: 'Developer' },
    { key: 'total_projects',  header: 'Projects',  render: (d) => d.total_projects },
    { key: 'active',          header: 'Active',    render: (d) => <Badge label={String(d.active)} color="green" /> },
    { key: 'sales_count',     header: 'Sales',     render: (d) => d.sales_count?.toLocaleString() ?? '—', className: 'hidden md:table-cell' },
    { key: 'sales_value',     header: 'Sales Value', render: (d) => fmtB(d.sales_value), className: 'hidden lg:table-cell' },
    {
      key: 'median_price_sqm',
      header: 'Median AED/sqm',
      render: (d) => d.median_price_sqm ? d.median_price_sqm.toLocaleString() : '—',
      className: 'hidden lg:table-cell',
    },
    {
      key: 'gross_yield',
      header: 'Gross Yield',
      render: (d) => d.gross_yield ? `${(d.gross_yield * 100).toFixed(1)}%` : '—',
      className: 'hidden xl:table-cell',
    },
  ];

  const total = devs?.length ?? 0;
  const totalProjects = devs?.reduce((s, d) => s + d.total_projects, 0) ?? 0;
  const totalSales = devs?.reduce((s, d) => s + (d.sales_value ?? 0), 0) ?? 0;
  const topByProjects = devs?.slice(0, 15) ?? [];
  const leaderboard = devs?.slice(0, 15) ?? [];
  const developersWithPricing = (devs ?? []).filter((developer) => developer.median_price_sqm != null && developer.sales_count > 0);
  const topPerformersByPrice = [...developersWithPricing]
    .sort((left, right) => (right.median_price_sqm ?? 0) - (left.median_price_sqm ?? 0))
    .slice(0, 5);
  const outsidersByPrice = [...developersWithPricing]
    .sort((left, right) => (left.median_price_sqm ?? 0) - (right.median_price_sqm ?? 0))
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <PageHeader title="Developers" subtitle={`${total} developers`} />

      {error && <ErrorMessage message={error} />}

      {loading ? <LoadingSpinner /> : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Total Developers" value={total} icon="🏢" color="blue" />
            <StatCard label="Total Projects" value={totalProjects.toLocaleString()} icon="🏗" color="emerald" />
            <StatCard label="Total Sales Value" value={fmtB(totalSales)} icon="💰" color="amber" />
            <StatCard label="Active Projects" value={devs?.reduce((s, d) => s + (d.active ?? 0), 0).toLocaleString() ?? '—'} icon="✅" color="violet" />
          </div>

          {/* Top developers bar chart */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
            <h3 className="mb-4 text-sm font-medium text-gray-600">Top 15 Developers by Projects</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={topByProjects} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 140 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="developer" tick={{ fontSize: 11 }} width={140} tickFormatter={(value: string) => truncateSingleLine(value)} />
                <Tooltip />
                <Bar dataKey="total_projects" name="Projects" fill="#10b981" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <DeveloperPriceListCard
              title="Top Performers by Median AED/sqm"
              subtitle="Highest median sales price per sqm among developers with sales activity."
              items={topPerformersByPrice}
              accentColor="emerald"
            />
            <DeveloperPriceListCard
              title="Outsiders by Median AED/sqm"
              subtitle="Lowest median sales price per sqm among developers with sales activity."
              items={outsidersByPrice}
              accentColor="amber"
            />
          </div>

          {/* Table */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-card overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100">
              <h3 className="text-sm font-medium text-gray-600">Developer Leaderboard · Top 15</h3>
            </div>
            <DataTable<DeveloperRow>
              columns={columns}
              data={leaderboard}
              rowKey={(d) => d.developer}
              onRowClick={(d) => setSelected(selected === d.developer ? null : d.developer)}
            />
          </div>

          {/* Developer detail panel */}
          {selected && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card space-y-4">
              {detailLoading ? <LoadingSpinner /> : detail ? (
                <DeveloperDetailPanel detail={detail} />
              ) : null}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function DeveloperPriceListCard({
  title,
  subtitle,
  items,
  accentColor,
}: {
  title: string;
  subtitle: string;
  items: DeveloperRow[];
  accentColor: 'emerald' | 'amber';
}) {
  const accentClasses = accentColor === 'emerald'
    ? 'bg-emerald-50 text-emerald-700 border-emerald-100'
    : 'bg-amber-50 text-amber-700 border-amber-100';

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
      <div className="mb-4">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        <p className="mt-1 text-xs text-gray-400">{subtitle}</p>
      </div>
      <div className="space-y-3">
        {items.map((item, index) => (
          <div key={item.developer} className="flex items-center justify-between gap-3 rounded-lg border border-gray-100 px-3 py-2.5">
            <div className="min-w-0 flex items-center gap-3">
              <div className={`flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold ${accentClasses}`}>
                {index + 1}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-gray-800">{item.developer}</p>
                <p className="text-xs text-gray-400">{item.sales_count.toLocaleString()} sales</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold text-gray-800">
                {item.median_price_sqm != null ? `AED ${item.median_price_sqm.toLocaleString()}` : '—'}
              </p>
              <p className="text-xs text-gray-400">per sqm</p>
            </div>
          </div>
        ))}
        {items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 px-3 py-4 text-center text-sm text-gray-400">
            No developer pricing data available.
          </div>
        ) : null}
      </div>
    </div>
  );
}

function DeveloperDetailPanel({ detail }: { detail: DeveloperDetail }) {
  const k = detail.kpis;
  return (
    <>
      <div className="flex items-center gap-3">
        <div
          className="h-12 w-12 flex-shrink-0 rounded-xl flex items-center justify-center text-white text-xl font-bold"
          style={{ backgroundColor: AVATAR_COLORS[detail.developer.charCodeAt(0) % AVATAR_COLORS.length] }}
        >
          {detail.developer[0]}
        </div>
        <div>
          <h2 className="font-semibold text-gray-900">{detail.developer}</h2>
          <p className="text-xs text-gray-500">
            {k.total_projects} projects · {k.active} active · {k.pending} pending
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6 text-center">
        {[
          { label: 'Sales', value: k.sales_count?.toLocaleString() ?? '—' },
          { label: 'Sales Value', value: fmtB(k.sales_value) },
          { label: 'Median $/sqm', value: k.median_price_sqm ? k.median_price_sqm.toLocaleString() : '—' },
          { label: 'Rent Contracts', value: k.rent_count?.toLocaleString() ?? '—' },
          { label: 'Median Rent/sqm', value: k.median_rent_sqm ? k.median_rent_sqm.toFixed(0) : '—' },
          { label: 'Gross Yield', value: k.gross_yield ? `${(k.gross_yield * 100).toFixed(1)}%` : '—' },
        ].map((item) => (
          <div key={item.label} className="rounded-lg bg-gray-50 py-2.5 px-2">
            <p className="text-sm font-semibold text-gray-800">{item.value}</p>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide mt-0.5">{item.label}</p>
          </div>
        ))}
      </div>

      {detail.monthly_sales.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-gray-500 mb-3">Monthly Sales (AED M)</h4>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={detail.monthly_sales} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(0, 7)} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: number) => `AED ${v.toFixed(1)}M`} labelFormatter={(l: string) => l.slice(0, 7)} />
              <Line type="monotone" dataKey="sales_value_m" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </>
  );
}

