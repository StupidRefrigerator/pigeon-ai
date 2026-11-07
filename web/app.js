/* Buildless local comparison: one request, one geometry set, three model views. */
const versions = ['V1', 'V5', 'V6'];
const maps = {}, layers = {}, cells = {}, circles = {};
let summary, selectedHex, syncing = false;
const status = document.getElementById('status');
const button = document.getElementById('analyze');
const fixed = (n) => Number(n).toFixed(2);
const escapeHtml = (s) => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function gapColor(gap) {
  if (gap <= 0) return '#dfe7df';
  if (gap <= .25) return '#f7e3aa';
  if (gap <= .5) return '#e9b75b';
  if (gap < 1) return '#df873c';
  if (gap < 2) return '#c94c35';
  return '#842f37';
}
function style(feature, version) {
  const value = feature.properties.models[version];
  const selected = feature.properties.hex_id === selectedHex;
  return {fillColor: gapColor(value.gap), fillOpacity: .78,
    color: selected ? '#152f37' : value.candidate ? '#68352f' : '#fff',
    weight: selected ? 3 : value.candidate ? 1.5 : .45, opacity: 1};
}
function selectHex(properties) {
  const previous = selectedHex;
  selectedHex = properties.hex_id;
  for (const version of versions) {
    if (previous && cells[version][previous]) cells[version][previous].setStyle(style(cells[version][previous].feature, version));
    const layer = cells[version][selectedHex];
    layer.setStyle(style(layer.feature, version));
    layer.bringToFront();
  }
  document.getElementById('detail-title').textContent = properties.hex_id;
  document.getElementById('actual-detail').textContent = `Actual toilets: ${properties.actual_count} · same hexagon in all three models`;
  const content = document.getElementById('detail-content');
  content.className = 'detail-grid';
  content.innerHTML = versions.map(v => {
    const value = properties.models[v];
    const importance = summary.importance[v].slice(0, 3);
    return `<div class="detail-model"><h3>${v}</h3><div class="detail-numbers"><div><span>Predicted toilets</span><strong>${fixed(value.predicted_count)}</strong></div><div><span>Gap score</span><strong>${fixed(value.gap)}</strong></div></div><p class="candidate ${value.candidate ? 'yes' : ''}">Candidate: ${value.candidate ? 'Yes · gap ≥ 1' : 'No'}</p><p class="importance-label">Model-wide feature importance (not local drivers)</p>${importance.map(row => `<div class="importance-row"><span>${escapeHtml(row.feature.replaceAll('_', ' '))}</span><strong>${(row.importance * 100).toFixed(1)}%</strong></div>`).join('')}</div>`;
  }).join('');
}
function resetDetails() {
  selectedHex = null;
  document.getElementById('detail-title').textContent = 'Select a hexagon';
  document.getElementById('actual-detail').textContent = 'Click any coloured cell to compare all three predictions.';
  const content = document.getElementById('detail-content');
  content.className = 'empty-details';
  content.innerHTML = '<p>The same hexagon will be highlighted across all three maps.</p>';
}
async function request(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The request failed.');
  return data;
}
async function analyze(event) {
  event.preventDefault();
  if (!document.getElementById('search').reportValidity()) return;
  button.disabled = true;
  button.textContent = 'Analyzing…';
  status.className = '';
  status.textContent = 'Selecting hexagons and running the three saved models…';
  try {
    const params = new URLSearchParams({location: document.getElementById('location').value, radius: document.getElementById('radius').value});
    const data = await request(`/api/analyze?${params}`);
    resetDetails();
    for (const version of versions) {
      if (layers[version]) maps[version].removeLayer(layers[version]);
      if (circles[version]) maps[version].removeLayer(circles[version]);
      cells[version] = {};
      layers[version] = L.geoJSON(data.geojson, {
        style: feature => style(feature, version),
        onEachFeature: (feature, layer) => {
          cells[version][feature.properties.hex_id] = layer;
          const value = feature.properties.models[version];
          layer.bindTooltip(`Gap ${fixed(value.gap)} · actual ${feature.properties.actual_count}`);
          layer.on('click', () => selectHex(feature.properties));
        }
      }).addTo(maps[version]);
      circles[version] = L.circle(data.center, {radius: data.radius_km * 1000, color: '#32574b', weight: 1.5, dashArray: '5 5', fill: false, interactive: false}).addTo(maps[version]);
      const totals = data.totals[version];
      document.getElementById(`total-${version}`).innerHTML = `<span><strong>${totals.candidates}</strong> candidates</span><span><strong>${fixed(totals.predicted)}</strong> predicted toilets</span><span>Gap sum <strong>${fixed(totals.gap)}</strong></span>`;
    }
    syncing = true;
    for (const v of versions) maps[v].fitBounds(circles[v].getBounds(), {padding: [12, 12], animate: false});
    syncing = false;
    status.textContent = `${data.location} · ${data.radius_km} km · ${data.hexagons.toLocaleString()} hexagons · ${data.actual_total} actual toilets`;
  } catch (error) {
    status.className = 'error';
    status.textContent = error.message + (layers.V1 ? ' Previous maps remain visible.' : '');
  } finally {
    button.disabled = false;
    button.textContent = 'Analyze';
  }
}
async function init() {
  try {
    if (!window.L) throw new Error('Map library could not load. Check the web/vendor/leaflet files and reload.');
    for (const v of versions) {
      maps[v] = L.map(`map-${v}`, {preferCanvas: true, zoomControl: false, zoomAnimation: false, fadeAnimation: false}).setView([-33.8732, 151.2069], 12);
      L.control.zoom({position: 'topright'}).addTo(maps[v]);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, opacity: .7, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(maps[v]);
      maps[v].on('move', () => {
        if (syncing) return;
        syncing = true;
        for (const other of versions) if (other !== v) maps[other].setView(maps[v].getCenter(), maps[v].getZoom(), {animate: false});
        syncing = false;
      });
    }
    summary = await request('/api/summary');
    const options = document.createDocumentFragment();
    for (const place of summary.places) {const option = document.createElement('option'); option.value = place; options.appendChild(option);}
    document.getElementById('places').appendChild(options);
    button.disabled = false;
    status.textContent = 'Choose a place and radius, then analyze to compare the models.';
    document.getElementById('search').addEventListener('submit', analyze);
  } catch (error) {status.className = 'error'; status.textContent = error.message;}
}
init();
