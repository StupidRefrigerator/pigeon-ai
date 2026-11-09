/** A hex is a candidate when the model predicts at least this many more toilets than exist. */
export const CANDIDATE_GAP = 1

export function gapOf(predicted: number, actual: number): number {
  return Math.max(0, predicted - actual)
}

export function isCandidate(predicted: number, actual: number): boolean {
  return predicted - actual >= CANDIDATE_GAP
}

/** Each bin covers gap < max (the first covers gap = 0), so a gap of exactly 1 lands in the candidate bin. */
export const GAP_BINS = [
  { max: 0, color: '#e8ecef', label: 'No gap' },
  { max: 0.25, color: '#fde3b0', label: '0 – 0.25' },
  { max: 0.5, color: '#f9b872', label: '0.25 – 0.5' },
  { max: 1, color: '#ee7b3c', label: '0.5 – 1' },
  { max: Infinity, color: '#b8321f', label: '1 or more (candidate)' },
] as const

export function gapColor(gap: number): string {
  if (gap <= 0) return GAP_BINS[0].color
  return (GAP_BINS.find((b) => gap < b.max) ?? GAP_BINS[4]).color
}

export interface StudyHexes {
  ids: string[]
  actual: number[]
  pred: number[]
}

export function candidateIds(h: StudyHexes): string[] {
  return h.ids.filter((_, i) => isCandidate(h.pred[i]!, h.actual[i]!))
}
