import { cellToLatLng } from 'h3-js'
import type { LiveLayer } from '../infra'
import type { Stats, Tracking } from '../lib/data'
import { distanceKm, searchPlaces, type Place } from '../map/area'
import { drivers, MODES, type Cell, type Cells, type Mode } from '../map/cells'
import type { AskEvent } from './protocol'

/** Everything the agent's tools read for one layer. Built once per server instance. */
export interface AgentData {
  layer: LiveLayer
  cells: Cells
  places: Place[]
  stats: Stats
  tracking: Tracking
}

/** What a tool call gives back: JSON for the model, a short label for the step list, and maybe a map event for the browser. */
export interface ToolResult {
  output: unknown
  label: string
  event?: Extract<AskEvent, { type: 'map' }>
}

type Json = Record<string, unknown>
const num = (description: string) => ({ type: ['number', 'null'], description })
const str = (description: string) => ({ type: ['string', 'null'], description })
const fn = (name: string, description: string, properties: Json) => ({
  type: 'function' as const,
  name,
  description,
  strict: true,
  parameters: { type: 'object', properties, required: Object.keys(properties), additionalProperties: false },
})

const MODE = { type: 'string', enum: MODES.map((m) => m.id), description: 'today = existing Sydney; growth = new growth suburbs; future = planned areas (Bradfield/Aerotropolis, Leppington) that are not built yet.' }
const WHERE = {
  place: str('Suburb or landmark name, e.g. "Parramatta". Null for all of Sydney or when lat/lng are given.'),
  lat: num('Latitude of the centre, if known.'),
  lng: num('Longitude of the centre, if known.'),
  radius_km: num('Search radius around the centre in km (default 2). Ignored without a centre.'),
}

export const TOOL_DEFS = [
  fn('find_place', 'Look up suburbs and landmarks the map knows, with coordinates.', { query: { type: 'string' } }),
  fn('search_spots', 'Find hexagons (about one city block each) ranked by how many units are missing, optionally around a place.', {
    mode: MODE,
    ...WHERE,
    suggested_only: { type: 'boolean', description: 'Only the ringed suggested spots.' },
    min_missing: num('Only hexagons missing at least this many units.'),
    max_today: num('Only hexagons with at most this many units today (0 = none yet).'),
    sort_by: { type: 'string', enum: ['rank', 'missing', 'predicted', 'chance'], description: 'rank = the suggested-spot order shown on the map (missing after counting OpenStreetMap units).' },
    limit: num('How many to return, up to 25 (default 10).'),
  }),
  fn('plan_sites', 'Pick N build sites that cover the most missing units, keeping a minimum walking spacing between them. Use this for budget questions after turning the budget into a count.', {
    mode: MODE,
    ...WHERE,
    count: { type: 'number', description: 'How many sites to build (1 to 20).' },
    min_spacing_m: num('Minimum distance between picked sites in metres (default 400).'),
    max_today: num('Only hexagons with at most this many units today.'),
  }),
  fn('get_hex', 'Everything known about one hexagon: prediction, what drives it, its 1 km neighbourhood and the saved explanation if it is a suggested spot.', { hex: { type: 'string' } }),
  fn('area_stats', 'Totals for an area: hexagons, units today, units predicted, units missing and its top spots.', { mode: MODE, ...WHERE }),
  fn('model_facts', 'How well the model was tested, to quote when the user asks whether to trust it.', {}),
  fn('show_on_map', 'Highlight hexagons on the user’s map. Call this once with the hexagons you recommend before answering.', {
    mode: MODE,
    hexes: { type: 'array', items: { type: 'string' } },
    caption: { type: 'string', description: 'A few words for the highlight, e.g. "3 sites for $1.2M in Parramatta".' },
  }),
]

const r2 = (x: number) => Math.round(x * 100) / 100
const ll = (hex: string) => cellToLatLng(hex) as [number, number]

type Center = { label: string; lat: number; lng: number; km: number }
type Where = { place: string | null; lat: number | null; lng: number | null; radius_km: number | null }

/** The circle a query is about, null for all of Sydney, or a message for the model when the place is unknown. */
function center(d: AgentData, w: Where): Center | null | string {
  const km = Math.min(Math.max(w.radius_km ?? 2, 0.2), 20)
  if (w.lat !== null && w.lng !== null) return { label: `${w.lat.toFixed(4)}, ${w.lng.toFixed(4)}`, lat: w.lat, lng: w.lng, km }
  if (!w.place) return null
  const [p] = searchPlaces(d.places, w.place, 1)
  if (!p) return `No place called "${w.place}" on the map. Try find_place, or pass lat/lng.`
  return { label: p[0], lat: p[1], lng: p[2], km }
}

const kmFrom = (c: Center, hex: string) => {
  const [lat, lng] = ll(hex)
  return distanceKm(c.lat, c.lng, lat, lng)
}

function within(cells: Cell[], c: Center | null) {
  return c ? cells.filter((x) => kmFrom(c, x.hex) <= c.km) : cells
}

function row(cell: Cell, c?: Center | null) {
  return {
    hex: cell.hex, name: cell.name, context: cell.context, suggested_rank: cell.spot ?? null, today: cell.today,
    predicted: r2(cell.predicted), missing: r2(cell.gap), chance_of_one_pct: Math.round(cell.chance * 100),
    ...(c ? { km_from_centre: r2(kmFrom(c, cell.hex)) } : {}),
  }
}

const SORT = { rank: (c: Cell) => -(c.spot ?? Infinity), missing: (c: Cell) => c.gap, predicted: (c: Cell) => c.predicted, chance: (c: Cell) => c.chance }

function cellIn(d: AgentData, hex: string): [Mode, Cell] | null {
  for (const { id } of MODES) {
    const c = d.cells[id].find((x) => x.hex === hex)
    if (c) return [id, c]
  }
  return null
}

export function runTool(d: AgentData, name: string, a: Json): ToolResult {
  const unit = d.layer.unit
  switch (name) {
    case 'find_place': {
      const hits = searchPlaces(d.places, String(a.query), 5)
      return { label: `Looked up “${a.query}”`, output: hits.map(([n, lat, lng]) => ({ name: n, lat, lng })) }
    }
    case 'search_spots': {
      const c = center(d, a as Where)
      if (typeof c === 'string') return { label: `Couldn’t find ${a.place}`, output: { error: c } }
      const mode = a.mode as Mode
      const min = (a.min_missing as number | null) ?? -Infinity
      const max = (a.max_today as number | null) ?? Infinity
      const key = SORT[a.sort_by as keyof typeof SORT] ?? SORT.missing
      const hits = within(d.cells[mode], c).filter((x) => (!a.suggested_only || x.spot !== undefined) && x.gap >= min && x.today <= max)
      const limit = Math.min(Math.max((a.limit as number | null) ?? 10, 1), 25)
      const spots = hits.sort((p, q) => key(q) - key(p)).slice(0, limit).map((x) => row(x, c))
      return { label: `Searched ${hits.length} hexagons${c ? ` within ${c.km} km of ${c.label}` : ''}`, output: { area: c?.label ?? 'all of Sydney', matched: hits.length, spots } }
    }
    case 'plan_sites': {
      const c = center(d, a as Where)
      if (typeof c === 'string') return { label: `Couldn’t find ${a.place}`, output: { error: c } }
      const mode = a.mode as Mode
      const count = Math.min(Math.max(Math.round(a.count as number), 1), 20)
      const spacing = ((a.min_spacing_m as number | null) ?? 400) / 1000
      const max = (a.max_today as number | null) ?? Infinity
      const pool = within(d.cells[mode], c).filter((x) => x.gap > 0 && x.today <= max).sort((p, q) => q.gap - p.gap)
      const picked: Cell[] = []
      for (const x of pool) {
        if (picked.length === count) break
        const [lat, lng] = ll(x.hex)
        if (picked.every((p) => distanceKm(lat, lng, ...ll(p.hex)) >= spacing)) picked.push(x)
      }
      return {
        label: `Planned ${picked.length} ${picked.length === 1 ? unit.one : unit.many}${c ? ` near ${c.label}` : ''}, ${spacing * 1000} m apart`,
        output: { area: c?.label ?? 'all of Sydney', candidates: pool.length, sites: picked.map((x) => row(x, c)), missing_covered: r2(picked.reduce((s, x) => s + x.gap, 0)) },
      }
    }
    case 'get_hex': {
      const found = cellIn(d, String(a.hex))
      if (!found) return { label: 'Hexagon not found', output: { error: `No hexagon ${a.hex} on the map.` } }
      const [mode, cell] = found
      const [lat, lng] = ll(cell.hex)
      const near = { label: cell.name, lat, lng, km: 1 }
      const hood = within(d.cells[mode], near).filter((x) => x.hex !== cell.hex)
      const served = d.cells[mode].filter((x) => x.today > 0 && x.hex !== cell.hex)
      const nearest = served.length ? Math.min(...served.map((x) => kmFrom(near, x.hex))) : null
      const nearestText = nearest === null ? 'none recorded' : nearest < 0.45 ? 'the next hexagon over (exact distance unknown, under about 500 m)' : `about ${r2(nearest)} km away, centre to centre`
      return {
        label: `Read ${cell.name}`,
        output: {
          ...row(cell), mode, lat, lng,
          drivers: drivers(cell, d.cells.feats).map(([f, v]) => ({ feature: f, effect: v >= 0 ? 'raises' : 'lowers', size: r2(Math.abs(v)) })),
          within_1km: {
            hexagons: hood.length, [`${unit.many}_today`]: hood.reduce((s, x) => s + x.today, 0),
            [`${unit.many}_predicted`]: r2(hood.reduce((s, x) => s + x.predicted, 0)),
            suggested_spots: hood.filter((x) => x.spot !== undefined).map((x) => row(x, near)),
          },
          [`nearest_hexagon_with_a_${unit.one.replace(/ /g, '_')}`]: nearestText,
          saved_explanation: cell.summary?.text ?? null,
        },
      }
    }
    case 'area_stats': {
      const c = center(d, a as Where)
      if (typeof c === 'string') return { label: `Couldn’t find ${a.place}`, output: { error: c } }
      const cells = within(d.cells[a.mode as Mode], c)
      const top = [...cells].sort((p, q) => q.gap - p.gap).slice(0, 5)
      return {
        label: `Totalled ${c ? `${c.km} km around ${c.label}` : 'all of Sydney'}`,
        output: {
          area: c?.label ?? 'all of Sydney', hexagons: cells.length, today: cells.reduce((s, x) => s + x.today, 0),
          predicted: r2(cells.reduce((s, x) => s + x.predicted, 0)), missing: r2(cells.reduce((s, x) => s + Math.max(0, x.gap), 0)),
          suggested_spots: cells.filter((x) => x.spot !== undefined).length, top: top.map((x) => row(x, c)),
        },
      }
    }
    case 'model_facts': {
      const { find, growth, council } = d.stats
      const { picks } = d.tracking.current
      return {
        label: 'Checked how the model was tested',
        output: {
          model: `Random forest over ${find.hexes.toLocaleString()} H3 hexagons (about one city block each), trained with 5-fold spatial cross-validation on 45 public inputs: census population, OpenStreetMap shops, food, transport, parks, footpaths, sports grounds, playgrounds and beaches. It never sees location, SEIFA disadvantage or population projections.`,
          held_out_top100: `${find.top100.x}/${find.top100.y} of the model's top 100 hexagons have a real ${unit.one}; random picks get about ${Math.round(find.random * 100)}.`,
          pr_auc: `${find.prAuc} (random ${find.random})`,
          ...(council ? { council_plans: `${council.top10.x}/${council.top10.y} council-planned sites fall in the model's top 10% (random about ${council.random}).` } : {}),
          growth_suburbs: `${growth.top100.x}/${growth.top100.y} real ${unit.one} hexagons in new growth suburbs found in the top 100 (random ${growth.randomTop100}).`,
          fairness: `${picks.poorest30.x} of ${picks.poorest30.y} suggested spots are in the poorest 30% of areas, ${picks.richest30.x} in the richest 30%.`,
        },
      }
    }
    case 'show_on_map': {
      const mode = a.mode as Mode
      const byHex = new Map(d.cells[mode].map((x) => [x.hex, x]))
      const spots = (a.hexes as string[]).flatMap((h) => (byHex.has(h) ? [{ hex: h, name: byHex.get(h)!.name }] : []))
      const missing = (a.hexes as string[]).filter((h) => !byHex.has(h))
      return {
        label: `Showed ${spots.length} on the map`,
        output: { shown: spots.length, ...(missing.length ? { not_on_map: missing } : {}) },
        event: { type: 'map', mode, caption: String(a.caption), spots },
      }
    }
    default:
      return { label: `Unknown tool ${name}`, output: { error: `There is no tool called ${name}.` } }
  }
}
