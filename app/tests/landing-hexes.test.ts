import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import type { HexData } from '../src/landing/engine'

const hex = JSON.parse(readFileSync(new URL('../public/landing-hexes.json', import.meta.url), 'utf8')) as HexData

describe('landing-hexes.json', () => {
  it('has one centre and one state per study hex', () => {
    expect(hex.s).toHaveLength(16228)
    expect(hex.xy.split(',')).toHaveLength(2 * 16228)
    expect(hex.s).toMatch(/^[pt0-9]+$/)
  })

  it('marks exactly the 100 suggested spots, in rank order', () => {
    expect(hex.picks).toHaveLength(100)
    expect(new Set(hex.picks).size).toBe(100)
    expect(hex.picks.every((i) => hex.s[i] === 'p')).toBe(true)
    expect([...hex.s].filter((c) => c === 'p')).toHaveLength(100)
  })
})
