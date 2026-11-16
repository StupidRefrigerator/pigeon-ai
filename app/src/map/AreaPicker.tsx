import { useEffect, useId, useState, type KeyboardEvent } from 'react'
import { cellToLatLng } from 'h3-js'
import { distanceKm, parseLatLng, RADII_KM, searchPlaces, type AreaSummary, type Place } from './area'
import { useLayer } from '../layer'
import type { Cell, Mode } from './cells'

interface Props {
  mode: Mode
  area: Place | null
  radius: number
  summary: AreaSummary | null
  selectedHex: string | null
  onPick: (place: Place) => void
  onRadius: (km: number) => void
  onClear: () => void
  onSpot: (cell: Cell) => void
}

const one = (x: number) => (Math.round(x * 10) / 10).toLocaleString()
const EMPTY: Record<Mode, string> = {
  today: 'No mapped hexagons inside this circle. Try a bigger radius.',
  growth: 'No growth suburb hexagons inside this circle. Try a bigger radius or another place.',
  future: 'No future area hexagons inside this circle. Try a bigger radius or another place.',
}
const away = ([, lat, lng]: Place, hex: string) => {
  const [hlat, hlng] = cellToLatLng(hex)
  return `${one(distanceKm(lat, lng, hlat, hlng))} km`
}

export function AreaPicker({ mode, area, radius, summary, selectedHex, onPick, onRadius, onClear, onSpot }: Props) {
  const id = useId()
  const { unit } = useLayer()
  const [places, setPlaces] = useState<Place[]>([])
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [miss, setMiss] = useState(false)

  useEffect(() => {
    let live = true
    fetch('/places.json')
      .then((r) => (r.ok ? (r.json() as Promise<{ places: Place[] }>) : Promise.reject()))
      .then((d) => live && setPlaces(d.places))
      .catch(() => {
        /* search still takes "lat, lng" without the list */
      })
    return () => {
      live = false
    }
  }, [])

  const point = parseLatLng(query)
  const options = point ? [point] : searchPlaces(places, query)
  const showList = open && query.trim() !== '' && query !== area?.[0]

  const pick = (p: Place) => {
    setQuery(p[0])
    setOpen(false)
    setMiss(false)
    onPick(p)
  }
  const clear = () => {
    setQuery('')
    setMiss(false)
    onClear()
  }
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      setOpen(true)
      setActive((a) => (options.length ? (a + (e.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length : 0))
    } else if (e.key === 'Enter') {
      const p = options[active] ?? options[0]
      if (p) pick(p)
      else if (query.trim()) setMiss(true)
    } else if (e.key === 'Escape') {
      e.stopPropagation()
      setOpen(false)
    }
  }

  return (
    <section className="area slab" aria-label="Pick an area">
      <div className="area-search">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="6.5" />
          <path d="m16 16 4.5 4.5" />
        </svg>
        <input
          role="combobox"
          aria-label="Suburb, landmark, or latitude and longitude"
          aria-expanded={showList}
          aria-controls={`${id}-list`}
          aria-activedescendant={showList && options[active] ? `${id}-${active}` : undefined}
          aria-autocomplete="list"
          placeholder="Suburb, landmark or lat, lng"
          value={query}
          spellCheck={false}
          autoComplete="off"
          onChange={(e) => {
            setQuery(e.target.value)
            setActive(0)
            setOpen(true)
            setMiss(false)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onKey}
        />
        {(area || query) && (
          <button className="x" aria-label="Clear the area and show all of Sydney" onClick={clear}>
            ×
          </button>
        )}
        {showList && options.length > 0 && (
          <ul className="area-list" role="listbox" id={`${id}-list`}>
            {options.map((p, i) => (
              <li
                key={p[0]}
                id={`${id}-${i}`}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => {
                  e.preventDefault()
                  pick(p)
                }}
                onMouseEnter={() => setActive(i)}
              >
                {p[0]}
              </li>
            ))}
          </ul>
        )}
      </div>
      {miss && (
        <p className="area-miss" role="alert">
          No Sydney suburb or landmark by that name. Try another, or type “-33.81, 151.00”.
        </p>
      )}

      <div className="area-radius" role="radiogroup" aria-label="Radius">
        {RADII_KM.map((km) => (
          <button key={km} role="radio" aria-checked={radius === km} onClick={() => onRadius(km)}>
            {km} km
          </button>
        ))}
      </div>

      {area && summary && (
        <div className="area-sum">
          <h2>Selected area</h2>
          <p className="area-sub">
            {radius} km around {area[0]}
          </p>
          {summary.hexes === 0 ? (
            <p className="area-note">{EMPTY[mode]}</p>
          ) : (
            <>
              <div className="nums">
                <div>
                  <b>{summary.hexes.toLocaleString()}</b>
                  <span>hexagons</span>
                </div>
                <div>
                  <b>{summary.today.toLocaleString()}</b>
                  <span>{unit.many} today</span>
                </div>
                <div>
                  <b>{one(summary.predicted)}</b>
                  <span>{unit.many} predicted</span>
                </div>
              </div>
              {summary.spots.length ? (
                <>
                  <h3>Suggested places inside</h3>
                  <ol className="area-spots">
                    {summary.spots.map((c) => (
                      <li key={c.hex}>
                        <button aria-current={c.hex === selectedHex ? 'true' : undefined} onClick={() => onSpot(c)}>
                          <span className="rank">{c.spot}</span>
                          <span className="name">
                            {c.name} <small>{away(area, c.hex)}</small>
                          </span>
                          <span className="miss">{one(c.gap)} missing</span>
                        </button>
                      </li>
                    ))}
                  </ol>
                </>
              ) : (
                <p className="area-note">
                  {mode === 'growth' ? 'Growth suburbs have no suggested places. Click a hexagon to see its numbers.' : 'No suggested places inside this circle.'}
                </p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}
