# PIGEON-AI web app

TanStack Start (React) + Clerk, hosted on Vercel via Nitro.

- `/` landing page (`src/routes/index.tsx`, styles and canvas code in `src/landing/`), `/app` dashboard (sidebar, user menu, Admin group; marked work in progress) with the 3D hexagon map (`src/map/`, deck.gl + MapLibre, loaded in the browser only), `/app/stats` Tracking (V12 results, results map, version history), `/app/tests` Tests (four questions).
- Model shown: V12. Every prediction is held out (spatial cross-validation). The suggested list is ranked by gap only.

## Run locally

```bash
cd app
npm install
npm run dev          # http://localhost:3000
npm run build        # production build (.output/)
npm run typecheck && npm test
```

Clerk uses the team's "Pigeon AI" application (`app_3Ls1IZXrkbrqOOmBnD6QCVOAzTn`). To get development keys, run `npx -y clerk@latest auth login` and then `npx -y clerk@latest env pull` from `app/`. This writes `.env.local`, which is gitignored. Without keys the app still builds, and the sign-in button is disabled. Auth is not enforced on any page.

## Data

`public/landing-hexes.json` feeds the landing-page map. It is generated from `data/model/hex_predictions.csv` and `data/model/recommendations.csv` and committed:

```bash
/tmp/pigeon-env/bin/python scripts/build_landing_data.py
```

`src/data/tracking.json`, `src/data/stats.json` (Tracking and Tests pages, bundled) and `public/heatmap.json` (the `/app` and Tracking-page maps, fetched at runtime) are generated from the V12 outputs in `data/model/` and `experiments/v2/combos/out/` and committed:

```bash
npm run build-data   # uses /tmp/pigeon-env/bin/python
```

The script asserts that its numbers match `summary_table.csv`. V1–V10 have no CSV in this repo; their rows live in `scripts/curated_stats.json`.
