import { LAYER_DATA } from '../infra-data'
import type { AgentData } from './tools'

/**
 * What Pigeon knows about the project itself: the hexagons, the inputs, how the model was trained and tested, and how the
 * suggested list is built. Facts come from docs/model.md and docs/findings.md; numbers for the current layer come from its stats.
 */
export function projectBrief(d: AgentData): string {
  const { one, many } = d.layer.unit
  const { find, growth, council } = d.stats
  const { labels, osmInLabel } = LAYER_DATA[d.layer.id]
  const { picks } = d.tracking.current
  return `## The project
Pigeon AI is a student project (Summit, Jimmy and Oscar) that predicts where Sydney needs public infrastructure. Public toilets were the first layer; water fountains reuse the same model and pipeline with different labels. The current layer is ${d.layer.name.toLowerCase()}.

## Hexagons
- Sydney is split into ${find.hexes.toLocaleString()} H3 resolution-9 hexagons, each about 0.1 km² (roughly one city block, about 175 m across). Every input, prediction and suggestion is per hexagon.
- One ring of neighbouring hexagons is about 400 m of walking, the City of Sydney's toilet coverage target.
- Resolution-6 hexagons (about 36 km², 90 in the study area) are used only to split Sydney for testing.

## Labels (what the model learns from)
- ${d.layer.name}: ${labels.long}.
- ${osmInLabel ? 'OpenStreetMap units are part of the label.' : 'OpenStreetMap public toilets are not labels or inputs, because they nearly copy the label. They are counted only afterwards, as existing toilets on the suggested list. The official map misses many toilets in shopping centres, stations and clubs.'}

## Inputs (45 columns, all public data)
- Census 2021 population inside the hexagon and within 250 m, 500 m and 1 km.
- OpenStreetMap shops, cafes and restaurants, bus stops and train stations, at the same distances.
- Park area and distance to the nearest park; walkable path length, pedestrian junctions and distance to a footpath.
- Sports grounds, playgrounds, beaches and surf clubs, at the same distances, with distance to the nearest one.
- The model never sees location (hexagon id, coordinates, council), SEIFA disadvantage, demographics or population projections. SEIFA is used only to report fairness.

## Training
- A random forest regressor: 300 decision trees, each grown on a random sample of hexagons and features, at least 20 hexagons per leaf. It predicts the expected count of ${many} a place like this usually has. Chance of at least one = 1 − e^(−prediction).
- 5-fold spatial cross-validation: the 90 resolution-6 blocks are split into 5 groups of 18. Each turn trains on 4 groups and predicts the 5th, so every hexagon's prediction comes from a model that never saw it or its surrounding area. Every number on the map is a held-out prediction.
- SHAP values give the top reasons ("drivers") behind each hexagon's prediction.
- The team tried 12 versions. The chosen one (V12) added sports grounds, playgrounds and beaches, the only change that beat seed noise (toilet PR-AUC 0.520 to 0.569). Tried and dropped: retraining on OpenStreetMap labels (29% too many toilets), a "good areas" model trained on the best-served blocks (41% too many), weighting the list by disadvantage (the model already predicts every SEIFA decile accurately), and 400 m coverage as a filter (kept as a map layer).

## How well it works (${d.layer.name.toLowerCase()}, held out)
- ${find.top100.x}/${find.top100.y} of the top 100 predicted hexagons really have a ${one}; random picks get about ${Math.round(find.random * 100)}. PR-AUC ${find.prAuc} vs ${find.random} for random.
- New growth suburbs it never trained on: ${growth.top100.x}/${growth.top100.y} real ${one} hexagons land in its top 100, against ${growth.randomTop100} for random.
${council ? `- Council-planned toilets: ${council.top10.x}/${council.top10.y} planned sites from 22 councils' strategies fall in the model's top 10%, against about ${council.random} for random.\n- Known misses: sports-field amenity blocks such as Ken Birdsey Park and Anthony Skarratt Reserve, where OpenStreetMap has no sports ground mapped.` : ''}
${d.layer.id === 'toilets' ? '- Predicted total 2,625 toilets vs 2,570 real; Poisson deviance 0.378 vs 0.719 for predicting the average everywhere.' : ''}

## The suggested list
- Missing = prediction − existing (${osmInLabel ? 'the label count' : 'the larger of the official count and OpenStreetMap public toilets'}), floored at 0.
- Ranked by missing alone, no disadvantage weighting; only spots missing at least 1 are listed. ${picks.poorest30.x} of ${picks.poorest30.y} suggested spots are in the poorest 30% of areas and ${picks.richest30.x} in the richest 30%.
- A suggestion means "places like this usually have one", not a site approval: land, access and servicing still need checking.

## Map modes
- today: existing Sydney.
- growth: 16 new growth suburbs (Oran Park, Marsden Park and others), scored with real features but never trained on.
- future: Bradfield / Aerotropolis and Leppington, not built yet. Their inputs are built from government plans: DPHI 2041 population projections spread over zoned land, planned Sydney Metro stations, zoned parks, and shop and bus densities per zone calibrated on 20 Sydney suburbs. Read the ranking, not the totals. A check on Oran Park found these plan-based inputs keep about half the real top 10. Bradfield Station is #1; the Bradfield City Centre Master Plan (Sept 2024, p64) marks amenities in Central Park beside it.`
}
