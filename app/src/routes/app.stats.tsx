import { Link, createFileRoute } from '@tanstack/react-router'
import { fmtRatio } from '../components/Bars'
import type { Tracking } from '../lib/data'
import trackingJson from '../data/tracking.json'

const t = trackingJson as Tracking
const c = t.current

export const Route = createFileRoute('/app/stats')({ component: TrackingPage })

const fmt = (v: number | null, digits: number) => (v === null ? 'Pending' : v.toFixed(digits))

function TrackingPage() {
  return (
    <div className="stats">
      <div className="stats-inner">
        <header>
          <h1>Model tracking</h1>
          <p className="note">{t.source}</p>
        </header>

        <section>
          <h2>Current model: {c.id}</h2>
          <div className="kpis">
            <div className="kpi">
              <b>{c.prAuc.value.toFixed(3)}</b>
              <span>
                PR-AUC, was {c.prAuc.was.toFixed(3)} (random: {c.prAuc.random})
              </span>
            </div>
            <div className="kpi">
              <b>{c.deviance.value.toFixed(3)}</b>
              <span>Poisson deviance, was {c.deviance.was.toFixed(3)} (lower is better)</span>
            </div>
            <div className="kpi">
              <b>{fmtRatio(c.top1000)}</b>
              <span>Real toilet hexes in the top 1,000</span>
            </div>
            <div className="kpi">
              <b>{fmtRatio(c.council)}</b>
              <span>Council-planned sites in the top 10%</span>
            </div>
          </div>
          <p>
            Predicts {c.predictedTotal.toLocaleString()} toilets across the study area (real: {c.actualTotal.toLocaleString()}).
          </p>
        </section>

        <section>
          <h2>How the list is made</h2>
          <ol className="steps">
            {c.setup.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <p>
            Result: {c.picks.listed} spots. Of the top 120, {fmtRatio(c.picks.osmAlready)} already have an OpenStreetMap toilet, {fmtRatio(c.picks.nearPlanned)} are near a
            council-planned site, and {fmtRatio(c.picks.poorest30)} are in Sydney's poorest 30% of areas against {fmtRatio(c.picks.richest30)} in the richest 30%.
          </p>
        </section>

        <section>
          <h2>All versions</h2>
          <table className="t">
            <thead>
              <tr>
                <th>Version</th>
                <th>Description</th>
                <th className="num">Hexagons</th>
                <th className="num">Features</th>
                <th className="num">Poisson deviance</th>
                <th className="num">PR-AUC</th>
                <th className="num">Top-100 hits</th>
              </tr>
            </thead>
            <tbody>
              {t.versions.map((v) => (
                <tr key={v.id} className={v.status === 'current' ? 'current' : undefined}>
                  <td>
                    <b>{v.id}</b>
                    {v.status === 'current' && <span className="tag">current</span>}
                  </td>
                  <td>{v.description}</td>
                  <td className="num">{v.hexes.toLocaleString()}</td>
                  <td className="num">{v.features}</td>
                  <td className="num">{fmt(v.deviance, 4)}</td>
                  <td className="num">{fmt(v.prAuc, 4)}</td>
                  <td className="num">{v.top100 ?? 'Pending'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="note">
            V9 covers a larger area, so its deviance is not directly comparable to the others. Every test behind these numbers is on the <Link to="/app/tests">Tests</Link> page.
          </p>
        </section>
      </div>
    </div>
  )
}
