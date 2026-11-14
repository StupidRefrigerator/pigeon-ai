/**
 * Plain-English definitions for every metric and technical term on the Tracking and Tests pages.
 * One sentence each, saying what the term means and what a good value looks like.
 * Shown by <Term> as a hover/focus tooltip; kept here so other pages can reuse them.
 */
export const DEFINITIONS = {
  hexagon:
    'Hexagon: one cell of the H3 grid at resolution 9, about 0.1 km² (roughly 350 m across); the model predicts a toilet count for each one.',
  prAuc:
    'PR-AUC: how early real toilet hexagons appear when every hexagon is ranked by the model; 1.0 is perfect and random guessing scores the share of hexagons with a toilet (0.118 across Sydney).',
  deviance:
    'Poisson deviance: the average difference between predicted and real toilet counts per hexagon, measured the standard way for counts; lower is better and 0 would be exact everywhere.',
  top100:
    'Top-100 hits: of the 100 hexagons the model ranks highest, how many really have a toilet; higher is better, and random guessing finds about 12.',
  top1000:
    'Top-1,000 hits: of the 1,000 hexagons the model ranks highest, how many really have a toilet; higher is better, and random guessing finds about 118.',
  council:
    "Council-planned sites: 42 future toilet sites taken from councils' own plans, which the model never trained on; good is many of them landing in the model's top 10%, where chance would put about 4.",
  predictedVsReal:
    'Predicted vs real: the model’s predicted toilets added up over every hexagon, next to the real count; close totals mean it is not over- or under-predicting overall.',
  chance:
    'Chance of a toilet: the model’s probability that a hexagon has at least one toilet, worked out from its predicted count; 80%+ means it looks strongly like places that have one.',
  toiletsMissing:
    'Toilets missing: predicted toilets minus the toilets already there (official map plus OpenStreetMap on the suggested list); 1 or more means the place is a whole toilet short of the Sydney average for similar places.',
  suggested:
    'Suggested list: every hexagon where the model expects at least one more toilet than exist, counting official-map and OpenStreetMap toilets; it is not capped at a fixed number.',
  officialMap:
    'Official map: the National Public Toilet Map (data.gov.au), the toilets the model learns from.',
  osm: 'OpenStreetMap: a volunteer-made world map; its public toilets catch some the official map misses, especially in new suburbs.',
  heldOut:
    'Held-out: scored only on hexagons the model did not see in training, so the score shows how it does on new places rather than how well it memorised.',
  crossValidation:
    'Five-fold spatial cross-validation: Sydney’s 90 blocks are split into 5 groups, and each turn trains on 4 groups and predicts the 5th, so every hexagon is predicted by a model that never saw its area.',
  seeds:
    'Mean of seeds 0–2: the model is trained three times from different random starts and the scores are averaged, so one lucky run cannot inflate them.',
  random:
    'Random baseline: what picking hexagons at random would score; a useful model beats it by a wide margin.',
  growthSuburbs:
    'Growth suburbs: 1,108 hexagons in new suburbs that were left out of the training data entirely, to test the model on places it has never seen.',
  seifa:
    'SEIFA decile: the ABS index of relative socio-economic disadvantage (IRSD), split into ten equal groups of hexagons; decile 1 is the most disadvantaged and 10 the least.',
  per10k:
    'Toilets per 10k residents: real toilets divided by estimated residents, times 10,000; higher means more toilets for the people living there.',
} as const satisfies Record<string, string>

export type TermId = keyof typeof DEFINITIONS
