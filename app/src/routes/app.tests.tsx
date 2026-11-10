import { createFileRoute } from '@tanstack/react-router'
import { Bars, fmtRatio, Table } from '../components/Bars'
import type { Stats } from '../lib/data'
import statsJson from '../data/stats.json'

const s = statsJson as Stats

export const Route = createFileRoute('/app/tests')({ component: TestsPage })

const SLATE = '#3d5a73'
const GREY = '#9aa5b1'
const ACCENT = '#b8321f'

function TestsPage() {
  const h = s.headline
  return (
    <div className="stats">
      <div className="stats-inner">
        <header>
          <h1>Tests</h1>
          <p className="note">
            Every test we ran. Sections 1–7 test V11, the model before the new features; section 8 compares V11 against V12 and the post-processing steps. {s.model}. Source: docs/findings.md, rebuilt by app/scripts/build_data.py.
          </p>
        </header>

        <section>
          <h2>1. Headline evaluation</h2>
          <div className="kpis">
            <div className="kpi">
              <b>{h.prAuc.value}</b>
              <span>PR-AUC (random: {h.prAuc.random})</span>
            </div>
            <div className="kpi">
              <b>{h.deviance}</b>
              <span>Poisson deviance (lower is better)</span>
            </div>
            <div className="kpi">
              <b>
                {h.predictedTotal.toLocaleString()} / {h.actualTotal.toLocaleString()}
              </b>
              <span>Predicted vs real toilets ({h.predictedTotalPctOfActual}%)</span>
            </div>
            <div className="kpi">
              <b>{h.candidates}</b>
              <span>Candidate hexes (predicted − actual ≥ 1)</span>
            </div>
          </div>
          <p>
            Study area: {h.hexes.toLocaleString()} hexes, {h.toilets.toLocaleString()} toilets in {h.toiletHexes.toLocaleString()} hexes. Real toilet hexes found
            among the model's highest-ranked hexes:
          </p>
          <Bars items={h.topN.map((t) => ({ label: t.label, value: t.pct, max: 100, text: fmtRatio(t) }))} />
        </section>

        <section>
          <h2>2. Are the suggested spots valid?</h2>
          <p>Each of the {s.validity.n} candidate hexes was checked against OpenStreetMap and NSW zoning.</p>
          <Bars items={s.validity.rows.map((r) => ({ label: r.label, value: r.pct, max: 100, text: fmtRatio(r), color: r.label.startsWith('Only') ? ACCENT : SLATE }))} />
          <p className="note">{s.validity.note}</p>
        </section>

        <section>
          <h2>3. Growth suburbs (never trained on)</h2>
          <p>
            {s.growth.suburbs} suburbs, {s.growth.hexes.toLocaleString()} hexes, {s.growth.actual} real toilets in {s.growth.toiletHexes} hexes. The model predicts{' '}
            {s.growth.predicted} (real: {s.growth.actual}).
          </p>
          <Bars
            items={[
              { label: 'Real toilet hexes in top 100', value: s.growth.top100.pct, max: 100, text: fmtRatio(s.growth.top100) },
              { label: 'A random top 100 would catch', value: 3 / s.growth.toiletHexes * 100, max: 100, text: `about 3/${s.growth.toiletHexes} (9%)`, color: GREY },
            ]}
          />
          <p>
            PR-AUC {s.growth.prAuc.value} (random: {s.growth.prAuc.random}). {s.growth.note}
          </p>
          <Table
            head={['Suburb', 'Hexes', 'Real toilets', 'Predicted']}
            rows={s.growth.perSuburb.map((r) => [r.suburb, r.hexes, r.actual, r.pred])}
          />
        </section>

        <section>
          <h2>4. Bradfield / Aerotropolis</h2>
          <p className="callout">Planned scenario — read the ranking, not the totals. No real data exists yet: features were built from government plans (scenario {s.bradfield.scenario}).</p>
          <Table
            head={['', 'Predicted toilets across the area']}
            rows={[
              ['Today, with real features (farmland)', s.bradfield.todayTotal],
              ['Mid scenario, 2041', s.bradfield.midTotal],
            ]}
          />
          <p>
            In the mid scenario {s.bradfield.hexesGe1} hexes reach a prediction of 1 or more; the highest single hex is {s.bradfield.maxHex}. Top hexes:
          </p>
          <Table
            head={['#', 'Zone', 'Nearest station', 'Distance (m)', 'Predicted', 'Top drivers']}
            numFrom={3}
            rows={s.bradfield.top.map((t) => [t.rank, t.zone, t.station, t.stationM, t.pred, t.drivers])}
          />
          <p>
            Proxy check on Oran Park, where real features exist: the proxy features overlap {s.bradfield.oranProxy.overlap.proxy}/{s.bradfield.oranProxy.overlap.of} of the
            real-feature top 10, and put {s.bradfield.oranProxy.toiletHexesInTop10.proxy}/{s.bradfield.oranProxy.toiletHexesInTop10.of} real toilet hexes in their top 10 (real
            features: {s.bradfield.oranProxy.overlap.real}/{s.bradfield.oranProxy.overlap.of} and {s.bradfield.oranProxy.toiletHexesInTop10.real}/
            {s.bradfield.oranProxy.toiletHexesInTop10.of}). The proxy keeps about half the ranking.
          </p>
        </section>

        <section>
          <h2>5. Council plan crosscheck</h2>
          <p>{s.plans.sources}</p>
          <Table
            head={['', 'n', "In model's top 10%", "In model's top 25%", 'Candidate within ~250 m', 'Median percentile']}
            numFrom={1}
            rows={[...s.plans.rows, s.plans.fairest].map((r) => [
              r.label,
              r.n.toLocaleString(),
              fmtRatio(r.top10),
              fmtRatio(r.top25),
              fmtRatio(r.candidateNear),
              `${r.medianPct}th`,
            ])}
          />
          <Bars
            items={[
              { label: 'Planned sites in top 25%', value: s.plans.rows[0]!.top25.pct, max: 100, text: fmtRatio(s.plans.rows[0]!.top25) },
              { label: 'Random empty hexes in top 25%', value: s.plans.rows[1]!.top25.pct, max: 100, text: fmtRatio(s.plans.rows[1]!.top25), color: GREY },
              { label: 'Random empty park hexes in top 25%', value: s.plans.rows[2]!.top25.pct, max: 100, text: fmtRatio(s.plans.rows[2]!.top25), color: GREY },
              { label: 'Brand-new sites, no toilet yet, top 25%', value: s.plans.fairest.top25.pct, max: 100, text: fmtRatio(s.plans.fairest.top25) },
            ]}
          />
          <p>
            Reverse check: {fmtRatio(s.plans.reverse.candidatesNear)} of the candidates are near a planned site, against {s.plans.reverse.chance.pct}% by chance (
            {s.plans.reverse.chance.x}/{s.plans.reverse.chance.y.toLocaleString()} hexes).
          </p>
          <p className="note">Misses: {s.plans.misses}</p>
        </section>

        <section>
          <h2>6. Socioeconomic shape (SEIFA deciles)</h2>
          <Bars
            items={[
              { label: 'Decile 1 (most disadvantaged)', value: s.seifa.toilets_per_10k_decile_1, max: 6, text: `${s.seifa.toilets_per_10k_decile_1} toilets per 10k residents` },
              { label: 'Decile 10 (least disadvantaged)', value: s.seifa.toilets_per_10k_decile_10, max: 6, text: `${s.seifa.toilets_per_10k_decile_10} toilets per 10k residents` },
            ]}
          />
          <p>
            Real ÷ predicted stays between {s.seifa.real_over_pred_min} and {s.seifa.real_over_pred_max} across all deciles. {s.seifa.note}
          </p>
        </section>

        <section>
          <h2>7. The three new-area tests</h2>
          <Table
            head={['Test', 'Where', 'Does real data exist?', 'What it shows', 'Result']}
            numFrom={99}
            rows={s.newAreaTests.map((t) => [t.test, t.where, t.real_data, t.shows, t.result])}
          />
        </section>
        <section>
          <h2>8. V12 and post-processing (every combination)</h2>
          <p>Each change was run with 3 seeds. A gain smaller than the seed spread is noise.</p>
          <Table
            head={['Change', 'PR-AUC', 'Council sites in top 10%', 'Growth toilet hexes in top 100', 'Verdict']}
            numFrom={1}
            rows={s.v2Changes.map((c) => [c.change, c.prAuc, c.council, c.growth, c.verdict])}
          />
          <p className="note">{s.v2Note}</p>
        </section>
      </div>
    </div>
  )
}
