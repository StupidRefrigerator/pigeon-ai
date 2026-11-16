import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { LIVE_LAYERS, type LiveLayerId } from '../src/infra'
import { LAYER_DATA } from '../src/infra-data'
import { FUTURE_AREAS } from '../src/lib/areas'
import type { HeatmapData } from '../src/lib/data'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
// Where `python scripts/train_model.py --target <layer>` writes its outputs.
const MODEL_DIR: Record<LiveLayerId, string> = { toilets: '../../data/model', bubblers: '../../data/model/bubblers' }

describe.each(LIVE_LAYERS)('$id data', (layer) => {
  const { stats, tracking, meanDeviance } = LAYER_DATA[layer.id]
  const heatmap = JSON.parse(read(`../public${layer.heatmapUrl}`)) as HeatmapData
  const picks = tracking.current.picks

  it('reports every ratio as x/y with a matching percentage', () => {
    const ratios: { x: number; y: number; pct: number }[] = []
    const walk = (v: unknown) => {
      if (v && typeof v === 'object') {
        const o = v as Record<string, unknown>
        if (typeof o.x === 'number' && typeof o.y === 'number' && typeof o.pct === 'number') ratios.push(o as never)
        Object.values(o).forEach(walk)
      }
    }
    walk(stats)
    walk(tracking)
    expect(ratios.length).toBeGreaterThan(8)
    for (const r of ratios) expect(Math.abs(r.pct - (100 * r.x) / r.y)).toBeLessThanOrEqual(0.5) // pct may be rounded to a whole number
  })

  it('has one row per SEIFA decile, and the list reach matches the Tracking page', () => {
    expect(stats.reach.deciles.map((d) => d.decile)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expect(stats.reach.poorest30).toEqual(picks.poorest30)
    expect(stats.reach.richest30).toEqual(picks.richest30)
  })

  it('reports the suggested list against its own length, not a fixed top 120', () => {
    for (const r of [picks.alreadyOne, picks.nearPlanned, picks.poorest30, picks.richest30]) if (r) expect(r.y).toBe(picks.listed)
    expect(picks.poorest30.x + picks.richest30.x + picks.noSeifa).toBeLessThanOrEqual(picks.listed)
    expect(stats.reach.listed).toBe(picks.listed)
  })

  it.runIf(stats.growth.withOsm)('counts more growth-suburb units once OpenStreetMap is included', () => {
    const withOsm = stats.growth.withOsm!
    expect(withOsm.toiletHexes).toBeGreaterThanOrEqual(stats.growth.toiletHexes)
    expect(withOsm.actual).toBeGreaterThanOrEqual(stats.growth.actual)
    expect(withOsm.top100.y).toBe(withOsm.toiletHexes)
  })

  it("quotes the mean-everywhere deviance from the layer's metrics.csv", () => {
    const row = read(`${MODEL_DIR[layer.id]}/metrics.csv`).split('\n').find((l) => l.startsWith('mean everywhere,'))!
    expect(meanDeviance).toBe(Number(Number(row.split(',')[1]).toFixed(3)))
  })

  it('marks exactly one current version, and it is the best PR-AUC', () => {
    const current = tracking.versions.filter((v) => v.status === 'current')
    expect(current.map((v) => v.id)).toEqual([tracking.current.id])
    const best = Math.max(...tracking.versions.map((v) => v.prAuc ?? 0))
    expect(current[0]!.prAuc).toBe(best)
  })

  it('has every study hexagon, and the suggested spots among them ranked 1 to the list length', () => {
    expect(heatmap.today).toHaveLength(16228)
    const ids = new Set(heatmap.today.map((h) => h[0]))
    expect(heatmap.recs.every(([id]) => ids.has(id))).toBe(true)
    expect(heatmap.recs.map((r) => r[1])).toEqual(Array.from({ length: picks.listed }, (_, i) => i + 1))
  })

  it('has the growth suburbs and the saved top 10 of each named future area', () => {
    expect(heatmap.growth).toHaveLength(stats.growth.hexes)
    expect(heatmap.growth.reduce((s, h) => s + h[1], 0)).toBe(stats.growth.actual)
    const perArea: Record<string, number> = {}
    for (const [area] of heatmap.future) perArea[area] = (perArea[area] ?? 0) + 1
    expect(perArea).toEqual(Object.fromEntries(Object.keys(FUTURE_AREAS).map((a) => [a, 10])))
  })

  it('points every driver and place at a real name', () => {
    for (const h of heatmap.today) {
      expect(heatmap.places[h[5]]).toBeDefined()
      for (const pair of h[4] ? h[4].split(',') : []) expect(heatmap.feats[Number(pair.split(':')[0])]).toBeDefined()
    }
  })
})

describe('toilets tracking.json', () => {
  it('keeps every version from the original comparison page', () => {
    expect(LAYER_DATA.toilets.tracking.versions.slice(0, 10).map((v) => v.id)).toEqual(['V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10'])
  })
})
