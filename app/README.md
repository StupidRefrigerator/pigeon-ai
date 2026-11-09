# PIGEON-AI web app

TanStack Start (React) + Clerk, hosted on Vercel via Nitro.

- `/` landing page, `/app` placeholder with sign-in and sign-out, `/app/stats` internal stats.
- Model shown: the original cross-validated RandomForest, `latest` feature set. Every prediction is held-out.

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

`src/data/stats.json` is generated from the repo CSVs and committed:

```bash
npm run build-data   # uses /tmp/pigeon-env/bin/python
```

The script reads `latest` held-out predictions from `git show origin/heatmap-held-out:web/predictions.csv` (or `app/data-src/predictions.csv` if present), checks that the 120 candidates match `data/review/candidate_review.csv`. Numbers that exist only in `docs/findings.md` live in `scripts/curated_stats.json`.
