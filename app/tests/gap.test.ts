import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { candidateIds, gapColor, gapOf, isCandidate, type StudyHexes } from '../src/lib/gap'

const load = <T>(rel: string) => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8')) as T

describe('gap and candidate rule', () => {
  it('gap is predicted minus actual, floored at 0', () => {
    expect(gapOf(2.4, 1)).toBeCloseTo(1.4)
    expect(gapOf(0.3, 2)).toBe(0)
    expect(gapOf(0, 0)).toBe(0)
  })

  it('a candidate needs predicted at least 1 above actual', () => {
    expect(isCandidate(1, 0)).toBe(true)
    expect(isCandidate(2.99, 2)).toBe(false)
    expect(isCandidate(3, 2)).toBe(true)
    expect(isCandidate(0.99, 0)).toBe(false)
    expect(isCandidate(0, 5)).toBe(false)
  })

  it('colours the candidate bin darkest and no-gap lightest', () => {
    expect(gapColor(0)).not.toBe(gapColor(0.1))
    expect(gapColor(1)).toBe(gapColor(5))
    expect(gapColor(0.9)).not.toBe(gapColor(1))
  })
})

describe('built data', () => {
  const hexes = load<StudyHexes>('../public/data/hexes.json')
  const review = readFileSync(new URL('../../data/review/candidate_review.csv', import.meta.url), 'utf8')
    .trim()
    .split('\n')
    .slice(1)
    .map((l) => l.split(',')[0]!)

  it('covers every study hex with aligned columns', () => {
    expect(hexes.ids).toHaveLength(16228)
    expect(hexes.actual).toHaveLength(16228)
    expect(hexes.pred).toHaveLength(16228)
    expect(hexes.actual.reduce((a, b) => a + b, 0)).toBe(2570)
  })

  it('has exactly 120 candidates, the same hexes as data/review/candidate_review.csv', () => {
    const ids = candidateIds(hexes)
    expect(ids).toHaveLength(120)
    expect(new Set(ids)).toEqual(new Set(review))
  })

  it('ships drivers for every candidate', () => {
    const drivers = load<Record<string, unknown>>('../public/data/candidates.json')
    expect(Object.keys(drivers)).toHaveLength(120)
  })
})
