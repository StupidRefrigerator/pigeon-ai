# PIGEON-AI web app

TanStack Start (React) + Clerk + Leaflet/h3-js, hosted on Vercel via Nitro.

- `/` landing page, `/app` map explorer, `/app/stats` internal stats.
- Model shown: the original cross-validated RandomForest, `latest` feature set. Every prediction is held-out.

## Run locally

```bash
cd app
npm install
npm run dev          # http://localhost:3000
npm run build        # production build (.output/)
npm run typecheck && npm test
```

Clerk is optional. Copy `.env.example` to `.env` and fill in the keys to enable sign-in. Without them the sign-in button is disabled. Auth is not enforced on any page.

## Data

`public/data/*.json` and `src/data/stats.json` are generated from the repo CSVs and committed:

```bash
npm run build-data   # uses /tmp/pigeon-env/bin/python
```

The script reads `latest` held-out predictions from `git show origin/heatmap-held-out:web/predictions.csv` (or `app/data-src/predictions.csv` if present), checks that the 120 candidates match `data/review/candidate_review.csv`, and writes ids and numbers only. Hex geometry comes from h3-js in the browser. Numbers that exist only in `docs/findings.md` live in `scripts/curated_stats.json`.
