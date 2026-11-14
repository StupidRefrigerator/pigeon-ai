import { Link, createFileRoute } from '@tanstack/react-router'
import 'leaflet/dist/leaflet.css'
import { Heatmap } from '../components/Heatmap'
import { Term } from '../components/Term'
import { fmtRatio, type Tracking } from '../lib/data'
import trackingJson from '../data/tracking.json'

const t = trackingJson as Tracking
const c = t.current

export const Route = createFileRoute('/app/stats')({ component: TrackingPage })

const fmt = (v: number | null, digits: number) => (v === null ? 'Pending' : v.toFixed(digits))
const STATUS = { done: 'Completed', pending: 'Pending', current: 'Current' } as const

function TrackingPage() {
  return (
    <div className="jimmy">
      <main>
        <section aria-labelledby="tracking-title">
          <h1 id="tracking-title">PIGEON-AI — Tracking</h1>
          <p>
            Pigeon AI predicts where the next public infrastructure should go, from a bird's-eye view of Sydney today and of its growth and future suburbs. Public toilets
            are the first layer.
          </p>
        </section>

        <section aria-labelledby="selected-title">
          <h2 id="selected-title">Selected model: {c.id}</h2>
          <ul>
            <li>
              <strong>
                <Term id="prAuc">PR-AUC</Term>:
              </strong>{' '}
              {c.prAuc.value.toFixed(3)} (V11: {c.prAuc.was.toFixed(3)}; <Term id="random">random guessing</Term>: {c.prAuc.random.toFixed(3)}).
            </li>
            <li>
              <strong>
                <Term id="deviance">Poisson deviance</Term>:
              </strong>{' '}
              {c.deviance.value.toFixed(3)} (V11: {c.deviance.was.toFixed(3)}; lower is better).
            </li>
            <li>
              <strong>
                <Term id="top1000">Top-1,000 hits</Term>:
              </strong>{' '}
              {fmtRatio(c.top1000)} of the model's 1,000 highest <Term id="hexagon">hexagons</Term> have a real toilet.
            </li>
            <li>
              <strong>
                <Term id="council">Council-planned sites</Term>:
              </strong>{' '}
              {fmtRatio(c.council)} land in the model's top 10%.
            </li>
            <li>
              <strong>
                <Term id="predictedVsReal">Predicted vs real</Term>:
              </strong>{' '}
              predicts {c.predictedTotal.toLocaleString()} toilets across the study area (real: {c.actualTotal.toLocaleString()}).
            </li>
          </ul>
          <p>
            <strong>Result:</strong> {c.picks.listed} <Term id="suggested">places need at least one more toilet</Term> than they have, counting toilets on
            both the <Term id="officialMap">official map</Term> and <Term id="osm">OpenStreetMap</Term>. They are ranked by{' '}
            <Term id="toiletsMissing">toilets missing</Term>, with no other weighting. Of these {c.picks.listed}:
          </p>
          <ul>
            <li>
              {fmtRatio(c.picks.alreadyOne)} already have one toilet, but the model expects 2 or more.
            </li>
            <li>{fmtRatio(c.picks.nearPlanned)} are near a council-planned site.</li>
            <li>
              {fmtRatio(c.picks.poorest30)} are in Sydney's poorest 30% of areas and {fmtRatio(c.picks.richest30)} in the richest 30% (by{' '}
              <Term id="seifa">SEIFA decile</Term>; {c.picks.noSeifa} have no score).
            </li>
          </ul>
          <p className="note">
            Every test behind these numbers is on the <Link to="/app/tests">Tests</Link> page.
          </p>
        </section>

        <section aria-labelledby="training-title">
          <h2 id="training-title">How it's trained and tested</h2>
          <p>
            The model learns from where Sydney's toilets are today. To test it fairly, Sydney's 16,228 hexagons are grouped into 90 larger blocks, and the blocks are
            split into 5 groups. Each turn, the model trains on 4 groups and predicts the 5th. After 5 turns, every hexagon has been predicted once, by a model that
            never saw its area. This is <Term id="crossValidation">five-fold spatial cross-validation</Term>, and every score above is{' '}
            <Term id="heldOut">held-out</Term> this way. The <Term id="growthSuburbs">growth-suburbs test</Term> is separate: 1,108 new-suburb hexagons were not in
            the training data at all.
          </p>
          <SplitDiagram />
        </section>

        <section aria-labelledby="heatmap-title">
          <h2 id="heatmap-title">Heatmap</h2>
          <Heatmap />
          <p className="note">
            Toilets missing = how many fewer toilets a place has than the Sydney average for places with similar population, shops, transport and parks. The
            model learns from where toilets are today, so it finds places below Sydney's own standard, not an absolute need. Map data ©{' '}
            <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>.
          </p>
        </section>

        <section aria-labelledby="versions-title">
          <h2 id="versions-title">Versions</h2>
          <div className="table-scroll" role="region" aria-label="Version comparison table" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">Version</th>
                  <th scope="col">Description</th>
                  <th scope="col">Hexagons</th>
                  <th scope="col">Features</th>
                  <th scope="col">
                    <Term id="deviance">Poisson deviance</Term>
                  </th>
                  <th scope="col">
                    <Term id="prAuc">PR-AUC</Term>
                  </th>
                  <th scope="col">
                    <Term id="top100">Top-100 hits</Term>
                  </th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {t.versions.map((v) => (
                  <tr key={v.id} className={v.status === 'current' ? 'current' : undefined}>
                    <td>{v.id}</td>
                    <td>{v.description}</td>
                    <td>{v.hexes.toLocaleString()}</td>
                    <td>{v.features}</td>
                    <td>{fmt(v.deviance, 4)}</td>
                    <td>{fmt(v.prAuc, 4)}</td>
                    <td>{v.top100 ?? 'Pending'}</td>
                    <td>{STATUS[v.status]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">
            <Term id="crossValidation">Five-fold spatial cross-validation</Term>. V1–V8 use the same 16,228 hexagons and folds; V8 is an exploratory future-population scenario, and V9's
            full-area deviance is not directly comparable. V10 is incomplete. V1–V10 are seed 0, from Jimmy's saved <code>comparison.csv</code>; V11 and V12 are the{' '}
            <Term id="seeds">mean of seeds 0–2</Term>.
          </p>
        </section>
      </main>
    </div>
  )
}

const GROUPS = 5
/** Five turns of the spatial split: each row trains on four groups of blocks and predicts the fifth. */
function SplitDiagram() {
  const box = { w: 128, h: 24, gap: 6 }
  const left = 64
  const rowH = box.h + 8
  return (
    <svg
      className="split-diagram"
      viewBox={`0 0 ${left + GROUPS * (box.w + box.gap) + 4} ${GROUPS * rowH + 36}`}
      role="img"
      aria-labelledby="split-diagram-title"
    >
      <title id="split-diagram-title">
        Five turns. In each, the model trains on four groups of 18 blocks and predicts the remaining group, so each group is predicted exactly once.
      </title>
      {Array.from({ length: GROUPS }, (_, g) => (
        <text key={g} x={left + g * (box.w + box.gap) + box.w / 2} y={14} textAnchor="middle">
          Group {g + 1} · 18 blocks
        </text>
      ))}
      {Array.from({ length: GROUPS }, (_, turn) => (
        <g key={turn} transform={`translate(0 ${24 + turn * rowH})`}>
          <text x={0} y={box.h / 2 + 4}>
            Turn {turn + 1}
          </text>
          {Array.from({ length: GROUPS }, (_, g) => {
            const predict = g === turn
            const x = left + g * (box.w + box.gap)
            return (
              <g key={g}>
                <rect x={x} y={0} width={box.w} height={box.h} fill={predict ? '#ededed' : '#262626'} stroke={predict ? '#ededed' : '#555'} />
                <text x={x + box.w / 2} y={box.h / 2 + 4} textAnchor="middle" style={predict ? { fill: '#0a0a0a', fontWeight: 600 } : undefined}>
                  {predict ? 'predict' : 'train'}
                </text>
              </g>
            )
          })}
        </g>
      ))}
    </svg>
  )
}
