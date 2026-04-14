export interface LatLng {
  lat: number;
  lng: number;
}

// ─── Developers ──────────────────────────────────────────────────────────────
export interface Developer {
  id: string;
  name: string;
  founded: number;
  projectsCount: number;
  totalAreaSqm: number;
  completedUnits: number;
  activeProjects: number;
  headquarters: string;
  status: 'active' | 'inactive';
  logoColor: string;
}

// ─── Deals ────────────────────────────────────────────────────────────────────
export type PropertyType = 'apartment' | 'villa' | 'townhouse' | 'penthouse' | 'commercial' | 'land';

export interface Deal {
  id: string;
  propertyName: string;
  developer: string;
  district: string;
  type: PropertyType;
  areaSqm: number;
  price: number;          // AED
  pricePerSqm: number;    // AED
  date: string;           // ISO
  coordinates: LatLng;
  bedrooms?: number;
}

// ─── Rentals ──────────────────────────────────────────────────────────────────
export interface Rental {
  id: string;
  propertyName: string;
  district: string;
  type: PropertyType;
  areaSqm: number;
  bedrooms: number;
  annualRent: number;     // AED
  monthlyRent: number;    // AED
  listedDate: string;     // ISO
  coordinates: LatLng;
  furnished: boolean;
}

// ─── Land ─────────────────────────────────────────────────────────────────────
export type LandZoning = 'residential' | 'commercial' | 'mixed-use' | 'industrial' | 'hospitality';

export interface LandPlot {
  id: string;
  plotNumber: string;
  district: string;
  areaSqm: number;
  zoning: LandZoning;
  price: number;          // AED
  pricePerSqm: number;
  status: 'available' | 'sold' | 'reserved';
  coordinates: LatLng;
}

// ─── Valuation ────────────────────────────────────────────────────────────────
export interface Valuation {
  id: string;
  propertyName: string;
  district: string;
  type: PropertyType;
  areaSqm: number;
  bedrooms?: number;
  currentValue: number;   // AED
  previousValue: number;  // AED
  changePercent: number;
  valuationDate: string;  // ISO
  coordinates: LatLng;
}

// ─── Projects ─────────────────────────────────────────────────────────────────
export type ProjectStatus = 'planned' | 'under-construction' | 'completed' | 'on-hold';

export interface Project {
  id: string;
  name: string;
  developer: string;
  district: string;
  status: ProjectStatus;
  type: PropertyType;
  totalUnits: number;
  soldUnits: number;
  completionDate: string;   // ISO
  launchDate: string;       // ISO
  description: string;
  coordinates: LatLng;
  priceFrom: number;        // AED
}

// ─── App State ────────────────────────────────────────────────────────────────
export type Page =
  | 'dashboard'
  | 'developers'
  | 'deals'
  | 'mortgages'
  | 'rentals'
  | 'land'
  | 'valuation'
  | 'projects';

export interface AppState {
  currentPage: Page;
  selectedDistrict: string | null;
  searchQuery: string;
  filterDeveloper: string;
  filterArea: string;
  filterDateFrom: string;
  filterDateTo: string;
}
