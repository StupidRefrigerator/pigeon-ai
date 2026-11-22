// Ask Pigeon eval: runs each question through the real agent, records tool calls, and grades with automatic checks.
// Usage: OPENAI_API_KEY=... npx tsx evals/agent-eval.mts [runs=3]
import { writeFileSync } from 'node:fs'
import OpenAI from 'openai'
import { cellToLatLng } from 'h3-js'
import { ask, agentData, MODEL } from '../src/ai/agent'
import { distanceKm } from '../src/map/area'

const KEY = process.env.OPENAI_API_KEY!
const RUNS = Number(process.argv[2] ?? 3)
const d = agentData('toilets')
const byHex = new Map(d.cells.today.map((c) => [c.hex, c]))
const top = d.cells.today.find((c) => c.spot === 1)!

type Run = { text: string; calls: { name: string; args: any; output: any }[]; searches: number; shown: string[]; cost: number; secs: number }
type Check = (r: Run) => [boolean, string]

// Record every function call and its output by watching the Responses API traffic.
let sink: Run | null = null
const proto = (OpenAI as any).Responses.prototype
const orig = proto.create
proto.create = async function (body: any, ...rest: any[]) {
  const run = sink!
  for (const item of Array.isArray(body.input) ? body.input : []) if (item.type === 'function_call_output') {
    const c = run.calls.find((x: any) => x.id === item.call_id); if (c) c.output = JSON.parse(item.output)
  }
  const s = await orig.call(this, body, ...rest)
  if (!body.stream) return s
  return (async function* () { for await (const ev of s) {
    if (ev.type === 'response.output_item.done' && ev.item.type === 'function_call') run.calls.push({ id: ev.item.call_id, name: ev.item.name, args: JSON.parse(ev.item.arguments || '{}'), output: null } as any)
    if (ev.type === 'response.output_item.done' && ev.item.type === 'web_search_call') run.searches++
    if (ev.type === 'response.completed') { const u = ev.response.usage; const cached = u.input_tokens_details?.cached_tokens ?? 0
      run.cost += ((u.input_tokens - cached) * 2 + cached * 0.1 + u.output_tokens * 10) / 1e6 }
    yield ev } })()
}

const called = (r: Run, n: string) => r.calls.filter((c) => c.name === n)
const nums = (s: string) => [...s.replace(/(\d),(\d{3})/g, '$1$2').matchAll(/\d+(?:\.\d+)?/g)].map((m) => Number(m[0]))
const near = (place: [number, number], km: number) => (h: string) => { const [la, ln] = cellToLatLng(h); return distanceKm(la, ln, ...place) <= km }
const spaced = (hs: string[], m: number) => hs.every((a, i) => hs.slice(i + 1).every((b) => distanceKm(...cellToLatLng(a), ...cellToLatLng(b)) * 1000 >= m - 1))
// Share of numbers in the answer that appear in some tool output (ignores 1-digit counts and years).
function grounded(r: Run): number {
  const pool = new Set<number>(); const add = (v: any) => { if (typeof v === 'number') { pool.add(v); pool.add(Math.round(v)); pool.add(Math.round(v * 10) / 10); pool.add(Math.round(v * 100)) } else if (v && typeof v === 'object') Object.values(v).forEach(add) }
  r.calls.forEach((c) => { add(c.output); add(c.args); nums(JSON.stringify(c.output ?? '')).forEach(add) })
  const ns = nums(r.text).filter((n) => n >= 10 && !(n >= 1990 && n <= 2060))
  return ns.length ? ns.filter((n) => pool.has(n) || pool.has(Math.round(n))).length / ns.length : 1
}

const CASES: { group: string; q: string; focusHex?: string; checks: Record<string, Check> }[] = [
  { group: 'Budget', q: 'I have $500k for new public toilets in Blacktown. Where should they go?', checks: {
    'plans sites': (r) => [called(r, 'plan_sites').length > 0, `${called(r, 'plan_sites').length} plan_sites calls`],
    'looks up a cost': (r) => [r.searches > 0 || /\$\s?\d/.test(r.text), `${r.searches} searches`],
    'shows what it planned': (r) => { const p = called(r, 'plan_sites').at(-1)?.output?.sites?.length ?? -1; return [p > 0 && r.shown.length === p, `planned ${p}, shown ${r.shown.length}`] },
    'sites in Blacktown (≤3 km)': (r) => [r.shown.length > 0 && r.shown.every(near([-33.77655, 150.9023], 3)), `${r.shown.filter(near([-33.77655, 150.9023], 3)).length}/${r.shown.length}`] } },
  { group: 'Budget', q: 'Our council has $1.2 million for toilets around Liverpool. How many can we build and where?', checks: {
    'plans sites': (r) => [called(r, 'plan_sites').length > 0, `${called(r, 'plan_sites').length} plan_sites calls`],
    'looks up a cost': (r) => [r.searches > 0 || /\$\s?\d/.test(r.text), `${r.searches} searches`],
    'shows what it planned': (r) => { const p = called(r, 'plan_sites').at(-1)?.output?.sites?.length ?? -1; return [p > 0 && r.shown.length === p, `planned ${p}, shown ${r.shown.length}`] },
    'sites in Liverpool (≤3 km)': (r) => [r.shown.length > 0 && r.shown.every(near([-33.92149, 150.91682], 3)), `${r.shown.filter(near([-33.92149, 150.91682], 3)).length}/${r.shown.length}`] } },
  { group: 'Constraints', q: 'Plan 5 new toilets in Parramatta, at least 400 m apart, only where there is no toilet yet.', checks: {
    'shows 5': (r) => [r.shown.length === 5, `shown ${r.shown.length}`],
    'all within 3 km': (r) => [r.shown.length > 0 && r.shown.every(near([-33.81494, 151.00816], 3)), ''],
    '≥400 m apart': (r) => [r.shown.length > 1 && spaced(r.shown, 400), ''],
    'no toilet there yet': (r) => [r.shown.length > 0 && r.shown.every((h) => (byHex.get(h)?.today ?? 1) === 0), `${r.shown.filter((h) => byHex.get(h)?.today === 0).length}/${r.shown.length}`] } },
  { group: 'Constraints', q: 'Give me 3 spots near Bondi Beach for toilets, at least 800 m apart.', checks: {
    'shows 3': (r) => [r.shown.length === 3, `shown ${r.shown.length}`],
    'all within 3 km': (r) => [r.shown.length > 0 && r.shown.every(near([-33.89088, 151.27386], 3)), ''],
    '≥800 m apart': (r) => [r.shown.length > 1 && spaced(r.shown, 800), ''] } },
  { group: 'Explain a hexagon', q: 'Why is this spot ranked so high?', focusHex: top.hex, checks: {
    'reads the hexagon': (r) => [called(r, 'get_hex').some((c) => c.args.hex === top.hex), ''],
    'numbers grounded (≥90%)': (r) => { const g = grounded(r); return [g >= 0.9, `${Math.round(g * 100)}%`] } } },
  { group: 'Explain a hexagon', q: 'What is around this hexagon and how many toilets does the model expect here?', focusHex: d.cells.today.find((c) => c.spot === 10)!.hex, checks: {
    'reads the hexagon': (r) => [called(r, 'get_hex').length > 0, ''],
    'states the prediction': (r) => { const p = d.cells.today.find((c) => c.spot === 10)!.predicted; return [nums(r.text).some((n) => Math.abs(n - p) < 0.06), `prediction ${p.toFixed(2)}`] },
    'numbers grounded (≥90%)': (r) => { const g = grounded(r); return [g >= 0.9, `${Math.round(g * 100)}%`] } } },
  { group: 'Project facts', q: 'How was the model trained and tested?', checks: {
    '300 trees': (r) => [/\b300\b/.test(r.text), ''],
    'spatial CV, 5 folds': (r) => [/spatial/i.test(r.text) && /\b5\b|five/i.test(r.text), ''],
    'no false SEIFA-input claim': (r) => [!/SEIFA[^.]{0,40}(input|feature)/i.test(r.text) || /never|not|n't|only/i.test(r.text.match(/[^.]*SEIFA[^.]*/i)?.[0] ?? ''), ''] } },
  { group: 'Project facts', q: 'How accurate is it?', checks: {
    'top 100 hits (85/100)': (r) => [/\b85\b/.test(r.text), ''],
    'compares with random': (r) => [/random/i.test(r.text), ''] } },
  { group: 'Out of scope', q: 'Where should a new hospital go in Penrith?', checks: {
    'no hexagons shown': (r) => [r.shown.length === 0 && called(r, 'plan_sites').length === 0, `shown ${r.shown.length}`],
    'says it only covers toilets/fountains': (r) => [/(only|isn[’']t|is not|doesn[’']t|does not|can[’']t|cannot|not (built|designed|trained))/i.test(r.text), ''] } },
  { group: 'Out of scope', q: 'What is the crime rate in Redfern?', checks: {
    'no hexagons shown': (r) => [r.shown.length === 0, `shown ${r.shown.length}`],
    'does not claim model data on crime': (r) => [!/(model|our data|pigeon)[^.]{0,40}(predicts|shows|has)[^.]{0,30}crime/i.test(r.text), ''] } },
]

async function runAgent(q: string, focusHex?: string): Promise<Run> {
  const r: Run = { text: '', calls: [], searches: 0, shown: [], cost: 0, secs: 0 }; sink = r; const t = Date.now()
  for await (const ev of ask({ layer: 'toilets', question: q, focusHex } as any, KEY)) {
    if (ev.type === 'text') r.text += ev.delta
    if (ev.type === 'map') r.shown = ev.spots.map((s) => s.hex)
  }
  r.secs = (Date.now() - t) / 1000; return r
}
// Baseline: the same model with web search only, no map tools and no project brief.
async function runBaseline(q: string): Promise<Run> {
  const r: Run = { text: '', calls: [], searches: 0, shown: [], cost: 0, secs: 0 }; sink = r; const t = Date.now()
  const s = await new OpenAI({ apiKey: KEY }).responses.create({ model: MODEL, stream: true, reasoning: { effort: 'medium' },
    instructions: 'You are a planning assistant for Pigeon AI, a tool that predicts where Sydney needs public toilets. Answer briefly.',
    tools: [{ type: 'web_search' }] as any, input: q })
  for await (const ev of s as any) if (ev.type === 'response.output_text.delta') r.text += ev.delta
  r.secs = (Date.now() - t) / 1000; return r
}

const results: any[] = []
for (const [system, runner] of [['agent', runAgent], ['baseline', runBaseline]] as const) {
  for (const c of CASES) for (let i = 0; i < (system === 'agent' ? RUNS : 1); i++) {
    const r = await (system === 'agent' ? runAgent(c.q, c.focusHex) : runBaseline(c.q)).catch((e) => ({ text: 'ERROR ' + e.message, calls: [], searches: 0, shown: [], cost: 0, secs: 0 }))
    const checks = Object.entries(c.checks).map(([name, f]) => { const [ok, note] = f(r); return { name, ok, note } })
    results.push({ outputsCaptured: r.calls.every((x) => x.output !== null), system, group: c.group, q: c.q, run: i + 1, pass: checks.every((x) => x.ok), checks, grounded: grounded(r), cost: r.cost, secs: r.secs, tools: r.calls.map((x) => x.name), searches: r.searches, text: r.text })
    console.log(`${system.padEnd(8)} ${checks.every((x) => x.ok) ? 'PASS' : 'FAIL'} ${c.group.padEnd(18)} ${c.q.slice(0, 50).padEnd(50)} ${checks.filter((x) => !x.ok).map((x) => x.name + (x.note ? ` (${x.note})` : '')).join('; ')}  $${r.cost.toFixed(3)} ${r.secs.toFixed(0)}s`)
  }
}
writeFileSync('evals/results.json', JSON.stringify({ model: MODEL, date: new Date().toISOString(), runs: RUNS, results }, null, 1))
