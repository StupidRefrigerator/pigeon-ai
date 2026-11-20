#!/bin/sh
# Rebuild the bike experiment from its downloads. Usage: experiments/bike/run_all.sh DOWNLOADS_DIR
# DOWNLOADS_DIR holds overpass/, tfnsw/, pbf/ and dem/ (see DATA.md, "Bike-lane experiment downloads").
# Python runs with -I because it reads downloaded files.
set -eu
D=${1:?usage: run_all.sh DOWNLOADS_DIR}
S=$(cd "$(dirname "$0")/scripts" && pwd)
PY=${PYTHON:-python}
$PY -I "$S/fetch_bike_osm.py" "$D/overpass"
$PY -I "$S/fetch_dem.py" "$D/dem"
$PY -I "$S/extract_pbf.py" "$D/pbf/australia-261113.osm.pbf" "$D/extract"
$PY -I "$S/build_labels.py" "$D/overpass" "$D/tfnsw/shp/Existing_Bicycle_Network.shp"
$PY -I "$S/build_features.py" "$D/extract" "$D/dem"
$PY -I "$S/run_experiments.py"
$PY -I "$S/seed_check.py"
$PY -I "$S/subtypes.py"
$PY -I "$S/analyse_gaps.py" rf_len_bike rf_cls_bike
