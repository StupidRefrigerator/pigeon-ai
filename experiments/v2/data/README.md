# PIGEON-AI v2: new OSM input features (sports, playgrounds, beaches, OSM toilets)

Built 2026-11-09/10 for the H3 resolution-9 hex model. No model was trained here.

## Files

| File | Rows | Key | What |
|---|---|---|---|
| `new_features_study.csv` | 16,228 | `hex_id` | New features for the study hexes (same hexes as `data/processed/sydney_extended_features.csv`) |
| `new_features_growth.csv` | 17,336 | `hex_id` | New features for the growth set (same hexes as `sydney_growth_features.csv`: study + 1,108 growth-suburb hexes) |
| `new_features_future.csv` | 1,014 | `hex_id` | Current-OSM features for future areas: 838 Aerotropolis/Bradfield hexes (unique `hex_id` in `experiments/future/aero_features.csv`) + 176 Leppington hexes (`leppington_features.csv`). Extra column `area` |
| `new_features_future_planned.csv` | 3,042 | `scenario`, `hex_id` | 1,014 future hexes × 3 scenarios (`current_osm`, `planned_re1`, `planned_re1_enz`), plus `area` |
| `osm_toilets.csv` | 2,462 | one row per OSM toilet | `lat`, `lng`, `access`, `fee`, `name`, `operator`, `osm_type`, `osm_id`, `hex_id`, `is_public`, `is_public_tagged`, `is_private` |
| `spot_checks.csv` | 5 | place | Five spot-check places (see below) |
| `re1_calibration.csv` | 11 | suburb | RE1 calibration per established suburb + pooled row |
| `checks.json` | – | – | Layer sizes, toilet access breakdown, OSM-vs-official comparison, Pearson and Spearman correlations |
| `planned_checks.json` | – | – | Calibration rates, RE1 parcel counts, scenario means |
| `run_features.log`, `planned.log` | – | – | Console output of the final runs |

Every hex has a value in every column (no nulls). 436 Leppington hexes also appear in the growth set. Their current-OSM values match in both files because the same code computes them.

Scripts are in `scripts/`. Run them with `/tmp/pigeon-env/bin/python`, from `scripts/`:
1. `python -I fetch_osm.py` (also `--reverse`, `--fine`, `--slsc`): downloads and caches the Overpass data.
2. `python run_features.py`: writes the three `new_features_*.csv` files, `osm_toilets.csv` and `checks.json`.
3. `python planned.py`: writes `new_features_future_planned.csv`, `re1_calibration.csv` and `planned_checks.json`.
4. `python spot_checks.py`: writes `spot_checks.csv`.

## Sources and query dates

- **OpenStreetMap via the Overpass API.** Queried 2026-11-09 between 12:13 and 15:07 UTC. Per-tile endpoint, element count and OSM data timestamp are in `downloads/fetch_log.json`.
  - Bbox: 150.4939, -34.1406, 151.3624, -33.5211 (W, S, E, N). This is the EPSG:7856 bounds of all 17,914 study/growth/future hex polygons, plus a 1.5 km margin, converted back to lon/lat.
  - Tiling: a 4×3 grid. Tiles that failed were split 2×2, and the most stubborn ones 2×2 again. That gives 39 tile files covering the bbox exactly (uncovered area 3e-15 deg²) and 19,753 elements before de-duplication. Elements on tile edges are de-duplicated by (type, id).
  - Endpoints: 25 responses from overpass-api.de, 8 from overpass.kumi.systems and 7 from overpass.private.coffee.
  - Failures along the way: the first fetch run was killed at its 30-minute limit after 7 tiles. After that, all three servers returned repeated HTTP 502/504 errors ("server is at capacity"). Each failure rotated to the next endpoint, with backoff and restarts.
  - **Data freshness varies by tile.** overpass-api.de tiles are current (2026-11-09). Mirror tiles have older snapshots: 0_2, 1_0, 2_0, 2_1_10, 2_2_01, 2_2_11, 3_0_00, 3_0_10, 3_0_11, 3_1_10_01, 3_1_10_10, 3_2_01_01, 3_2_01_10 and 3_2_11 range from 2026-05-31 to 2026-07-28. Edits made in OSM since then are missing in those tiles.
  - Query per tile: `nwr` with `leisure~pitch|sports_centre|stadium|track|golf_course|playground|beach_resort`, `natural=beach`, `emergency~lifeguard|lifeguard_base|lifeguard_tower`, `club~surf|lifesaving` (case-insensitive), `amenity~lifeguard|surf_life_saving_club`, and `amenity=toilets`, with `out tags geom`.
  - Tile variations: the first 7 whole tiles and the 2_1_* subtiles also included `name~"surf life ?saving"`. That regex made dense tiles too slow, so later tiles used `sport~surf|lifesaving` instead. To keep surf-club coverage even, one extra query, `name~"surf life ?saving|SLSC"`, ran over the coastal strip east of 151.10° (`downloads/overpass_slsc_names.json`, 54 elements).
- **NSW Principal Planning zoning (Land Zoning layer 19).** These are the GeoJSON files already downloaded by the earlier future-areas work in `/tmp/pigeon-eval/future/downloads/`, copied unchanged to `downloads/zoning/`:
  - `arcgis_zoning_aero_*`;
  - `arcgis_zoning_leppington_*`;
  - 20 × `arcgis_zoning_cal_*` (bboxes of the calibration suburbs);
  - `arcgis_sal_d85ccc8971ed.geojson` (ABS 2021 suburb polygons).
- **Nominatim** (2026-11-10), only to confirm where the two sports parks are (`downloads/nominatim/`):
  - Ken Birdsey Park is OSM relation 21918715 in **Schofields** at -33.70005, 150.89201, not Oakhurst;
  - Anthony Skarratt Reserve is only a park *node* (9057873122) in Box Hill.

## Method (matches `src/pigeon_ai/osm.py`)

- Hexes are H3 res-9 polygons from `h3.cell_to_boundary`, projected to **EPSG:7856**. Buffers are circles around the hex centroid.
- **Counts**:
  - `<x>_inside` counts features whose representative point lies within the hex polygon;
  - `<x>_<r>m` counts features whose representative point intersects a centroid circle of radius r (geopandas `buffer`, 16 segments per quadrant);
  - representative points are taken in WGS84 and then projected, as in `osm.py`;
  - nodes count as their own point; ways and multipolygon relations are rebuilt as polygons, or lines for unclosed ways such as running tracks.
- **Areas**: the area of the hex, or of a 500 m centroid circle, that intersects the *union* of the polygons. The union stops nested features, such as a pitch inside a stadium, from counting twice. Circles use `shapely.buffer` with 8 segments per quadrant, the same as the park-area features.
- **Distances**: the distance from the hex centroid to the nearest feature geometry. It is 0 when the centroid is inside the polygon, the same as `distance_nearest_park_m`. The search covers every feature in the bbox.

## Column definitions

| Column | Definition |
|---|---|
| `sports_inside`, `sports_250m`, `sports_500m`, `sports_1000m` | Count of `leisure` = `pitch`, `sports_centre`, `stadium` or `track` (12,871 features: 12,048 pitches, 431 tracks, 352 sports centres, 40 stadiums) |
| `sports_area_inside_m2`, `sports_area_500m_m2` | Area (m²) of the union of sports polygons in the hex or the 500 m circle. Points and lines add no area |
| `distance_nearest_sports_m` | m from hex centroid to the nearest sports feature |
| `playground_inside`, `playground_250m`, `playground_500m`, `playground_1000m` | Count of `leisure=playground` (3,575: 2,680 polygons, 895 nodes) |
| `distance_nearest_playground_m` | m from hex centroid to the nearest playground |
| `beach_inside`, `beach_250m`, `beach_500m`, `beach_1000m` | Count of beach features: `natural=beach` (322) + surf lifesaving clubs and lifeguard posts (63). `leisure=beach_resort` returned 0 features. The total is 385 |
| `distance_nearest_beach_m` | m from hex centroid to the nearest beach feature |
| `osm_toilets_public` | OSM `amenity=toilets` in the hex (H3 cell of the representative point, as `geography.add_toilet_counts` does) whose `access` is yes, permissive, public or missing |
| `osm_toilets_public_tagged` | Same, but `access` explicitly yes, permissive or public |
| `osm_toilets_private` | `access` is customers, private or no |
| `scenario` (planned file) | `current_osm`, `planned_re1` or `planned_re1_enz` (see below) |
| `area` (future files) | `aerotropolis` or `leppington` |

## Spot checks (`spot_checks.csv`)

| Place | Hex (set) | Official toilets | Sports in / 500 m | Sports area 500 m (m²) | Playground in / 500 m | Beach in / 500 m | Nearest sports / playground / beach (m) | OSM public toilets in hex |
|---|---|---|---|---|---|---|---|---|
| Ken Birdsey Park, Schofields (BL01 coord) | 89be085a827ffff (growth) | – | 0 / 4 | 6,650 | 0 / 0 | 0 / 0 | 387 / 636 / 12,720 | 0 |
| Anthony Skarratt Reserve, Box Hill (TH01) | 89be0858cd3ffff (growth) | – | 0 / 0 | 0 | 0 / 0 | 0 / 0 | 1,137 / 1,434 / 10,774 | 0 |
| Bondi Beach | 89be0e37307ffff (study) | 1 | 1 / 2 | 1,473 | 0 / 2 | 2 / 3 | 149 / 293 / 0 | 0 |
| Centennial Park playground (Ian Potter Wild Play Garden) | 89be0e34637ffff (**in no set**; computed directly) | – | 0 / 5 | 22,441 | 1 / 1 | 0 / 0 | 306 / 50 / 2,621 | 2 |
| Sydney Olympic Park (Accor Stadium) | 89be0e26c13ffff (study) | 0 | 3 / 34 | 146,854 | 0 / 2 | 0 / 0 | 0 / 322 / 1,940 | 0 |

What the spot checks show:
- **The new features do not fix the two misses at council-planned sports fields.**
  - At Ken Birdsey Park, OSM maps the park boundary but no pitch: the nearest pitch is 564 m from the site point. The 4 sports features within 500 m belong to neighbouring grounds.
  - Anthony Skarratt Reserve is a node with no pitch within 1.3 km.
  - Both sites have zero sports and zero playgrounds in their hex. Better OSM mapping, or council open-space data, would be needed to flag them.
- Bondi, Centennial Park and Olympic Park behave as expected.
  - Bondi: beach distance 0, the beach and two surf clubs fall in the hex.
  - Centennial Park: the playground is in the hex, and there are 2 OSM public toilets.
  - Olympic Park: 34 sports features and 14.7 ha of sports land within 500 m.
- The Centennial Park playground hex is not in the study grid. Only 2 of its 6 neighbours are in it, so the study area excludes most of the parkland.
- The Olympic Park hex has 0 official toilets and 0 OSM toilets. The 4 OSM toilets within 300 m of the stadium point are in neighbouring hexes.

## OSM toilets vs the official National Public Toilet Map (`toilet_count`)

- **All OSM toilets in the bbox: 2,462.**
  - Public: 2,291 (`access` missing 1,692, yes 565, permissive 34).
  - Explicitly public-tagged: 599.
  - Private: 147 (customers 82, private 62, no 3).
  - Other access values, counted in neither group: 24 (permit 12, students 7, centralkey 3, unknown 2).
- Of the 2,462, 2,032 fall in a study, growth or future hex and 2,003 in a study hex.
- **Study hexes (16,228):**

| | Official (`toilet_count`) | OSM public | OSM public, explicitly tagged |
|---|---|---|---|
| Total toilets | 2,570 | 1,862 | 475 |
| Hexes with ≥ 1 | 1,911 | 1,170 | – |

- Overlap between OSM public toilets and official counts in study hexes:
  - Hexes with OSM public > 0 **and `toilet_count == 0`: 272**. With explicit public tagging only: 55.
  - Hexes with official > 0 and OSM public = 0: 1,013.
  - Hexes with both: 898.
- In study hexes there are 120 OSM private toilets.

## Correlation with `toilet_count` (study hexes, n = 16,228)

| Feature | Pearson | Spearman |
|---|---|---|
| sports_inside | 0.209 | 0.295 |
| sports_250m | 0.216 | 0.292 |
| sports_500m | 0.180 | 0.246 |
| sports_1000m | 0.160 | 0.216 |
| sports_area_inside_m2 | 0.234 | 0.304 |
| sports_area_500m_m2 | 0.168 | 0.243 |
| playground_inside | 0.216 | 0.248 |
| playground_250m | 0.216 | 0.243 |
| playground_500m | 0.182 | 0.222 |
| playground_1000m | 0.183 | 0.217 |
| beach_inside | 0.088 | 0.101 |
| beach_250m | 0.093 | 0.106 |
| beach_500m | 0.080 | 0.090 |
| beach_1000m | 0.085 | 0.093 |
| distance_nearest_beach_m | -0.123 | -0.154 |
| distance_nearest_sports_m | -0.185 | -0.290 |
| distance_nearest_playground_m | -0.163 | -0.272 |
| osm_toilets_public | 0.472 | 0.569 |
| osm_toilets_public_tagged | 0.329 | 0.360 |
| osm_toilets_private | 0.109 | 0.089 |

`osm_toilets_*` largely duplicate the label. Use them for evaluation or label repair, **not** as model inputs, or the model learns to copy the label.

## Planned scenario for the future areas (`new_features_future_planned.csv`)

Today's OSM in Aerotropolis and Leppington mostly shows farmland. The planned scenarios fill undeveloped public-recreation land with sports and playground features. They use the rates measured on RE1 land in established suburbs.

**Calibration (`re1_calibration.csv`).**
- The 10 established suburbs are the ones used by `experiments/future/calibrate.py`: Parramatta, Penrith, Liverpool, Campbelltown, Blacktown, Castle Hill, Bankstown, Hornsby, Chatswood and Burwood.
- RE1 land is the union of RE1 zone polygons, clipped to each ABS suburb polygon: 947.6 ha in total.
- Pooled rates (ratio of sums):
  - **pitch share of RE1 area 6.8%** (64.8 ha);
  - **all-sports share 8.0%** (76.0 ha; this rate fills `sports_area_*`);
  - **sports features 0.253 per ha** (240);
  - **playgrounds 0.170 per ha** (161, i.e. one per 5.9 ha).
- Rates vary a lot by suburb: pitch share runs from 0.9% (Burwood) to 23% (Chatswood), playgrounds from 0.04 to 0.66 per ha. Hornsby's RE1 is mostly bushland, with a pitch share of 1.5%.

**Scenarios.**
- `current_osm`: the same values as `new_features_future.csv`.
- `planned_re1`: uses RE1 parcels (contiguous dissolved RE1 polygons from the Aerotropolis and Leppington zoning files) within 1,050 m of any future hex centroid.
  - "Developed" parcels contain an OSM sports or playground point already: 15 parcels, 71.5 ha. They keep their OSM values unchanged.
  - The other 97 parcels (285.2 ha) are treated as not yet built:
    - counts get expected values of rate × area of (undeveloped RE1 ∩ hex or circle) added to today's OSM counts, so planned counts are **fractional**;
    - `sports_area_*` gets 8.0% × the same area added;
    - distances become the minimum of today's distance and the distance to the nearest undeveloped RE1 parcel large enough to expect ≥ 0.5 of a feature: ≥ 1.98 ha for sports, ≥ 2.94 ha for playgrounds.
- `planned_re1_enz`: the same, but the Aerotropolis SEPP **ENZ** zone (Environment and Recreation) is also treated as RE1.
  - Undeveloped land rises to 1,624.4 ha.
  - This is an upper bound: much ENZ is riparian corridor (South Creek, Wianamatta) that will not get pitches.
  - Leppington has no ENZ near it, so its values match `planned_re1`.

Scenario means (`sports_500m` / `playground_500m` / nearest sports m / nearest playground m):

| Area | current_osm | planned_re1 | planned_re1_enz |
|---|---|---|---|
| Aerotropolis (838) | 0.11 / 0.03 / 1,839 / 2,571 | 0.22 / 0.10 / 1,570 / 1,915 | 2.24 / 1.46 / 514 / 544 |
| Leppington (176) | 0.59 / 0.12 / 1,010 / 1,254 | 1.90 / 1.00 / 404 / 536 | 1.90 / 1.00 / 404 / 536 |

Aerotropolis gains little under `planned_re1` because its zoning designates open space mostly as ENZ, not RE1.

Beach features are not changed in any scenario: there is no planned beach.

## Assumptions and caveats

1. **Golf is excluded** from `sports_*`. `leisure=golf_course` was downloaded (73 features) but is not used: golf courses are large, have members' clubhouses and would dominate `sports_area`.
2. **The sports set includes `track`** (431 features). These include running tracks and some horse or motor racing tracks.
   - Unclosed track ways (69 line features in total, sports layer) count by their representative point and add no area.
   - Pitches inside a stadium or sports centre count separately in the counts, but the area union counts their land once.
3. **Beaches include harbour, bay and river beaches** tagged `natural=beach`, as well as ocean beaches.
   - Surf clubs are `emergency=lifeguard*`, `club~surf|lifesaving`, `amenity=lifeguard|surf_life_saving_club`, `sport~life_saving`, or a name containing "surf life saving"/"SLSC".
   - The name rule drops bus stops, defibrillators, car parks and toilets named after a club.
   - A beach polygon and its surf club both count, so a surf beach typically scores 2–3.
4. **Toilet access groups:**
   - `public` (yes, permissive, missing) is mutually exclusive with `private` (customers, private, no);
   - the non-standard `access=public` counts as yes, though no OSM toilet here used it;
   - 24 toilets with other values (permit, students, centralkey, unknown) are in neither group;
   - `fee` is kept in `osm_toilets.csv` but not used to filter (4 toilets have fee=yes).
5. Duplicate mapping (a playground node inside a playground polygon) is not merged. Both count.
6. Mirror tiles carry OSM snapshots from 2026-05-31 to 2026-07-28 (see Sources). The SLSC name query has no recorded data timestamp.
7. Planned-scenario assumptions:
   - future RE1 and ENZ land is assumed to be built like established-suburb RE1 (pooled average);
   - an RE1 parcel counts as "developed" if it already has any OSM sports or playground point;
   - planned features are spread evenly over each parcel;
   - the 0.5-expected-feature threshold for planned distances is a judgement call.
8. The spot-check labels come from the brief. "Ken Birdsey Park (Oakhurst)" is in Schofields per OSM, Nominatim and `planned_sites.csv`, and the coordinate used is the `planned_sites.csv` one.
