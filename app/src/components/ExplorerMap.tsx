import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { memo, useEffect } from 'react'
import { Circle, MapContainer, Marker, Polygon, Popup, TileLayer, useMap } from 'react-leaflet'
import type { PlannedSite } from '../lib/data'
import type { HexView } from '../lib/explorer'
import { gapColor } from '../lib/gap'

export interface MapProps {
  center: [number, number]
  radiusKm: number
  hexes: HexView[]
  showCounts: boolean
  plans: PlannedSite[] | null
  selectedId: string | null
  onSelect: (hex: HexView) => void
}

function Fit({ center, radiusKm }: Pick<MapProps, 'center' | 'radiusKm'>) {
  const map = useMap()
  useEffect(() => {
    map.fitBounds(L.latLng(center).toBounds(radiusKm * 2000), { animate: true })
  }, [map, center, radiusKm])
  return null
}

function style(h: HexView) {
  const newArea = h.dataset !== 'study'
  return {
    fillColor: gapColor(h.gap),
    fillOpacity: h.gap === 0 ? 0.2 : 0.65,
    color: h.candidate ? '#111' : newArea ? '#6a3ea1' : '#ffffff',
    weight: h.candidate ? 3 : newArea ? 1.5 : 0.6,
    dashArray: newArea && !h.candidate ? '4 3' : undefined,
  }
}

const HexLayer = memo(function HexLayer({ hexes, onSelect }: Pick<MapProps, 'hexes' | 'onSelect'>) {
  // Candidates last so their outline is drawn on top.
  const ordered = [...hexes].sort((a, b) => Number(a.candidate) - Number(b.candidate))
  return (
    <>
      {ordered.map((h) => (
        <Polygon key={`${h.dataset}-${h.id}`} positions={h.boundary} pathOptions={style(h)} eventHandlers={{ click: () => onSelect(h) }} />
      ))}
    </>
  )
})

const countIcon = (n: number) => L.divIcon({ className: '', html: `<div class="hex-label">${n}</div>`, iconSize: [20, 18], iconAnchor: [10, 9] })
const planIcon = L.divIcon({ className: '', html: '<div class="plan-pin"></div>', iconSize: [14, 14], iconAnchor: [7, 7] })

const CountLayer = memo(function CountLayer({ hexes }: { hexes: HexView[] }) {
  return (
    <>
      {hexes
        .filter((h) => (h.actual ?? 0) > 0)
        .map((h) => (
          <Marker key={`c-${h.dataset}-${h.id}`} position={[h.lat, h.lng]} icon={countIcon(h.actual!)} interactive={false} />
        ))}
    </>
  )
})

export default function ExplorerMap({ center, radiusKm, hexes, showCounts, plans, selectedId, onSelect }: MapProps) {
  const selected = hexes.find((h) => h.id === selectedId)
  return (
    <MapContainer center={center} zoom={13} preferCanvas style={{ height: '100%', width: '100%' }}>
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <Fit center={center} radiusKm={radiusKm} />
      <Circle center={center} radius={radiusKm * 1000} pathOptions={{ color: '#3d5a73', weight: 1, fill: false, dashArray: '2 6' }} />
      <HexLayer hexes={hexes} onSelect={onSelect} />
      {selected && <Polygon positions={selected.boundary} pathOptions={{ color: '#0b5fff', weight: 4, fill: false }} interactive={false} />}
      {showCounts && <CountLayer hexes={hexes} />}
      {plans?.map((p) => (
        <Marker key={p.id} position={[p.lat, p.lng]} icon={planIcon}>
          <Popup>
            <strong>{p.name}</strong>
            <br />
            {p.council}
            <br />
            Status: {p.status}
            <br />
            Model percentile of this hex: {p.pct === null ? 'n/a (outside study area)' : `${p.pct}th`}
            <br />
            <a href={p.url} target="_blank" rel="noreferrer">
              Source
            </a>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
