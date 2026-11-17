import { describe, expect, it } from 'vitest'
import { LIVE_LAYERS } from '../src/infra'
import { LAYER_DATA } from '../src/infra-data'
import { DEFINITIONS } from '../src/lib/definitions'

describe.each(LIVE_LAYERS)('DEFINITIONS for $id', (layer) => {
  const defs = DEFINITIONS[layer.id]
  const { stats, tracking } = LAYER_DATA[layer.id]

  it('gives every term one sentence', () => {
    for (const text of Object.values(defs)) {
      expect(text).toMatch(/^[^:]+: \S/)
      expect(text.endsWith('.')).toBe(true)
      expect(text.slice(0, -1)).not.toMatch(/\.\s/)
    }
  })

  it('quotes the same numbers as the data', () => {
    const fmt = (n: number) => n.toLocaleString('en-AU')
    expect(defs.prAuc).toContain(`(${tracking.current.prAuc.random.toFixed(3)} across Sydney)`)
    expect(defs.top100).toContain(`about ${Math.round(stats.find.random * 100)}.`)
    expect(defs.top1000).toContain(`about ${Math.round(stats.find.random * 1000)}.`)
    expect(defs.council).toContain(`${stats.council.top10.y} future ${layer.unit.one} sites`)
    expect(defs.council).toContain(`about ${stats.council.random}.`)
    expect(defs.growthSuburbs).toContain(`${fmt(stats.growth.hexes)} hexagons`)
  })
})
