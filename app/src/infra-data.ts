import type { References, Stats, Tracking } from './lib/data'
import type { LiveLayerId } from './infra'
import toiletsStats from './data/infra/toilets/stats.json'
import toiletsTracking from './data/infra/toilets/tracking.json'
import toiletsReferences from './data/infra/toilets/references.json'
import bubblersStats from './data/infra/bubblers/stats.json'
import bubblersTracking from './data/infra/bubblers/tracking.json'

/** Where the real units the model trains on come from. */
export interface Labels {
  /** The term in running text, capitalised, such as "Official map". */
  term: string
  /** Where a unit is recorded, completing "a toilet ...", such as "on the official map". */
  on: string
  /** The full name, for the definition. */
  long: string
  /** Listed first under References. */
  sources: { name: string; url: string }[]
}

/** Bundled JSON and facts for a live layer. `references` is present only when the layer has planning documents to cite. */
export interface LayerData {
  tracking: Tracking
  stats: Stats
  references?: References
  labels: Labels
  /** OpenStreetMap units are part of the label itself, instead of being counted on the suggested list after the model. */
  osmInLabel: boolean
  /** Poisson deviance of predicting the study-area average everywhere: the "mean everywhere" row of the layer's data/model metrics.csv. */
  meanDeviance: number
}

/** One entry per live layer: a layer without an entry here does not compile. */
export const LAYER_DATA: Record<LiveLayerId, LayerData> = {
  toilets: {
    tracking: toiletsTracking as Tracking,
    stats: toiletsStats as Stats,
    references: toiletsReferences,
    labels: {
      term: 'Official map',
      on: 'on the official map',
      long: 'National Public Toilet Map (data.gov.au)',
      sources: [{ name: 'National Public Toilet Map (data.gov.au)', url: 'https://data.gov.au/data/dataset/national-public-toilet-map' }],
    },
    osmInLabel: false,
    meanDeviance: 0.719,
  },
  bubblers: {
    tracking: bubblersTracking as Tracking,
    stats: bubblersStats as Stats,
    labels: {
      term: 'Council records',
      on: 'in council records or OpenStreetMap',
      long: 'water fountain records of five councils (Sydney, Parramatta, Fairfield, Northern Beaches and Penrith), plus OpenStreetMap fountains more than 50 m from any council one',
      sources: [
        { name: 'City of Sydney: drinking fountains', url: 'https://services1.arcgis.com/cNVyNtjGVZybOQWZ/arcgis/rest/services/Drinking_fountains/FeatureServer/0' },
        { name: 'City of Parramatta: drinking fountains', url: 'https://services6.arcgis.com/NrOjMi9LSYL3MUze/arcgis/rest/services/Drinking_Fountains/FeatureServer/0' },
        { name: 'Fairfield City Council: bubbler inspections (partial)', url: 'https://services9.arcgis.com/ptMeJSvCigyke2Tt/arcgis/rest/services/Bubbler_Inspection_Data_View_Layer/FeatureServer/0' },
        { name: 'Northern Beaches Council: bubblers', url: 'https://maps.northernbeaches.nsw.gov.au/arcgis/rest/services/Bubblers/MapServer/0' },
        { name: 'Penrith City Council: bubbler locations (partial)', url: 'https://services-ap1.arcgis.com/2ifYh4l3ar2sldJb/arcgis/rest/services/Bubbler_Locations/FeatureServer/0' },
      ],
    },
    osmInLabel: true,
    meanDeviance: 0.771,
  },
}
