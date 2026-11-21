# PIGEON-AI web app

TanStack Start (React), hosted on Vercel via Nitro. There is no sign-in: every page is open.

- `/` landing page (`src/routes/index.tsx`, styles and canvas code in `src/landing/`), `/app` dashboard (sidebar, Admin group; marked work in progress) with the 3D hexagon map (`src/map/`, deck.gl + MapLibre, loaded in the browser only), `/app/stats` Tracking (V12 results, results map, version history), `/app/tests` Tests (four questions).
- Model shown: V12. Every prediction is held out (spatial cross-validation). The suggested list is ranked by gap only.

## Run locally

```bash
cd app
npm install
npm run dev          # http://localhost:3000
npm run build        # production build (.output/)
npm run typecheck && npm test
```

## Ask Pigeon (AI)

The map's Ask Pigeon panel is an agent on OpenAI's Responses API (`gpt-6.1-sol`; set `OPENAI_MODEL` to change it). `POST /api/ask` (`src/routes/api.ask.ts`, `src/ai/agent.ts`) streams the model's reasoning summary, each tool step and the answer as NDJSON. Its tools (`src/ai/tools.ts`) read the same `heatmap.json` as the map: place lookup, spot search, `plan_sites` for budget and spacing constraints, one hexagon's details, area totals, how the model was tested, and `show_on_map`, which highlights hexagons in the browser. It also has OpenAI's hosted web search.

The server needs `OPENAI_API_KEY`. Locally, put it in the repo-root `.env` (git-ignored) and load it before starting, for example `set -a; . ../.env; set +a; npm run dev`. On Vercel, set it as a project environment variable.

The "Why here" note on the top 100 suggested spots of each layer is precomputed into `public/infra/<layer>/summaries.json`, so cards open instantly and every visitor sees the same text. Each prompt carries the agent's read of the hexagon, the raw inputs from `data/processed/`, council-planned sites within 1 km, and web search. Re-running fills only missing spots; pass `--force` to rewrite all of them after the data changes:

```bash
npm run summaries -- toilets      # then: bubblers
```

## Infrastructure layers

`src/infra.ts` is the registry of layers (toilets live; bike lanes and water fountains announced). A live layer names its heatmap URL under `public/infra/<id>/`, and `src/infra-data.ts` bundles its JSON from `src/data/infra/<id>/`. `/app` reads `?layer=<id>` (unknown or absent means the first live layer), and pages take the layer's name and unit from it.

## Data

`public/landing-hexes.json` feeds the landing-page map. It is generated from `data/model/hex_predictions.csv` and `data/model/recommendations.csv` and committed:

```bash
/tmp/pigeon-env/bin/python scripts/build_landing_data.py
```

`src/data/infra/toilets/tracking.json`, `src/data/infra/toilets/stats.json` (Tracking and Tests pages, bundled) and `public/infra/toilets/heatmap.json` (the `/app` and Tracking-page maps, fetched at runtime) are generated from the V12 outputs in `data/model/` and `experiments/v2/combos/out/` and committed:

```bash
npm run build-data   # uses /tmp/pigeon-env/bin/python; pass -- --target <layer> for another layer
```

The script asserts that its numbers match `summary_table.csv`.

`public/places.json` feeds the map's area search: the suburbs and landmarks from `data/reference/sydney_places.json` that have a map hexagon within 2 km. Regenerate it after a layer's `heatmap.json` changes:

```bash
node scripts/build_places.mjs
``` V1–V10 have no CSV in this repo; their rows live in `scripts/curated_stats.json`.
