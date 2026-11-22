import { useEffect, useRef, useState } from 'react'
import { Markdown } from '../ai/Markdown'
import type { AskRequest } from '../ai/protocol'
import { applyEvent, newTurn, splitLines, type MapEvent, type Turn } from '../ai/turn'
import { useLayer } from '../layer'

/** A question handed over from elsewhere on the page, such as a hexagon card. `key` makes the same question askable twice. */
export interface Prompt {
  key: number
  question: string
  hex?: string
}

/** `peek` is the phone-only bar left at the bottom while the map shows the answer's hexagons. */
export type AskView = 'closed' | 'open' | 'peek'

interface Props {
  view: AskView
  onView: (view: AskView) => void
  prompt: Prompt | null
  /** Highlight a set of hexagons on the map, optionally opening one. */
  onShow: (map: MapEvent, select?: string) => void
}

/** Side panel for the Pigeon agent: it streams the agent's reasoning, tool steps and answer, and hands highlighted hexagons to the map. */
export function AskPanel({ view, onView, prompt, onShow }: Props) {
  const open = view !== 'closed'
  const layer = useLayer()
  const { unit } = layer
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const closeRef = useRef<HTMLButtonElement>(null)
  const openRef = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const abort = useRef<AbortController | null>(null)
  const wasOpen = useRef(open)
  const busy = turns.at(-1)?.state === 'running'
  const lastMap = [...turns].reverse().find((t) => t.maps.length)?.maps.at(-1)

  useEffect(() => {
    if (open && !wasOpen.current) inputRef.current?.focus()
    else if (!open && wasOpen.current) openRef.current?.focus()
    wasOpen.current = open
  }, [open])
  useEffect(() => () => abort.current?.abort(), [])
  useEffect(() => {
    const el = logRef.current
    if (el && el.scrollHeight - el.scrollTop - el.clientHeight < 160) el.scrollTop = el.scrollHeight
  }, [turns])

  const update = (id: number, f: (t: Turn) => Turn) => setTurns((ts) => ts.map((t) => (t.id === id ? f(t) : t)))

  async function send(question: string, hex?: string) {
    const q = question.trim()
    if (!q || busy) return
    const id = Date.now()
    const previousResponseId = [...turns].reverse().find((t) => t.responseId)?.responseId
    setTurns((ts) => [...ts, newTurn(id, q)])
    setDraft('')
    const ctrl = new AbortController()
    abort.current = ctrl
    const body: AskRequest = { layer: layer.id, question: q, previousResponseId, focusHex: hex }
    try {
      const res = await fetch('/api/ask', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body), signal: ctrl.signal })
      if (!res.ok || !res.body) {
        const err = (await res.json().catch(() => null)) as { error?: string } | null
        throw new Error(err?.error ?? `Pigeon could not answer (HTTP ${res.status}).`)
      }
      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
      let buffer = ''
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        const [events, tail] = splitLines(buffer + value)
        buffer = tail
        for (const e of events) {
          update(id, (t) => applyEvent(t, e))
          if (e.type === 'map') onShow(e)
        }
      }
      update(id, (t) => (t.state === 'running' ? applyEvent(t, { type: 'error', message: 'The answer stopped early. Try again.' }) : t))
    } catch (e) {
      if (ctrl.signal.aborted) return update(id, (t) => applyEvent(t, { type: 'error', message: 'Stopped.' }))
      update(id, (t) => applyEvent(t, { type: 'error', message: e instanceof Error ? e.message : 'Something went wrong.' }))
    }
  }

  /** A prompt is sent once, when it arrives; one left over from another layer is ignored. */
  const sent = useRef(prompt?.key)
  useEffect(() => {
    if (!prompt || prompt.key === sent.current) return
    sent.current = prompt.key
    send(prompt.question, prompt.hex)
  }, [prompt])

  const starters = [
    `I have $1.5M for ${unit.many} around Parramatta. Where should they go?`,
    `Which growth suburbs are most short of ${unit.many}?`,
    `Are councils already planning ${unit.many} near the top suggested spots?`,
  ]

  return (
    <>
      <button ref={openRef} className="ask-toggle slab" aria-expanded={open} aria-controls="ask-panel" hidden={open} onClick={() => onView('open')}>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 5h16v11H9l-5 4z" />
        </svg>
        Ask Pigeon
      </button>
      <aside id="ask-panel" className={view === 'peek' ? 'ask-panel peek' : 'ask-panel'} aria-labelledby="ask-title" hidden={!open}>
        <div className="ask-peek-bar">
          <div className="ask-peek-row">
            <p>{busy ? 'Pigeon is still answering…' : lastMap ? `Showing ${lastMap.caption}` : 'Answer ready'}</p>
            <button className="ask-close" onClick={() => onView('open')}>
              Open chat
            </button>
          </div>
          {lastMap && (
            <div className="ask-chips">
              {lastMap.spots.map((s) => (
                <button key={s.hex} onClick={() => onShow(lastMap, s.hex)}>
                  {s.name}
                </button>
              ))}
            </div>
          )}
        </div>
        <header>
          <h2 id="ask-title">Ask Pigeon</h2>
          <div className="ask-head-btns">
            {turns.length > 0 && !busy && (
              <button className="ask-close" onClick={() => setTurns([])}>
                New chat
              </button>
            )}
            <button ref={closeRef} className="ask-close" onClick={() => onView('closed')}>
              Close
            </button>
          </div>
        </header>
        <div className="ask-body" ref={logRef} aria-live="polite">
          {turns.length === 0 && (
            <div className="ask-empty">
              <p>
                Ask about any suburb, a budget or a constraint. Pigeon checks the model, searches the web, and puts its picks on the map.
              </p>
              {starters.map((s) => (
                <button key={s} className="ask-starter" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}
          {turns.map((t) => (
            <TurnView key={t.id} turn={t} onShow={onShow} />
          ))}
        </div>
        <form
          className="ask-composer"
          onSubmit={(e) => {
            e.preventDefault()
            send(draft)
          }}
        >
          <textarea
            ref={inputRef} rows={2} value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Question"
            placeholder={`Why is Woolloomooloo short of ${unit.many}?`}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send(draft)
              }
            }}
          />
          {busy ? (
            <button type="button" onClick={() => abort.current?.abort()}>
              Stop
            </button>
          ) : (
            <button disabled={!draft.trim()}>Ask</button>
          )}
        </form>
      </aside>
    </>
  )
}

function TurnView({ turn, onShow }: { turn: Turn; onShow: Props['onShow'] }) {
  const thinking = turn.state === 'running' && !turn.text
  return (
    <div className="ask-turn">
      <p className="ask-q">{turn.question}</p>
      {(turn.reasoning || thinking) && (
        <details className="ask-think" open={thinking}>
          <summary>{thinking ? 'Thinking…' : 'Reasoning'}</summary>
          {turn.reasoning && <Markdown text={turn.reasoning} />}
        </details>
      )}
      {turn.steps.length > 0 && (
        <ol className="ask-steps">
          {turn.steps.map((s) => (
            <li key={s.id} className={s.state}>
              {s.label}
            </li>
          ))}
        </ol>
      )}
      {turn.text && (
        <div className="ask-a">
          <Markdown text={turn.text} />
        </div>
      )}
      {turn.maps.map((m, i) => (
        <div key={i} className="ask-map">
          <button className="ask-map-all" onClick={() => onShow(m)}>
            Show {m.caption} on the map
          </button>
          <div className="ask-chips">
            {m.spots.map((s) => (
              <button key={s.hex} onClick={() => onShow(m, s.hex)}>
                {s.name}
              </button>
            ))}
          </div>
        </div>
      ))}
      {turn.error && <p className="ask-err">{turn.error}</p>}
    </div>
  )
}
