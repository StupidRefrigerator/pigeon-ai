import { createFileRoute } from '@tanstack/react-router'
import { lazy, Suspense, useEffect, useState } from 'react'
import type { MapEvent } from '../ai/turn'
import { useLayer } from '../layer'
import { AskPanel, type AskView, type Prompt } from '../map/AskPanel'
import type { Cell } from '../map/cells'
import type { Focus } from '../map/HexMap'
import '../map/map.css'

/** deck.gl and MapLibre need WebGL, so the map loads in the browser only, in its own chunk. */
const HexMap = lazy(() => import('../map/HexMap'))

const PHONE = '(max-width: 900px)'

export const Route = createFileRoute('/app/')({ component: MapPage })

function MapPage() {
  const layer = useLayer()
  const [mounted, setMounted] = useState(false)
  const [ask, setAsk] = useState<AskView>('closed')
  const [focus, setFocus] = useState<Focus | null>(null)
  const [prompt, setPrompt] = useState<Prompt | null>(null)
  useEffect(() => setMounted(true), [])

  const askAbout = (cell: Cell) => {
    setAsk('open')
    setPrompt({ key: Date.now(), hex: cell.hex, question: `Why does ${cell.name} need ${layer.unit.many} at this spot, and what should the council do about it?` })
  }
  /** On a phone the chat covers the map, so showing hexagons shrinks it to a bar at the bottom. */
  const show = ({ mode, caption, spots }: MapEvent, select?: string) => {
    if (window.matchMedia(PHONE).matches) setAsk((v) => (v === 'closed' ? v : 'peek'))
    setFocus({ key: Date.now(), mode, caption, spots, select })
  }

  return (
    <div className={ask === 'closed' ? 'mappage' : `mappage ask-${ask}`}>
      <h1 className="mappage-title slab">{`${layer.name} in Sydney`}</h1>
      {mounted && (
        <Suspense fallback={<p className="hexmap-status slab">Loading the map…</p>}>
          <HexMap key={layer.id} focus={focus} onAsk={askAbout} />
        </Suspense>
      )}
      <AskPanel key={layer.id} view={ask} onView={setAsk} prompt={prompt} onShow={show} />
    </div>
  )
}
