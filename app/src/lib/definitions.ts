/**
 * Plain-English definitions for every metric and technical term on the Tracking and Tests pages.
 * One sentence each, saying what the term means and what a good value looks like.
 * Shown by <Term> as a hover/focus tooltip; kept here so other pages can reuse them.
 * Worded and numbered per layer: the unit comes from the registry, the figures from the layer's bundled data.
 */
import { capitalize, LIVE_LAYERS, type LiveLayer, type LiveLayerId } from '../infra'
import { LAYER_DATA } from '../infra-data'

function definitionsFor(layer: LiveLayer) {
  const { stats, tracking, labels, osmInLabel, meanDeviance } = LAYER_DATA[layer.id]
  const counted = osmInLabel ? labels.on : `${labels.on} plus OpenStreetMap on the suggested list`
  const { one, many } = layer.unit
  const fmt = (n: number) => n.toLocaleString('en-AU')
  return {
    hexagon: `Hexagon: one cell of the H3 grid at resolution 9, about 0.1 km² (roughly 350 m across); the model predicts a ${one} count for each one.`,
    prAuc: `PR-AUC: how early real ${one} hexagons appear when every hexagon is ranked by the model; 1.0 is perfect and random guessing scores the share of hexagons with a ${one} (${tracking.current.prAuc.random.toFixed(3)} across Sydney).`,
    deviance: `Poisson deviance: how far predicted ${one} counts are from real ones, on hexagons the model never saw; lower means it learned Sydney’s pattern better (predicting the average everywhere scores ${meanDeviance.toFixed(3)}), but it won’t reach 0 and shouldn’t, because the places it misses are partly the gaps we’re looking for.`,
    top100: `Top-100 hits: of the 100 hexagons the model ranks highest, how many really have a ${one}; higher is better, and random guessing finds about ${Math.round(stats.find.random * 100)}.`,
    top1000: `Top-1,000 hits: of the 1,000 hexagons the model ranks highest, how many really have a ${one}; higher is better, and random guessing finds about ${Math.round(stats.find.random * 1000)}.`,
    council: stats.council
      ? `Council-planned sites: ${stats.council.top10.y} future ${one} sites taken from councils' own plans, which the model never trained on; good is many of them landing in the model's top 10%, where chance would put about ${stats.council.random}.`
      : `Council-planned sites: future ${one} sites from councils' own plans, not collected for this layer.`,
    predictedVsReal: `Predicted vs real: the model’s predicted ${many} added up over every hexagon, next to the real count; close totals mean it is not over- or under-predicting overall.`,
    chance: `Chance of a ${one}: the model’s probability that a hexagon has at least one ${one}, worked out from its predicted count; 80%+ means it looks strongly like places that have one.`,
    missing: `${capitalize(many)} missing: predicted ${many} minus the ${many} already there (${counted}); 1 or more means the place is a whole ${one} short of the Sydney average for similar places.`,
    suggested: `Suggested list: every hexagon where the model expects at least one more ${one} than exist, counting ${many} ${osmInLabel ? labels.on : `${labels.on} and OpenStreetMap`}; it is not capped at a fixed number.`,
    officialMap: `${labels.term}: the ${labels.long}, the ${many} the model trains on.`,
    osm: `OpenStreetMap: a volunteer-made world map; ${osmInLabel ? `its ${many} fill in where councils keep no records` : `its public ${many} catch some the official map misses, especially in new suburbs`}.`,
    heldOut:
      'Held-out: scored only on hexagons the model did not see in training, so the score shows how it does on new places rather than how well it memorised.',
    crossValidation:
      'Five-fold spatial cross-validation: Sydney’s 90 blocks are split into 5 groups, and each turn trains on 4 groups and predicts the 5th, so every hexagon is predicted by a model that never saw its area.',
    seeds:
      'Mean of seeds 0–2: the model is trained three times from different random starts and the scores are averaged, so one lucky run cannot inflate them.',
    random: 'Random baseline: what picking hexagons at random would score; a useful model beats it by a wide margin.',
    growthSuburbs: `Growth suburbs: ${fmt(stats.growth.hexes)} hexagons in new suburbs that were left out of the training data entirely, to test the model on places it has never seen.`,
    seifa:
      'SEIFA decile: the ABS index of relative socio-economic disadvantage (IRSD), split into ten equal groups of hexagons; decile 1 is the most disadvantaged and 10 the least.',
    per10k: `${capitalize(many)} per 10k residents: real ${many} divided by estimated residents, times 10,000; higher means more ${many} for the people living there.`,
  } as const satisfies Record<string, string>
}

export type TermId = keyof ReturnType<typeof definitionsFor>

export const DEFINITIONS = Object.fromEntries(LIVE_LAYERS.map((l) => [l.id, definitionsFor(l)])) as Record<LiveLayerId, Record<TermId, string>>
