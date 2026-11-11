export interface Ratio {
  x: number
  y: number
  pct: number
}

export const fmtRatio = (r: Ratio) => `${r.x.toLocaleString()}/${r.y.toLocaleString()}`

/** src/data/stats.json: the four answers on the Tests page. */
export interface Stats {
  find: { hexes: number; toiletHexes: number; top100: Ratio; top1000: Ratio; prAuc: number; random: number }
  council: { top10: Ratio; random: number }
  growth: {
    hexes: number
    toiletHexes: number
    top100: Ratio
    randomTop100: number
    prAuc: number
    random: number
    predicted: number
    actual: number
  }
  reach: {
    poorest30: Ratio
    richest30: Ratio
    deciles: { decile: number; real: number; predicted: number; per10k: number }[]
  }
}

export interface Version {
  id: string
  description: string
  hexes: number
  features: number
  deviance: number | null
  prAuc: number | null
  top100: number | null
  status: 'done' | 'pending' | 'current'
}

/** src/data/tracking.json: version history and the current model's headline. */
export interface Tracking {
  versions: Version[]
  current: {
    id: string
    prAuc: { value: number; was: number; random: number }
    deviance: { value: number; was: number }
    top1000: Ratio
    council: Ratio
    predictedTotal: number
    actualTotal: number
    picks: { listed: number; osmAlready: Ratio; nearPlanned: Ratio; poorest30: Ratio; richest30: Ratio }
  }
}

/** public/heatmap.json, fetched by the Tracking-page map. Drivers are "featIndex:value" pairs joined by commas. */
export interface HeatmapData {
  feats: string[]
  places: string[]
  /** hex, real toilets, predicted, chance of ≥1, drivers, nearest place */
  today: [string, number, number, number, string, number][]
  /** hex, rank, gap after counting OSM toilets, OSM public toilets in the hex */
  recs: [string, number, number, number][]
  /** hex, real toilets, predicted, chance of ≥1, nearest place */
  growth: [string, number, number, number, number][]
  /** area, rank, hex, predicted, chance of ≥1, zone, nearest station, metres to it, drivers */
  future: [string, number, string, number, number, string, string, number, string][]
}
