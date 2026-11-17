import { Link, createFileRoute } from '@tanstack/react-router'
import 'leaflet/dist/leaflet.css'
import { Heatmap } from '../components/Heatmap'
import { Term } from '../components/Term'
import { capitalize, LIVE_LAYERS, type Unit } from '../infra'
import { LAYER_DATA, type Labels } from '../infra-data'
import { useLayer } from '../layer'
import { fmtRatio, type References } from '../lib/data'

export const Route = createFileRoute('/app/stats')({ component: TrackingPage })

const fmt = (v: number | null, digits: number) => (v === null ? 'Pending' : v.toFixed(digits))
const STATUS = { done: 'Completed', pending: 'Pending', current: 'Current' } as const

const settingsFor = (many: string) =>
  [
    ['Trees', '300', 'Averaging many trees steadies the prediction'],
    ['Leaf size', 'At least 20 hexagons', 'Each guess averages 20+ similar places, so it learns patterns, not single spots'],
    ['Inputs per question', 'Half, picked at random', 'Stops one input (like shops) from taking over every tree'],
    ['Depth limit', 'None', 'Leaf size stops the trees, at about 21 questions deep'],
    ['Rebalancing', 'None', `Keeps predictions on the real scale: 1.2 means 1.2 ${many}`],
  ] as const

// Tested on toilets, from experiments/leaf_size/results.csv: leaf size, deviance on trained hexagons, deviance on unseen areas, PR-AUC.
const LEAF_SWEEP = [
  [1, 0.0784, 0.4091, 0.5592],
  [5, 0.1705, 0.3845, 0.5734],
  [10, 0.2248, 0.3795, 0.5752],
  [20, 0.2716, 0.3782, 0.5687],
  [50, 0.323, 0.3836, 0.5536],
  [100, 0.3527, 0.3928, 0.5343],
  [500, 0.4102, 0.4323, 0.455],
] as const

const ORDINALS = ['first', 'second', 'third', 'fourth'] as const

function TrackingPage() {
  const layer = useLayer()
  const { one, many } = layer.unit
  const { tracking: t, stats, references, labels, osmInLabel, meanDeviance } = LAYER_DATA[layer.id]
  const c = t.current
  const previous = t.versions.at(-2)?.id
  const settings = settingsFor(many)
  return (
    <div className="jimmy">
      <main>
        <section aria-labelledby="tracking-title">
          <h1 id="tracking-title">PIGEON-AI — Tracking</h1>
          <p>
            Pigeon AI predicts where the next public infrastructure should go, from a bird's-eye view of Sydney today and of its growth and future suburbs. {`Public ${many} are the ${ORDINALS[LIVE_LAYERS.indexOf(layer)]} layer.`}
          </p>
        </section>

        <section aria-labelledby="selected-title">
          <h2 id="selected-title">Selected model: {c.id}</h2>
          <ul>
            <li>
              <strong>
                <Term id="prAuc">PR-AUC</Term>:
              </strong>{' '}
              {c.prAuc.value.toFixed(3)} ({c.prAuc.was !== undefined && `${previous}: ${c.prAuc.was.toFixed(3)}; `}
              <Term id="random">random guessing</Term>: {c.prAuc.random.toFixed(3)}).
            </li>
            <li>
              <strong>
                <Term id="deviance">Poisson deviance</Term>:
              </strong>{' '}
              {c.deviance.value.toFixed(3)} ({c.deviance.was !== undefined && `${previous}: ${c.deviance.was.toFixed(3)} `}against {meanDeviance.toFixed(3)} for predicting the
              average everywhere).
            </li>
            <li>
              <strong>
                <Term id="top1000">Top-1,000 hits</Term>:
              </strong>{' '}
              {fmtRatio(c.top1000)} of the model's 1,000 highest <Term id="hexagon">hexagons</Term> have a real {one}.
            </li>
            {c.council && (
              <li>
                <strong>
                  <Term id="council">Council-planned sites</Term>:
                </strong>{' '}
                {fmtRatio(c.council)} land in the model's top 10%.
              </li>
            )}
            <li>
              <strong>
                <Term id="predictedVsReal">Predicted vs real</Term>:
              </strong>{' '}
              predicts {c.predictedTotal.toLocaleString()} {many} across the study area (real: {c.actualTotal.toLocaleString()}).
            </li>
          </ul>
          <p>
            <strong>Result:</strong> {c.picks.listed} <Term id="suggested">places need at least one more {one}</Term> than they have, counting {many}{' '}
            <Term id="officialMap">{labels.on}</Term>
            {!osmInLabel && (
              <>
                {' '}
                and <Term id="osm">OpenStreetMap</Term>
              </>
            )}
            . They are ranked by{' '}
            <Term id="missing">{many} missing</Term>, with no other weighting. Of these {c.picks.listed}:
          </p>
          <ul>
            <li>
              {fmtRatio(c.picks.alreadyOne)} already have at least one {one}, but the model expects at least one more.
            </li>
            {c.picks.nearPlanned && <li>{fmtRatio(c.picks.nearPlanned)} are near a council-planned site.</li>}
            <li>
              {fmtRatio(c.picks.poorest30)} are in Sydney's poorest 30% of areas and {fmtRatio(c.picks.richest30)} in the richest 30% (by{' '}
              <Term id="seifa">SEIFA decile</Term>; {c.picks.noSeifa} have no score).
            </li>
          </ul>
          <p className="note">
            Every test behind these numbers is on the <Link to="/app/tests" search={(prev) => prev}>
              Tests
            </Link> page.
          </p>
        </section>

        <section aria-labelledby="model-title">
          <h2 id="model-title">The model</h2>
          <p>
            Pigeon AI uses a random forest: 300 decision trees that each predict how many {many} a hexagon should have. The final prediction is the average of
            the 300.
          </p>
          <p>
            <strong>One tree</strong> is a list of yes/no questions about a place, such as "4 or more food places within 250 m?". Each hexagon answers the questions
            and lands in a leaf. The leaf's prediction is the average {one} count of the hexagons in it.
          </p>
          <p>
            <strong>What it sees:</strong> 45 inputs per hexagon. These are population, shops, food, transport, parks, footpaths, sports grounds, playgrounds and
            beaches, counted inside the hexagon and within 250 m, 500 m and 1 km.
          </p>
          <p>
            <strong>What it doesn't see, on purpose:</strong> location, council, income or demographics, and OpenStreetMap {many}. Location would let it learn
            "this area has few {many}" and repeat that gap. OpenStreetMap {many} would nearly give it the answer.
          </p>
          <div className="table-scroll">
            <table className="small">
              <thead>
                <tr>
                  <th>Setting</th>
                  <th>Our choice</th>
                  <th>Why</th>
                </tr>
              </thead>
              <tbody>
                {settings.map(([setting, choice, why]) => (
                  <tr key={setting}>
                    <td>{setting}</td>
                    <td>{choice}</td>
                    <td>{why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3>Why leaf size 20?</h3>
          <p>
            We tested it on toilets, and every layer uses the same settings. Smaller leaves fit the training hexagons better but do worse on areas the model never saw, which means it is memorising. Bigger leaves
            are too blunt everywhere. Leaf sizes 10 to 20 are the sweet spot, and we kept 20.
          </p>
          <div className="table-scroll">
            <table className="small">
              <thead>
                <tr>
                  <th>Leaf size</th>
                  <th>Error on trained hexagons</th>
                  <th>Error on unseen areas</th>
                  <th>
                    <Term id="prAuc">PR-AUC</Term>
                  </th>
                </tr>
              </thead>
              <tbody>
                {LEAF_SWEEP.map(([leaf, trained, unseen, prAuc]) => (
                  <tr key={leaf}>
                    <td>{leaf === 20 ? <strong>20 (ours)</strong> : leaf}</td>
                    <td>{trained.toFixed(3)}</td>
                    <td>{unseen.toFixed(3)}</td>
                    <td>{prAuc.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">
            Tested on toilets. Error is <Term id="deviance">Poisson deviance</Term> (lower is better). Each row is a full V12 toilet run with only the leaf size changed. Rerun it with{' '}
            <code>experiments/leaf_size/sweep.py</code>.
          </p>
        </section>

        <section aria-labelledby="training-title">
          <h2 id="training-title">How it's trained and tested</h2>
          <p>
            The model learns the pattern of where Sydney's {many} go: how many a place has for its population, shops, transport and parks. To test it fairly, Sydney's {stats.find.hexes.toLocaleString()} hexagons are grouped into 90 larger blocks, and the blocks are
            split into 5 groups. Each turn, the model trains on 4 groups and predicts the 5th. After 5 turns, every hexagon has been predicted once, by a model that
            never saw its area. This is <Term id="crossValidation">five-fold spatial cross-validation</Term>, and every score above is{' '}
            <Term id="heldOut">held-out</Term> this way. The <Term id="growthSuburbs">growth-suburbs test</Term> is separate: {stats.growth.hexes.toLocaleString()} new-suburb hexagons were not in
            the training data at all.
          </p>
          <SplitDiagram />
          <h3>Why the scores aren't perfect, and shouldn't be</h3>
          <p>
            Every score is measured on hexagons the model never saw, so it can't copy their {many}. It can only score well by learning Sydney's pattern: more
            people, shops and stations means more {many}. A perfect score would mean every place already has exactly the {many} that places like it have, so
            Sydney would have no shortfalls. Lower <Term id="deviance">deviance</Term> means the model learned the pattern better, and what's left over is partly the
            shortfalls we're looking for. That is how Pigeon AI measures need: against Sydney's own standard, applied the same way to growth and new suburbs.
          </p>
        </section>

        <section aria-labelledby="heatmap-title">
          <h2 id="heatmap-title">Heatmap</h2>
          <Heatmap key={layer.id} />
          <p className="note">
            {capitalize(many)} missing = how many fewer {many} a place has than the Sydney average for places with similar population, shops, transport and parks. Map
            data ©{' '}
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
          {t.versions.length === 1 ? (
            <p className="note">
              <Term id="crossValidation">Five-fold spatial cross-validation</Term>. {c.id} uses V12's inputs and settings unchanged; its scores are the{' '}
              <Term id="seeds">mean of seeds 0–2</Term>.
            </p>
          ) : (
          <p className="note">
            <Term id="crossValidation">Five-fold spatial cross-validation</Term>. V1–V8 use the same {stats.find.hexes.toLocaleString()} hexagons and folds; V8 is an exploratory future-population scenario, and V9's
            full-area deviance is not directly comparable. V10 is incomplete. V1–V10 are seed 0, from Jimmy's saved <code>comparison.csv</code>; V11 and V12 are the{' '}
            <Term id="seeds">mean of seeds 0–2</Term>.
          </p>
          )}
        </section>
        <section aria-labelledby="references-title">
          <details className="references">
            <summary>
              <h2 id="references-title">References</h2>
            </summary>
            <h3>Data</h3>
            <ul>
              {dataSources(layer.unit, labels, osmInLabel).map(([name, url, use]) => (
                <li key={url}>
                  <a href={url}>{name}</a>: {use}
                </li>
              ))}
            </ul>
            {references && <CouncilPlans references={references} unit={layer.unit.one} />}
          </details>
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

function dataSources({ one, many }: Unit, labels: Labels, osmInLabel: boolean): [string, string, string][] {
  return [
    ...labels.sources.map(({ name, url }): [string, string, string] => [name, url, `${one} locations the model trains on.`]),
    [
      'OpenStreetMap',
      'https://www.openstreetmap.org/copyright',
      `shops, food, transport, parks, sports grounds, playgrounds, beaches, footpaths, and ${many} ${osmInLabel ? 'where councils keep no records' : 'the official map misses'} (Geofabrik NSW extract and the Overpass API).`,
    ],
    ['ABS 2021 Census DataPacks', 'https://www.abs.gov.au/census/find-census-data/datapacks', 'population per area.'],
    ['ABS Australian Statistical Geography Standard', 'https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3', 'Greater Sydney, suburb and SA1 boundaries.'],
    ['ABS SEIFA 2021', 'https://www.abs.gov.au/statistics/people/people-and-communities/socio-economic-indexes-areas-seifa-australia/latest-release', 'disadvantage deciles for the fairness check (never a model input).'],
    ['NSW Planning Portal open data', 'https://www.planningportal.nsw.gov.au/opendata', 'zoning used to build features for future areas.'],
    ['H3 hexagonal grid', 'https://h3geo.org', 'the resolution-9 hexagons everything is measured on.'],
  ]
}

function CouncilPlans({ references, unit }: { references: References; unit: string }) {
  const councils = Object.entries(
    references.councilDocs.reduce<Record<string, References['councilDocs']>>((acc, d) => {
      ;(acc[d.council] ??= []).push(d)
      return acc
    }, {}),
  )
  return (
    <>
      <h3>
        Council {unit} plans ({references.councilSites} sites from {councils.length} councils)
      </h3>
      <p className="note">Used to check the model against where councils plan to build. Each link is the document the sites came from.</p>
      <ul>
        {councils.map(([council, docs]) => (
          <li key={council}>
            <strong>{council}</strong>
            <ul>
              {docs.map((d) => (
                <li key={d.url + d.document}>
                  <a href={d.url}>{d.document}</a> ({d.sites} {d.sites === 1 ? 'site' : 'sites'})
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </>
  )
}
