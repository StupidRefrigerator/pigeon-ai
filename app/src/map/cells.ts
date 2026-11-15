import type { HeatmapData } from '../lib/data'

export type Mode = 'today' | 'growth' | 'future'

export const MODES: { id: Mode; label: string }[] = [
  { id: 'today', label: 'Today' },
  { id: 'growth', label: 'Growth suburbs' },
  { id: 'future', label: 'Future areas' },
]

/** One hexagon on the map, in the words the click card uses. */
export interface Cell {
  hex: string
  /** Suburb name, or the station precinct for a future area. */
  name: string
  context: string
  today: number
  predicted: number
  /** Chance a hexagon like this has at least one toilet, 0–1. */
  chance: number
  /** Predicted minus today; negative means better served than expected. */
  gap: number
  /** Raw "featIndex:value" pairs; parse with drivers(). */
  driverPairs: string
  /** Rank in the 100 suggested spots (Today) or in the area's picks (Future). */
  spot?: number
  spotLabel?: string
}

export interface Cells {
  today: Cell[]
  growth: Cell[]
  future: Cell[]
  feats: string[]
}

/** Plain-language names for the model's features, in heatmap.json's feats order. */
const FEATURE_LABELS: Record<string, string> = {
  shop_inside: 'shops in the hex',
  park_area_inside_m2: 'park area in the hex',
  shop_250m: 'shops within 250 m',
  food_inside: 'cafes and food in the hex',
  distance_nearest_playground_m: 'distance to a playground',
  park_area_250m_m2: 'park area within 250 m',
  sports_area_inside_m2: 'sports grounds in the hex',
  distance_nearest_sports_m: 'distance to sports grounds',
  food_250m: 'cafes and food within 250 m',
  distance_nearest_footpath_m: 'distance to a footpath',
  sports_inside: 'sports facilities in the hex',
  distance_nearest_beach_m: 'distance to a beach',
  distance_nearest_park_m: 'distance to a park',
  beach_inside: 'beach in the hex',
  beach_250m: 'beach within 250 m',
  train_station_250m: 'train station within 250 m',
  train_station_inside: 'train station in the hex',
  train_station_500m: 'train station within 500 m',
  sports_area_500m_m2: 'sports grounds within 500 m',
  population_est: 'residents in the hex',
  park_area_1000m_m2: 'park area within 1 km',
  population_500m: 'residents within 500 m',
  walkable_junctions_500m: 'walkable street junctions',
  shop_500m: 'shops within 500 m',
  sports_1000m: 'sports facilities within 1 km',
  playground_inside: 'playground in the hex',
  sports_250m: 'sports facilities within 250 m',
  food_1000m: 'cafes and food within 1 km',
  bus_stop_500m: 'bus stops within 500 m',
  population_250m: 'residents within 250 m',
  bus_stop_inside: 'bus stop in the hex',
  food_500m: 'cafes and food within 500 m',
}

const AREA_NAMES: Record<string, string> = { aerotropolis: 'the Aerotropolis', leppington: 'Leppington' }

export function toCells(d: HeatmapData): Cells {
  const place = (i: number) => d.places[i] ?? 'Sydney'
  const spots = new Map(d.recs.map(([hex, rank]) => [hex, rank]))
  const today = d.today.map(([hex, real, pred, chance, drivers, pl]): Cell => {
    const spot = spots.get(hex)
    return {
      hex, name: place(pl), context: 'Sydney today', today: real, predicted: pred, chance, gap: pred - real, driverPairs: drivers,
      spot, spotLabel: spot ? `Suggested spot ${spot} of ${d.recs.length}` : undefined,
    }
  })
  const growth = d.growth.map(([hex, real, pred, chance, pl]): Cell => ({
    hex, name: place(pl), context: 'Growth suburb, scored on its planned land use', today: real, predicted: pred, chance, gap: pred - real, driverPairs: '',
  }))
  const future = d.future.map(([area, rank, hex, pred, chance, zone, station, metres, drivers]): Cell => ({
    hex, name: `${station.replace(/ Station$/, '')} precinct`, context: `${zone}, ${(metres / 1000).toFixed(1)} km from ${station}`,
    today: 0, predicted: pred, chance, gap: pred, driverPairs: drivers, spot: rank, spotLabel: `Pick ${rank} for ${AREA_NAMES[area] ?? area}`,
  }))
  return { today, growth, future, feats: d.feats.map((f) => FEATURE_LABELS[f] ?? f.replace(/_/g, ' ')) }
}

/** Top drivers of a prediction, as [plain-language feature, signed contribution]. */
export function drivers(cell: Cell, feats: string[]): [string, number][] {
  return cell.driverPairs
    .split(',')
    .filter(Boolean)
    .map((p) => {
      const [i, v] = p.split(':')
      return [feats[Number(i)] ?? `feature ${i}`, Number(v)] as [string, number]
    })
}
