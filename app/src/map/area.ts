import { cellToLatLng } from 'h3-js'
import type { Cell } from './cells'

/** A suburb, landmark, or typed point the user picked, as [name, lat, lng] like public/places.json. */
export type Place = [name: string, lat: number, lng: number]

export const RADII_KM = [0.5, 1, 2, 3, 5] as const
export const DEFAULT_RADIUS_KM = 1

export interface AreaSummary {
  /** Hexes whose centre lies within the radius. */
  inside: Set<string>
  hexes: number
  today: number
  predicted: number
  /** Suggested places inside the circle, best rank first. */
  spots: Cell[]
}

const RAD = Math.PI / 180
/** Great-circle distance in km, the same formula the old comparison page used. */
export function distanceKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const a = Math.sin(((lat2 - lat1) * RAD) / 2) ** 2 + Math.cos(lat1 * RAD) * Math.cos(lat2 * RAD) * Math.sin(((lng2 - lng1) * RAD) / 2) ** 2
  return 6371.0088 * 2 * Math.asin(Math.sqrt(Math.min(1, a)))
}

/** Keeps whole hexes: a hex is in the area when its centre is within radiusKm of the place. */
export function selectArea(cells: Cell[], [, lat, lng]: Place, radiusKm: number): AreaSummary {
  const picked = cells.filter((c) => {
    const [clat, clng] = cellToLatLng(c.hex)
    return distanceKm(lat, lng, clat, clng) <= radiusKm
  })
  return {
    inside: new Set(picked.map((c) => c.hex)),
    hexes: picked.length,
    today: picked.reduce((s, c) => s + c.today, 0),
    predicted: picked.reduce((s, c) => s + c.predicted, 0),
    spots: picked.filter((c) => c.spot !== undefined).sort((a, b) => a.spot! - b.spot!),
  }
}

/** "lat, lng" inside the Sydney study box, or null. */
export function parseLatLng(q: string): Place | null {
  const m = q.trim().match(/^(-?\d+(?:\.\d+)?)\s*[,\s]\s*(-?\d+(?:\.\d+)?)$/)
  if (!m) return null
  const [lat, lng] = [Number(m[1]), Number(m[2])]
  if (!(lat >= -34.6 && lat <= -33 && lng >= 149.8 && lng <= 151.7)) return null
  return [`${lat.toFixed(5)}, ${lng.toFixed(5)}`, lat, lng]
}

/** Names starting with the query first, then names with a word starting with it, then any match. */
export function searchPlaces(places: Place[], q: string, limit = 6): Place[] {
  const needle = q.trim().toLowerCase()
  if (!needle) return []
  const rank = (name: string) => {
    const n = name.toLowerCase()
    if (n.startsWith(needle)) return 0
    if (n.includes(` ${needle}`) || n.includes(`(${needle}`)) return 1
    return n.includes(needle) ? 2 : 3
  }
  return places
    .map((p) => [rank(p[0]), p] as const)
    .filter(([r]) => r < 3)
    .sort((a, b) => a[0] - b[0] || a[1][0].length - b[1][0].length || a[1][0].localeCompare(b[1][0]))
    .slice(0, limit)
    .map(([, p]) => p)
}
