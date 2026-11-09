/* Client-side analysis of the committed held-out predictions. No server is needed. */
const CANDIDATE_THRESHOLD = 1;  // pigeon_ai.model.THRESHOLD: predicted - actual >= 1
const MODEL_LABELS = {
  V1: 'V1 — Baseline',
  V5: 'V5 — 1 km features',
  V6: 'V6 — Accessibility',
  latest: 'Latest — V5 + V6 (production)',
};

function parsePredictions(text) {
  const [header, ...lines] = text.trim().split('\n');
  const columns = header.trim().split(',');
  const versions = columns.slice(3);  // hex_id, toilet_count, fold, then one column per model
  const rows = lines.map(line => {
    const cells = line.trim().split(',');
    return {hexId: cells[0], actual: Number(cells[1]),
            predicted: Object.fromEntries(versions.map((v, i) => [v, Number(cells[3 + i])]))};
  });
  return {versions, rows};
}

function resolvePlace(query, places) {
  query = query.trim();
  const match = Object.keys(places).find(name => name.toLowerCase() === query.toLowerCase());
  if (match) return {name: match, center: places[match]};
  const parts = query.split(',').map(Number);
  if (parts.length === 2 && parts.every(Number.isFinite)) {
    const [lat, lng] = parts;
    if (lat >= -34.6 && lat <= -33.0 && lng >= 149.8 && lng <= 151.7)
      return {name: `${lat.toFixed(5)}, ${lng.toFixed(5)}`, center: [lat, lng]};
  }
  const similar = Object.keys(places).filter(name => name.toLowerCase().startsWith(query.toLowerCase().slice(0, 3))).slice(0, 3);
  throw new Error('Choose a Sydney suburb or listed landmark, or enter latitude, longitude.'
                  + (query && similar.length ? ` Try: ${similar.join(', ')}.` : ''));
}

function distanceKm([lat1, lng1], [lat2, lng2]) {
  const rad = Math.PI / 180;
  const a = Math.sin((lat2 - lat1) * rad / 2) ** 2
          + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin((lng2 - lng1) * rad / 2) ** 2;
  return 6371.0088 * 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, a))));
}

function analyzeArea(data, places, location, radiusKm) {
  const {name, center} = resolvePlace(location, places);
  if (!Number.isFinite(radiusKm) || radiusKm < 0.1 || radiusKm > 30) throw new Error('Radius must be between 0.1 and 30 km.');
  const selected = data.rows.filter(row => distanceKm(row.center, center) <= radiusKm);
  if (!selected.length) throw new Error('No study-area hexagons inside this circle. Try a larger radius or another Sydney location.');
  const totals = Object.fromEntries(data.versions.map(v => [v, {predicted: 0, gap: 0, candidates: 0}]));
  const features = selected.map(row => {
    const models = {};
    for (const v of data.versions) {
      const pred = row.predicted[v];
      const value = {predicted_count: pred, gap: Math.max(0, pred - row.actual), candidate: pred - row.actual >= CANDIDATE_THRESHOLD};
      models[v] = value;
      totals[v].predicted += pred;
      totals[v].gap += value.gap;
      totals[v].candidates += value.candidate;
    }
    return {type: 'Feature', geometry: {type: 'Polygon', coordinates: [row.boundary]},
            properties: {hex_id: row.hexId, actual_count: row.actual, models}};
  });
  return {location: name, center, radius_km: radiusKm, hexagons: selected.length,
          actual_total: selected.reduce((sum, row) => sum + row.actual, 0), totals,
          geojson: {type: 'FeatureCollection', features}};
}

function addGeometry(data, h3) {
  for (const row of data.rows) {
    row.center = h3.cellToLatLng(row.hexId);
    row.boundary = h3.cellToBoundary(row.hexId, true);  // [lng, lat], closed ring
  }
  return data;
}

if (typeof module !== 'undefined') module.exports = {parsePredictions, resolvePlace, analyzeArea, addGeometry, MODEL_LABELS};
