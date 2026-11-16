import { createFileRoute } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import { Term } from '../components/Term'
import { capitalize } from '../infra'
import { LAYER_DATA } from '../infra-data'
import { useLayer } from '../layer'
import { fmtRatio } from '../lib/data'

export const Route = createFileRoute('/app/tests')({ component: TestsPage })

function Compare({ rows }: { rows: [ReactNode, string, string][] }) {
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
          {rows.map(([m, v, cmp], i) => (
            <tr key={i}>
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
  const layer = useLayer()
  const { one, many } = layer.unit
  const { find, council, growth, reach } = LAYER_DATA[layer.id].stats
  return (
    <div className="jimmy">
      <main>
        <section aria-labelledby="tests-title">
          <h1 id="tests-title">PIGEON-AI — Tests</h1>
          <p>
            Four questions about the selected model, V12. Every answer scores predictions for <Term id="hexagon">hexagons</Term> the model did not train on (
            <Term id="heldOut">held-out</Term>).
          </p>
        </section>

        <section aria-labelledby="q1">
          <h2 id="q1">{`1. Does it find where ${many} really are?`}</h2>
          <p>
            Yes. {find.top100.x} of its top 100 hexagons have a real {one}, where <Term id="random">random guessing</Term> would find about{' '}
            {Math.round(find.random * 100)}.
          </p>
          <Compare
            rows={[
              [<Term id="top100">Real {one} hexagons in the top 100</Term>, fmtRatio(find.top100), `≈${Math.round(find.random * 100)} by random guessing`],
              [<Term id="top1000">Real {one} hexagons in the top 1,000</Term>, fmtRatio(find.top1000), `≈${Math.round(find.random * 1000)} by random guessing`],
              [<Term id="prAuc">PR-AUC</Term>, find.prAuc.toFixed(3), `${find.random.toFixed(3)} by random guessing`],
            ]}
          />
          <p className="note">
            {find.hexes.toLocaleString()} study hexagons, {find.toiletHexes.toLocaleString()} with a {one} on the <Term id="officialMap">official map</Term>. Scored
            by <Term id="crossValidation">five-fold spatial cross-validation</Term>; <Term id="seeds">mean of seeds 0–2</Term>.
          </p>
        </section>

        <section aria-labelledby="q2">
          <h2 id="q2">2. Does it agree with councils' own plans?</h2>
          <p>
            Mostly. {council.top10.x} of {council.top10.y} <Term id="council">sites that councils plan to build</Term> land in the model's top 10%, against about{' '}
            {council.random} by chance.
          </p>
          <Compare rows={[[<Term id="council">Council-planned sites in the model's top 10%</Term>, fmtRatio(council.top10), `≈${council.random}/${council.top10.y} by chance`]]} />
          <p className="note">Sites taken from councils' strategies, project pages, development reports and media releases.</p>
        </section>

        <section aria-labelledby="q3">
          <h2 id="q3">3. Does it work on suburbs it never saw?</h2>
          <p>
            Yes. The <Term id="growthSuburbs">growth suburbs</Term> were left out of training entirely. Counting {many} on both the official map and{' '}
            <Term id="osm">OpenStreetMap</Term>, {growth.withOsm.top100.x} of the {growth.withOsm.top100.y} hexagons with a {one} are in its top 100, and it
            predicts {growth.predicted} {many} where {growth.withOsm.actual} exist.
          </p>
          <Compare
            rows={[
              [<Term id="top100">{capitalize(one)} hexagons in the top 100</Term>, fmtRatio(growth.withOsm.top100), `≈${Math.round(growth.withOsm.random * 100)} by random guessing`],
              [<Term id="prAuc">PR-AUC</Term>, growth.withOsm.prAuc.toFixed(3), `${growth.withOsm.random.toFixed(3)} by random guessing`],
              [<Term id="predictedVsReal">{capitalize(many)}</Term>, `${growth.predicted} predicted`, `${growth.withOsm.actual} real`],
            ]}
          />
          <p className="note">{growth.hexes.toLocaleString()} hexagons, none of them in the training data.</p>
        </section>

        <section aria-labelledby="q4">
          <h2 id="q4">4. Who does the list reach?</h2>
          <p>
            With no weighting, the {reach.listed} places that need at least one more {one} lean towards poorer areas: {fmtRatio(reach.poorest30)} are in the poorest 30%
            of areas and {fmtRatio(reach.richest30)} in the richest 30% ({reach.noSeifa} have no <Term id="seifa">SEIFA</Term> score). The model's predictions stay
            close to the real count in every decile.
          </p>
          <div className="table-scroll">
            <table className="small">
              <thead>
                <tr>
                  <th scope="col">
                    <Term id="seifa">Decile</Term>
                  </th>
                  <th scope="col">Real {many}</th>
                  <th scope="col">
                    <Term id="predictedVsReal">V12 predicted</Term>
                  </th>
                  <th scope="col">
                    <Term id="per10k">{capitalize(many)} per 10k residents</Term>
                  </th>
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
