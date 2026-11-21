import type { LiveLayerId } from '../infra'
import type { Mode } from '../map/cells'

/** POST /api/ask body. `previousResponseId` continues a conversation; OpenAI keeps the history. */
export interface AskRequest {
  layer: LiveLayerId
  question: string
  previousResponseId?: string
  /** The hexagon whose card the question was asked from. */
  focusHex?: string
}

/** A hexagon the agent wants on the map, named the way the click card names it. */
export interface MapSpot {
  hex: string
  name: string
}

/** One line of the NDJSON stream /api/ask returns, in the order the agent produces them. */
export type AskEvent =
  | { type: 'reasoning'; delta: string }
  | { type: 'step'; id: string; label: string; state: 'running' | 'done' }
  | { type: 'text'; delta: string }
  | { type: 'map'; mode: Mode; caption: string; spots: MapSpot[] }
  | { type: 'done'; responseId: string }
  | { type: 'error'; message: string }

/** A precomputed explanation for one suggested spot, as stored in public/infra/<layer>/summaries.json. */
export interface SpotSummary {
  text: string
  sources: { title: string; url: string }[]
}

export interface SummaryFile {
  model: string
  generated: string
  spots: Record<string, SpotSummary>
}
