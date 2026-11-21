import type { AskEvent } from './protocol'

export type MapEvent = Extract<AskEvent, { type: 'map' }>

export interface Step {
  id: string
  label: string
  state: 'running' | 'done'
}

/** One question and everything the agent streamed back for it. */
export interface Turn {
  id: number
  question: string
  reasoning: string
  steps: Step[]
  text: string
  maps: MapEvent[]
  state: 'running' | 'done' | 'error'
  error?: string
  responseId?: string
}

export const newTurn = (id: number, question: string): Turn => ({ id, question, reasoning: '', steps: [], text: '', maps: [], state: 'running' })

/** Folds one streamed event into its turn. A step event with a known id updates that step in place. */
export function applyEvent(t: Turn, e: AskEvent): Turn {
  switch (e.type) {
    case 'reasoning':
      return { ...t, reasoning: t.reasoning + e.delta }
    case 'text':
      return { ...t, text: t.text + e.delta }
    case 'step': {
      const i = t.steps.findIndex((s) => s.id === e.id)
      const step = { id: e.id, label: e.label, state: e.state }
      return { ...t, steps: i < 0 ? [...t.steps, step] : t.steps.map((s, k) => (k === i ? step : s)) }
    }
    case 'map':
      return { ...t, maps: [...t.maps, e] }
    case 'done':
      return { ...t, state: 'done', responseId: e.responseId, steps: t.steps.map((s) => ({ ...s, state: 'done' })) }
    case 'error':
      return { ...t, state: 'error', error: e.message, steps: t.steps.map((s) => ({ ...s, state: 'done' })) }
  }
}

/** Splits an NDJSON chunk stream into events; returns the unfinished tail to prepend to the next chunk. */
export function splitLines(buffer: string): [AskEvent[], string] {
  const parts = buffer.split('\n')
  const tail = parts.pop() ?? ''
  return [parts.filter((l) => l.trim()).map((l) => JSON.parse(l) as AskEvent), tail]
}
