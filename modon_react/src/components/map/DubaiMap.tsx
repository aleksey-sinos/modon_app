import {
  APIProvider,
  Map,
  AdvancedMarker,
  Pin,
  InfoWindow,
  useMap,
  useMapsLibrary,
} from '@vis.gl/react-google-maps';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { LatLng } from '../../types';

export interface MapMarkerData {
  id: string;
  position: LatLng;
  label: string;
  subLabel?: string;
  color?: string;
  glyphColor?: string;
}

export interface MapHeatmapAreaData {
  id: string;
  area: string;
  transactionCount: number;
  salesValueM: number;
  weight?: number;
}

export interface MapBubbleData {
  id: string;
  area: string;
  year: number;
  value: number;
  color: string;
}

interface ResolvedHeatmapAreaData extends MapHeatmapAreaData {
  position: LatLng;
}

interface DubaiMapProps {
  apiKey: string;
  markers?: MapMarkerData[];
  heatmapAreas?: MapHeatmapAreaData[];
  bubbles?: MapBubbleData[];
  height?: string;
}

const DUBAI_CENTER = { lat: 25.1512, lng: 55.2435 };

const MAX_MARKERS = 10;
const GEOCODE_CACHE_KEY = 'modon.transactionAreaGeocodes.v1';
const MAP_LIBRARIES: Array<'visualization' | 'geocoding'> = ['visualization', 'geocoding'];
const HEATMAP_RADIUS = 64;
const HEATMAP_GRADIENT = [
  'rgba(220, 252, 231, 0)',
  'rgba(187, 247, 208, 0.35)',
  'rgba(110, 231, 183, 0.55)',
  'rgba(16, 185, 129, 0.75)',
  'rgba(5, 150, 105, 0.9)',
  'rgba(4, 120, 87, 1)',
];

function toAreaKey(area: string) {
  return area.trim().toLowerCase();
}

function readGeocodeCache(): Record<string, LatLng> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(GEOCODE_CACHE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Record<string, LatLng>;
  } catch {
    return {};
  }
}

function writeGeocodeCache(cache: Record<string, LatLng>) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(GEOCODE_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // Ignore storage failures so the map still renders.
  }
}

function geocodeArea(geocoder: google.maps.Geocoder, area: string): Promise<LatLng | null> {
  return new Promise((resolve) => {
    geocoder.geocode({ address: `Dubai ${area}` }, (results: google.maps.GeocoderResult[] | null, status: google.maps.GeocoderStatus) => {
      if (status !== 'OK' || !results?.[0]?.geometry?.location) {
        resolve(null);
        return;
      }
      const location = results[0].geometry.location;
      resolve({ lat: location.lat(), lng: location.lng() });
    });
  });
}

function TransactionHeatmap({ areas }: { areas: MapHeatmapAreaData[] }) {
  const map = useMap();
  const geocodingLibrary = useMapsLibrary('geocoding');
  const visualizationLibrary = useMapsLibrary('visualization');
  const [resolvedAreas, setResolvedAreas] = useState<ResolvedHeatmapAreaData[]>([]);
  const heatmapRef = useRef<google.maps.visualization.HeatmapLayer | null>(null);

  useEffect(() => {
    if (!areas.length) {
      setResolvedAreas([]);
      return;
    }
    if (!geocodingLibrary || !visualizationLibrary || typeof google === 'undefined') {
      return;
    }

    let cancelled = false;
    const cache = readGeocodeCache();
    const cachedAreas: ResolvedHeatmapAreaData[] = [];
    const missingAreas: MapHeatmapAreaData[] = [];

    for (const area of areas) {
      const cachedPosition = cache[toAreaKey(area.area)];
      if (cachedPosition) {
        cachedAreas.push({ ...area, position: cachedPosition });
      } else {
        missingAreas.push(area);
      }
    }

    setResolvedAreas(cachedAreas);

    if (!missingAreas.length) {
      return () => {
        cancelled = true;
      };
    }

    const geocoder = new google.maps.Geocoder();

    const resolveMissingAreas = async () => {
      const nextCache = { ...cache };
      const nextResolved = [...cachedAreas];

      for (const area of missingAreas) {
        const position = await geocodeArea(geocoder, area.area);
        if (!position || cancelled) {
          continue;
        }
        nextCache[toAreaKey(area.area)] = position;
        writeGeocodeCache(nextCache);
        nextResolved.push({ ...area, position });
        setResolvedAreas([...nextResolved]);
      }
    };

    void resolveMissingAreas();

    return () => {
      cancelled = true;
    };
  }, [areas, geocodingLibrary, visualizationLibrary]);

  useEffect(() => {
    if (!map || !visualizationLibrary) {
      return;
    }

    if (!heatmapRef.current) {
      heatmapRef.current = new visualizationLibrary.HeatmapLayer({
        dissipating: true,
        gradient: HEATMAP_GRADIENT,
        opacity: 0.8,
        radius: HEATMAP_RADIUS,
      });
    }

    heatmapRef.current.setMap(map);

    return () => {
      heatmapRef.current?.setMap(null);
    };
  }, [map, visualizationLibrary]);

  useEffect(() => {
    if (!heatmapRef.current || typeof google === 'undefined') {
      return;
    }

    heatmapRef.current.setData(
      resolvedAreas.map((area) => ({
        location: new google.maps.LatLng(area.position.lat, area.position.lng),
        weight: area.weight ?? area.transactionCount,
      })),
    );
  }, [resolvedAreas]);

  return null;
}

function SupplyBubbleLayer({ bubbles }: { bubbles: MapBubbleData[] }) {
  const geocodingLibrary = useMapsLibrary('geocoding');
  const [positionByArea, setPositionByArea] = useState<Record<string, LatLng>>({});

  const uniqueAreas = useMemo(() => [...new Set(bubbles.map((b) => b.area))], [bubbles]);
  const maxValue = useMemo(() => Math.max(1, ...bubbles.map((b) => b.value)), [bubbles]);

  useEffect(() => {
    if (!uniqueAreas.length || !geocodingLibrary || typeof google === 'undefined') return;
    let cancelled = false;
    const cache = readGeocodeCache();
    const resolved: Record<string, LatLng> = {};
    const missing: string[] = [];

    for (const area of uniqueAreas) {
      const cached = cache[toAreaKey(area)];
      if (cached) {
        resolved[area] = cached;
      } else {
        missing.push(area);
      }
    }
    setPositionByArea({ ...resolved });

    if (!missing.length) return;
    const geocoder = new google.maps.Geocoder();
    const resolveAll = async () => {
      const nextCache = { ...cache };
      const next = { ...resolved };
      for (const area of missing) {
        const pos = await geocodeArea(geocoder, area);
        if (!pos || cancelled) continue;
        nextCache[toAreaKey(area)] = pos;
        writeGeocodeCache(nextCache);
        next[area] = pos;
        setPositionByArea({ ...next });
      }
    };
    void resolveAll();
    return () => { cancelled = true; };
  }, [uniqueAreas, geocodingLibrary]);

  return (
    <>
      {bubbles.map((bubble) => {
        const pos = positionByArea[bubble.area];
        if (!pos) return null;
        const norm = Math.sqrt(bubble.value / maxValue);
        const size = Math.round(14 + norm * 58);
        return (
          <AdvancedMarker key={bubble.id} position={pos}>
            <div
              title={`${bubble.area} ${bubble.year}: ${Math.round(bubble.value).toLocaleString()} units`}
              style={{
                width: `${size}px`,
                height: `${size}px`,
                borderRadius: '50%',
                background: `${bubble.color}44`,
                border: `2px solid ${bubble.color}`,
                cursor: 'default',
                pointerEvents: 'none',
              }}
            />
          </AdvancedMarker>
        );
      })}
    </>
  );
}

export default function DubaiMap({ apiKey, markers = [], heatmapAreas = [], bubbles = [], height = '500px' }: DubaiMapProps) {
  const [selected, setSelected] = useState<MapMarkerData | null>(null);
  const visibleMarkers = useMemo(() => markers.slice(0, MAX_MARKERS), [markers]);

  return (
    <APIProvider apiKey={apiKey} libraries={MAP_LIBRARIES}>
      <div style={{ height }} className="w-full rounded-xl overflow-hidden shadow-md">
        <Map
          defaultCenter={DUBAI_CENTER}
          defaultZoom={11}
          mapId="80516a9b2d61eca742f01c3b"
          reuseMaps
          gestureHandling="cooperative"
          disableDefaultUI={false}
          mapTypeControl={false}
        >
          {heatmapAreas.length > 0 ? <TransactionHeatmap areas={heatmapAreas} /> : null}
          {bubbles.length > 0 ? <SupplyBubbleLayer bubbles={bubbles} /> : null}

          {visibleMarkers.map((marker) => (
            <AdvancedMarker
              key={marker.id}
              position={marker.position}
              onClick={() => setSelected(selected?.id === marker.id ? null : marker)}
            >
              <Pin
                background={marker.color ?? '#0284c7'}
                borderColor={marker.glyphColor ?? '#075985'}
                glyphColor="#fff"
                scale={1.1}
              />
            </AdvancedMarker>
          ))}

          {selected && (
            <InfoWindow
              position={selected.position}
              onCloseClick={() => setSelected(null)}
              headerContent={<strong className="text-sm">{selected.label}</strong>}
            >
              {selected.subLabel && (
                <p className="text-xs text-gray-600 mt-1">{selected.subLabel}</p>
              )}
            </InfoWindow>
          )}
        </Map>
      </div>
    </APIProvider>
  );
}
