import { Link, createFileRoute } from '@tanstack/react-router'
import { fmtRatio } from '../components/Bars'
import type { Tracking } from '../lib/data'
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
        <section aria-labelledby="comparison-title">
          <h1 id="comparison-title">PIGEON-AI — Dataset Comparison</h1>
          <p>Saved five-fold spatial cross-validation results for the toilet-count experiments.</p>
          <div className="table-scroll" role="region" aria-label="Dataset comparison table" tabIndex={0}>
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
          <ul>
            <li>On the comparable historical study-area experiments, V5 has the highest PR-AUC and V6 the lowest deviance.</li>
            <li>V2 performs substantially worse than the baseline.</li>
            <li>V9's expanded coverage does not meaningfully improve original-area performance (deviance 0.4271; PR-AUC 0.5104).</li>
            <li>
              {c.id} has the highest PR-AUC ({c.prAuc.value.toFixed(3)}) and the lowest deviance ({c.deviance.value.toFixed(3)}) of every version, and is the current model.
            </li>
          </ul>
          <p className="note">
            V1–V8 use the same 16,228 hexagons and folds; V8 is an exploratory future-population scenario. V9's full-area deviance is not directly comparable to V1–V8. V10 is
            incomplete and remains pending. V1–V10 are seed 0, from the saved <code>comparison.csv</code>; V11 and V12 are the mean of seeds 0–2.
          </p>
        </section>

        <section aria-labelledby="selected-title">
          <h2 id="selected-title">Selected Model: {c.id}</h2>
          <ul>
            <li>
              <strong>PR-AUC:</strong> {c.prAuc.value.toFixed(3)}, up from {c.prAuc.was.toFixed(3)} for V11 (random guessing: {c.prAuc.random}).
            </li>
            <li>
              <strong>Poisson deviance:</strong> {c.deviance.value.toFixed(3)}, down from {c.deviance.was.toFixed(3)}.
            </li>
            <li>
              <strong>Top-1,000 hits:</strong> {fmtRatio(c.top1000)} real toilet hexagons.
            </li>
            <li>
              <strong>Council-planned sites:</strong> {fmtRatio(c.council)} in the top 10%.
            </li>
            <li>
              <strong>Total:</strong> predicts {c.predictedTotal.toLocaleString()} toilets across the study area (real: {c.actualTotal.toLocaleString()}).
            </li>
          </ul>
        </section>

        <section aria-labelledby="list-title">
          <h2 id="list-title">Recommended List</h2>
          <ol>
            {c.setup.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <p>
            Result: {c.picks.listed} spots. Of the top 120, {fmtRatio(c.picks.osmAlready)} already have an OpenStreetMap toilet, {fmtRatio(c.picks.nearPlanned)} are near a
            council-planned site, and {fmtRatio(c.picks.poorest30)} are in Sydney's poorest 30% of areas against {fmtRatio(c.picks.richest30)} in the richest 30%.
          </p>
          <p className="note">
            Every test behind these numbers is on the <Link to="/app/tests">Tests</Link> page.
          </p>
        </section>
      </main>
    </div>
  )
}
