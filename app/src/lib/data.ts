export interface Ratio {
  x: number
  y: number
  pct: number
}

export interface Stats {
  model: string
  headline: {
    hexes: number
    toilets: number
    toiletHexes: number
    prAuc: { value: number; random: number }
    topN: (Ratio & { label: string })[]
    deviance: number
    predictedTotal: number
    actualTotal: number
    predictedTotalPctOfActual: number
    candidates: number
  }
  validity: { n: number; rows: (Ratio & { label: string })[]; note: string }
  growth: {
    hexes: number
    suburbs: number
    actual: number
    predicted: number
    toiletHexes: number
    top100: Ratio
    prAuc: { value: number; random: number }
    perSuburb: { suburb: string; hexes: number; actual: number; pred: number }[]
    note: string
  }
  bradfield: {
    label: string
    scenario: string
    todayTotal: number
    midTotal: number
    hexesGe1: number
    maxHex: number
    top: { rank: number; zone: string; station: string; stationM: number; pred: number; drivers: string }[]
    oranProxy: {
      overlap: { real: number; proxy: number; of: number }
      toiletHexesInTop10: { real: number; proxy: number; of: number }
    }
  }
  plans: {
    rows: PlanRow[]
    fairest: PlanRow
    reverse: { candidatesNear: Ratio; chance: Ratio }
    sources: string
    misses: string
  }
  seifa: {
    toilets_per_10k_decile_1: number
    toilets_per_10k_decile_10: number
    real_over_pred_min: number
    real_over_pred_max: number
    note: string
  }
  newAreaTests: { test: string; where: string; real_data: string; shows: string; result: string }[]
}

export interface PlanRow {
  label: string
  n: number
  top10: Ratio
  top25: Ratio
  candidateNear: Ratio
  medianPct: number
}
