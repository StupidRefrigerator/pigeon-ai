import { createFileRoute } from '@tanstack/react-router'
import { ask } from '../ai/agent'
import type { AskEvent, AskRequest } from '../ai/protocol'
import { LIVE_LAYERS } from '../infra'

function parse(body: unknown): AskRequest | null {
  if (typeof body !== 'object' || body === null) return null
  const b = body as Record<string, unknown>
  const layer = LIVE_LAYERS.find((l) => l.id === b.layer)?.id
  const question = typeof b.question === 'string' ? b.question.trim().slice(0, 2000) : ''
  if (!layer || !question) return null
  const prev = typeof b.previousResponseId === 'string' && /^resp_[\w-]+$/.test(b.previousResponseId) ? b.previousResponseId : undefined
  const hex = typeof b.focusHex === 'string' && /^[0-9a-f]{15}$/.test(b.focusHex) ? b.focusHex : undefined
  return { layer, question, previousResponseId: prev, focusHex: hex }
}

export const Route = createFileRoute('/api/ask')({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const key = process.env.OPENAI_API_KEY
        if (!key) return Response.json({ error: 'Ask Pigeon is not set up on this server (no OPENAI_API_KEY).' }, { status: 503 })
        const req = parse(await request.json().catch(() => null))
        if (!req) return Response.json({ error: 'Send { layer, question }.' }, { status: 400 })

        const enc = new TextEncoder()
        const line = (e: AskEvent) => enc.encode(JSON.stringify(e) + '\n')
        const body = new ReadableStream<Uint8Array>({
          async start(ctrl) {
            try {
              for await (const e of ask(req, key)) ctrl.enqueue(line(e))
            } catch (err) {
              ctrl.enqueue(line({ type: 'error', message: err instanceof Error ? err.message : 'Something went wrong.' }))
            }
            ctrl.close()
          },
        })
        return new Response(body, { headers: { 'content-type': 'application/x-ndjson; charset=utf-8', 'cache-control': 'no-store' } })
      },
    },
  },
})
