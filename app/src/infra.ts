/** The infrastructure registry: every layer the app can show, in sidebar order. Adding a layer starts here. */

export interface Unit {
  one: string
  many: string
}

interface LayerBase {
  name: string
  color: string
  /** What one piece of this infrastructure is called in running text, lower case. */
  unit: Unit
}

/** A layer with data. Its bundled JSON is registered in infra-data.ts under the same id. */
interface LiveShape extends LayerBase {
  live: true
  /** Fetched at runtime by the maps; lives under public/. */
  heatmapUrl: string
  /** Saved AI explanations for the top suggested spots, written by scripts/summaries.ts; lives under public/. */
  summariesUrl: string
}

/** A layer that is announced but has no data, so it has no data paths. */
interface SoonShape extends LayerBase {
  live: false
}

export const LAYERS = [
  { id: 'toilets', name: 'Toilets', color: '#FF48B0', live: true, unit: { one: 'toilet', many: 'toilets' }, heatmapUrl: '/infra/toilets/heatmap.json', summariesUrl: '/infra/toilets/summaries.json' },
  { id: 'bikeLanes', name: 'Bike lanes', color: '#FFE800', live: false, unit: { one: 'bike lane', many: 'bike lanes' } },
  { id: 'bubblers', name: 'Water fountains', color: '#3255A4', live: true, unit: { one: 'water fountain', many: 'water fountains' }, heatmapUrl: '/infra/bubblers/heatmap.json', summariesUrl: '/infra/bubblers/summaries.json' },
] as const satisfies readonly ((LiveShape | SoonShape) & { id: string })[]

export type Layer = (typeof LAYERS)[number]
export type LayerId = Layer['id']
export type LiveLayer = Extract<Layer, { live: true }>
export type LiveLayerId = LiveLayer['id']

export const LIVE_LAYERS: readonly LiveLayer[] = LAYERS.filter((l): l is LiveLayer => l.live)

/** The layer a bare /app shows. */
export const DEFAULT_LAYER: LiveLayer = LIVE_LAYERS[0]!

/** Turn an untrusted layer id (a URL param) into a live layer, falling back to the default. */
export function resolveLayer(id: unknown): LiveLayer {
  return LIVE_LAYERS.find((l) => l.id === id) ?? DEFAULT_LAYER
}

export const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
