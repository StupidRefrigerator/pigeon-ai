import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { cellToLatLng, gridDisk, latLngToCell } from 'h3-js'
import type { HeatmapData } from '../src/lib/data'
import { distanceKm, parseLatLng, searchPlaces, selectArea, type Place } from '../src/map/area'
import { toCells, type Cell } from '../src/map/cells'

const cell = (hex: string, today: number, predicted: number, spot?: number): Cell => ({
  hex, name: hex, context: '', today, predicted, chance: 0.5, gap: predicted - today, driverPairs: '', spot,
})

describe('selectArea', () => {
  const centre = latLngToCell(-33.815, 151.003, 9)
  const [lat, lng] = cellToLatLng(centre)
  const here: Place = ['Here', lat, lng]

  it('keeps hexes whose centre is within the radius and sums their toilets', () => {
    const ring = gridDisk(centre, 1).filter((h) => h !== centre)
    const far = latLngToCell(-33.9, 151.2, 9)
    const cells = [cell(centre, 2, 1.5, 7), ...ring.map((h, i) => cell(h, 0, 0.25, i === 0 ? 3 : undefined)), cell(far, 5, 9, 1)]

    const s = selectArea(cells, here, 0.5)
    expect(s.hexes).toBe(7)
    expect(s.inside.has(far)).toBe(false)
    expect(s.today).toBe(2)
    expect(s.predicted).toBeCloseTo(1.5 + 6 * 0.25)
    expect(s.spots.map((c) => c.spot)).toEqual([3, 7])

    expect(selectArea(cells, here, 0.1).hexes).toBe(1)
    expect(selectArea(cells, here, 30).hexes).toBe(cells.length)
  })

  it('measures distance to the hex centre, not its edge', () => {
    const neighbour = gridDisk(centre, 1).find((h) => h !== centre)!
    const [nlat, nlng] = cellToLatLng(neighbour)
    const d = distanceKm(lat, lng, nlat, nlng)
    expect(selectArea([cell(neighbour, 0, 1)], here, d + 1e-6).hexes).toBe(1)
    expect(selectArea([cell(neighbour, 0, 1)], here, d - 1e-6).hexes).toBe(0)
  })

  it('finds suggested places around Parramatta on the real map data', () => {
    const heat = JSON.parse(readFileSync(new URL('../public/heatmap.json', import.meta.url), 'utf8')) as HeatmapData
    const places = (JSON.parse(readFileSync(new URL('../public/places.json', import.meta.url), 'utf8')) as { places: Place[] }).places
    const parra = places.find((p) => p[0] === 'Parramatta')!
    const s = selectArea(toCells(heat).today, parra, 1)
    expect(s.hexes).toBeGreaterThan(20)
    expect(s.predicted).toBeGreaterThan(0)
    expect(s.spots.every((c, i) => i === 0 || c.spot! > s.spots[i - 1]!.spot!)).toBe(true)
  })
})

describe('area search', () => {
  const places: Place[] = [['North Parramatta', -33.8, 151], ['Parramatta', -33.81, 151], ['Paddington', -33.88, 151.22], ['Harris Park', -33.82, 151.01]]

  it('ranks names that start with the query first', () => {
    expect(searchPlaces(places, 'parra').map((p) => p[0])).toEqual(['Parramatta', 'North Parramatta'])
    expect(searchPlaces(places, 'park').map((p) => p[0])).toEqual(['Harris Park'])
    expect(searchPlaces(places, '  ')).toEqual([])
  })

  it('reads "lat, lng" inside Sydney only', () => {
    expect(parseLatLng('-33.815, 151.003')).toEqual(['-33.81500, 151.00300', -33.815, 151.003])
    expect(parseLatLng('-33.815 151.003')?.[1]).toBe(-33.815)
    expect(parseLatLng('51.5, -0.12')).toBeNull()
    expect(parseLatLng('Parramatta')).toBeNull()
  })
})
