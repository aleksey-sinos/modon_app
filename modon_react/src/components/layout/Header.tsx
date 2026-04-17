import { useCallback, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { useFetch } from '../../hooks/useFetch';
import { getFilterOptions } from '../../api/services';

const pageTitles: Record<string, string> = {
  dashboard:  'Dashboard',
  developers: 'Developers',
  deals:      'Sales Transactions',
  mortgages:  'Mortgages',
  rentals:    'Rent Market',
  land:       'Land',
  valuation:  'Property Type Analysis',
  projects:   'Supply',
};

const FILTER_PAGES = new Set(['deals', 'rentals', 'valuation']);
// Pages where the developer dropdown should NOT appear
const NO_DEVELOPER_PAGES = new Set(['rentals']);

export default function Header() {
  const {
    state,
    setFilterDeveloper, setFilterArea, setFilterDateFrom, setFilterDateTo, clearFilters,
  } = useApp();

  const showFilters = FILTER_PAGES.has(state.currentPage);
  const showDeveloper = showFilters && !NO_DEVELOPER_PAGES.has(state.currentPage);

  // Clear developer filter when navigating to a page that doesn't show it
  useEffect(() => {
    if (NO_DEVELOPER_PAGES.has(state.currentPage) && state.filterDeveloper) {
      setFilterDeveloper('');
    }
  }, [state.currentPage, state.filterDeveloper, setFilterDeveloper]);

  const fetcher = useCallback(() => getFilterOptions({
    developer: state.filterDeveloper || undefined,
    area: state.filterArea || undefined,
    date_from: state.filterDateFrom || undefined,
    date_to: state.filterDateTo || undefined,
  }), [state.filterArea, state.filterDateFrom, state.filterDateTo, state.filterDeveloper]);
  const { data: opts } = useFetch(fetcher);

  useEffect(() => {
    if (!opts) return;
    if (state.filterDeveloper && !opts.developers.includes(state.filterDeveloper)) {
      setFilterDeveloper('');
    }
    if (state.filterArea && !opts.areas.includes(state.filterArea)) {
      setFilterArea('');
    }
  }, [opts, setFilterArea, setFilterDeveloper, state.filterArea, state.filterDeveloper]);

  const hasActiveFilter =
    !!state.filterDeveloper || !!state.filterArea || !!state.filterDateFrom || !!state.filterDateTo;

  return (
    <header className="border-b border-gray-200 bg-white">
      {/* Top bar */}
      <div className="flex h-14 items-center justify-between px-6">
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-semibold text-gray-900">
            {pageTitles[state.currentPage]}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {/* Avatar */}
          <div className="h-8 w-8 rounded-full bg-brand-500 flex items-center justify-center text-white text-xs font-semibold ring-2 ring-brand-100">
            A
          </div>
        </div>
      </div>

      {/* Filter bar — shown on pages that use common filters */}
      {showFilters && (
        <div className="flex flex-wrap items-center gap-3 border-t border-gray-100 px-6 py-2.5">
          {/* Developer — hidden on pages with sparse developer data */}
          {showDeveloper && (
          <select
            value={state.filterDeveloper}
            onChange={(e) => setFilterDeveloper(e.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 py-1.5 pl-3 pr-7 text-xs text-gray-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
          >
            <option value="">All Developers</option>
            {opts?.developers.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          )}

          {/* Area */}
          <select
            value={state.filterArea}
            onChange={(e) => setFilterArea(e.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 py-1.5 pl-3 pr-7 text-xs text-gray-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
          >
            <option value="">All Areas</option>
            {opts?.areas.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>

          {/* Date from */}
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <span>From</span>
            <input
              type="date"
              value={state.filterDateFrom}
              onChange={(e) => setFilterDateFrom(e.target.value)}
              className="rounded-lg border border-gray-200 bg-gray-50 py-1.5 px-2 text-xs text-gray-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>

          {/* Date to */}
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <span>To</span>
            <input
              type="date"
              value={state.filterDateTo}
              onChange={(e) => setFilterDateTo(e.target.value)}
              className="rounded-lg border border-gray-200 bg-gray-50 py-1.5 px-2 text-xs text-gray-700 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>

          {/* Clear */}
          {hasActiveFilter && (
            <button
              onClick={clearFilters}
              className="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      )}
    </header>
  );
}

