# PIGEON-AI v2: every combination of new features, label fix and post-processing

Built 2026-11-10. Every number is held-out: study-area predictions come from 5-fold GroupKFold grouped on the res-6 parent, and growth and future predictions come from models that never saw those hexes. Scripts and CSVs are listed at the end.

**What was varied**

- **F, new features:** the 17 sports, playground and beach columns from `pigeon-v2/data/new_features_study.csv`. No `osm_toilets_*` column was used as a feature.
- **L, label fix:** `label = max(toilet_count, osm_toilets_public)`. The sensitivity version uses `osm_toilets_public_tagged`.
- **Models:**
  - M0 = base (`latest`, 28 features);
  - M1 = +F (45 features);
  - M2 = +L;
  - M3 = +F+L.
  - M2t and M3t are the tagged-only versions of M2 and M3.
  - Growth and future tests use the same four variants on the `v1` family (19 features, or 36 with F).
- **Extra, not in the brief:** "OSM fix after model" (written M0+postL and M1+postL). The model is trained on official labels as usual, and only the gap uses the corrected label: `gap = pred − max(official, OSM public)`. It answers whether the label fix needs retraining at all.
- **Post-processing** (functions from `pigeon-v2/postprocess/postprocess.py`, k = 1):
  - P0: none;
  - P1: equity w = 1;
  - P2: coverage filter;
  - P3: coverage + equity.
  - Every variant takes the top 120. L models compute the gap and coverage against the corrected label, and OSM toilet hexes are passed as extra existing toilets.
- **Seeds:** 0, 1 and 2 for every model. Model metrics show the mean with the min–max over the seeds in brackets. Pick tables show seed 0 exact counts, with the seed range in [brackets] when it differs. **A difference smaller than the seed range is noise.**

**Baselines reproduced.**

| Baseline | Reproduced | Previous |
|---|---|---|
| M0 study area | PR-AUC 0.520 (0.519–0.521), 85–86/100, deviance 0.417, 2,632 predicted, 120 candidates | 0.519, 86/100, 0.419, 2,632, 120 |
| Growth v1 | 54.6 predicted, 24/35 found, PR-AUC 0.312 (seed 0) | 55, 24/35, 0.312 |
| Bradfield | 139.4 predicted, #1 hex = Bradfield Station | 139.4, Bradfield Station |
| Council | 26/42 in the top 10%, 8/39 with a candidate in the 1-ring | 26/42, 8/39 |

## Summary: every combination

Model-level columns repeat across P0–P3 because post-processing doesn't change the model. "PR-AUC (labels agree)" is the fair test of L (see section 1). "Council top 10%" is planned sites in the model's top 10%. "Growth found" is real toilet hexes in the growth top 100. The pick columns are seed 0, top 120. The chance rate for "near planned site" is 1.5%.

{{summary}}

**Short version**

- **F is the only change that clearly beats the noise.**
  - PR-AUC goes from 0.520 to 0.569 (seed range ±0.001).
  - Deviance goes from 0.417 to 0.378.
  - The top 1,000 gains 60 toilet hexes (617 to 677).
  - Council sites in the top 10% go from 26/42 to 30/42.
  - The top-100 hits do not move (85/100).
- **Retraining on L doesn't help.**
  - It ranks real toilets slightly worse on every label set, including its own corrected labels.
  - It predicts 29% more toilets (3,390).
  - It more than doubles the candidates (267 against 120).
- **Applying the OSM fix after the model gives the benefit L was meant to give.** Picks that already have an OSM public toilet in the hex fall from 37/120 to 9/120, with no retraining.
- **Equity w = 1 is still nearly free.** The coverage filter still breaks the ranking: only 5–20 of its 120 picks are real candidates.

## 1. Does it find where toilets already are?

### How many hexes the label fix changes

{{label_changes}}

- The main version (OSM public) adds 762 toilets in 436 study hexes. 272 of those hexes had no official toilet.
- 1,692 of the 2,291 OSM "public" toilets in the bbox have no `access` tag, so some are customer-only. The tagged-only version changes only 79 hexes (+114 toilets).

### Against the official labels (all 16,228 hexes)

{{study_metrics official all}}

### Against the OSM-corrected labels (all 16,228 hexes)

{{study_metrics osm_public all}}

### Against the 15,792 hexes where both labels agree (the fair test)

{{study_metrics official labels_agree}}

<details><summary>Against the tagged-only corrected labels</summary>

{{study_metrics osm_tagged all}}

</details>

**Which comparison is fair**

- **Official labels favour M0 and M1.** An L model learns to predict toilets where OSM lists them. Official labels call 272 of those hexes empty, so each one counts as a false positive. This is why M2 drops to 75/100.
- **Corrected labels favour M2 and M3,** because they were trained on the same definition.
- **The fair test uses only the 15,792 hexes where both labels give the same answer.** Neither model is rewarded or punished for the 436 disputed hexes.
  - M2 against M0: PR-AUC 0.492 against 0.501 (a small loss, beyond the seed range); top-100 83 against 81 (seed ranges 83–84 and 80–82, a marginal gain).
  - M3 against M1: 0.550 against 0.560.
- **On corrected labels M2 still doesn't beat M0** (0.565 against 0.567, top-100 87 against 92). L doesn't rank toilets better under any label. It mainly raises the predicted total (3,390, which matches the corrected 3,332) and the number of candidates.

**F helps under every label.**

| Labels | PR-AUC, M0 → M1 | Top 1,000, M0 → M1 |
|---|---|---|
| Official | 0.520 → 0.569 | 617 → 677 |
| Labels agree | 0.501 → 0.560 | 578 → 656 |
| Corrected | 0.567 → 0.620 | 675 → 740 |

- Each gain is far larger than the seed spread (±0.001 for PR-AUC).
- The top-100 hits are flat (85 → 85). The gain is further down the ranking (top 500 and top 1,000), not at the very top.
- M1 makes 136 candidates (134–139) against 120.

## 2. Are the suggested spots valid?

Each combination below is the top 120 at seed 0.

- **"OSM public toilet already"** is the new full-coverage `osm_toilets_public > 0` in the pick's own hex.
- **"Busy destination"** is a shopping centre or strong destination (station, beach, 1 ha+ park, library and so on) from `experiments/validity/hex_osm_classified.csv`. That file only covers 1,199 checked hexes, so its denominator varies.
- **"no_toilet / shortfall"** is counted against the label the model uses.
- **"Near planned site"** means the pick is in a council-planned site's hex or 1-ring.
- **"Newly covered residents"** counts residents in hexes with no official or OSM toilet within k = 1 who would be covered if every pick got a toilet. The same yardstick is used for every variant.

{{picks}}

**What the table shows**

- **Picks with an OSM toilet already:** 39/120 (32%) for M0 and 37/120 for M1.
  - Retraining on L only cuts this to 24/120 (M2) and 22/120 (M3). The L model learns that OSM-toilet hexes are busy and raises its prediction there, so many stay on the list as shortfall hexes (33/120 for M2, against 14/120 for M0).
  - The after-model fix cuts it to 11/120 (M0) and 9/120 (M1).
- **Cost of the after-model fix:** once OSM toilets count, M1 has only about 101 hexes with a gap ≥ 1, so a fixed top 120 reaches below gap 1. M1+postL has 100/120 picks with gap ≥ 1, and 87/120 with equity.
- **Busy destinations stay at 86–92%** of checked hexes for every model under P0 and P1. The coverage filter drops this to 62–77%, with far fewer hexes checked.
- **The model's picks are mostly no_toilet hexes:** 106/120 for M0 and 108/120 for M1. L models move the list toward shortfall (30–35/120).
- **M1 finds more uncovered gaps than M0:** 17/120 of its own picks are uncovered against 8/120. F adds sports grounds in the suburbs, which are often far from any toilet.

**The earlier 50% figure.** `docs/findings.md` reported 60/120 (50%) of the original candidates with an OSM public toilet. That check counted toilets mapped up to 50 m outside the hex edge and used a different Overpass pull. The strict in-hex count from the new data gives 39/120. Under the old check (checked hexes only, seed 0), the counts are:

| | P0 | P1 |
|---|---|---|
| M0 | 60/120 | 57/118 |
| M1 | 60/114 | 53/112 |
| M2 | 46/111 | 49/112 |
| M3 | 44/110 | 44/111 |
| M0+postL | 40/118 | 35/115 |
| M1+postL | 38/113 | 33/109 |

About a third of picks still have an OSM toilet within 50 m of the hex after the fix, usually in the next hex. The app should show this as a badge ("OSM lists a toilet nearby"). It is not grounds to drop the pick.

## 3. Council plans (42 placed sites)

This uses the method of `experiments/gov/scripts/crosscheck.py`.

- **Percentile:** the site hex's prediction against all study hexes with no official toilet.
- **Candidate in 1-ring:** a candidate (pred − label ≥ 1, using the model's own label) in the site hex or its 6 neighbours. 39 of the 42 sites are in the study grid. The other 3 are in growth hexes, scored with that variant's `v1`-family growth model (as before).
- **Controls:** the same 1,000 random empty hexes and 1,000 random empty park hexes for every model, with the same RNG seed as the original.
- **Reverse check:** the share of all candidates within 1 ring of a planned site. Chance: 249/16,228 hexes (1.5%).

{{council}}

- **F lifts planned sites without lifting parks in general.**
  - M1 puts 30/42 (71%) planned sites in its top 10% against 26/42 (62%), and 39–40/42 in its top 25% against 36–38/42. The seed ranges don't overlap.
  - Random empty park hexes go *down*: 47% → 45% in the top 25%. F helps the model separate council-chosen park sites from parks in general.
  - The fair subset (15 brand-new sites in empty hexes) moves from 5.7/15 to 6.0/15 in the top 10%. That is within noise.
- **L raises "candidate within 1 ring" from 8/39 to 12/39, but only because L makes 2.2× as many candidates.** Its random-hex control rises from 2% to 5% as well. Per flag, the reverse check is about the same for every model: 8.6% (M0), 8.1% (M1), 9.9% (M2), 8.8% (M3), all against 1.5% chance.

### Sports-field sites

{{sports sites}}

- **Pennant Hills Park:** 69th → 95th percentile with F. **Freshwater Park:** 64th → 78th. **York Street Park:** 75th → 78th. **Freshwater Beach:** 99th, unchanged.
- **Ken Birdsey Park (30th → 31st) and Anthony Skarratt Reserve (39th → 20th) are not fixed.**
  - Both sites are in growth hexes, where OSM maps no pitch and no playground in the hex. The nearest pitch is 564 m from Ken Birdsey and 1,314 m from Anthony Skarratt (`pigeon-v2/data/spot_checks.csv`).
  - F tells the model there is no sports ground nearby, so Anthony Skarratt drops.
  - These two need council open-space data, or better OSM mapping, before any model can flag them.

## 4. SEIFA deciles of the picks

Deciles are cut over the study hexes. Decile 1 is the most disadvantaged. "none" means the hex has no SEIFA score.

{{seifa deciles of picks}}

- **Without equity:** every model puts 28–39 picks in deciles 1–3 and 10–17 in deciles 8–10.
- **With equity w = 1:** 45–59 in deciles 1–3 and 1–5 in deciles 8–10.
- **M1+postL with equity is the most pro-disadvantage list** that keeps the model's ranking: 59/120 in deciles 1–3 and 4/120 in deciles 8–10.

## 5. Growth suburbs (1,108 hexes, 39 toilets in 35 hexes)

Each model is trained on all 16,228 study hexes with the `v1` family (+F where used) and predicts the growth hexes. The corrected growth labels have 56 toilets in 48 hexes.

### Against official growth labels

{{growth official}}

### Against OSM-corrected growth labels

{{growth osm_corrected}}

- **F ranks growth toilets better and predicts a total closer to the real one, but finds 2 fewer in the top 100.**
  - PR-AUC: 0.317 → 0.337 (seed ranges 0.312–0.319 and 0.330–0.343).
  - Total: 49 against 55 (real: 39).
  - Found in the top 100: 22/35 against 24/35. This is just beyond the seed range (23–24 against 22).
  - On the corrected labels F gains more: PR-AUC 0.461 → 0.511, found 32 → 31/48.
- **L over-predicts growth suburbs:** 75 toilets for M2 against 39 real (56 corrected). It doesn't rank them better: PR-AUC 0.299 official and 0.445 corrected.

## 6. Bradfield / Aerotropolis and Leppington

- **Features:** the `v1` features from the earlier "mid" scenario (`dphi2041|shops_mid|bus_calibrated`, `experiments/future/*_features.csv`).
- **F features:** from `pigeon-v2/data/new_features_future_planned.csv`.
  - `planned_re1` is the main scenario: undeveloped RE1 land filled at established-suburb rates.
  - `planned_re1_enz` also treats the ENZ zone as sports land. It is an upper bound.
- **Models:** trained on all study hexes. The top-10 tables are seed 0, and the totals give the mean of 3 seeds. "Drivers" are the top-2 SHAP features.

| Area | F scenario | Model | Total (3 seeds) | Hexes ≥ 1 | #1 hex | Bradfield Station rank |
|---|---|---|---|---|---|---|
| Aerotropolis | — | M0 | 141.8 (139.4–144.8) | 3 | Bradfield Station | 1 in all 3 seeds |
| Aerotropolis | planned_re1 | M1 | 106.7 (105.0–108.1) | 4 | Bradfield Station | 1 in all 3 seeds |
| Aerotropolis | — | M2 | 191.0 (186.9–196.0) | 3 | Bradfield Station | 1 in all 3 seeds |
| Aerotropolis | planned_re1 | M3 | 133.3 (129.9–136.4) | 4 | Bradfield Station | 1 in all 3 seeds |
| Aerotropolis | planned_re1_enz | M1 | 226.4 (225.8–227.1) | 52 | ENZ riparian hex 3.2 km from Luddenham | **11** |
| Aerotropolis | planned_re1_enz | M3 | 265.1 (262.8–268.4) | 60 | Bradfield Station | 1 in all 3 seeds |
| Aerotropolis | today (real farmland features) | M0 / M1 / M2 / M3 | 9.8 / 8.2 / 22.2 / 18.0 | 0 | — | — |
| Leppington | — | M0 | 22.5 | 1 | Leppington Station (MU1, 126 m) | — |
| Leppington | planned_re1 | M1 | 28.0 | 1 | Leppington Station | — |
| Leppington | — | M2 | 26.4 | 1 | Leppington Station | — |
| Leppington | planned_re1 | M3 | 31.9 | 3 | Leppington Station | — |

### Aerotropolis top 10 (planned_re1)

{{future aerotropolis planned_re1}}

### Aerotropolis top 10 (planned_re1_enz, upper bound)

{{future aerotropolis planned_re1_enz}}

### Leppington top 10 (planned_re1)

{{future leppington planned_re1}}

**What changes in the future areas**

- **Bradfield Station stays #1** for every variant in the main scenario and every seed. The master plan (p64) marks "Amenities" there.
- **F lowers the Aerotropolis total by about 25%** (142 → 107). M1 also predicts less than M0 for today's farmland (8.2 against 9.8) and for the growth suburbs (49 against 55), so with F the model predicts lower totals in sparse areas in general.
- **F moves planned RE1 parks into the top 10.**
  - Two RE1 Public Recreation hexes 2.3–2.4 km from Bradfield are #3–4 (1.05 each). Their main driver is planned sports area.
  - These are the kind of sports-ground amenity blocks councils actually build, such as Ken Birdsey Park. But they come from a fill rate (8% of RE1 area as sports land), not from a design.
- **The ENZ upper-bound scenario shows the risk.** If ENZ riparian land is treated as sports land, M1's top 10 becomes ten near-identical ENZ hexes (1.19–1.20 each) and Bradfield falls to #11. Use `planned_re1`, and treat F in unbuilt areas as an assumption to show, not a fact.
- **L raises the totals** (191 for M2) and makes the station hexes stronger (Bradfield 1.66–1.75), but it does not change the ordering much.
- **Leppington:** the station hex is #1 for every variant. F pushes more RE1 hexes into the top 10 (7 of 10 for M1 against 6 for M0). The leppington ENZ scenario is identical to `planned_re1`, because there is no ENZ nearby.

### Oran Park proxy check (can the planned features be trusted?)

- **Hexes and toilets:** 103 Oran Park hexes (the earlier proxy set) with 5 real toilets in 4 hexes.
- **Proxy v1:** the earlier zoning proxy (mid).
- **Proxy F:** the `planned.py` method applied to Oran Park's RE1 zoning. All 180 RE1 parcels (797.6 ha in the context bbox) are treated as unbuilt and filled at the pooled rates. Sports and playground counts start at 0, the two distances start at 2,500 m, and beach values stay real.
- **Models:** seed 0.

| Model | Features | Total | Spearman with real-feature prediction | Top-10 overlap with real-feature top 10 | Toilet hexes in top 10 |
|---|---|---|---|---|---|
| M0 | real | 8.3 | 1.00 | 10/10 | 3/4 |
| M0 | proxy v1 | 9.2 | 0.50 | 5/10 | 2/4 |
| M1 | real | 7.9 | 1.00 | 10/10 | 2/4 |
| M1 | proxy v1 + proxy F | 8.3 | 0.48 | 3/10 | 3/4 |
| M1 | real v1 + proxy F | 5.9 | 0.65 | 4/10 | 3/4 |
| M1 | proxy v1 + real F | 7.7 | 0.73 | 5/10 | 2/4 |
| M3 | real | 8.9 | 1.00 | 10/10 | 2/4 |
| M3 | proxy v1 + proxy F | 10.1 | 0.12 | 3/10 | 3/4 |

- The proxy keeps about half of M0's ranking (5/10) but only 3/10 of M1's. Proxy F is the weaker part. With real v1 and proxy F, the overlap is 4/10.
- **Proxy F under-counts sports grounds.** Within 500 m, the proxy gives 0.33 sports features per hex on average, against 1.76 in the real OSM data: about 5× fewer.
- **Toilet hexes caught** are 2–3 out of 4 in every row. With 4 toilet hexes, that difference is noise.
- **Conclusion:** in unbuilt areas, F adds as much uncertainty as it adds signal. Read the Bradfield ranking as "the station hex first, then sports parks", not as a list of exact hexes.

## Recommendation

**Model: M1 (`latest` + sports, playground and beach features), trained on the official labels.**

- It is the only change that beats the seed noise on the main tests:
  - PR-AUC 0.569 against 0.520;
  - deviance 0.378 against 0.417;
  - top 1,000: 677 against 617;
  - planned council sites in the top 10%: 30/42 against 26/42;
  - growth PR-AUC 0.337 against 0.317, with a growth total closer to the real one (49 against 55, real 39).
- **What it doesn't fix:** top-100 hits stay at 85/100. In growth suburbs it finds 2 fewer toilet hexes in the top 100 (22 against 24). The two sports-field misses (Ken Birdsey, Anthony Skarratt) are unchanged, because OSM has no pitch there.

**Label fix: do not retrain on the OSM label (M2/M3). Apply it after the model.**

- **Why not retrain:** it ranks toilets no better on any label set, adds 29% to the predicted total, and more than doubles the candidates.
- **The after-model fix** (`gap = pred − max(official, OSM public)`) cuts picks with an OSM toilet already in the hex from 37/120 to 9/120.
- **The tagged-only version** changes too few hexes to matter: M3t ≈ M1 on every metric.

**Post-processing: equity w = 1 on the main list. Coverage as a separate layer, never as a filter.**

- **M1 + OSM fix after model + equity w = 1 (seed 0):**
  - 87/120 picks with gap ≥ 1;
  - 10/120 with an OSM toilet in the hex;
  - 97/109 checked picks at a busy destination (89%);
  - 8/120 near a planned site (6.7%, 4.4× chance);
  - 59/120 in deciles 1–3 and 4/120 in deciles 8–10.
- **Cost against M0 + equity** (the earlier post-processing recommendation): 8 rather than 11 picks near a planned site. That is 3 picks, at a seed spread of 0 for both. On the other side, it has 10 rather than 34 picks with an OSM toilet already, and 59 rather than 45 picks in deciles 1–3.
- **The coverage filter (P2/P3) fails for every model.** Only 5–20/120 of its picks are real candidates (gap ≥ 1), and 0–3/120 are near a planned site. It answers a different question: where people live far from any toilet.

**What the app should display**

1. **Main list:** M1 candidates ranked by `gap × (1 + disadvantage)`, with gap measured against official + OSM public toilets.
   - Show only hexes with gap ≥ 1 (87 at seed 0) rather than padding to 120.
   - Say that the ranking includes a disadvantage weight and counts OpenStreetMap toilets.
2. **Badges on each pick:**
   - kind (no toilet / shortfall);
   - "OSM lists a toilet nearby" when there is one in the hex or within 50 m;
   - "no toilet within ~400 m" when the pick is uncovered (16/120 for M1+postL with equity);
   - the top-3 SHAP drivers.
3. **Coverage layer:** shade uncovered hexes (k = 1, official + OSM). Keep the "access gaps" view as its own tab, labelled as an access view and not a model prediction.
4. **New and future areas:**
   - Show the ranking and the drivers, not the total. Under the main planned scenario, the Bradfield total is 107 with M1, against 139 previously.
   - Use the `planned_re1` scenario only, and mark planned sports land as an assumption.
5. **Known blind spot:** sports grounds that OSM doesn't map (Ken Birdsey Park, Anthony Skarratt Reserve). Say so in the app until council open-space data is added.

## Files

Scripts are in `pigeon-v2/combos/`. Run them with `/tmp/pigeon-env/bin/python <script>` from that folder, in this order:

| Script | Writes (in `out/`) |
|---|---|
| `common.py` | Shared loaders, the F column list, and the model and label definitions. |
| `study_cv.py` | `study_oof_predictions.csv`: held-out predictions, 6 models × 3 seeds, about 3 min. |
| `growth.py` | `growth_predictions.csv`, `growth_metrics_by_seed.csv`, `growth_metrics.csv`. |
| `evaluate_study.py` (needs both of the above) | `study_metrics_by_seed.csv`, `study_metrics.csv`, `picks_metrics_by_seed.csv`, `picks_metrics.csv`, `picks_top120_seed0.csv` (every top-120 list at seed 0, with hex id, gap, decile, coverage, OSM and busy flags), `council_by_seed.csv`, `council_sites_by_model_seed.csv`. |
| `future.py` | `future_summary.csv`, `future_top10.csv`. |
| `oran.py` | `oran_proxy_check.csv`. Reads Oran Park zoning from `/tmp/pigeon-eval/future/downloads/`. |
| `tables.py`, `summary_table.py`, `future_tables.py`, `build_results.py` | `tables.md`, `summary_table.md/.csv`, `future_tables.md` → `results.md` (from `results_template.md`). |

Console logs are `out/*.log`. Nothing in the PIGEON-AI-DATASET repo was changed.
