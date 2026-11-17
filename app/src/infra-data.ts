import type { References, Stats, Tracking } from './lib/data'
import type { LiveLayerId } from './infra'
import toiletsStats from './data/infra/toilets/stats.json'
import toiletsTracking from './data/infra/toilets/tracking.json'
import toiletsReferences from './data/infra/toilets/references.json'

/** Bundled JSON for a live layer. `references` is present only when the layer has planning documents to cite. */
export interface LayerData {
  tracking: Tracking
  stats: Stats
  references?: References
  /** The authoritative dataset the model trains on, listed first under References. */
  officialMap: { name: string; url: string }
}

/** One entry per live layer: a layer without an entry here does not compile. */
export const LAYER_DATA: Record<LiveLayerId, LayerData> = {
  toilets: {
    tracking: toiletsTracking as Tracking,
    stats: toiletsStats as Stats,
    references: toiletsReferences,
    officialMap: { name: 'National Public Toilet Map (data.gov.au)', url: 'https://data.gov.au/data/dataset/national-public-toilet-map' },
  },
}
