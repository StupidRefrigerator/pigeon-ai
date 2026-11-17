export interface Ratio {
  x: number
  y: number
  pct: number
}

export const fmtRatio = (r: Ratio) => `${r.x.toLocaleString()}/${r.y.toLocaleString()}`

/** src/data/infra/<layer>/stats.json: the answers on the Tests page. `toiletHexes` counts hexagons with at least one unit of the layer. */
export interface Stats {
  find: { hexes: number; toiletHexes: number; top100: Ratio; top1000: Ratio; prAuc: number; random: number }
  /** Present only for a layer with council-planned sites to test against. */
  council?: { top10: Ratio; random: number }
  growth: {
    hexes: number
    toiletHexes: number
    top100: Ratio
    randomTop100: number
    prAuc: number
    random: number
    predicted: number
    actual: number
    /** The same test with OpenStreetMap units counted as real too; absent when the label already counts them. */
    withOsm?: { toiletHexes: number; top100: Ratio; prAuc: number; random: number; actual: number }
  }
  reach: {
    listed: number
    noSeifa: number
    poorest30: Ratio
    richest30: Ratio
    deciles: { decile: number; real: number; predicted: number; per10k: number }[]
  }
}

/** src/data/infra/<layer>/references.json: the planning documents behind the layer's planned sites. */
export interface References {
  councilSites: number
  councilDocs: { council: string; document: string; url: string; sites: number }[]
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

/** src/data/infra/<layer>/tracking.json: version history and the current model's headline. `was` is the previous version, when there is one. */
/** Councils whose records hold far fewer units than the model predicts, so its predictions there are less checked. */
export interface Undercount {
  councils: string[]
  recorded: number
  predicted: number
  /** Hexagons on the suggested list inside those councils. */
  listed: number
}

export interface Tracking {
  undercount?: Undercount
  versions: Version[]
  current: {
    id: string
    prAuc: { value: number; was?: number; random: number }
    deviance: { value: number; was?: number }
    top1000: Ratio
    council?: Ratio
    predictedTotal: number
    actualTotal: number
    /** The suggested list: every hexagon where the model expects at least one more unit than exist. */
    picks: { listed: number; alreadyOne: Ratio; nearPlanned?: Ratio; poorest30: Ratio; richest30: Ratio; noSeifa: number }
  }
}

/** public/infra/<layer>/heatmap.json, fetched by the Tracking-page map. Drivers are "featIndex:value" pairs joined by commas. */
export interface HeatmapData {
  feats: string[]
  places: string[]
  /** hex, real units, predicted, chance of ≥1, drivers, nearest place */
  today: [string, number, number, number, string, number][]
  /** hex, rank, gap after counting OSM units, OSM units in the hex */
  recs: [string, number, number, number][]
  /** hex, real units, predicted, chance of ≥1, nearest place */
  growth: [string, number, number, number, number][]
  /** area, rank, hex, predicted, chance of ≥1, zone, nearest station, metres to it, drivers */
  future: [string, number, string, number, number, string, string, number, string][]
}
