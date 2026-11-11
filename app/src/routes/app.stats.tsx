import { Link, createFileRoute } from '@tanstack/react-router'
import 'leaflet/dist/leaflet.css'
import { Heatmap } from '../components/Heatmap'
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
              <strong>PR-AUC:</strong> {c.prAuc.value.toFixed(3)} (V11: {c.prAuc.was.toFixed(3)}; random guessing: {c.prAuc.random.toFixed(3)}).
            </li>
            <li>
              <strong>Poisson deviance:</strong> {c.deviance.value.toFixed(3)} (V11: {c.deviance.was.toFixed(3)}; lower is better).
            </li>
            <li>
              <strong>Top-1,000 hits:</strong> {fmtRatio(c.top1000)} of the model's 1,000 highest hexagons have a real toilet.
            </li>
            <li>
              <strong>Council-planned sites:</strong> {fmtRatio(c.council)} land in the model's top 10%.
            </li>
            <li>
              <strong>Total:</strong> predicts {c.predictedTotal.toLocaleString()} toilets across the study area (real: {c.actualTotal.toLocaleString()}).
            </li>
          </ul>
          <p>
            <strong>Result:</strong> {c.picks.listed} suggested spots, each short of at least one toilet, ranked by gap only. Of the top 120:
          </p>
          <ul>
            <li>{fmtRatio(c.picks.osmAlready)} already have a toilet on OpenStreetMap.</li>
            <li>{fmtRatio(c.picks.nearPlanned)} are near a council-planned site.</li>
            <li>{fmtRatio(c.picks.poorest30)} are in Sydney's poorest 30% of areas.</li>
            <li>{fmtRatio(c.picks.richest30)} are in the richest 30%.</li>
          </ul>
          <p className="note">
            Every test behind these numbers is on the <Link to="/app/tests">Tests</Link> page.
          </p>
        </section>

        <section aria-labelledby="heatmap-title">
          <h2 id="heatmap-title">Heatmap</h2>
          <Heatmap />
          <p className="note">
            Gap = predicted − real toilets. The model learns where toilets exist today, not unmet need: suggested spots are places to investigate. Map data ©{' '}
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
                  <th scope="col">Poisson deviance</th>
                  <th scope="col">PR-AUC</th>
                  <th scope="col">Top-100 hits</th>
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
            Five-fold spatial cross-validation. V1–V8 use the same 16,228 hexagons and folds; V8 is an exploratory future-population scenario, and V9's
            full-area deviance is not directly comparable. V10 is incomplete. V1–V10 are seed 0, from Jimmy's saved <code>comparison.csv</code>; V11 and V12 are the
            mean of seeds 0–2.
          </p>
        </section>
      </main>
    </div>
  )
}
