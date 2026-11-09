import { cellToBoundary, cellToLatLng } from 'h3-js'
import type { CandidateInfo, NewSuburbs } from './data'
import { gapOf, isCandidate, type StudyHexes } from './gap'
import { haversineKm } from './geo'

export type Dataset = 'study' | 'growth' | 'bradfield'

export interface HexRecord {
  id: string
  dataset: Dataset
  /** null when there are no real toilet counts (Bradfield is a planned scenario). */
  actual: number | null
  pred: number
  lat: number
  lng: number
  /** Suburb or zone, where the source has one. */
  area?: string
  drivers?: string
}

export interface HexView extends HexRecord {
  gap: number
  candidate: boolean
  boundary: [number, number][]
}

export interface HexSources {
  hexes: StudyHexes
  candidates: Record<string, CandidateInfo>
  newSuburbs: NewSuburbs
}

function record(id: string, dataset: Dataset, actual: number | null, pred: number, extra: Partial<HexRecord> = {}): HexRecord {
  const [lat, lng] = cellToLatLng(id)
  return { id, dataset, actual, pred, lat: lat!, lng: lng!, ...extra }
}

/** Build the three hex tables once. Geometry is computed with h3-js, not stored. */
export function buildIndex({ hexes, candidates, newSuburbs }: HexSources) {
  const study = hexes.ids.map((id, i) =>
    record(id, 'study', hexes.actual[i]!, hexes.pred[i]!, { drivers: candidates[id]?.drivers }),
  )
  const g = newSuburbs.growth
  const growth = g.ids.map((id, i) => record(id, 'growth', g.actual[i]!, g.pred[i]!, { area: g.suburb[i] }))
  const b = newSuburbs.bradfield
  const bradfield = b.ids.map((id, i) =>
    record(id, 'bradfield', null, b.pred[i]!, {
      area: `${b.zone[i]} · ${b.stationM[i]} m from ${b.station[i]}`,
      drivers: b.drivers[id],
    }),
  )
  return { study, growth, bradfield }
}

export type HexIndex = ReturnType<typeof buildIndex>

export function toView(r: HexRecord): HexView {
  const actual = r.actual ?? 0
  return {
    ...r,
    gap: gapOf(r.pred, actual),
    candidate: isCandidate(r.pred, actual),
    boundary: cellToBoundary(r.id).map(([lat, lng]) => [lat!, lng!]),
  }
}

export function hexesNear(index: HexIndex, lat: number, lng: number, radiusKm: number, includeNew: boolean): HexView[] {
  const tables = includeNew ? [index.study, index.growth, index.bradfield] : [index.study]
  return tables.flat().filter((r) => haversineKm(lat, lng, r.lat, r.lng) <= radiusKm).map(toView)
}
