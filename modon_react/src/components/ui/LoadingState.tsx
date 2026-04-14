export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-16 text-gray-400">
      <svg className="h-6 w-6 animate-spin mr-2" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
      <span className="text-sm">Loading…</span>
    </div>
  );
}

export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
      <span className="font-medium">Error:</span> {message}
    </div>
  );
}
