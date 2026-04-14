interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

import React from 'react';

export default function PageHeader({ title, subtitle, action }: PageHeaderProps) {
  return (
    <div className="mb-5 flex items-start justify-between">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 tracking-tight">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-gray-400">{subtitle}</p>}
      </div>
      {action && <div className="ml-4">{action}</div>}
    </div>
  );
}
