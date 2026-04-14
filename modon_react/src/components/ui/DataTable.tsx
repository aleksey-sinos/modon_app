import clsx from 'clsx';
import React from 'react';

export interface Column<T extends object> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T extends object> {
  columns: Column<T>[];
  data: T[];
  keyField?: keyof T;
  rowKey?: (row: T) => string;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
}

export default function DataTable<T extends object>({
  columns,
  data,
  keyField,
  rowKey,
  emptyMessage = 'No records found.',
  onRowClick,
}: DataTableProps<T>) {
  function getKey(row: T): string {
    if (rowKey) return rowKey(row);
    if (keyField) return String((row as Record<string, unknown>)[String(keyField)]);
    return String(Math.random());
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-card">
      <table className="w-full text-sm">
        <thead className="border-b border-gray-100 bg-gray-50/60">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  'px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-400',
                  col.className,
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-10 text-center text-sm text-gray-400">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={getKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={clsx('hover:bg-gray-50/70 transition-colors', onRowClick && 'cursor-pointer')}
              >
                {columns.map((col) => (
                  <td key={col.key} className={clsx('px-4 py-3 text-sm text-gray-700', col.className)}>
                    {col.render
                      ? col.render(row)
                      : String((row as Record<string, unknown>)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
