import { createFileRoute } from '@tanstack/react-router'
import { fmtRatio, type Stats } from '../lib/data'
import statsJson from '../data/stats.json'

const s = statsJson as Stats
const { find, council, growth, reach } = s

export const Route = createFileRoute('/app/tests')({ component: TestsPage })

function Compare({ rows }: { rows: [string, string, string][] }) {
  return (
    <div className="table-scroll">
      <table className="small">
        <thead>
          <tr>
            <th scope="col">Measure</th>
            <th scope="col">V12</th>
            <th scope="col">Compare with</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([m, v, cmp]) => (
            <tr key={m}>
              <td>{m}</td>
              <td>{v}</td>
              <td>{cmp}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TestsPage() {
  return (
    <div className="jimmy">
      <main>
        <section aria-labelledby="tests-title">
          <h1 id="tests-title">PIGEON-AI — Tests</h1>
          <p>Four questions about the selected model, V12. Every answer scores predictions for hexagons the model did not train on.</p>
        </section>

        <section aria-labelledby="q1">
          <h2 id="q1">1. Does it find where toilets really are?</h2>
          <p>
            Yes. {find.top100.x} of its top 100 hexagons have a real toilet, where random guessing would find about {Math.round(find.random * 100)}.
          </p>
          <Compare
            rows={[
              ['Real toilet hexagons in the top 100', fmtRatio(find.top100), `≈${Math.round(find.random * 100)} by random guessing`],
              ['Real toilet hexagons in the top 1,000', fmtRatio(find.top1000), `≈${Math.round(find.random * 1000)} by random guessing`],
              ['PR-AUC', find.prAuc.toFixed(3), `${find.random.toFixed(3)} by random guessing`],
            ]}
          />
          <p className="note">
            {find.hexes.toLocaleString()} study hexagons, {find.toiletHexes.toLocaleString()} with a toilet. Mean of seeds 0–2.
          </p>
        </section>

        <section aria-labelledby="q2">
          <h2 id="q2">2. Does it agree with councils' own plans?</h2>
          <p>
            Mostly. {council.top10.x} of {council.top10.y} sites that councils plan to build land in the model's top 10%, against about {council.random} by chance.
          </p>
          <Compare rows={[["Council-planned sites in the model's top 10%", fmtRatio(council.top10), `≈${council.random}/${council.top10.y} by chance`]]} />
          <p className="note">Sites taken from councils' strategies, project pages, development reports and media releases.</p>
        </section>

        <section aria-labelledby="q3">
          <h2 id="q3">3. Does it work on suburbs it never saw?</h2>
          <p>
            Yes, though less sharply. In growth suburbs left out of training, {growth.top100.x} of the {growth.top100.y} hexagons with a toilet are in its top 100, and it
            predicts {growth.predicted} toilets where {growth.actual} exist.
          </p>
          <Compare
            rows={[
              ['Toilet hexagons in the top 100', fmtRatio(growth.top100), `≈${growth.randomTop100} by random guessing`],
              ['PR-AUC', growth.prAuc.toFixed(3), `${growth.random.toFixed(3)} by random guessing`],
              ['Toilets', `${growth.predicted} predicted`, `${growth.actual} real`],
            ]}
          />
          <p className="note">
            {growth.hexes.toLocaleString()} hexagons. Predicting more than exist is expected: these suburbs are still filling in.
          </p>
        </section>

        <section aria-labelledby="q4">
          <h2 id="q4">4. Who does the list reach?</h2>
          <p>
            With no weighting, the top 120 spots lean towards poorer areas: {fmtRatio(reach.poorest30)} are in the poorest 30% of areas and {fmtRatio(reach.richest30)} in the
            richest 30%. The model's predictions stay close to the real count in every decile.
          </p>
          <div className="table-scroll">
            <table className="small">
              <thead>
                <tr>
                  <th scope="col">Decile</th>
                  <th scope="col">Real toilets</th>
                  <th scope="col">V12 predicted</th>
                  <th scope="col">Toilets per 10k residents</th>
                </tr>
              </thead>
              <tbody>
                {reach.deciles.map((d) => (
                  <tr key={d.decile}>
                    <td>
                      {d.decile}
                      {d.decile === 1 ? ' (most disadvantaged)' : d.decile === 10 ? ' (least disadvantaged)' : ''}
                    </td>
                    <td>{d.real}</td>
                    <td>{d.predicted}</td>
                    <td>{d.per10k.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">Deciles of the ABS SEIFA disadvantage index (IRSD) across the study hexagons. Hexagons without a SEIFA score are left out. Predictions are seed 0.</p>
        </section>
      </main>
    </div>
  )
}
