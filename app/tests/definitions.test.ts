import { describe, expect, it } from 'vitest'
import stats from '../src/data/stats.json'
import tracking from '../src/data/tracking.json'
import { DEFINITIONS } from '../src/lib/definitions'

describe('DEFINITIONS', () => {
  it('gives every term one sentence', () => {
    for (const text of Object.values(DEFINITIONS)) {
      expect(text).toMatch(/^[^:]+: \S/)
      expect(text.endsWith('.')).toBe(true)
      expect(text.slice(0, -1)).not.toMatch(/\.\s/)
    }
  })

  it('quotes the same numbers as the data', () => {
    const fmt = (n: number) => n.toLocaleString('en-AU')
    expect(DEFINITIONS.prAuc).toContain(`(${tracking.current.prAuc.random.toFixed(3)} across Sydney)`)
    expect(DEFINITIONS.top100).toContain(`about ${Math.round(stats.find.random * 100)}.`)
    expect(DEFINITIONS.top1000).toContain(`about ${Math.round(stats.find.random * 1000)}.`)
    expect(DEFINITIONS.council).toContain(`${stats.council.top10.y} future toilet sites`)
    expect(DEFINITIONS.council).toContain(`about ${stats.council.random}.`)
    expect(DEFINITIONS.growthSuburbs).toContain(`${fmt(stats.growth.hexes)} hexagons`)
  })
})
