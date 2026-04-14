import { createContext, useContext, useEffect, useReducer, useMemo, type ReactNode } from 'react';
import type { AppState, Page } from '../types';

const PAGE_STORAGE_KEY = 'modon.currentPage';
const VALID_PAGES: Page[] = ['dashboard', 'developers', 'deals', 'mortgages', 'rentals', 'land', 'valuation', 'projects'];

// ─── State & Actions ─────────────────────────────────────────────────────────
type Action =
  | { type: 'SET_PAGE'; payload: Page }
  | { type: 'SET_DISTRICT'; payload: string | null }
  | { type: 'SET_SEARCH'; payload: string }
  | { type: 'SET_FILTER_DEVELOPER'; payload: string }
  | { type: 'SET_FILTER_AREA'; payload: string }
  | { type: 'SET_FILTER_DATE_FROM'; payload: string }
  | { type: 'SET_FILTER_DATE_TO'; payload: string }
  | { type: 'CLEAR_FILTERS' };

const initialState: AppState = {
  currentPage: 'dashboard',
  selectedDistrict: null,
  searchQuery: '',
  filterDeveloper: '',
  filterArea: '',
  filterDateFrom: '',
  filterDateTo: '',
};

function getInitialState(): AppState {
  if (typeof window === 'undefined') {
    return initialState;
  }

  const storedPage = window.localStorage.getItem(PAGE_STORAGE_KEY);
  if (!storedPage || !VALID_PAGES.includes(storedPage as Page)) {
    return initialState;
  }

  return { ...initialState, currentPage: storedPage as Page };
}

function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_PAGE':
      return { ...state, currentPage: action.payload, searchQuery: '' };
    case 'SET_DISTRICT':
      return { ...state, selectedDistrict: action.payload };
    case 'SET_SEARCH':
      return { ...state, searchQuery: action.payload };
    case 'SET_FILTER_DEVELOPER':
      return { ...state, filterDeveloper: action.payload };
    case 'SET_FILTER_AREA':
      return { ...state, filterArea: action.payload };
    case 'SET_FILTER_DATE_FROM':
      return { ...state, filterDateFrom: action.payload };
    case 'SET_FILTER_DATE_TO':
      return { ...state, filterDateTo: action.payload };
    case 'CLEAR_FILTERS':
      return { ...state, filterDeveloper: '', filterArea: '', filterDateFrom: '', filterDateTo: '' };
    default:
      return state;
  }
}

// ─── Context ─────────────────────────────────────────────────────────────────
interface AppContextValue {
  state: AppState;
  navigate: (page: Page) => void;
  setDistrict: (district: string | null) => void;
  setSearch: (query: string) => void;
  setFilterDeveloper: (v: string) => void;
  setFilterArea: (v: string) => void;
  setFilterDateFrom: (v: string) => void;
  setFilterDateTo: (v: string) => void;
  clearFilters: () => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, undefined, getInitialState);

  useEffect(() => {
    window.localStorage.setItem(PAGE_STORAGE_KEY, state.currentPage);
  }, [state.currentPage]);

  const navigate = (page: Page) => dispatch({ type: 'SET_PAGE', payload: page });
  const setDistrict = (district: string | null) => dispatch({ type: 'SET_DISTRICT', payload: district });
  const setSearch = (query: string) => dispatch({ type: 'SET_SEARCH', payload: query });
  const setFilterDeveloper = (v: string) => dispatch({ type: 'SET_FILTER_DEVELOPER', payload: v });
  const setFilterArea = (v: string) => dispatch({ type: 'SET_FILTER_AREA', payload: v });
  const setFilterDateFrom = (v: string) => dispatch({ type: 'SET_FILTER_DATE_FROM', payload: v });
  const setFilterDateTo = (v: string) => dispatch({ type: 'SET_FILTER_DATE_TO', payload: v });
  const clearFilters = () => dispatch({ type: 'CLEAR_FILTERS' });

  return (
    <AppContext.Provider value={{
      state, navigate, setDistrict, setSearch,
      setFilterDeveloper, setFilterArea, setFilterDateFrom, setFilterDateTo, clearFilters,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}

/** Returns current filters as a CommonFilters object for API calls */
export function useFilters() {
  const { state } = useApp();
  return useMemo(() => ({
    developer: state.filterDeveloper || undefined,
    area: state.filterArea || undefined,
    date_from: state.filterDateFrom || undefined,
    date_to: state.filterDateTo || undefined,
  }), [state.filterDeveloper, state.filterArea, state.filterDateFrom, state.filterDateTo]);
}
