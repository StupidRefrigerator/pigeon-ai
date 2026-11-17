import { createContext, useContext } from 'react'
import type { LiveLayer } from './infra'

const LayerContext = createContext<LiveLayer | null>(null)

/** Provided once by the /app shell, from the validated `?layer=` search param. */
export const LayerProvider = LayerContext.Provider

/** The layer the app is showing. Pages and components read it here instead of assuming toilets. */
export function useLayer(): LiveLayer {
  const layer = useContext(LayerContext)
  if (!layer) throw new Error('useLayer needs a LayerProvider above it')
  return layer
}
