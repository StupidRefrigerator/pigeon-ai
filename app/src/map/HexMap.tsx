import { AmbientLight, DirectionalLight, FlyToInterpolator, LightingEffect, type MapViewState, type PickingInfo } from '@deck.gl/core'
import { H3HexagonLayer } from '@deck.gl/geo-layers'
import { ScatterplotLayer } from '@deck.gl/layers'
import DeckGL from '@deck.gl/react'
import { cellToLatLng } from 'h3-js'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useMemo, useState } from 'react'
import type { Map as MaplibreMap } from 'maplibre-gl'
import { Map as BaseMap } from 'react-map-gl/maplibre'
import type { HeatmapData } from '../lib/data'
import { drivers, MODES, toCells, type Cell, type Cells, type Mode } from './cells'

/** Keyless CARTO basemap, recoloured to the riso paper palette once it loads. */
const BASEMAP = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
const PALETTE = { land: '#FAFAF6', water: '#DCE3F2', park: '#F1F0E4', building: '#F0EFE8', road: '#E7E5DA', boundary: '#C9D1E8', label: '#8A97C2', halo: '#FAFAF6' }

const VIEWS: Record<Mode, MapViewState> = {
  today: { longitude: 151.16, latitude: -33.88, zoom: 11.7, pitch: 55, bearing: -12 },
  growth: { longitude: 150.84, latitude: -33.9, zoom: 10, pitch: 42, bearing: 6 },
  future: { longitude: 150.75, latitude: -33.915, zoom: 11.7, pitch: 58, bearing: 20 },
}

/** Metres of column per predicted toilet at the overview zoom; growth and future predictions are small, so they get taller columns. */
const ELEVATION: Record<Mode, number> = { today: 650, growth: 4200, future: 1100 }
/** Colour gain per mode, so each mode's typical gap reaches the warm end of the ramp. */
const GAIN: Record<Mode, number> = { today: 1, growth: 2.2, future: 1.2 }

type RGBA = [number, number, number, number]
const rgb = (hex: string, a = 255): RGBA => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).concat(a) as RGBA
const RAMP: [number, RGBA][] = [
  [-0.4, rgb('#3255A4', 230)], [-0.05, rgb('#9FB0DC', 220)], [0.03, rgb('#DCE1EE', 200)], [0.12, rgb('#E8E6D6', 220)],
  [0.3, rgb('#FFE800')], [0.75, rgb('#FF8A1F')], [1.3, rgb('#FF48B0')], [2.2, rgb('#C21C86')],
]
function gapColor(x: number): RGBA {
  let [v0, c0] = RAMP[0]!
  if (x <= v0) return c0
  for (const [v1, c1] of RAMP.slice(1)) {
    if (x <= v1) {
      const t = (x - v0) / (v1 - v0)
      return c0.map((c, k) => Math.round(c + (c1[k]! - c) * t)) as RGBA
    }
    ;[v0, c0] = [v1, c1]
  }
  return c0
}

const PURPLE: RGBA = [50, 24, 113, 255]
const MATERIAL = { ambient: 0.55, diffuse: 0.6, shininess: 12, specularColor: [255, 255, 255] as [number, number, number] }
const LIGHTING = new LightingEffect({
  ambient: new AmbientLight({ color: [255, 255, 255], intensity: 1.05 }),
  key: new DirectionalLight({ color: [255, 250, 240], intensity: 1.6, direction: [-2, -5, -6] }),
  fill: new DirectionalLight({ color: [255, 255, 255], intensity: 0.56, direction: [3, 4, -2] }),
})

/** Shrinks columns as you zoom in, so close-up hexagons stay readable instead of towering. */
const zoomFactor = (zoom: number) => Math.min(1.6, Math.max(0.08, 2 ** ((10.35 - zoom) * 0.62)))
const lngLat = (hex: string): [number, number] => {
  const [lat, lng] = cellToLatLng(hex)
  return [lng, lat]
}
const fmt = (x: number) => String(Math.round(x * 100) / 100)

function reduceMotion() {
  return typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches
}

function restyle(map: MaplibreMap) {
  for (const l of map.getStyle().layers) {
    const id = l.id
    const set = (k: string, v: string) => {
      try {
        map.setPaintProperty(id, k, v)
      } catch {
        /* layer lacks this paint property */
      }
    }
    if (l.type === 'background') set('background-color', PALETTE.land)
    else if (l.type === 'fill') set('fill-color', /water/.test(id) ? PALETTE.water : /park|wood|grass|green|landcover/.test(id) ? PALETTE.park : /building/.test(id) ? PALETTE.building : PALETTE.land)
    else if (l.type === 'line') set('line-color', /water|river/.test(id) ? PALETTE.water : /boundary|admin/.test(id) ? PALETTE.boundary : PALETTE.road)
    else if (l.type === 'symbol') {
      if (/poi|housenum|road|highway|transit/.test(id)) map.setLayoutProperty(id, 'visibility', 'none')
      else {
        set('text-color', PALETTE.label)
        set('text-halo-color', PALETTE.halo)
      }
    }
  }
}

type Load = { state: 'loading' } | { state: 'error'; message: string } | { state: 'ready'; cells: Cells }

export default function HexMap({ dataUrl = '/heatmap.json' }: { dataUrl?: string }) {
  const [load, setLoad] = useState<Load>({ state: 'loading' })
  const [mode, setMode] = useState<Mode>('today')
  const [view, setView] = useState<MapViewState>(VIEWS.today)
  const [selected, setSelected] = useState<Cell | null>(null)

  useEffect(() => {
    let live = true
    fetch(dataUrl)
      .then((r) => (r.ok ? (r.json() as Promise<HeatmapData>) : Promise.reject(new Error(`The map data did not load (HTTP ${r.status}).`))))
      .then((d) => live && setLoad({ state: 'ready', cells: toCells(d) }))
      .catch((e: Error) => live && setLoad({ state: 'error', message: e.message }))
    return () => {
      live = false
    }
  }, [dataUrl])

  const fly = (to: MapViewState, duration: number) =>
    setView({ ...to, transitionDuration: reduceMotion() ? 0 : duration, transitionInterpolator: new FlyToInterpolator({ speed: 1.4 }) })

  const switchMode = (m: Mode) => {
    if (m === mode) return
    setMode(m)
    setSelected(null)
    fly(VIEWS[m], 1800)
  }

  const select = (cell: Cell) => {
    setSelected(cell)
    const [longitude, latitude] = lngLat(cell.hex)
    fly({ longitude, latitude, zoom: Math.max(view.zoom, 13.4), pitch: 58, bearing: (view.bearing ?? 0) + 25 }, 1700)
  }

  const z = zoomFactor(view.zoom)
  const layers = useMemo(() => {
    if (load.state !== 'ready') return []
    const { cells } = load
    const data = cells[mode]
    const scale = ELEVATION[mode] * z
    const gain = GAIN[mode]
    const dim = selected ? 0.8 : 1
    const out = []
    if (mode !== 'today') {
      out.push(new H3HexagonLayer<Cell>({ id: 'context', data: cells.today, getHexagon: (d) => d.hex, extruded: false, coverage: 0.86, getFillColor: [50, 85, 164, 22] }))
    }
    out.push(
      new H3HexagonLayer<Cell>({
        id: `hex-${mode}`, data, getHexagon: (d) => d.hex, extruded: true, coverage: 0.8, highPrecision: mode !== 'today',
        elevationScale: scale, getElevation: (d) => d.predicted, getFillColor: (d) => gapColor(d.gap * gain),
        material: MATERIAL, pickable: true, autoHighlight: true, highlightColor: [50, 24, 113, 200], opacity: dim,
      }),
    )
    const spots = data.filter((d) => d.spot !== undefined)
    if (spots.length) {
      out.push(
        new ScatterplotLayer<Cell>({
          id: `spots-${mode}`, data: spots, getPosition: (d) => [...lngLat(d.hex), d.predicted * scale], radiusUnits: 'pixels', getRadius: 6,
          stroked: true, filled: true, getFillColor: [250, 250, 246, 220], getLineColor: PURPLE, lineWidthUnits: 'pixels', getLineWidth: 2.5,
          parameters: { depthCompare: 'always' }, opacity: selected ? 0.4 : 1, updateTriggers: { getPosition: scale },
        }),
      )
    }
    if (selected) {
      out.push(
        new H3HexagonLayer<Cell>({
          id: 'selected', data: [selected], getHexagon: (d) => d.hex, extruded: true, coverage: 0.94, highPrecision: true,
          elevationScale: scale, getElevation: (d) => Math.max(d.predicted, 0.35) * 1.08, getFillColor: PURPLE, material: MATERIAL,
        }),
      )
    }
    return out
  }, [load, mode, z, selected])

  const onClick = (info: PickingInfo<Cell>) => {
    if (info.object?.hex) select(info.object)
  }

  return (
    <div className="hexmap">
      <DeckGL
        viewState={view}
        onViewStateChange={({ viewState }) => setView(viewState as MapViewState)}
        controller
        layers={layers}
        effects={[LIGHTING]}
        onClick={onClick}
        getCursor={({ isHovering, isDragging }) => (isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab')}
      >
        <BaseMap mapStyle={BASEMAP} attributionControl={{ compact: true }} onLoad={(e) => restyle(e.target)} />
      </DeckGL>

      <div className="hexmap-modes slab" role="group" aria-label="Time frame">
        {MODES.map((m) => (
          <button key={m.id} aria-pressed={mode === m.id} onClick={() => switchMode(m.id)}>
            {m.label}
          </button>
        ))}
      </div>

      <div className="hexmap-legend slab">
        <b>Toilets missing</b>
        <div className="ramp" />
        <div className="ends">
          <span>Well served</span>
          <span>2+ short</span>
        </div>
        <p>
          Column height is how many toilets the model expects.
          {mode !== 'growth' && (
            <>
              {' '}
              <i className="ring" aria-hidden="true" />
              {mode === 'future' ? 'Rings are the picks for each future area.' : 'Rings are the 100 suggested spots.'}
            </>
          )}
        </p>
      </div>

      {load.state === 'loading' && <p className="hexmap-status slab">Loading 16,228 hexagons…</p>}
      {load.state === 'error' && <p className="hexmap-status slab" role="alert">{load.message} Reload the page to try again.</p>}

      {selected && load.state === 'ready' && <HexCard cell={selected} feats={load.cells.feats} onClose={() => setSelected(null)} />}
    </div>
  )
}

function HexCard({ cell, feats, onClose }: { cell: Cell; feats: string[]; onClose: () => void }) {
  const top = drivers(cell, feats)
  const max = Math.max(0.01, ...top.map(([, v]) => Math.abs(v)))
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    addEventListener('keydown', onKey)
    return () => removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <aside className="hexcard slab" aria-labelledby="hexcard-name" key={cell.hex}>
      <button className="x" aria-label="Close" onClick={onClose}>
        ×
      </button>
      <h2 id="hexcard-name">{cell.name}</h2>
      <p className="sub">
        {cell.context}
        {cell.spotLabel && <span className="tag">{cell.spotLabel}</span>}
      </p>
      <div className="nums">
        <div>
          <b>{fmt(cell.predicted)}</b>
          <span>toilets predicted</span>
        </div>
        <div>
          <b>{cell.today}</b>
          <span>toilets today</span>
        </div>
      </div>
      <div className="row">
        <span>Chance a hexagon like this has one</span>
        <b>{Math.round(cell.chance * 100)}%</b>
      </div>
      <div className="row">
        <span>Toilets missing</span>
        <b>{cell.gap > 0 ? fmt(cell.gap) : 'none'}</b>
      </div>
      {top.length > 0 && (
        <>
          <h3>What drives the prediction</h3>
          <div className="drv">
            {top.map(([name, v]) => (
              <span key={name} className="drv-row">
                <span>{name}</span>
                <i className={v < 0 ? 'neg' : undefined} style={{ width: Math.max(6, (Math.abs(v) / max) * 92) }} title={v < 0 ? 'lowers the prediction' : 'raises the prediction'} />
              </span>
            ))}
          </div>
        </>
      )}
    </aside>
  )
}
