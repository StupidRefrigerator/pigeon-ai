import { describe, expect, it } from 'vitest'
import { existsSync } from 'node:fs'
import { DEFAULT_LAYER, LAYERS, LIVE_LAYERS, resolveLayer } from '../src/infra'
import { LAYER_DATA } from '../src/infra-data'

const file = (p: string) => new URL(`../${p}`, import.meta.url)

describe('infrastructure registry', () => {
  it('has unique ids, and a default layer that is live', () => {
    expect(new Set(LAYERS.map((l) => l.id)).size).toBe(LAYERS.length)
    expect(DEFAULT_LAYER.live).toBe(true)
    expect(LIVE_LAYERS[0]).toBe(DEFAULT_LAYER)
  })

  it('has its data files on disk for every live layer', () => {
    expect(LIVE_LAYERS.length).toBeGreaterThan(0)
    for (const l of LIVE_LAYERS) {
      expect(existsSync(file(`public${l.heatmapUrl}`)), `${l.id} heatmap`).toBe(true)
      expect(existsSync(file(`src/data/infra/${l.id}/tracking.json`)), `${l.id} tracking`).toBe(true)
      expect(existsSync(file(`src/data/infra/${l.id}/stats.json`)), `${l.id} stats`).toBe(true)
      expect(LAYER_DATA[l.id]).toBeDefined()
    }
  })

  it('gives a layer that is not live no data paths', () => {
    for (const l of LAYERS.filter((x) => !x.live)) expect(Object.keys(l).sort()).toEqual(['color', 'id', 'live', 'name', 'unit'])
  })

  it('falls back to the default layer for an unknown or not-live id', () => {
    expect(resolveLayer('toilets')).toBe(DEFAULT_LAYER)
    expect(resolveLayer('bikeLanes')).toBe(DEFAULT_LAYER)
    expect(resolveLayer(undefined)).toBe(DEFAULT_LAYER)
    expect(resolveLayer('nope')).toBe(DEFAULT_LAYER)
  })
})
