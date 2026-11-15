import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import type { HeatmapData } from '../src/lib/data'
import { drivers, toCells } from '../src/map/cells'

const heatmap = JSON.parse(readFileSync(new URL('../public/heatmap.json', import.meta.url), 'utf8')) as HeatmapData
const cells = toCells(heatmap)

describe('map cells', () => {
  it('names every hexagon and marks all 100 suggested spots on Today', () => {
    expect(cells.today).toHaveLength(heatmap.today.length)
    expect(heatmap.today.every((r) => heatmap.places[r[5]] !== undefined)).toBe(true)
    expect(heatmap.growth.every((r) => heatmap.places[r[4]] !== undefined)).toBe(true)
    const spots = cells.today.filter((c) => c.spot !== undefined).map((c) => c.spot)
    expect(spots.sort((a, b) => a! - b!)).toEqual(Array.from({ length: 100 }, (_, i) => i + 1))
  })

  it('gives the first suggested spot a suburb, a gap and plain-language drivers', () => {
    const first = cells.today.find((c) => c.spot === 1)!
    expect(first.name).toBe('Woolloomooloo')
    expect(first.gap).toBeCloseTo(heatmap.recs[0]![2], 2)
    const top = drivers(first, cells.feats)
    expect(top.length).toBeGreaterThan(0)
    for (const [name] of top) expect(name).not.toMatch(/_/)
  })

  it('labels future picks by station precinct', () => {
    expect(cells.future).toHaveLength(heatmap.future.length)
    expect(cells.future[0]!.name).toBe('Bradfield precinct')
    expect(cells.future[0]!.spotLabel).toBe('Pick 1 for the Aerotropolis')
  })
})
