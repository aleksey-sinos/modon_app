interface BadgeProps {
  label: string;
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'gray' | 'orange';
}

const colors = {
  blue:   'bg-blue-50    text-blue-700   ring-blue-200/60',
  green:  'bg-emerald-50 text-emerald-700 ring-emerald-200/60',
  yellow: 'bg-amber-50   text-amber-700  ring-amber-200/60',
  red:    'bg-rose-50    text-rose-700   ring-rose-200/60',
  purple: 'bg-violet-50  text-violet-700 ring-violet-200/60',
  gray:   'bg-gray-50    text-gray-600   ring-gray-200/60',
  orange: 'bg-orange-50  text-orange-700 ring-orange-200/60',
};

export default function Badge({ label, color = 'gray' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${colors[color]}`}>
      {label}
    </span>
  );
}
