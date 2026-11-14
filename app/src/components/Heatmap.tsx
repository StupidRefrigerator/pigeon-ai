import { useEffect, useMemo, useRef, useState } from 'react'
import type * as Leaflet from 'leaflet'
import type { HeatmapData } from '../lib/data'

/** One results map in Jimmy's heatmap style. Leaflet and h3-js load in the browser only, after the page renders. */

type Area = 'today' | 'growth' | 'future'
type Metric = 'gap' | 'pred' | 'p'

interface Hex {
  id: string
  real: number
  pred: number
  p: number
  /** predicted − real; for suggested spots, after counting OpenStreetMap toilets too */
  gap: number
  drivers: { f: string; v: number }[] | null
  place: string
  rec?: { rank: number; osm: number }
  future?: { area: string; rank: number; zone: string; station: string; dist: number }
}

const AREAS: { id: Area; label: string }[] = [
  { id: 'today', label: 'Sydney today' },
  { id: 'growth', label: 'Growth suburbs' },
  { id: 'future', label: 'Future areas' },
]
const METRICS: { id: Metric; label: string }[] = [
  { id: 'gap', label: 'Toilets missing' },
  { id: 'pred', label: 'Predicted toilets' },
  { id: 'p', label: 'Chance of a toilet' },
]
const NOTES: Record<Area, string> = {
  today:
    'All 16,228 study hexagons. Each prediction comes from a model that never saw that hexagon in training. Dark outlines mark the 100 places that need at least one more toilet.',
  growth: '1,108 hexagons in growth suburbs the model never trained on. Toilets there today are the real count.',
  future:
    'Bradfield (Aerotropolis) and Leppington as planned, with no toilets yet, so toilets missing equals the prediction. Only the top 10 hexagons per area were saved, so only those are shown. Read the order, not the totals.',
}
const FUTURE_NAMES: Record<string, string> = { aerotropolis: 'Bradfield (Aerotropolis)', leppington: 'Leppington' }

// Jimmy's gap colours, reused for every metric so the scale reads the same way.
const RAMP = ['#dfe7df', '#f7e3aa', '#e9b75b', '#df873c', '#c94c35', '#842f37']
const SCALES: Record<Metric, { title: string; cuts: number[]; labels: string[]; value: (h: Hex) => number }> = {
  gap: { title: 'Toilets missing', cuts: [0, 0.25, 0.5, 1, 2], labels: ['0', '>0–0.25', '0.25–0.5', '0.5–1', '1–2', '2+'], value: (h) => Math.max(0, h.gap) },
  pred: { title: 'Predicted toilets', cuts: [0.05, 0.25, 0.5, 1, 2], labels: ['<0.05', '0.05–0.25', '0.25–0.5', '0.5–1', '1–2', '2+'], value: (h) => h.pred },
  p: { title: 'Chance of at least one toilet', cuts: [0.05, 0.2, 0.4, 0.6, 0.8], labels: ['<5%', '5–20%', '20–40%', '40–60%', '60–80%', '80%+'], value: (h) => h.p },
}
const binOf = (v: number, cuts: number[]) => cuts.filter((c) => v > c).length

function parse(d: HeatmapData): Record<Area, Map<string, Hex>> {
  const drivers = (s: string) =>
    s
      ? s.split(',').map((x) => {
          const [i, v] = x.split(':')
          return { f: d.feats[Number(i)]!, v: Number(v) }
        })
      : []
  const today = new Map<string, Hex>()
  for (const [id, real, pred, p, drv, pl] of d.today) today.set(id, { id, real, pred, p, gap: pred - real, drivers: drivers(drv), place: d.places[pl]! })
  for (const [id, rank, gap, osm] of d.recs) Object.assign(today.get(id)!, { gap, rec: { rank, osm } })
  const growth = new Map<string, Hex>()
  for (const [id, real, pred, p, pl] of d.growth) growth.set(id, { id, real, pred, p, gap: pred - real, drivers: null, place: d.places[pl]! })
  const future = new Map<string, Hex>()
  for (const [area, rank, id, pred, p, zone, station, dist, drv] of d.future)
    future.set(id, {
      id, real: 0, pred, p, gap: pred, drivers: drivers(drv), place: FUTURE_NAMES[area] ?? area,
      future: { area, rank, zone: zone.replace(/^[A-Z0-9]+ /, ''), station, dist },
    })
  return { today, growth, future }
}

// Feature names in plain words.
const NOUNS: Record<string, string> = {
  park_area: 'Park area', food: 'Cafes and food outlets', shop: 'Shops', train_station: 'A train station', bus_stop: 'Bus stops',
  population: 'Residents', walkable_junctions: 'Walkable street corners', sports_area: 'Sports field area', sports: 'Sports facilities',
  beach: 'A beach', playground: 'A playground',
}
export function driverName(f: string) {
  f = f.replace(/_m2$/, '')
  let m = f.match(/^distance_nearest_(.+)_m$/)
  if (m) return 'Distance to the nearest ' + (m[1] === 'sports' ? 'sports facility' : m[1]!.replace(/_/g, ' '))
  if (f === 'population_est') return 'Residents in the hexagon'
  m = f.match(/^(.+)_(inside|(\d+)m)$/)
  if (!m) return f.replace(/_/g, ' ')
  const noun = NOUNS[m[1]!] ?? m[1]!.replace(/_/g, ' ')
  if (m[2] === 'inside') return `${noun} in the hexagon`
  const dist = Number(m[3])
  return `${noun} within ${dist >= 1000 ? `${dist / 1000} km` : `${dist} m`}`
}

const f2 = (v: number) => v.toFixed(2)
const signed = (v: number) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(2)

interface MapRefs {
  L: typeof Leaflet
  h3: typeof import('h3-js')
  map: Leaflet.Map
  layer: Leaflet.LayerGroup | null
  cache: Map<string, Leaflet.LayerGroup>
  selected: Leaflet.Polygon
}

export function Heatmap() {
  const el = useRef<HTMLDivElement>(null)
  const refs = useRef<MapRefs | null>(null)
  const [sets, setSets] = useState<Record<Area, Map<string, Hex>> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [area, setArea] = useState<Area>('today')
  const [metric, setMetric] = useState<Metric>('gap')
  const [selected, setSelected] = useState<Hex | null>(null)
  const areaRef = useRef(area)
  areaRef.current = area

  // load Leaflet, h3-js and the data, then create the map
  useEffect(() => {
    let cancelled = false
    let map: Leaflet.Map | undefined
    Promise.all([import('leaflet'), import('h3-js'), fetch('/heatmap.json').then((r) => (r.ok ? r.json() : Promise.reject(new Error(`heatmap.json: ${r.status}`))))])
      .then(([leaflet, h3, data]: [typeof import('leaflet'), typeof import('h3-js'), HeatmapData]) => {
        if (cancelled || !el.current) return
        // leaflet is UMD: Vite hands it over as the default export
        const L = (leaflet as unknown as { default?: typeof Leaflet }).default ?? leaflet
        const parsed = parse(data)
        const m = L.map(el.current, { preferCanvas: true, zoomControl: false, scrollWheelZoom: false, zoomSnap: 0.25 })
        map = m
        L.control.zoom({ position: 'topright' }).addTo(m)
        m.once('click', () => m.scrollWheelZoom.enable())
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19, opacity: 0.7, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        }).addTo(m)
        const selectedOutline = L.polygon([], { interactive: false, fill: false, color: '#152f37', weight: 3 }).addTo(m)
        // the clicked hexagon comes straight from the click position, so the hexes need no hit testing
        m.on('click', (e: Leaflet.LeafletMouseEvent) => {
          const hex = parsed[areaRef.current].get(h3.latLngToCell(e.latlng.lat, e.latlng.lng, 9))
          if (hex) setSelected(hex)
        })
        refs.current = { L, h3, map: m, layer: null, cache: new Map(), selected: selectedOutline }
        setSets(parsed)
      })
      .catch((e: Error) => !cancelled && setError(`The map could not load: ${e.message}`))
    return () => {
      cancelled = true
      map?.remove()
      refs.current = null
    }
  }, [])

  // fit the view when the area changes
  useEffect(() => {
    const m = refs.current
    if (!m || !sets) return
    setSelected(null)
    m.map.fitBounds(m.L.latLngBounds([...sets[area].keys()].map((id) => m.h3.cellToLatLng(id))).pad(area === 'future' ? 0.15 : 0.02), { animate: false })
  }, [sets, area])

  // draw the coloured hexes
  useEffect(() => {
    const m = refs.current
    if (!m || !sets) return
    const key = area + metric
    let layer = m.cache.get(key)
    if (!layer) {
      const { L, h3 } = m
      const scale = SCALES[metric]
      const byBin: Hex[][] = RAMP.map(() => [])
      for (const h of sets[area].values()) byBin[binOf(scale.value(h), scale.cuts)]!.push(h)
      layer = L.layerGroup()
      // one multipolygon per colour keeps the canvas fast with 16,000 hexagons
      byBin.forEach((hs, b) => {
        if (hs.length) L.polygon(hs.map((h) => [h3.cellToBoundary(h.id)]), { interactive: false, fillColor: RAMP[b], fillOpacity: 0.78, color: '#fff', weight: 0.45 }).addTo(layer!)
      })
      const outlined = [...sets[area].values()].filter((h) => h.rec || h.future)
      if (outlined.length) L.polygon(outlined.map((h) => [h3.cellToBoundary(h.id)]), { interactive: false, fill: false, color: '#68352f', weight: 1.5 }).addTo(layer)
      m.cache.set(key, layer)
    }
    if (m.layer) m.map.removeLayer(m.layer)
    m.layer = layer.addTo(m.map)
    m.selected.bringToFront()
  }, [sets, area, metric])

  // outline the selected hexagon
  useEffect(() => {
    const m = refs.current
    if (!m) return
    m.selected.setLatLngs(selected ? m.h3.cellToBoundary(selected.id) : [])
    m.selected.bringToFront()
  }, [selected])

  const totals = useMemo(() => {
    if (!sets) return null
    const hs = [...sets[area].values()]
    return { hexes: hs.length, pred: hs.reduce((s, h) => s + h.pred, 0), real: hs.reduce((s, h) => s + h.real, 0) }
  }, [sets, area])

  const scale = SCALES[metric]
  return (
    <>
      <div className="switches">
        <div className="switch" role="group" aria-label="Area">
          <span>Area</span>
          {AREAS.map((a) => (
            <button key={a.id} type="button" aria-pressed={area === a.id} onClick={() => setArea(a.id)}>
              {a.label}
            </button>
          ))}
        </div>
        <div className="switch" role="group" aria-label="Colour by">
          <span>Colour by</span>
          {METRICS.map((m) => (
            <button key={m.id} type="button" aria-pressed={metric === m.id} onClick={() => setMetric(m.id)}>
              {m.label}
            </button>
          ))}
        </div>
      </div>
      <p className="note">{NOTES[area]}</p>
      {error && <p className="status error">{error}</p>}
      <div ref={el} className="map" aria-label={`Map of ${AREAS.find((a) => a.id === area)!.label}, coloured by ${scale.title.toLowerCase()}`} />
      <div className="map-total">
        {totals ? (
          <>
            <span>
              <strong>{totals.hexes.toLocaleString()}</strong> hexagons
            </span>
            <span>
              <strong>{totals.pred.toLocaleString(undefined, { maximumFractionDigits: totals.pred < 100 ? 1 : 0 })}</strong> predicted toilets
            </span>
            {area !== 'future' && (
              <span>
                <strong>{totals.real.toLocaleString()}</strong> real toilets
              </span>
            )}
            {area === 'today' && (
              <span>
                <strong>100</strong> places need at least one more toilet
              </span>
            )}
            <span>V12, seed 0</span>
          </>
        ) : (
          !error && 'Loading the map…'
        )}
      </div>
      <div className="legend-row">
        <div className="legend">
          <strong>{scale.title}</strong>
          {RAMP.map((c, i) => (
            <span key={c}>
              <i style={{ background: c }} />
              {scale.labels[i]}
            </span>
          ))}
        </div>
        <p>{area === 'today' ? 'Dark outlines mark the 100 places that need at least one more toilet' : area === 'future' ? 'Dark outlines mark the saved top 10 per area' : 'Same colours on every view'} · click a hexagon for details</p>
      </div>
      <Detail hex={selected} area={area} />
    </>
  )
}

function Detail({ hex, area }: { hex: Hex | null; area: Area }) {
  if (!hex)
    return (
      <div className="details">
        <h3>Select a hexagon</h3>
        <p className="empty-details">Click any coloured cell on the map to see its numbers and what drove its prediction.</p>
      </div>
    )
  const title = hex.rec
    ? `Short by at least one toilet: ${hex.rec.rank} of 100, near ${hex.place}`
    : hex.future
      ? `${hex.place}: ${hex.future.rank} of 10`
      : `Hexagon near ${hex.place}`
  const where = hex.future
    ? `${hex.future.zone}, ${hex.future.dist.toLocaleString()} m from ${hex.future.station}`
    : area === 'growth'
      ? 'Growth suburb, never seen in training'
      : 'Sydney today'
  return (
    <div className="details">
      <h3>{title}</h3>
      <p className="empty-details">
        {where} · <code>{hex.id}</code>
      </p>
      <div className="detail-numbers">
        <div>
          <span>Predicted toilets</span>
          <strong>{f2(hex.pred)}</strong>
        </div>
        {!hex.future && (
          <div>
            <span>Toilets there today</span>
            <strong>{hex.real}</strong>
          </div>
        )}
        <div>
          <span>Toilets missing{hex.rec ? ' (after OSM toilets)' : ''}</span>
          <strong>{signed(hex.gap)}</strong>
        </div>
        <div>
          <span>Chance of a toilet</span>
          <strong>{Math.round(hex.p * 100)}%</strong>
        </div>
        {hex.rec && (
          <div>
            <span>OpenStreetMap toilets</span>
            <strong>{hex.rec.osm}</strong>
          </div>
        )}
      </div>
      <p className="importance-label">What moved this prediction most</p>
      {hex.drivers === null ? (
        <p className="empty-details">Drivers were not saved for the growth-suburb run.</p>
      ) : hex.drivers.length === 0 ? (
        <p className="empty-details">No drivers saved for this hexagon.</p>
      ) : (
        <div className="drivers">
          {hex.drivers.map((d) => (
            <div key={d.f} className="importance-row">
              <span>{driverName(d.f)}</span>
              <span className="dir">{d.v >= 0 ? 'raises it' : 'lowers it'}</span>
              <strong>{signed(d.v)}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
