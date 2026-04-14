interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: string;
  trend?: number;
  color?: 'emerald' | 'amber' | 'blue' | 'rose' | 'violet' | 'default';
}

const iconBg: Record<NonNullable<StatCardProps['color']>, string> = {
  emerald: 'bg-emerald-50  text-emerald-600',
  amber:   'bg-amber-50    text-amber-600',
  blue:    'bg-blue-50     text-blue-600',
  rose:    'bg-rose-50     text-rose-600',
  violet:  'bg-violet-50   text-violet-600',
  default: 'bg-gray-100    text-gray-500',
};

export default function StatCard({ label, value, sub, icon, trend, color = 'default' }: StatCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-card hover:shadow-card-hover transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-gray-500 truncate">{label}</p>
          <p className="mt-1 text-xl font-semibold text-gray-900 truncate tracking-tight">{value}</p>
          {sub && <p className="mt-0.5 text-xs text-gray-400 truncate">{sub}</p>}
          {trend !== undefined && (
            <p className={`mt-1.5 inline-flex items-center gap-1 text-xs font-medium rounded-full px-1.5 py-0.5 ${
              trend >= 0
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-rose-50 text-rose-700'
            }`}>
              {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
            </p>
          )}
        </div>
        {icon && (
          <div className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-base ${iconBg[color]}`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

