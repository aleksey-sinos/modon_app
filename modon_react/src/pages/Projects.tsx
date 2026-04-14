import { useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import PageHeader from '../components/ui/PageHeader';
import DubaiMap from '../components/map/DubaiMap';
import type { MapBubbleData } from '../components/map/DubaiMap';
import { LoadingSpinner, ErrorMessage } from '../components/ui/LoadingState';
import { useFetch } from '../hooks/useFetch';
import { getSupplyKPIs, getPipelineByYear, getCompletionBands, getSupplyAreaHeatmap } from '../api/services';
import { getDevelopers } from '../api/services';

function truncateSingleLine(value: string, maxLength = 22) {
  const clean = value.replace(/\s+/g, ' ').trim();
  if (clean.length <= maxLength) return clean;
  return `${clean.slice(0, maxLength - 1)}…`;
}

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;

const YEAR_COLORS: Record<number, string> = {
  2024: '#3b82f6',
  2025: '#10b981',
  2026: '#f59e0b',
  2027: '#8b5cf6',
  2028: '#f43f5e',
  2029: '#06b6d4',
  2030: '#f97316',
};

export default function Projects() {
  const kpiFetcher      = useCallback(() => getSupplyKPIs(), []);
  const pipelineFetcher = useCallback(() => getPipelineByYear(), []);
  const bandsFetcher    = useCallback(() => getCompletionBands(), []);
  const devFetcher      = useCallback(() => getDevelopers(), []);
  const heatmapFetcher  = useCallback(() => getSupplyAreaHeatmap(80), []);

  const { data: kpis,     loading: kpisLoading, error: kpisError } = useFetch(kpiFetcher);
  const { data: pipeline, loading: plLoading } = useFetch(pipelineFetcher);
  const { data: bands } = useFetch(bandsFetcher);
  const { data: devs,     loading: devsLoading } = useFetch(devFetcher);
  const { data: heatmap,  loading: heatmapLoading } = useFetch(heatmapFetcher);

  const bubbles: MapBubbleData[] = (heatmap ?? []).map((item) => ({
    id: `${item.area}-${item.year}`,
    area: item.area,
    year: item.year,
    value: item.units,
    color: YEAR_COLORS[item.year] ?? '#6b7280',
  }));

  const activeYears = [...new Set((heatmap ?? []).map((i) => i.year))].sort();

  // Top 15 developers by active projects
  const topDevs = (devs ?? [])
    .sort((a, b) => b.active - a.active)
    .slice(0, 15)
    .map((d) => ({ developer: d.developer, active: d.active, pending: d.pending }));

  return (
    <div className="space-y-6">
      <PageHeader title="Supply" subtitle="Pipeline and development status" />

      {kpisError && <ErrorMessage message={kpisError} />}

      {kpisLoading ? <LoadingSpinner /> : kpis ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Active Projects" value={kpis.active_projects} icon="✅" color="amber" />
          <StatCard label="Pending Projects" value={kpis.pending_projects} icon="⏳" color="rose" />
          <StatCard label="Units in Pipeline" value={kpis.units_in_pipeline.toLocaleString()} icon="🏗" color="emerald" />
          <StatCard label="Developers Tracked" value={(devs?.length ?? 0).toLocaleString()} icon="🏢" color="blue" />
        </div>
      ) : null}

      {/* Pipeline by year */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <h3 className="mb-4 text-sm font-medium text-gray-600">Pipeline — Units & Projects Completing by Year</h3>
        {plLoading ? <LoadingSpinner /> : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={pipeline ?? []} margin={{ top: 4, right: 24, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="completion_year" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar yAxisId="left" dataKey="units" name="Units" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar yAxisId="right" dataKey="projects" name="Projects" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Completion bands */}
      {bands && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h3 className="mb-4 text-sm font-medium text-gray-600">Projects by Completion %</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={bands} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="band" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="projects" name="Projects" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Developer pipeline */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <h3 className="mb-4 text-sm font-medium text-gray-600">Top 15 Developers — Active vs Pending Projects</h3>
        {devsLoading ? <LoadingSpinner /> : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topDevs} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 150 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="developer" tick={{ fontSize: 10 }} width={150} tickFormatter={(value: string) => truncateSingleLine(value)} />
              <Tooltip />
              <Bar dataKey="active" name="Active" fill="#10b981" stackId="a" radius={[0, 0, 0, 0]} />
              <Bar dataKey="pending" name="Pending" fill="#8b5cf6" stackId="a" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Supply bubble map */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium text-gray-600">Units Pipeline Map</h3>
            <p className="mt-1 text-xs text-gray-400">Bubble size = units announced. Each color represents a completion year.</p>
          </div>
          {activeYears.length > 0 && (
            <div className="flex flex-wrap gap-3">
              {activeYears.map((year) => (
                <div key={year} className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ background: YEAR_COLORS[year] ?? '#6b7280' }}
                  />
                  <span className="text-xs text-gray-600">{year}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        {heatmapLoading && !heatmap ? <LoadingSpinner /> : (
          <DubaiMap apiKey={MAPS_KEY} markers={[]} bubbles={bubbles} height="420px" />
        )}
      </div>
    </div>
  );
}
