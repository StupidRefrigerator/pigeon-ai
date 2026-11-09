// Run with: node --test tests/analyze.test.js
const test = require('node:test');
const assert = require('node:assert');
const h3 = require('../web/vendor/h3-js/h3-js.umd.js');
const {parsePredictions, analyzeArea, addGeometry} = require('../web/analyze.js');

const NEAR = h3.latLngToCell(-33.8732, 151.2069, 9);  // Town Hall
const FAR = h3.latLngToCell(-33.8140, 151.0010, 9);   // Parramatta, about 17 km away
const places = {'Town Hall': [-33.8732, 151.2069]};
const data = addGeometry(parsePredictions(
  `hex_id,toilet_count,fold,V1,latest\n${NEAR},1,0,2.5,0.4\n${FAR},0,1,3.0,1.0\n`), h3);

test('returns the file predictions, gaps and candidates', () => {
  const result = analyzeArea(data, places, 'town hall', 2);
  assert.equal(result.hexagons, 1);
  assert.equal(result.actual_total, 1);
  const {models} = result.geojson.features[0].properties;
  assert.deepEqual(models.V1, {predicted_count: 2.5, gap: 1.5, candidate: true});
  assert.deepEqual(models.latest, {predicted_count: 0.4, gap: 0, candidate: false});
  assert.deepEqual(result.totals.V1, {predicted: 2.5, gap: 1.5, candidates: 1});
});

test('a larger radius includes the far hex', () => {
  const result = analyzeArea(data, places, 'Town Hall', 30);
  assert.equal(result.hexagons, 2);
  assert.equal(result.totals.V1.candidates, 2);
  assert.equal(result.totals.latest.candidates, 1);  // 1.0 predicted for an empty hex
});

test('versions come from the predictions columns', () => {
  assert.deepEqual(data.versions, ['V1', 'latest']);
});

test('rejects unknown places and bad radii', () => {
  assert.throws(() => analyzeArea(data, places, 'Nowhereville', 2), /Choose a Sydney suburb/);
  assert.throws(() => analyzeArea(data, places, 'Town Hall', 50), /Radius/);
});
