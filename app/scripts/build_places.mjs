// Write public/places.json, the suburb and landmark list behind the map's area search.
//
// Run from app/:  node scripts/build_places.mjs
//
// Reads ../data/reference/sydney_places.json (ABS suburbs plus six landmarks) and keeps the places
// with at least one map hexagon (public/heatmap.json) within 2 km, so every result lands on data.
// Output: {"places": [[name, lat, lng], ...]}, sorted by name, "(NSW)" dropped from the ABS names.
import { readFileSync, writeFileSync } from 'node:fs'
import { cellToLatLng } from 'h3-js'

const NEAR_KM = 2
const read = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url), 'utf8'))
const { places } = read('../../data/reference/sydney_places.json')
const heat = read('../public/heatmap.json')
const hexes = new Set([...heat.today.map((r) => r[0]), ...heat.growth.map((r) => r[0]), ...heat.future.map((r) => r[2])])
const centres = [...hexes].map((h) => cellToLatLng(h))

const rad = Math.PI / 180
function km(lat1, lng1, lat2, lng2) {
  const a = Math.sin(((lat2 - lat1) * rad) / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lng2 - lng1) * rad) / 2) ** 2
  return 6371.0088 * 2 * Math.asin(Math.sqrt(Math.min(1, a)))
}
const display = (n) => n.replace(' (NSW)', '').replace(' - NSW)', ')')

const rows = Object.entries(places)
  .filter(([, [lat, lng]]) => centres.some(([a, b]) => km(lat, lng, a, b) <= NEAR_KM))
  .map(([n, [lat, lng]]) => [display(n), +lat.toFixed(5), +lng.toFixed(5)])
  .sort((a, b) => a[0].localeCompare(b[0]))
const names = new Set(rows.map((r) => r[0]))
if (names.size !== rows.length) throw new Error('display names must stay unique')
for (const n of ['Parramatta', 'Sydney Opera House', 'Bradfield']) if (!names.has(n)) throw new Error(`missing ${n}`)
writeFileSync(new URL('../public/places.json', import.meta.url), JSON.stringify({ places: rows }))
console.log(`${rows.length} of ${Object.keys(places).length} places kept`)
