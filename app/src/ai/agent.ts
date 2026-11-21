import OpenAI from 'openai'
import { LIVE_LAYERS, type LiveLayerId } from '../infra'
import { LAYER_DATA } from '../infra-data'
import type { HeatmapData } from '../lib/data'
import type { Place } from '../map/area'
import { toCells } from '../map/cells'
import toiletsHeat from '../../public/infra/toilets/heatmap.json'
import bubblersHeat from '../../public/infra/bubblers/heatmap.json'
import toiletsSummaries from '../../public/infra/toilets/summaries.json'
import bubblersSummaries from '../../public/infra/bubblers/summaries.json'
import placesFile from '../../public/places.json'
import type { AskEvent, AskRequest, SummaryFile } from './protocol'
import { projectBrief } from './brief'
import { runTool, TOOL_DEFS, type AgentData } from './tools'

export const MODEL = process.env.OPENAI_MODEL ?? 'gpt-6.1-sol'
const MAX_ROUNDS = 10

const RAW: Record<LiveLayerId, { heat: unknown; summaries: unknown }> = {
  toilets: { heat: toiletsHeat, summaries: toiletsSummaries },
  bubblers: { heat: bubblersHeat, summaries: bubblersSummaries },
}

const cache = new Map<LiveLayerId, AgentData>()
export function agentData(id: LiveLayerId): AgentData {
  let d = cache.get(id)
  if (!d) {
    const layer = LIVE_LAYERS.find((l) => l.id === id)!
    d = {
      layer, cells: toCells(RAW[id].heat as HeatmapData, (RAW[id].summaries as SummaryFile).spots), places: (placesFile as { places: Place[] }).places,
      stats: LAYER_DATA[id].stats, tracking: LAYER_DATA[id].tracking,
    }
    cache.set(id, d)
  }
  return d
}

function instructions(d: AgentData) {
  const { one, many } = d.layer.unit
  return `You are Pigeon, the planning assistant inside Pigeon AI, a map that predicts where Sydney needs public ${many}.

${projectBrief(d)}

Answer questions about the project, the hexagons, the data and the training from this brief; it is accurate. Say so plainly when something is not in it rather than guessing.

How to work:
- Use the tools for every number about places. Never invent a hexagon, rank or count.
- Turn constraints into tool arguments. For a budget, find a typical cost per ${one} (search the web if the user gives none, and say which figure you used), divide, then call plan_sites with that count. Respect spacing, area and "no ${one} yet" constraints.
- Use web search for facts outside the model: costs, council plans and strategies, upcoming developments, local news. Cite those sources.
- Before answering with recommended hexagons, call show_on_map once with them.
- Answer in plain Australian English, short, without long dashes. Lead with the recommendation, then a few bullets of evidence with numbers. Keep answers under about 200 words and avoid tables unless asked. Mention a limit of the data only when it changes the answer (for example the model only sees public data and the official toilet map misses some toilets in shopping centres).`
}

const ORIGIN = { type: 'approximate' as const, country: 'AU', city: 'Sydney', region: 'New South Wales' }

/** Runs the agent loop for one question, yielding the events the browser renders. */
export async function* ask(req: AskRequest, apiKey: string): AsyncGenerator<AskEvent> {
  const d = agentData(req.layer)
  const client = new OpenAI({ apiKey })
  const tools = [{ type: 'web_search' as const, user_location: ORIGIN }, ...TOOL_DEFS]
  const focus = req.focusHex ? `\n\n(The user asked this from the card for hexagon ${req.focusHex}.)` : ''
  let input: OpenAI.Responses.ResponseInput = [{ role: 'user', content: req.question + focus }]
  let previous = req.previousResponseId
  let parts = 0
  let wrote = false

  for (let round = 0; round < MAX_ROUNDS; round++) {
    const stream = await client.responses.create({
      model: MODEL, instructions: instructions(d), input, previous_response_id: previous, tools: tools as OpenAI.Responses.Tool[],
      reasoning: { effort: 'medium', summary: 'detailed' }, stream: true, store: true,
    })
    const calls: { id: string; name: string; args: string }[] = []
    let roundText = false
    let responseId = ''
    for await (const ev of stream) {
      switch (ev.type) {
        case 'response.created':
          responseId = ev.response.id
          break
        case 'response.reasoning_summary_part.added':
          if (parts++ > 0) yield { type: 'reasoning', delta: '\n\n' }
          break
        case 'response.reasoning_summary_text.delta':
          yield { type: 'reasoning', delta: ev.delta }
          break
        case 'response.output_text.delta':
          if (!roundText && wrote) yield { type: 'text', delta: '\n\n' }
          roundText = wrote = true
          yield { type: 'text', delta: ev.delta }
          break
        case 'response.output_item.added':
          if (ev.item.type === 'web_search_call') yield { type: 'step', id: ev.item.id, label: 'Searching the web', state: 'running' }
          if (ev.item.type === 'function_call') yield { type: 'step', id: ev.item.call_id, label: 'Checking the map', state: 'running' }
          break
        case 'response.output_item.done':
          if (ev.item.type === 'web_search_call') {
            const action = ev.item.action as { query?: string } | undefined
            yield { type: 'step', id: ev.item.id, label: action?.query ? `Searched the web for “${action.query}”` : 'Searched the web', state: 'done' }
          }
          if (ev.item.type === 'function_call') calls.push({ id: ev.item.call_id, name: ev.item.name, args: ev.item.arguments })
          break
        case 'response.failed':
          throw new Error(ev.response.error?.message ?? 'The model failed to answer.')
      }
    }
    if (!calls.length) {
      yield { type: 'done', responseId }
      return
    }
    input = []
    for (const c of calls) {
      let parsed: Record<string, unknown>
      try {
        parsed = JSON.parse(c.args || '{}')
      } catch {
        parsed = {}
      }
      const res = runTool(d, c.name, parsed)
      yield { type: 'step', id: c.id, label: res.label, state: 'done' }
      if (res.event) yield res.event
      input.push({ type: 'function_call_output', call_id: c.id, output: JSON.stringify(res.output) })
    }
    previous = responseId
  }
  yield { type: 'error', message: 'Pigeon took too many steps on that question. Try asking something narrower.' }
}
