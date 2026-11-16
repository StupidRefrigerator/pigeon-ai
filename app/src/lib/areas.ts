/** The planned areas scored with none of a layer's units yet, keyed as in heatmap.json's future rows. Every layer scores the same areas. */
export const FUTURE_AREAS: Record<string, { name: string; short: string }> = {
  aerotropolis: { name: 'Bradfield (Aerotropolis)', short: 'the Aerotropolis' },
  leppington: { name: 'Leppington', short: 'Leppington' },
}

export const futureAreaList = () => Object.values(FUTURE_AREAS).map((a) => a.name).join(' and ')
