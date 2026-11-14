import { createFileRoute } from '@tanstack/react-router'
import { lazy, Suspense, useEffect, useState } from 'react'
import { AskPanel } from '../map/AskPanel'
import '../map/map.css'

/** deck.gl and MapLibre need WebGL, so the map loads in the browser only, in its own chunk. */
const HexMap = lazy(() => import('../map/HexMap'))

export const Route = createFileRoute('/app/')({ component: MapPage })

function MapPage() {
  const [mounted, setMounted] = useState(false)
  const [askOpen, setAskOpen] = useState(false)
  useEffect(() => setMounted(true), [])

  return (
    <div className={askOpen ? 'mappage ask-open' : 'mappage'}>
      <h1 className="mappage-title slab">Toilets in Sydney</h1>
      {mounted && (
        <Suspense fallback={<p className="hexmap-status slab">Loading the map…</p>}>
          <HexMap />
        </Suspense>
      )}
      <AskPanel open={askOpen} onToggle={setAskOpen} />
    </div>
  )
}
