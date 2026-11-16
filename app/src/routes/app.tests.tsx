import { createFileRoute } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import { Caveat } from '../components/Caveat'
import { Term } from '../components/Term'
import { capitalize } from '../infra'
import { LAYER_DATA } from '../infra-data'
import { useLayer } from '../layer'
import { fmtRatio, type Stats } from '../lib/data'

export const Route = createFileRoute('/app/tests')({ component: TestsPage })

function Compare({ model, rows }: { model: string; rows: [ReactNode, string, string][] }) {
  return (
    <div className="table-scroll">
      <table className="small">
        <thead>
          <tr>
            <th scope="col">Measure</th>
            <th scope="col">{model}</th>
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

const NUMBER_WORDS = ['Three', 'Four'] as const

/** The decile whose prediction is furthest from the real count, as a ratio; `close` when every decile is within 25%. */
function worstDecile(deciles: Stats['reach']['deciles']) {
  const off = (d: (typeof deciles)[number]) => Math.abs(Math.log(d.predicted / Math.max(d.real, 1)))
  const worst = deciles.reduce((a, b) => (off(b) > off(a) ? b : a))
  return { worst, close: off(worst) <= Math.log(1.25) }
}

function TestsPage() {
  const layer = useLayer()
  const { one, many } = layer.unit
  const { stats, tracking, labels, osmInLabel } = LAYER_DATA[layer.id]
  const { find, council, growth, reach } = stats
  const model = tracking.current.id
  // The growth test counts OpenStreetMap units too: from the label itself, or from the OSM-corrected rerun.
  const g = growth.withOsm ?? growth
  const counted = osmInLabel ? labels.on : `${labels.on.replace(/^on /, 'on both ')} and`
  const decile = worstDecile(reach.deciles)
  let n = 0
  return (
    <div className="jimmy">
      <main>
        <section aria-labelledby="tests-title">
          <h1 id="tests-title">PIGEON-AI — Tests</h1>
          <p>
            {NUMBER_WORDS[council ? 1 : 0]} questions about the selected model, {model}. Every answer scores predictions for <Term id="hexagon">hexagons</Term>{' '}
            the model did not train on (<Term id="heldOut">held-out</Term>).
          </p>
          <Caveat />
        </section>

        <section aria-labelledby="q1">
          <h2 id="q1">{`${++n}. Does it find where ${many} really are?`}</h2>
          <p>
            Yes. {find.top100.x} of its top 100 hexagons have a real {one}, where <Term id="random">random guessing</Term> would find about{' '}
            {Math.round(find.random * 100)}.
          </p>
          <Compare
            model={model}
            rows={[
              [<Term id="top100">Real {one} hexagons in the top 100</Term>, fmtRatio(find.top100), `≈${Math.round(find.random * 100)} by random guessing`],
              [<Term id="top1000">Real {one} hexagons in the top 1,000</Term>, fmtRatio(find.top1000), `≈${Math.round(find.random * 1000)} by random guessing`],
              [<Term id="prAuc">PR-AUC</Term>, find.prAuc.toFixed(3), `${find.random.toFixed(3)} by random guessing`],
            ]}
          />
          <p className="note">
            {find.hexes.toLocaleString()} study hexagons, {find.toiletHexes.toLocaleString()} with a {one} <Term id="officialMap">{labels.on}</Term>. Scored by{' '}
            <Term id="crossValidation">five-fold spatial cross-validation</Term>; <Term id="seeds">mean of seeds 0–2</Term>.
          </p>
        </section>

        {council && (
          <section aria-labelledby="q2">
            <h2 id="q2">{++n}. Does it agree with councils' own plans?</h2>
            <p>
              Mostly. {council.top10.x} of {council.top10.y} <Term id="council">sites that councils plan to build</Term> land in the model's top 10%, against
              about {council.random} by chance.
            </p>
            <Compare
              model={model}
              rows={[
                [
                  <Term id="council">Council-planned sites in the model's top 10%</Term>,
                  fmtRatio(council.top10),
                  `≈${council.random}/${council.top10.y} by chance`,
                ],
              ]}
            />
            <p className="note">Sites taken from councils' strategies, project pages, development reports and media releases.</p>
          </section>
        )}

        <section aria-labelledby="q3">
          <h2 id="q3">{++n}. Does it work on suburbs it never saw?</h2>
          <p>
            Yes. The <Term id="growthSuburbs">growth suburbs</Term> were left out of training entirely. Counting {many} {counted}
            {!osmInLabel && (
              <>
                {' '}
                <Term id="osm">OpenStreetMap</Term>
              </>
            )}
            , {g.top100.x} of the {g.top100.y} hexagons with a {one} are in its top 100, and it predicts {growth.predicted} {many} where {g.actual} exist.
          </p>
          <Compare
            model={model}
            rows={[
              [<Term id="top100">{capitalize(one)} hexagons in the top 100</Term>, fmtRatio(g.top100), `≈${Math.round(g.random * 100)} by random guessing`],
              [<Term id="prAuc">PR-AUC</Term>, g.prAuc.toFixed(3), `${g.random.toFixed(3)} by random guessing`],
              [<Term id="predictedVsReal">{capitalize(many)}</Term>, `${growth.predicted} predicted`, `${g.actual} real`],
            ]}
          />
          <p className="note">{growth.hexes.toLocaleString()} hexagons, none of them in the training data.</p>
        </section>

        <section aria-labelledby="q4">
          <h2 id="q4">{++n}. Who does the list reach?</h2>
          <p>
            With no weighting, the {reach.listed} places that need at least one more {one} lean towards poorer areas: {fmtRatio(reach.poorest30)} are in the
            poorest 30% of areas and {fmtRatio(reach.richest30)} in the richest 30% ({reach.noSeifa} have no <Term id="seifa">SEIFA</Term> score).{' '}
            {decile.close
              ? "The model's predictions stay close to the real count in every decile."
              : `The model's predictions are far from the real count in some deciles: in decile ${decile.worst.decile} it predicts ${decile.worst.predicted} ${many} where ${decile.worst.real} are recorded.`}
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
                    <Term id="predictedVsReal">{model} predicted</Term>
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
          <p className="note">
            Deciles of the ABS SEIFA disadvantage index (IRSD) across the study hexagons. Hexagons without a SEIFA score are left out. Predictions are seed 0.
          </p>
        </section>
      </main>
    </div>
  )
}
