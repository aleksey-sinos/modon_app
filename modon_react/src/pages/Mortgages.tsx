import { useCallback, useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import PageHeader from '../components/ui/PageHeader';
import DataTable from '../components/ui/DataTable';
import type { Column } from '../components/ui/DataTable';
import { LoadingSpinner, ErrorMessage } from '../components/ui/LoadingState';
import { useFetch } from '../hooks/useFetch';
import {
  getMortgageKPIs,
  getMortgagesMonthly,
  getMortgagesByProcedure,
  getMortgages,
} from '../api/services';
import type { MortgageFilters, MortgageTransactionItem } from '../api/types';

function formatCurrency(value: number | null | undefined) {
  if (value == null) return '—';
  if (value >= 1e9) return `AED ${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `AED ${(value / 1e6).toFixed(1)}M`;
  return `AED ${value.toLocaleString()}`;
}

export default function Mortgages() {
  const [page, setPage] = useState(1);
  const [procedure, setProcedure] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const filters = useMemo<MortgageFilters>(() => ({
    procedure: procedure || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  }), [dateFrom, dateTo, procedure]);

  const aggregateFilters = useMemo<Omit<MortgageFilters, 'procedure'>>(() => ({
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  }), [dateFrom, dateTo]);

  const kpiFetcher = useCallback(() => getMortgageKPIs(filters), [filters]);
  const monthlyFetcher = useCallback(() => getMortgagesMonthly(filters), [filters]);
  const procedureFetcher = useCallback(() => getMortgagesByProcedure(aggregateFilters), [aggregateFilters]);
  const tableFetcher = useCallback(() => getMortgages(filters, page, 50), [filters, page]);

  const { data: kpis, loading: kpisLoading, error: kpisError } = useFetch(kpiFetcher);
  const { data: monthly, loading: monthlyLoading } = useFetch(monthlyFetcher);
  const { data: byProcedure, loading: procedureLoading } = useFetch(procedureFetcher);
  const { data: paginated, loading: tableLoading } = useFetch(tableFetcher);

  const procedureOptions = byProcedure?.map((item) => item.procedure) ?? [];
  const totalPages = paginated ? Math.ceil(paginated.total / paginated.page_size) : 1;

  const columns: Column<MortgageTransactionItem>[] = [
    { key: 'instance_date', header: 'Date', render: (row) => row.instance_date ?? '—', className: 'hidden md:table-cell' },
    { key: 'transaction_number', header: 'Transaction', render: (row) => row.transaction_number ?? '—' },
    { key: 'procedure', header: 'Procedure', render: (row) => row.procedure ?? '—' },
    { key: 'mortgage_value', header: 'Mortgage Value', render: (row) => formatCurrency(row.mortgage_value) },
    { key: 'row_count', header: 'Rows', render: (row) => row.row_count.toLocaleString(), className: 'hidden lg:table-cell' },
    { key: 'prop_type', header: 'Type', render: (row) => row.prop_type ?? '—', className: 'hidden xl:table-cell' },
    { key: 'is_offplan', header: 'Stage', render: (row) => row.is_offplan ?? '—', className: 'hidden xl:table-cell' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mortgages"
        subtitle={kpis ? `${kpis.total_mortgage_transactions.toLocaleString()} transactions · ${formatCurrency(kpis.total_mortgage_value)}` : 'Loading…'}
      />

      {kpisError && <ErrorMessage message={kpisError} />}

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-gray-500">
            <span>Procedure</span>
            <select
              value={procedure}
              onChange={(event) => {
                setProcedure(event.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
            >
              <option value="">All procedures</option>
              {procedureOptions.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-xs text-gray-500">
            <span>From</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => {
                setDateFrom(event.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs text-gray-500">
            <span>To</span>
            <input
              type="date"
              value={dateTo}
              onChange={(event) => {
                setDateTo(event.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </label>

          {(procedure || dateFrom || dateTo) && (
            <button
              onClick={() => {
                setProcedure('');
                setDateFrom('');
                setDateTo('');
                setPage(1);
              }}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {kpisLoading ? <LoadingSpinner /> : kpis ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          <StatCard label="Mortgage Transactions" value={kpis.total_mortgage_transactions.toLocaleString()} icon="🏦" color="blue" />
          <StatCard label="Total Mortgage Value" value={formatCurrency(kpis.total_mortgage_value)} icon="💳" color="emerald" />
          <StatCard label="Average Mortgage" value={formatCurrency(kpis.avg_mortgage_value)} icon="📐" color="amber" />
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card lg:col-span-2">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Monthly Mortgage Value (AED M)</h3>
          {monthlyLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={monthly ?? []} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(value: string) => value.slice(0, 7)} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(value: number) => `AED ${value.toFixed(1)}M`} labelFormatter={(value: string) => value.slice(0, 7)} />
                <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">By Procedure</h3>
          {procedureLoading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={byProcedure ?? []} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 120 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="procedure" tick={{ fontSize: 10 }} width={120} />
                <Tooltip formatter={(value: number) => value.toLocaleString()} />
                <Bar dataKey="transaction_count" name="Transactions" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {byProcedure && byProcedure.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white shadow-card overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h3 className="text-sm font-medium text-gray-600">Procedure Breakdown</h3>
          </div>
          <DataTable
            columns={[
              { key: 'procedure', header: 'Procedure' },
              { key: 'transaction_count', header: 'Transactions', render: (row) => row.transaction_count.toLocaleString() },
              { key: 'total_value_m', header: 'Total Value', render: (row) => `AED ${row.total_value_m.toFixed(1)}M` },
              { key: 'avg_value', header: 'Average Value', render: (row) => formatCurrency(row.avg_value) },
            ]}
            data={byProcedure}
            rowKey={(row) => row.procedure}
          />
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-white shadow-card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-600">Mortgage Transactions</h3>
          {paginated && <span className="text-xs text-gray-400">{paginated.total.toLocaleString()} total</span>}
        </div>
        {tableLoading ? <LoadingSpinner /> : (
          <DataTable<MortgageTransactionItem>
            columns={columns}
            data={paginated?.items ?? []}
            rowKey={(row) => `${row.transaction_number ?? 'na'}-${row.instance_date ?? 'na'}-${row.procedure ?? 'na'}`}
          />
        )}
        {paginated && totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3">
            <button
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 disabled:opacity-40 hover:bg-gray-50"
            >
              Previous
            </button>
            <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((value) => value + 1)}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}