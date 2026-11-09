import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import type { CandidateInfo, NewSuburbs } from '../src/lib/data'
import { buildIndex, hexesNear } from '../src/lib/explorer'
import type { StudyHexes } from '../src/lib/gap'

const load = <T>(rel: string) => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8')) as T
const index = buildIndex({
  hexes: load<StudyHexes>('../public/data/hexes.json'),
  candidates: load<Record<string, CandidateInfo>>('../public/data/candidates.json'),
  newSuburbs: load<NewSuburbs>('../public/data/newsuburbs.json'),
})

describe('hexesNear', () => {
  const sydneyCbd = [-33.8678, 151.2101] as const
  const oranPark = [-33.9890, 150.7410] as const

  it('returns study hexes within the radius with their gap and candidate flags', () => {
    const near = hexesNear(index, ...sydneyCbd, 2, false)
    expect(near.length).toBeGreaterThan(50)
    expect(near.every((h) => h.dataset === 'study')).toBe(true)
    for (const h of near) {
      expect(h.gap).toBeCloseTo(Math.max(0, h.pred - (h.actual ?? 0)))
      expect(h.candidate).toBe(h.pred - (h.actual ?? 0) >= 1)
      expect(h.boundary).toHaveLength(6)
    }
    expect(near.some((h) => h.candidate)).toBe(true)
  })

  it('adds growth and Bradfield hexes only when asked', () => {
    expect(hexesNear(index, ...oranPark, 2, false).every((h) => h.dataset === 'study')).toBe(true)
    const withNew = hexesNear(index, ...oranPark, 3, true)
    expect(withNew.some((h) => h.dataset === 'growth')).toBe(true)
  })

  it('has no real toilet count for Bradfield hexes', () => {
    expect(index.bradfield).toHaveLength(838)
    expect(index.bradfield.every((h) => h.actual === null)).toBe(true)
    expect(index.growth).toHaveLength(1108)
  })
})
