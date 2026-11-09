import { ClientOnly, createFileRoute } from '@tanstack/react-router'
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { loadExplorerData, type ExplorerData } from '../lib/data'
import { buildIndex, hexesNear, type HexView } from '../lib/explorer'
import { GAP_BINS } from '../lib/gap'

const ExplorerMap = lazy(() => import('../components/ExplorerMap'))

export const Route = createFileRoute('/app/')({ component: Explorer })

const RADII = [1, 2, 3, 5]
const DEFAULT_PLACE = 'Sydney'

function Explorer() {
  const [data, setData] = useState<ExplorerData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [place, setPlace] = useState(DEFAULT_PLACE)
  const [radiusKm, setRadiusKm] = useState(2)
  const [showNew, setShowNew] = useState(false)
  const [showPlans, setShowPlans] = useState(false)
  const [showCounts, setShowCounts] = useState(true)
  const [selected, setSelected] = useState<HexView | null>(null)

  useEffect(() => {
    loadExplorerData().then(setData, (e: Error) => setError(e.message))
  }, [])

  const index = useMemo(() => (data ? buildIndex(data) : null), [data])
  const found = data?.places.find((p) => p[0].toLowerCase() === place.trim().toLowerCase())
  const [lastCenter, setLastCenter] = useState<[number, number]>([-33.8678, 151.2101])
  useEffect(() => {
    if (found) setLastCenter([found[1], found[2]])
  }, [found])

  const hexes = useMemo(
    () => (index ? hexesNear(index, lastCenter[0], lastCenter[1], radiusKm, showNew) : []),
    [index, lastCenter, radiusKm, showNew],
  )
  const candidates = hexes.filter((h) => h.candidate && h.dataset === 'study').length

  if (error) return <p className="loading">Could not load data: {error}</p>
  if (!data) return <p className="loading">Loading held-out predictions…</p>

  return (
    <div className="explorer">
      <aside className="panel">
        <h2>Where should the next toilet go?</h2>
        <label className="field">
          Suburb or place
          <input list="places" value={place} onChange={(e) => setPlace(e.target.value)} aria-invalid={!found} />
          <datalist id="places">
            {data.places.map((p) => (
              <option key={p[0]} value={p[0]} />
            ))}
          </datalist>
          {!found && <span className="warn">Pick a name from the list.</span>}
        </label>
        <label className="field">
          Radius
          <select value={radiusKm} onChange={(e) => setRadiusKm(Number(e.target.value))}>
            {RADII.map((r) => (
              <option key={r} value={r}>
                {r} km
              </option>
            ))}
          </select>
        </label>
        <label className="toggle">
          <input type="checkbox" checked={showCounts} onChange={(e) => setShowCounts(e.target.checked)} />
          <span>Existing toilet counts</span>
        </label>
        <label className="toggle">
          <input type="checkbox" checked={showNew} onChange={(e) => setShowNew(e.target.checked)} />
          <span>
            New suburbs
            <small>Growth suburbs and Bradfield / Aerotropolis (planned scenario — read the ranking, not the totals).</small>
          </span>
        </label>
        <label className="toggle">
          <input type="checkbox" checked={showPlans} onChange={(e) => setShowPlans(e.target.checked)} />
          <span>
            Council plans
            <small>{data.plans.length} planned toilet sites from council documents.</small>
          </span>
        </label>

        <div className="legend">
          <strong>Gap = predicted − actual (min 0)</strong>
          {GAP_BINS.map((b) => (
            <div className="row" key={b.label}>
              <span className="swatch" style={{ background: b.color }} /> {b.label}
            </div>
          ))}
          <div className="row">
            <span className="swatch outline" /> Candidate (gap ≥ 1)
          </div>
          {showNew && (
            <div className="row">
              <span className="swatch newsub" /> New-suburb hex
            </div>
          )}
          {showPlans && (
            <div className="row">
              <span className="dot plan" /> Council plan
            </div>
          )}
        </div>
        <p className="note">
          {hexes.length.toLocaleString()} hexes shown, {candidates} candidate{candidates === 1 ? '' : 's'} in the study area. All predictions are held-out
          (5-fold spatial cross-validation).
        </p>

        {selected ? <HexInfo hex={selected} /> : <p className="note">Click a hex for details.</p>}
      </aside>
      <div className="mapwrap">
        <ClientOnly fallback={<p className="loading">Loading map…</p>}>
          <Suspense fallback={<p className="loading">Loading map…</p>}>
            <ExplorerMap
              center={lastCenter}
              radiusKm={radiusKm}
              hexes={hexes}
              showCounts={showCounts}
              plans={showPlans ? data.plans : null}
              selectedId={selected?.id ?? null}
              onSelect={setSelected}
            />
          </Suspense>
        </ClientOnly>
      </div>
    </div>
  )
}

const DATASET_LABEL = {
  study: 'Study area (held-out)',
  growth: 'Growth suburb (never trained on)',
  bradfield: 'Bradfield / Aerotropolis — planned scenario, read the ranking, not the totals',
} as const

function HexInfo({ hex }: { hex: HexView }) {
  return (
    <div className="info">
      <strong>{DATASET_LABEL[hex.dataset]}</strong>
      {hex.area && <div>{hex.area}</div>}
      <dl>
        <dt>Actual toilets</dt>
        <dd>{hex.actual === null ? 'none yet (not built)' : hex.actual}</dd>
        <dt>Predicted</dt>
        <dd>{hex.pred.toFixed(2)}</dd>
        <dt>Gap</dt>
        <dd>{hex.gap.toFixed(2)}</dd>
        <dt>Candidate</dt>
        <dd>{hex.candidate ? <span className="tag">Yes</span> : 'No'}</dd>
        <dt>Top drivers</dt>
        <dd>{hex.drivers ?? 'not available for this hex'}</dd>
      </dl>
    </div>
  )
}
