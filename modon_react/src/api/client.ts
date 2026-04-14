import type { CommonFilters } from './types';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api';

function buildUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') {
        url.searchParams.set(k, String(v));
      }
    }
  }
  return url.toString();
}

export async function apiFetch<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const res = await fetch(buildUrl(path, params));
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function filtersToParams(f?: CommonFilters): Record<string, string | undefined> {
  return {
    developer: f?.developer,
    area: f?.area,
    prop_type: f?.prop_type,
    date_from: f?.date_from,
    date_to: f?.date_to,
  };
}
