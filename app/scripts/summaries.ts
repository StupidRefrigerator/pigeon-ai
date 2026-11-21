/**
 * Writes public/infra/<layer>/summaries.json: a short, sourced explanation for each of the top 100 suggested spots.
 *
 *   OPENAI_API_KEY=... npx tsx scripts/summaries.ts toilets|bubblers [--force]
 *
 * Re-running only fills spots that have no summary yet, so an interrupted run picks up where it stopped.
 * Each prompt carries the same hexagon read the Ask Pigeon agent gets, plus the raw feature values from
 * data/processed, nearby council-planned sites, and web search for what is actually there.
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import OpenAI from 'openai'
import { agentData, MODEL } from '../src/ai/agent'
import type { SpotSummary, SummaryFile } from '../src/ai/protocol'
import { runTool } from '../src/ai/tools'
import { LIVE_LAYERS, type LiveLayerId } from '../src/infra'
import { distanceKm } from '../src/map/area'

const TOP = 100
const CONCURRENCY = 6
const REPO = resolve(import.meta.dirname, '../..')

const layerId = process.argv[2] as LiveLayerId
const layer = LIVE_LAYERS.find((l) => l.id === layerId)
if (!layer) throw new Error(`Usage: tsx scripts/summaries.ts ${LIVE_LAYERS.map((l) => l.id).join('|')} [--force]`)
const force = process.argv.includes('--force')
const key = process.env.OPENAI_API_KEY
if (!key) throw new Error('Set OPENAI_API_KEY.')

/** A CSV without quoted fields, keyed by its first column. */
function readPlainCsv(path: string): Map<string, Record<string, string>> {
  const [head, ...rows] = readFileSync(resolve(REPO, path), 'utf8').trim().split('\n')
  const cols = head!.split(',')
  return new Map(rows.map((r) => {
    const v = r.split(',')
    return [v[0]!, Object.fromEntries(cols.map((c, i) => [c, v[i]!]))]
  }))
}

/** A CSV with quoted fields, as rows of objects. */
function readCsv(path: string): Record<string, string>[] {
  const text = readFileSync(resolve(REPO, path), 'utf8')
  const rows: string[][] = [[]]
  let cell = ''
  let quoted = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]!
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') (cell += '"'), i++
      else if (ch === '"') quoted = false
      else cell += ch
    } else if (ch === '"') quoted = true
    else if (ch === ',') rows.at(-1)!.push(cell), (cell = '')
    else if (ch === '\n') rows.at(-1)!.push(cell), (cell = ''), rows.push([])
    else if (ch !== '\r') cell += ch
  }
  if (cell) rows.at(-1)!.push(cell)
  const [head, ...body] = rows.filter((r) => r.length > 1)
  return body.map((r) => Object.fromEntries(head!.map((c, i) => [c, r[i] ?? ''])))
}

/** Raw model inputs worth showing a writer, with plain names. */
const RAW_FEATURES: Record<string, string> = {
  population_est: 'residents in the hexagon', population_500m: 'residents within 500 m', population_1000m: 'residents within 1 km',
  population_projected_2041: 'residents projected for 2041 (its SA2 share)', population_growth_pct_2021_2031: 'projected growth 2021-2031 (%)',
  age_0_17_pct: 'children 0-17 (%)', age_65plus_pct: 'people 65+ (%)', seifa_irsd_score: 'SEIFA disadvantage score (lower = more disadvantaged; Australia averages 1000)',
  shop_inside: 'shops in the hexagon', shop_500m: 'shops within 500 m', food_inside: 'cafes and food outlets in the hexagon', food_500m: 'cafes and food within 500 m',
  bus_stop_500m: 'bus stops within 500 m', train_station_500m: 'train stations within 500 m', train_station_1000m: 'train stations within 1 km',
  park_area_500m_m2: 'park area within 500 m (m²)', distance_nearest_park_m: 'metres to the nearest park', walkable_junctions_500m: 'walkable street junctions within 500 m',
  sports_500m: 'sports facilities within 500 m', playground_500m: 'playgrounds within 500 m', distance_nearest_beach_m: 'metres to the nearest beach',
  osm_toilets_public: 'OpenStreetMap public toilets in the hexagon',
}

const features = readPlainCsv('data/processed/sydney_extended_features.csv')
const recreation = readPlainCsv('data/processed/sydney_recreation_features.csv')
const planned = layerId === 'toilets' ? readCsv('experiments/gov/planned_sites.csv').filter((s) => s.lat && s.lng) : []

function rawContext(hex: string) {
  const row = { ...features.get(hex), ...recreation.get(hex) }
  return Object.fromEntries(Object.entries(RAW_FEATURES).flatMap(([col, label]) => (row[col] ? [[label, Math.round(Number(row[col]) * 100) / 100]] : [])))
}

function plannedNear(lat: number, lng: number) {
  return planned
    .map((s) => ({ s, km: distanceKm(lat, lng, Number(s.lat), Number(s.lng)) }))
    .filter(({ km }) => km <= 1)
    .sort((a, b) => a.km - b.km)
    .slice(0, 4)
    .map(({ s, km }) => ({ name: s.name, council: s.council, status: s.status, metres_away: Math.round(km * 1000), document: s.document, url: s.url }))
}

const d = agentData(layerId)
const { one, many } = layer.unit
const spots = d.cells.today.filter((c) => c.spot !== undefined && c.spot <= TOP).sort((a, b) => a.spot! - b.spot!)
const outPath = resolve(import.meta.dirname, '..', 'public', layer.summariesUrl.slice(1))
const file: SummaryFile = JSON.parse(readFileSync(outPath, 'utf8'))
const todo = spots.filter((c) => force || !file.spots[c.hex])
console.log(`${layer.name}: ${spots.length} spots, ${todo.length} to write with ${MODEL}`)

const INSTRUCTIONS = `You write the "Why here" note on Pigeon AI's map card for one suggested spot, read by council infrastructure planners.
Write 70 to 110 words of plain text: no markdown, no bullet points, no links, no long dashes.
Say concretely why this block needs a public ${one}: name what is actually here (centres, stations, parks, streets, schools), who uses it, and the model's numbers that matter (${many} missing, residents, shops, transport). Use web search to identify the real places at these coordinates and any council plans or works nearby; mention a plan only if a source confirms it. If nearby planned sites are listed, say how close they are. End with one sentence on what to build or check on site. Never invent figures.`

const client = new OpenAI({ apiKey: key })

async function summarise(hex: string): Promise<SpotSummary> {
  const read = runTool(d, 'get_hex', { hex }).output as { lat: number; lng: number }
  const context = { layer: layer!.name, hexagon: read, raw_inputs: rawContext(hex), ...(planned.length ? { council_planned_sites_within_1km: plannedNear(read.lat, read.lng) } : {}) }
  const res = await client.responses.create({
    model: MODEL, instructions: INSTRUCTIONS, reasoning: { effort: 'low' },
    tools: [{ type: 'web_search', search_context_size: 'low', user_location: { type: 'approximate', country: 'AU', city: 'Sydney' } }],
    input: JSON.stringify(context),
  })
  const sources = new Map<string, string>()
  for (const item of res.output) {
    if (item.type !== 'message') continue
    for (const part of item.content) {
      if (part.type !== 'output_text') continue
      for (const a of part.annotations) if (a.type === 'url_citation') sources.set(a.url.replace(/[?&]utm_source=openai$/, ''), a.title)
    }
  }
  const text = res.output_text.replace(/\s*\(\[[^\]]*\]\([^)]*\)\)/g, '').replace(/\s*\[[^\]]*\]\([^)]*\)/g, '').replace(/\s+/g, ' ').trim()
  return { text, sources: [...sources].map(([url, title]) => ({ title, url })) }
}

let done = 0
async function worker(queue: typeof todo) {
  for (let c = queue.shift(); c; c = queue.shift()) {
    try {
      file.spots[c.hex] = await summarise(c.hex)
      file.model = MODEL
      file.generated = new Date().toISOString().slice(0, 10)
      writeFileSync(outPath, JSON.stringify(file, null, 1) + '\n')
      console.log(`${++done}/${todo.length} #${c.spot} ${c.name}`)
    } catch (e) {
      console.error(`#${c.spot} ${c.name} failed: ${e instanceof Error ? e.message : e}`)
    }
  }
}
const queue = [...todo]
await Promise.all(Array.from({ length: CONCURRENCY }, () => worker(queue)))
console.log(`Wrote ${Object.keys(file.spots).length} summaries to ${outPath}`)
