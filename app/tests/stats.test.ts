import { describe, expect, it } from 'vitest'
import stats from '../src/data/stats.json'

describe('stats.json', () => {
  it('has the 120 candidates of the held-out model', () => {
    expect(stats.headline.candidates).toBe(120)
  })

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
    expect(ratios.length).toBeGreaterThan(10)
    for (const r of ratios) expect(Math.abs(r.pct - (100 * r.x) / r.y)).toBeLessThanOrEqual(0.5)  // pct may be rounded to a whole number
  })
})

import tracking from '../src/data/tracking.json'

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
