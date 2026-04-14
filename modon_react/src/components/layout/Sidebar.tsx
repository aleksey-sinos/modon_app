import clsx from 'clsx';
import { useApp } from '../../context/AppContext';
import type { Page } from '../../types';

// ─── SVG icon components ──────────────────────────────────────────────────────
function IconDashboard({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="2" y="2" width="7" height="7" rx="1.5" />
      <rect x="11" y="2" width="7" height="7" rx="1.5" />
      <rect x="2" y="11" width="7" height="7" rx="1.5" />
      <rect x="11" y="11" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function IconBuilding({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M4 18V5a1 1 0 011-1h10a1 1 0 011 1v13" strokeLinecap="round" />
      <path d="M2 18h16" strokeLinecap="round" />
      <path d="M8 18v-4h4v4" />
      <path d="M7 8h1m4 0h1M7 11h1m4 0h1" strokeLinecap="round" />
    </svg>
  );
}

function IconHandshake({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 10l3-3 2.5 2.5L11 7l6 3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 10l2 4h4l3-2 4 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconKey({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="7.5" cy="7.5" r="3.5" />
      <path d="M10.5 7.5h6M14.5 7.5v2.5" strokeLinecap="round" />
    </svg>
  );
}

function IconShield({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M10 2l6 2.5v4.8c0 3.6-2.2 6.9-6 8.7-3.8-1.8-6-5.1-6-8.7V4.5L10 2z" strokeLinejoin="round" />
      <path d="M7 10l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconMap({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M2 5l5-2 6 2 5-2v13l-5 2-6-2-5 2V5z" strokeLinejoin="round" />
      <path d="M7 3v13M13 5v12" />
    </svg>
  );
}

function IconChart({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M3 15l4-5 4 3 3-6 3 4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M2 18h16" strokeLinecap="round" />
    </svg>
  );
}

function IconCrane({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M10 3v12" strokeLinecap="round" />
      <path d="M10 3h7" strokeLinecap="round" />
      <path d="M17 3l-7 5" strokeLinecap="round" />
      <path d="M7 15h6" strokeLinecap="round" />
      <path d="M8 18h4" strokeLinecap="round" />
      <path d="M10 15v3" strokeLinecap="round" />
    </svg>
  );
}

type IconComponent = (props: { className?: string }) => JSX.Element;

interface NavItem {
  id: Page;
  label: string;
  Icon: IconComponent;
}

const navItems: NavItem[] = [
  { id: 'dashboard',  label: 'Dashboard',  Icon: IconDashboard },
  { id: 'deals',      label: 'Sales',      Icon: IconHandshake },
  { id: 'rentals',    label: 'Rents',      Icon: IconKey       },
  { id: 'mortgages',  label: 'Mortgages',  Icon: IconShield    },
  { id: 'developers', label: 'Developers', Icon: IconBuilding  },
  { id: 'land',       label: 'Land',       Icon: IconMap       },
  { id: 'valuation',  label: 'Property Types', Icon: IconChart },
  { id: 'projects',   label: 'Supply',     Icon: IconCrane     },
];

export default function Sidebar() {
  const { state, navigate } = useApp();

  return (
    <aside className="flex h-full w-[220px] flex-shrink-0 flex-col bg-white border-r border-gray-200">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-gray-100">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-white font-bold text-sm">
          D
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900 leading-tight">Dubai RE</p>
          <p className="text-[11px] text-gray-400 leading-tight">Analytics</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        <p className="px-2 mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
          Overview
        </p>
        {navItems.slice(0, 1).map((item) => (
          <NavButton key={item.id} item={item} active={state.currentPage === item.id} onClick={() => navigate(item.id)} />
        ))}
        <p className="px-2 mt-4 mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
          Market Data
        </p>
        {navItems.slice(1).map((item) => (
          <NavButton key={item.id} item={item} active={state.currentPage === item.id} onClick={() => navigate(item.id)} />
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-100 px-5 py-4">
        <p className="text-[11px] text-gray-400">Data as of April 2026</p>
      </div>
    </aside>
  );
}

function NavButton({ item, active, onClick }: { item: NavItem; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-all duration-100',
        active
          ? 'bg-brand-50 text-brand-700'
          : 'text-gray-400 hover:bg-gray-50 hover:text-gray-700',
      )}
    >
      <item.Icon className="h-4 w-4 flex-shrink-0" />
      <span className={active ? 'text-brand-700' : 'text-gray-600 group-hover:text-gray-800'}>
        {item.label}
      </span>
      {active && (
        <span className="ml-auto h-1.5 w-1.5 rounded-full bg-brand-500" />
      )}
    </button>
  );
}


