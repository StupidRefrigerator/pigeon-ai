import { cellToLatLng, latLngToCell } from 'h3-js'
import { describe, expect, it } from 'vitest'
import { distanceKm } from '../src/map/area'
import { agentData } from '../src/ai/agent'
import { applyEvent, newTurn, splitLines } from '../src/ai/turn'
import { runTool } from '../src/ai/tools'

const d = agentData('toilets')
const where = { place: 'Parramatta', lat: null, lng: null, radius_km: 3 }

describe('agent tools on the toilet data', () => {
  it('plans the asked number of sites, all at least the spacing apart and inside the area', () => {
    const out = runTool(d, 'plan_sites', { mode: 'today', ...where, count: 6, min_spacing_m: 500, max_today: 0 }).output as { sites: { hex: string; today: number; km_from_centre: number }[] }
    expect(out.sites).toHaveLength(6)
    for (const s of out.sites) {
      expect(s.today).toBe(0)
      expect(s.km_from_centre).toBeLessThanOrEqual(3)
    }
    const pts = out.sites.map((s) => cellToLatLng(s.hex))
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) expect(distanceKm(...pts[i]!, ...pts[j]!)).toBeGreaterThanOrEqual(0.5)
  })

  it('searches suggested spots best-first and reports unknown places instead of guessing', () => {
    const out = runTool(d, 'search_spots', { mode: 'today', place: null, lat: null, lng: null, radius_km: null, suggested_only: true, min_missing: null, max_today: null, sort_by: 'rank', limit: 5 }).output as { spots: { suggested_rank: number; missing: number }[] }
    expect(out.spots.map((s) => s.suggested_rank)).toEqual([1, 2, 3, 4, 5])
    const bad = runTool(d, 'area_stats', { mode: 'today', place: 'Atlantis', lat: null, lng: null, radius_km: 1 }).output as { error?: string }
    expect(bad.error).toMatch(/No place called "Atlantis"/)
  })

  it('shows only hexagons that exist in the mode, and says which it dropped', () => {
    const real = d.cells.today.find((c) => c.spot === 1)!
    const offMap = latLngToCell(0, 0, 9)
    const res = runTool(d, 'show_on_map', { mode: 'today', hexes: [real.hex, offMap], caption: 'test' })
    expect(res.event?.spots).toEqual([{ hex: real.hex, name: real.name }])
    expect(res.output).toEqual({ shown: 1, not_on_map: [offMap] })
  })
})

describe('streamed turns', () => {
  it('updates a running step in place when it finishes and closes every step on done', () => {
    let t = newTurn(1, 'q')
    t = applyEvent(t, { type: 'step', id: 'a', label: 'Searching the web', state: 'running' })
    t = applyEvent(t, { type: 'step', id: 'b', label: 'Checking the map', state: 'running' })
    t = applyEvent(t, { type: 'step', id: 'a', label: 'Searched the web for “cost”', state: 'done' })
    expect(t.steps.map((s) => s.label)).toEqual(['Searched the web for “cost”', 'Checking the map'])
    t = applyEvent(t, { type: 'done', responseId: 'resp_1' })
    expect(t.steps.every((s) => s.state === 'done')).toBe(true)
    expect(t.responseId).toBe('resp_1')
  })

  it('keeps a half-received line for the next chunk', () => {
    const [events, tail] = splitLines('{"type":"text","delta":"a"}\n{"type":"te')
    expect(events).toEqual([{ type: 'text', delta: 'a' }])
    expect(tail).toBe('{"type":"te')
  })
})

describe('project brief', () => {
  it('states the training setup and never claims SEIFA is an input', async () => {
    const { projectBrief } = await import('../src/ai/brief')
    const { agentData } = await import('../src/ai/agent')
    const b = projectBrief(agentData('toilets'))
    expect(b).toContain('5-fold spatial cross-validation')
    expect(b).toContain('never sees location')
    expect(b).not.toMatch(/\$\{|undefined/)
  })
})
