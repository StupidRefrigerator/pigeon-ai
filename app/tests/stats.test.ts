import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import stats from '../src/data/stats.json'
import tracking from '../src/data/tracking.json'
import type { HeatmapData } from '../src/lib/data'

const heatmap = JSON.parse(readFileSync(new URL('../public/heatmap.json', import.meta.url), 'utf8')) as HeatmapData

describe('stats.json', () => {
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
    expect(stats.reach.poorest30).toEqual(tracking.current.picks.poorest30)
    expect(stats.reach.richest30).toEqual(tracking.current.picks.richest30)
  })
})

describe('tracking.json', () => {
  it('marks exactly one current version, and it is the best PR-AUC', () => {
    const current = tracking.versions.filter((v) => v.status === 'current')
    expect(current.map((v) => v.id)).toEqual([tracking.current.id])
    const best = Math.max(...tracking.versions.map((v) => v.prAuc ?? 0))
    expect(current[0]!.prAuc).toBe(best)
  })

  it('keeps every version from the original comparison page', () => {
    expect(tracking.versions.slice(0, 10).map((v) => v.id)).toEqual(['V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10'])
  })
})

describe('heatmap.json', () => {
  it('has every study hexagon, and the suggested spots among them ranked 1 to the list length', () => {
    expect(heatmap.today).toHaveLength(16228)
    const ids = new Set(heatmap.today.map((h) => h[0]))
    expect(heatmap.recs.every(([id]) => ids.has(id))).toBe(true)
    expect(heatmap.recs.map((r) => r[1])).toEqual(Array.from({ length: tracking.current.picks.listed }, (_, i) => i + 1))
  })

  it('has the growth suburbs and the saved top 10 of each future area', () => {
    expect(heatmap.growth).toHaveLength(stats.growth.hexes)
    expect(heatmap.growth.reduce((s, h) => s + h[1], 0)).toBe(stats.growth.actual)
    const perArea: Record<string, number> = {}
    for (const [area] of heatmap.future) perArea[area] = (perArea[area] ?? 0) + 1
    expect(perArea).toEqual({ aerotropolis: 10, leppington: 10 })
  })

  it('points every driver and place at a real name', () => {
    for (const h of heatmap.today) {
      expect(heatmap.places[h[5]]).toBeDefined()
      for (const pair of h[4] ? h[4].split(',') : []) expect(heatmap.feats[Number(pair.split(':')[0])]).toBeDefined()
    }
  })
})
