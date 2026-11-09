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
