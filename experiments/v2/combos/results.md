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

| model | post-processing | PR-AUC (official) | PR-AUC (labels agree) | top-100 hits | deviance | council top 10% | growth found | growth predicted (39) | picks gap ≥ 1 | OSM toilet already | near planned site | deciles 1–3 / 8–10 | newly covered residents |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 base | P0 none | 0.520 | 0.501 | 85/100 | 0.417 | 26/42 | 24/35 | 55 | 120/120 | 39/120 | 10/120 | 30 / 17 | 36k |
| M0 base | P1 equity w=1 | 0.520 | 0.501 | 85/100 | 0.417 | 26/42 | 24/35 | 55 | 102/120 | 34/120 | 11/120 | 45 / 5 | 42k |
| M0 base | P2 coverage filter | 0.520 | 0.501 | 85/100 | 0.417 | 26/42 | 24/35 | 55 | 8/120 | 10/120 | 1/120 | 40 / 22 | 141k |
| M0 base | P3 coverage + equity | 0.520 | 0.501 | 85/100 | 0.417 | 26/42 | 24/35 | 55 | 8/120 | 11/120 | 1/120 | 58 / 7 | 145k |
| M1 +F | P0 none | 0.569 | 0.560 | 85/100 | 0.378 | 30/42 | 22/35 | 49 | 120/120 | 37/120 | 10/120 | 32 / 17 | 46k |
| M1 +F | P1 equity w=1 | 0.569 | 0.560 | 85/100 | 0.378 | 30/42 | 22/35 | 49 | 102/120 | 34/120 | 8/120 | 54 / 3 | 53k |
| M1 +F | P2 coverage filter | 0.569 | 0.560 | 85/100 | 0.378 | 30/42 | 22/35 | 49 | 20/120 | 17/120 | 3/120 | 37 / 19 | 129k |
| M1 +F | P3 coverage + equity | 0.569 | 0.560 | 85/100 | 0.378 | 30/42 | 22/35 | 49 | 20/120 | 17/120 | 3/120 | 56 / 7 | 137k |
| M2 +L | P0 none | 0.506 | 0.492 | 75/100 | 0.434 | 24/42 | 24/35 | 75 | 120/120 | 24/120 | 13/120 | 28 / 10 | 36k |
| M2 +L | P1 equity w=1 | 0.506 | 0.492 | 75/100 | 0.434 | 24/42 | 24/35 | 75 | 120/120 | 27/120 | 12/120 | 45 / 2 | 42k |
| M2 +L | P2 coverage filter | 0.506 | 0.492 | 75/100 | 0.434 | 24/42 | 24/35 | 75 | 11/120 | 0/120 | 0/120 | 35 / 27 | 151k |
| M2 +L | P3 coverage + equity | 0.506 | 0.492 | 75/100 | 0.434 | 24/42 | 24/35 | 75 | 11/120 | 0/120 | 0/120 | 58 / 5 | 160k |
| M3 +F+L | P0 none | 0.555 | 0.550 | 76/100 | 0.394 | 29/42 | 22/35 | 64 | 120/120 | 22/120 | 14/120 | 28 / 10 | 37k |
| M3 +F+L | P1 equity w=1 | 0.555 | 0.550 | 76/100 | 0.394 | 29/42 | 22/35 | 64 | 120/120 | 22/120 | 12/120 | 48 / 1 | 45k |
| M3 +F+L | P2 coverage filter | 0.555 | 0.550 | 76/100 | 0.394 | 29/42 | 22/35 | 64 | 17/120 | 0/120 | 1/120 | 35 / 22 | 148k |
| M3 +F+L | P3 coverage + equity | 0.555 | 0.550 | 76/100 | 0.394 | 29/42 | 22/35 | 64 | 17/120 | 0/120 | 1/120 | 56 / 10 | 165k |
| M0, OSM fix after model | P0 none | 0.520 | 0.501 | 85/100 | 0.417 | 26/42 | 24/35 | 55 | 89/120 | 11/120 | 11/120 | 37 / 14 | 47k |
| M0, OSM fix after model | P1 equity w=1 | 0.520 | 0.501 | 85/100 | 0.417 | 26/42 | 24/35 | 55 | 83/120 | 10/120 | 9/120 | 54 / 5 | 55k |
| M0, OSM fix after model | P2 coverage filter | 0.520 | 0.501 | 85/100 | 0.417 | 26/42 | 24/35 | 55 | 5/120 | 0/120 | 0/120 | 41 / 25 | 164k |
| M0, OSM fix after model | P3 coverage + equity | 0.520 | 0.501 | 85/100 | 0.417 | 26/42 | 24/35 | 55 | 5/120 | 0/120 | 0/120 | 58 / 6 | 172k |
| M1, OSM fix after model | P0 none | 0.569 | 0.560 | 85/100 | 0.378 | 30/42 | 22/35 | 49 | 100/120 | 9/120 | 8/120 | 39 / 17 | 59k |
| M1, OSM fix after model | P1 equity w=1 | 0.569 | 0.560 | 85/100 | 0.378 | 30/42 | 22/35 | 49 | 87/120 | 10/120 | 8/120 | 59 / 4 | 65k |
| M1, OSM fix after model | P2 coverage filter | 0.569 | 0.560 | 85/100 | 0.378 | 30/42 | 22/35 | 49 | 10/120 | 0/120 | 1/120 | 40 / 19 | 168k |
| M1, OSM fix after model | P3 coverage + equity | 0.569 | 0.560 | 85/100 | 0.378 | 30/42 | 22/35 | 49 | 10/120 | 0/120 | 1/120 | 59 / 8 | 177k |

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

| label | area | hexes changed | empty hexes that gain a toilet | toilets added | toilets before | toilets after | toilet hexes before | toilet hexes after |
|---|---|---|---|---|---|---|---|---|
| public | study | 436 | 272 | 762 | 2570 | 3332 | 1911 | 2183 |
| public | growth | 16 | 13 | 17 | 39 | 56 | 35 | 48 |
| tagged | study | 79 | 55 | 114 | 2570 | 2684 | 1911 | 1966 |
| tagged | growth | 5 | 5 | 6 | 39 | 45 | 35 | 40 |

- The main version (OSM public) adds 762 toilets in 436 study hexes. 272 of those hexes had no official toilet.
- 1,692 of the 2,291 OSM "public" toilets in the bbox have no `access` tag, so some are customer-only. The tagged-only version changes only 79 hexes (+114 toilets).

### Against the official labels (all 16,228 hexes)

| model | PR-AUC | top 100 | top 500 | top 1,000 | deviance | predicted total | actual | candidates |
|---|---|---|---|---|---|---|---|---|
| M0 | 0.520 (0.519–0.521) | 85 (85–86)/100 | 360 (359–361)/500 | 617 (615–619)/1,000 | 0.417 (0.416–0.418) | 2,633 (2,631–2,635) | 2,570 | 120 (119–121) |
| M1 | 0.569 (0.569–0.570) | 85/100 | 370 (365–372)/500 | 677 (671–681)/1,000 | 0.378 (0.378–0.378) | 2,625 (2,622–2,628) | 2,570 | 136 (134–139) |
| M2 | 0.506 (0.506–0.506) | 75 (74–76)/100 | 350 (349–350)/500 | 609 (606–615)/1,000 | 0.434 (0.434–0.435) | 3,390 (3,384–3,397) | 2,570 | 267 (265–268) |
| M3 | 0.555 (0.554–0.556) | 76 (75–78)/100 | 365 (363–367)/500 | 662 (661–664)/1,000 | 0.394 (0.393–0.394) | 3,386 (3,383–3,390) | 2,570 | 294 (287–298) |
| M2t | 0.518 (0.517–0.518) | 84/100 | 358 (356–361)/500 | 612 (610–614)/1,000 | 0.417 (0.417–0.417) | 2,741 (2,740–2,743) | 2,570 | 139 (137–141) |
| M3t | 0.567 (0.567–0.567) | 87/100 | 364 (362–366)/500 | 677 (674–679)/1,000 | 0.378 (0.378–0.379) | 2,735 (2,733–2,737) | 2,570 | 161 (161–162) |

### Against the OSM-corrected labels (all 16,228 hexes)

| model | PR-AUC | top 100 | top 500 | top 1,000 | deviance | predicted total | actual | candidates |
|---|---|---|---|---|---|---|---|---|
| M0 | 0.567 (0.566–0.567) | 92/100 | 394 (393–395)/500 | 675 (673–677)/1,000 | 0.525 (0.523–0.526) | 2,633 (2,631–2,635) | 3,332 | 88 (87–89) |
| M1 | 0.620 (0.620–0.621) | 92/100 | 404 (400–406)/500 | 740 (737–742)/1,000 | 0.474 (0.474–0.475) | 2,625 (2,622–2,628) | 3,332 | 101 (99–103) |
| M2 | 0.565 (0.564–0.565) | 87 (86–87)/100 | 395 (394–396)/500 | 680 (677–684)/1,000 | 0.506 (0.505–0.507) | 3,390 (3,384–3,397) | 3,332 | 209 (206–212) |
| M3 | 0.617 (0.616–0.618) | 86 (85–87)/100 | 405 (404–408)/500 | 735 (733–736)/1,000 | 0.454 (0.454–0.455) | 3,386 (3,383–3,390) | 3,332 | 230 (223–234) |
| M2t | 0.568 (0.567–0.568) | 92 (91–92)/100 | 393 (391–394)/500 | 677 (675–678)/1,000 | 0.518 (0.517–0.518) | 2,741 (2,740–2,743) | 3,332 | 104 (102–105) |
| M3t | 0.622 (0.621–0.622) | 93 (93–94)/100 | 403 (401–404)/500 | 741 (739–743)/1,000 | 0.467 (0.467–0.468) | 2,735 (2,733–2,737) | 3,332 | 117 (116–119) |

### Against the 15,792 hexes where both labels agree (the fair test)

| model | PR-AUC | top 100 | top 500 | top 1,000 | deviance | predicted total | actual | candidates |
|---|---|---|---|---|---|---|---|---|
| M0 | 0.501 (0.501–0.502) | 81 (80–82)/100 | 339 (337–342)/500 | 578 (576–582)/1,000 | 0.403 (0.402–0.403) | 2,349 (2,347–2,350) | 2,330 | 87 (86–87) |
| M1 | 0.560 (0.560–0.560) | 82 (80–83)/100 | 368 (366–372)/500 | 656 (653–658)/1,000 | 0.361 (0.361–0.362) | 2,325 (2,323–2,328) | 2,330 | 99 (98–101) |
| M2 | 0.492 (0.491–0.492) | 83 (83–84)/100 | 335 (334–336)/500 | 569 (567–571)/1,000 | 0.415 (0.415–0.416) | 2,984 (2,979–2,990) | 2,330 | 195 (192–197) |
| M3 | 0.550 (0.548–0.551) | 82 (81–83)/100 | 365 (363–366)/500 | 639 (637–643)/1,000 | 0.372 (0.372–0.373) | 2,961 (2,959–2,965) | 2,330 | 216 (210–219) |
| M2t | 0.501 (0.500–0.501) | 83 (82–84)/100 | 340 (338–343)/500 | 575 (573–577)/1,000 | 0.402 (0.402–0.402) | 2,439 (2,438–2,440) | 2,330 | 102 (100–103) |
| M3t | 0.560 (0.559–0.560) | 84 (83–85)/100 | 370 (369–371)/500 | 655 (650–658)/1,000 | 0.361 (0.361–0.362) | 2,417 (2,416–2,417) | 2,330 | 115 (114–117) |

<details><summary>Against the tagged-only corrected labels</summary>

| model | PR-AUC | top 100 | top 500 | top 1,000 | deviance | predicted total | actual | candidates |
|---|---|---|---|---|---|---|---|---|
| M0 | 0.536 (0.536–0.537) | 86/100 | 374 (373–375)/500 | 637 (635–639)/1,000 | 0.425 (0.425–0.426) | 2,633 (2,631–2,635) | 2,684 | 106 (105–107) |
| M1 | 0.585 (0.585–0.586) | 85 (85–86)/100 | 384 (379–387)/500 | 699 (693–703)/1,000 | 0.385 (0.385–0.385) | 2,625 (2,622–2,628) | 2,684 | 123 (121–126) |
| M2 | 0.527 (0.527–0.527) | 79 (78–80)/100 | 369 (368–369)/500 | 632 (629–638)/1,000 | 0.437 (0.436–0.438) | 3,390 (3,384–3,397) | 2,684 | 250 (247–252) |
| M3 | 0.577 (0.576–0.577) | 80 (78–81)/100 | 383 (381–385)/500 | 686 (684–687)/1,000 | 0.395 (0.395–0.396) | 3,386 (3,383–3,390) | 2,684 | 275 (267–280) |
| M2t | 0.535 (0.535–0.536) | 85 (84–85)/100 | 375 (373–377)/500 | 634 (632–636)/1,000 | 0.424 (0.424–0.424) | 2,741 (2,740–2,743) | 2,684 | 123 (121–125) |
| M3t | 0.586 (0.585–0.586) | 87 (87–88)/100 | 381 (379–382)/500 | 700 (697–702)/1,000 | 0.384 (0.384–0.385) | 2,735 (2,733–2,737) | 2,684 | 143 (142–143) |

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

| model | post | gap ≥ 1 | total gap | no_toilet / shortfall | OSM public toilet already | busy destination | near planned site | uncovered (official) | deciles 1–3 | deciles 8–10 | no SEIFA | newly covered residents | same as M0-P0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 | P0 | 120 [119–120]/120 | 159 | 106 / 14 | 39 [39–40]/120 (32%) | 107/120 (89%) | 10 [10–11]/120 (8.3%) | 8/120 | 30 [29–30] | 17 | 20 | 35,741 | 120/120 |
| M0 | P1 | 102 [102–103]/120 | 156 | 106 / 14 | 34 [34–36]/120 (28%) | 105/118 (89%) | 11/120 (9.2%) | 9/120 | 45 [43–46] | 5 | 19 | 41,898 | 102/120 |
| M0 | P2 | 8 [7–9]/120 | 79 | 120 / 0 | 10 [10–12]/120 (8%) | 72/95 (76%) | 1/120 (0.8%) | 120/120 | 40 [38–40] | 22 [22–23] | 21 | 140,551 | 8/120 |
| M0 | P3 | 8 [7–9]/120 | 77 | 120 / 0 | 11 [11–12]/120 (9%) | 61/79 (77%) | 1/120 (0.8%) | 120/120 | 58 [58–59] | 7 | 21 | 145,384 | 8/120 |
| M1 | P0 | 120/120 | 158 | 108 / 12 | 37 [37–39]/120 (31%) | 102/114 (89%) | 10 [10–11]/120 (8.3%) | 17/120 | 32 [26–32] | 17 [17–19] | 17 | 46,492 | 95/120 |
| M1 | P1 | 102 [102–105]/120 | 155 | 108 / 12 | 34 [33–34]/120 (28%) | 102/112 (91%) | 8 [8–10]/120 (6.7%) | 15/120 | 54 [51–54] | 3 | 14 | 53,081 | 84/120 |
| M1 | P2 | 20 [19–20]/120 | 90 | 120 / 0 | 17/120 (14%) | 36/52 (69%) | 3/120 (2.5%) | 120/120 | 37 [35–37] | 19 | 29 | 128,581 | 8/120 |
| M1 | P3 | 20 [19–20]/120 | 88 | 120 / 0 | 17 [16–17]/120 (14%) | 37/52 (71%) | 3/120 (2.5%) | 120/120 | 56 [55–56] | 7 [7–8] | 25 | 137,072 | 8/120 |
| M2 | P0 | 120/120 | 219 | 87 / 33 | 24 [23–25]/120 (20%) | 99/111 (89%) | 13/120 (10.8%) | 5/120 | 28 | 10 [8–10] | 22 | 36,303 | 80/120 |
| M2 | P1 | 120/120 | 215 | 85 / 35 | 27 [24–27]/120 (22%) | 102/112 (91%) | 12/120 (10.0%) | 5/120 | 45 [44–45] | 2 | 20 | 41,756 | 75/120 |
| M2 | P2 | 11 [11–12]/120 | 88 | 120 / 0 | 0/120 (0%) | 49/68 (72%) | 0/120 (0.0%) | 120/120 | 35 [35–36] | 27 [22–27] | 22 | 151,409 | 5/120 |
| M2 | P3 | 11 [11–12]/120 | 85 | 120 / 0 | 0/120 (0%) | 46/64 (72%) | 0/120 (0.0%) | 120/120 | 58 | 5 [5–6] | 22 | 159,632 | 5/120 |
| M3 | P0 | 120/120 | 219 | 90 / 30 | 22 [22–23]/120 (18%) | 95/110 (86%) | 14/120 (11.7%) | 7/120 | 28 [27–28] | 10 [10–13] | 22 | 36,511 | 75/120 |
| M3 | P1 | 120/120 | 214 | 90 / 30 | 22 [22–23]/120 (18%) | 99/111 (89%) | 12 [12–13]/120 (10.0%) | 9/120 | 48 [45–48] | 1 [1–4] | 19 | 44,689 | 68/120 |
| M3 | P2 | 17 [17–18]/120 | 94 | 120 / 0 | 0/120 (0%) | 29/47 (62%) | 1/120 (0.8%) | 120/120 | 35 [34–35] | 22 [22–24] | 28 | 148,038 | 5/120 |
| M3 | P3 | 17 [17–18]/120 | 92 | 120 / 0 | 0/120 (0%) | 31/45 (69%) | 1/120 (0.8%) | 120/120 | 56 [52–56] | 10 | 25 | 164,805 | 5/120 |
| M2t | P0 | 120/120 | 162 | 105 / 15 | 27 [27–28]/120 (22%) | 107/120 (89%) | 10 [10–11]/120 (8.3%) | 9/120 | 33 [29–33] | 13 | 20 | 38,748 | 102/120 |
| M2t | P1 | 104 [102–104]/120 | 158 | 105 / 15 | 27/120 (22%) | 108/118 (92%) | 10 [10–11]/120 (8.3%) | 6/120 | 48 [45–48] | 2 [2–4] | 19 | 40,607 | 89/120 |
| M2t | P2 | 7/120 | 80 | 120 / 0 | 8/120 (7%) | 59/79 (75%) | 0/120 (0.0%) | 120/120 | 36 [36–40] | 19 | 27 | 141,099 | 7/120 |
| M2t | P3 | 7/120 | 78 | 120 / 0 | 8 [8–9]/120 (7%) | 54/73 (74%) | 0/120 (0.0%) | 120/120 | 58 [58–62] | 6 | 24 | 152,152 | 7/120 |
| M3t | P0 | 120/120 | 162 | 107 / 13 | 33 [30–33]/120 (28%) | 100/113 (88%) | 9 [8–9]/120 (7.5%) | 17/120 | 32 [30–32] | 14 [12–14] | 21 | 44,887 | 84/120 |
| M3t | P1 | 105 [104–105]/120 | 158 | 108 / 12 | 28 [26–28]/120 (23%) | 101/112 (90%) | 9 [8–9]/120 (7.5%) | 11/120 | 54 [53–54] | 2 | 15 | 51,554 | 79/120 |
| M3t | P2 | 14 [13–14]/120 | 87 | 120 / 0 | 13 [13–14]/120 (11%) | 34/52 (65%) | 2/120 (1.7%) | 120/120 | 38 [37–38] | 18 [18–20] | 32 | 135,091 | 7/120 |
| M3t | P3 | 14 [13–14]/120 | 85 | 120 / 0 | 13 [13–14]/120 (11%) | 34/50 (68%) | 2/120 (1.7%) | 120/120 | 59 [56–59] | 6 [6–7] | 27 | 147,649 | 7/120 |
| M0+postL | P0 | 89 [87–89]/120 | 144 | 104 / 16 | 11 [10–11]/120 (9%) | 103/118 (87%) | 11/120 (9.2%) | 12/120 | 37 [35–37] | 14 | 15 | 47,392 | 90/120 |
| M0+postL | P1 | 83 [83–84]/120 | 141 | 105 / 15 | 10 [9–10]/120 (8%) | 102/115 (89%) | 9/120 (7.5%) | 12/120 | 54 [54–55] | 5 [5–7] | 11 | 54,690 | 84/120 |
| M0+postL | P2 | 5 [4–5]/120 | 73 | 120 / 0 | 0/120 (0%) | 55/74 (74%) | 0/120 (0.0%) | 120/120 | 41 [39–41] | 25 [23–26] | 19 | 164,359 | 5/120 |
| M0+postL | P3 | 5 [4–5]/120 | 70 | 120 / 0 | 0/120 (0%) | 49/66 (74%) | 0/120 (0.0%) | 120/120 | 58 [58–60] | 6 [5–6] | 19 | 171,698 | 5/120 |
| M1+postL | P0 | 100 [99–103]/120 | 146 | 108 / 12 | 9 [9–10]/120 (8%) | 100/113 (88%) | 8 [8–9]/120 (6.7%) | 18/120 | 39 [37–39] | 17 [16–17] | 12 | 58,718 | 79/120 |
| M1+postL | P1 | 87 [86–89]/120 | 143 | 107 / 13 | 10 [9–10]/120 (8%) | 97/109 (89%) | 8/120 (6.7%) | 16/120 | 59 [59–61] | 4 | 10 | 65,249 | 71/120 |
| M1+postL | P2 | 10 [9–10]/120 | 79 | 120 / 0 | 0/120 (0%) | 30/47 (64%) | 1/120 (0.8%) | 120/120 | 40 [39–41] | 19 [19–22] | 29 | 167,739 | 5/120 |
| M1+postL | P3 | 10 [9–10]/120 | 77 | 120 / 0 | 0/120 (0%) | 31/46 (67%) | 1/120 (0.8%) | 120/120 | 59 [57–59] | 8 [7–9] | 23 | 177,147 | 5/120 |

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

| set | model | top 10% | top 25% | median pct | candidate in 1-ring |
|---|---|---|---|---|---|
| planned (42) | M0 | 26.0/42 (62%) | 36.7 (36.0–38.0)/42 (87%) | 95.0 (94.8–95.2) | 8.0/39 (21%) |
| planned new, empty hex | M0 | 5.7 (5.0–6.0)/15 (38%) | 10.7 (10.0–12.0)/15 (71%) | 84.3 (83.9–85.0) | 3.0/13 (23%) |
| control: random empty hexes | M0 | 106.7 (105.0–109.0)/1000 (11%) | 249.0 (248.0–251.0)/1000 (25%) | 49.3 (48.9–49.6) | 23.0 (22.0–24.0)/1000 (2%) |
| control: random empty park hexes | M0 | 195.7 (195.0–196.0)/1000 (20%) | 471.0 (470.0–472.0)/1000 (47%) | 73.4 (73.1–73.7) | 46.7 (45.0–48.0)/1000 (5%) |
| reverse: candidates near a planned site | M0 |  |  |  | 10.3 (10.0–11.0) of 120 (119–121) candidates (8.6%) |
| planned (42) | M1 | 30.0/42 (71%) | 39.3 (39.0–40.0)/42 (94%) | 97.9 (97.9–98.0) | 8.0/39 (21%) |
| planned new, empty hex | M1 | 6.0/15 (40%) | 12.3 (12.0–13.0)/15 (82%) | 85.5 (85.1–85.7) | 3.0/13 (23%) |
| control: random empty hexes | M1 | 107.0 (104.0–110.0)/1000 (11%) | 261.3 (259.0–263.0)/1000 (26%) | 50.9 (50.4–51.7) | 30.0 (29.0–31.0)/1000 (3%) |
| control: random empty park hexes | M1 | 188.0 (185.0–191.0)/1000 (19%) | 446.0 (442.0–449.0)/1000 (45%) | 71.4 (71.3–71.5) | 56.3 (55.0–58.0)/1000 (6%) |
| reverse: candidates near a planned site | M1 |  |  |  | 11.0 of 136 (134–139) candidates (8.1%) |
| planned (42) | M2 | 23.7 (23.0–24.0)/42 (56%) | 36.7 (36.0–37.0)/42 (87%) | 94.7 (94.4–94.9) | 12.0 (11.0–13.0)/39 (31%) |
| planned new, empty hex | M2 | 4.3 (4.0–5.0)/15 (29%) | 10.7 (10.0–11.0)/15 (71%) | 83.3 (83.0–83.7) | 3.0 (2.0–4.0)/13 (23%) |
| control: random empty hexes | M2 | 109.7 (109.0–111.0)/1000 (11%) | 255.0 (254.0–257.0)/1000 (26%) | 49.2 (49.1–49.3) | 47.7 (46.0–51.0)/1000 (5%) |
| control: random empty park hexes | M2 | 189.7 (187.0–193.0)/1000 (19%) | 449.7 (443.0–453.0)/1000 (45%) | 72.2 (72.0–72.3) | 71.7 (70.0–73.0)/1000 (7%) |
| reverse: candidates near a planned site | M2 |  |  |  | 20.7 (19.0–22.0) of 209 (206–212) candidates (9.9%) |
| planned (42) | M3 | 29.0/42 (69%) | 38.0/42 (90%) | 97.6 (97.5–97.7) | 11.7 (11.0–13.0)/39 (30%) |
| planned new, empty hex | M3 | 6.0/15 (40%) | 11.0/15 (73%) | 86.0 (85.6–86.3) | 2.3 (2.0–3.0)/13 (18%) |
| control: random empty hexes | M3 | 113.3 (111.0–116.0)/1000 (11%) | 263.3 (260.0–265.0)/1000 (26%) | 51.6 (51.0–52.0) | 57.0/1000 (6%) |
| control: random empty park hexes | M3 | 179.7 (177.0–182.0)/1000 (18%) | 431.7 (428.0–436.0)/1000 (43%) | 70.7 (70.6–70.7) | 91.0 (87.0–94.0)/1000 (9%) |
| reverse: candidates near a planned site | M3 |  |  |  | 20.3 (20.0–21.0) of 230 (223–234) candidates (8.8%) |
| planned (42) | M2t | 26.7 (26.0–28.0)/42 (63%) | 37.0/42 (88%) | 95.1 (94.9–95.2) | 9.3 (9.0–10.0)/39 (24%) |
| planned new, empty hex | M2t | 5.7 (5.0–7.0)/15 (38%) | 11.0/15 (73%) | 83.9 (83.1–84.9) | 3.0/13 (23%) |
| control: random empty hexes | M2t | 106.3 (105.0–107.0)/1000 (11%) | 252.3 (252.0–253.0)/1000 (25%) | 49.2 (48.9–49.4) | 22.0/1000 (2%) |
| control: random empty park hexes | M2t | 193.0 (191.0–194.0)/1000 (19%) | 468.7 (468.0–469.0)/1000 (47%) | 73.2 (73.1–73.4) | 44.3 (44.0–45.0)/1000 (4%) |
| reverse: candidates near a planned site | M2t |  |  |  | 10.3 (10.0–11.0) of 123 (121–125) candidates (8.4%) |
| planned (42) | M3t | 30.0/42 (71%) | 39.7 (39.0–40.0)/42 (94%) | 97.8 (97.8–97.9) | 7.3 (7.0–8.0)/39 (19%) |
| planned new, empty hex | M3t | 6.0/15 (40%) | 12.7 (12.0–13.0)/15 (84%) | 86.1 (86.1–86.2) | 2.3 (2.0–3.0)/13 (18%) |
| control: random empty hexes | M3t | 107.7 (106.0–109.0)/1000 (11%) | 260.3 (259.0–262.0)/1000 (26%) | 51.0 (50.9–51.1) | 33.0/1000 (3%) |
| control: random empty park hexes | M3t | 188.7 (188.0–189.0)/1000 (19%) | 442.0 (436.0–445.0)/1000 (44%) | 71.6 (71.5–71.7) | 56.0 (53.0–59.0)/1000 (6%) |
| reverse: candidates near a planned site | M3t |  |  |  | 10.0 (9.0–11.0) of 143 (142–143) candidates (7.0%) |

- **F lifts planned sites without lifting parks in general.**
  - M1 puts 30/42 (71%) planned sites in its top 10% against 26/42 (62%), and 39–40/42 in its top 25% against 36–38/42. The seed ranges don't overlap.
  - Random empty park hexes go *down*: 47% → 45% in the top 25%. F helps the model separate council-chosen park sites from parks in general.
  - The fair subset (15 brand-new sites in empty hexes) moves from 5.7/15 to 6.0/15 in the top 10%. That is within noise.
- **L raises "candidate within 1 ring" from 8/39 to 12/39, but only because L makes 2.2× as many candidates.** Its random-hex control rises from 2% to 5% as well. Per flag, the reverse check is about the same for every model: 8.6% (M0), 8.1% (M1), 9.9% (M2), 8.8% (M3), all against 1.5% chance.

### Sports-field sites

| site_id | name | grid | toilet_count_hex | M0 | M1 | M2 | M2t | M3 | M3t |
|---|---|---|---|---|---|---|---|---|---|
| BL01 | Ken Birdsey Park amenities building | growth | 0.0 | 30 | 31 | 33 | 28 | 45 | 28 |
| CU01 | York Street Park new Exeloo | study | 0.0 | 75 | 78 | 74 | 74 | 73 | 78 |
| HO02 | Pennant Hills Park new No.2 amenities building | study | 1.0 | 69 | 95 | 68 | 70 | 96 | 96 |
| NB01 | Freshwater Beach north-end amenities building | study | 1.0 | 99 | 99 | 99 | 99 | 99 | 99 |
| ST02 | Freshwater Park new public toilet | study | 0.0 | 64 | 78 | 64 | 64 | 77 | 77 |
| TH01 | Anthony Skarratt Reserve amenities building | growth | 0.0 | 39 | 20 | 42 | 43 | 16 | 17 |

- **Pennant Hills Park:** 69th → 95th percentile with F. **Freshwater Park:** 64th → 78th. **York Street Park:** 75th → 78th. **Freshwater Beach:** 99th, unchanged.
- **Ken Birdsey Park (30th → 31st) and Anthony Skarratt Reserve (39th → 20th) are not fixed.**
  - Both sites are in growth hexes, where OSM maps no pitch and no playground in the hex. The nearest pitch is 564 m from Ken Birdsey and 1,314 m from Anthony Skarratt (`pigeon-v2/data/spot_checks.csv`).
  - F tells the model there is no sports ground nearby, so Anthony Skarratt drops.
  - These two need council open-space data, or better OSM mapping, before any model can flag them.

## 4. SEIFA deciles of the picks

Deciles are cut over the study hexes. Decile 1 is the most disadvantaged. "none" means the hex has no SEIFA score.

| model | post | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | none |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 | P0 | 8 | 7 | 15 | 12 | 15 | 18 | 8 | 13 | 2 | 2 | 20 |
| M0 | P1 | 14 | 12 | 19 | 15 | 15 | 16 | 5 | 5 | 0 | 0 | 19 |
| M0 | P2 | 19 | 10 | 11 | 13 | 7 | 7 | 10 | 6 | 8 | 8 | 21 |
| M0 | P3 | 31 | 15 | 12 | 17 | 7 | 6 | 4 | 5 | 2 | 0 | 21 |
| M1 | P0 | 8 | 8 | 16 | 15 | 15 | 18 | 6 | 10 | 3 | 4 | 17 |
| M1 | P1 | 20 | 14 | 20 | 15 | 15 | 16 | 3 | 3 | 0 | 0 | 14 |
| M1 | P2 | 15 | 13 | 9 | 15 | 6 | 7 | 7 | 7 | 5 | 7 | 29 |
| M1 | P3 | 27 | 18 | 11 | 15 | 6 | 7 | 4 | 4 | 2 | 1 | 25 |
| M2 | P0 | 8 | 7 | 13 | 16 | 18 | 19 | 7 | 7 | 2 | 1 | 22 |
| M2 | P1 | 14 | 16 | 15 | 18 | 16 | 16 | 3 | 1 | 1 | 0 | 20 |
| M2 | P2 | 14 | 10 | 11 | 12 | 7 | 9 | 8 | 9 | 10 | 8 | 22 |
| M2 | P3 | 29 | 15 | 14 | 14 | 7 | 9 | 5 | 4 | 1 | 0 | 22 |
| M3 | P0 | 8 | 8 | 12 | 17 | 17 | 18 | 8 | 7 | 2 | 1 | 22 |
| M3 | P1 | 16 | 14 | 18 | 18 | 16 | 14 | 4 | 1 | 0 | 0 | 19 |
| M3 | P2 | 13 | 14 | 8 | 11 | 7 | 9 | 8 | 8 | 5 | 9 | 28 |
| M3 | P3 | 24 | 19 | 13 | 14 | 6 | 5 | 4 | 6 | 0 | 4 | 25 |
| M2t | P0 | 9 | 8 | 16 | 15 | 16 | 17 | 6 | 9 | 3 | 1 | 20 |
| M2t | P1 | 17 | 11 | 20 | 17 | 17 | 14 | 3 | 1 | 0 | 1 | 19 |
| M2t | P2 | 18 | 10 | 8 | 15 | 5 | 7 | 11 | 7 | 6 | 6 | 27 |
| M2t | P3 | 31 | 15 | 12 | 17 | 5 | 5 | 5 | 5 | 1 | 0 | 24 |
| M3t | P0 | 10 | 8 | 14 | 16 | 15 | 16 | 6 | 8 | 3 | 3 | 21 |
| M3t | P1 | 19 | 14 | 21 | 18 | 15 | 13 | 3 | 1 | 0 | 1 | 15 |
| M3t | P2 | 16 | 14 | 8 | 13 | 5 | 8 | 6 | 7 | 4 | 7 | 32 |
| M3t | P3 | 28 | 20 | 11 | 13 | 4 | 6 | 5 | 4 | 1 | 1 | 27 |
| M0+postL | P0 | 11 | 9 | 17 | 16 | 13 | 16 | 9 | 11 | 2 | 1 | 15 |
| M0+postL | P1 | 20 | 13 | 21 | 17 | 13 | 14 | 6 | 4 | 0 | 1 | 11 |
| M0+postL | P2 | 20 | 10 | 11 | 15 | 5 | 5 | 10 | 7 | 10 | 8 | 19 |
| M0+postL | P3 | 31 | 15 | 12 | 18 | 7 | 5 | 7 | 5 | 1 | 0 | 19 |
| M1+postL | P0 | 11 | 10 | 18 | 19 | 11 | 15 | 7 | 10 | 4 | 3 | 12 |
| M1+postL | P1 | 22 | 15 | 22 | 19 | 11 | 13 | 4 | 3 | 0 | 1 | 10 |
| M1+postL | P2 | 14 | 15 | 11 | 13 | 6 | 5 | 8 | 7 | 4 | 8 | 29 |
| M1+postL | P3 | 25 | 21 | 13 | 14 | 7 | 4 | 5 | 6 | 0 | 2 | 23 |

- **Without equity:** every model puts 28–39 picks in deciles 1–3 and 10–17 in deciles 8–10.
- **With equity w = 1:** 45–59 in deciles 1–3 and 1–5 in deciles 8–10.
- **M1+postL with equity is the most pro-disadvantage list** that keeps the model's ranking: 59/120 in deciles 1–3 and 4/120 in deciles 8–10.

## 5. Growth suburbs (1,108 hexes, 39 toilets in 35 hexes)

Each model is trained on all 16,228 study hexes with the `v1` family (+F where used) and predicts the growth hexes. The corrected growth labels have 56 toilets in 48 hexes.

### Against official growth labels

| model | predicted total | actual | PR-AUC | toilet hexes in top 100 | deviance |
|---|---|---|---|---|---|
| M0 | 54.7 (54.6–54.9) | 39 | 0.317 (0.312–0.319) | 24 (23–24)/35 | 0.162 (0.162–0.163) |
| M1 | 48.7 (48.4–49.2) | 39 | 0.337 (0.330–0.343) | 22/35 | 0.170 (0.168–0.171) |
| M2 | 74.7 (74.3–74.9) | 39 | 0.299 (0.295–0.305) | 24 (24–25)/35 | 0.173 (0.173–0.173) |
| M3 | 64.3 (64.1–64.6) | 39 | 0.326 (0.323–0.329) | 22/35 | 0.170 (0.168–0.172) |
| M2t | 57.7 (57.6–57.9) | 39 | 0.309 (0.299–0.316) | 23 (22–24)/35 | 0.161 (0.161–0.162) |
| M3t | 50.6 (50.6–50.6) | 39 | 0.330 (0.328–0.331) | 22/35 | 0.172 (0.172–0.173) |

### Against OSM-corrected growth labels

| model | predicted total | actual | PR-AUC | toilet hexes in top 100 | deviance |
|---|---|---|---|---|---|
| M0 | 54.7 (54.6–54.9) | 56 | 0.461 (0.458–0.463) | 32 (31–33)/48 | 0.189 (0.189–0.190) |
| M1 | 48.7 (48.4–49.2) | 56 | 0.511 (0.508–0.515) | 31/48 | 0.189 (0.188–0.190) |
| M2 | 74.7 (74.3–74.9) | 56 | 0.445 (0.441–0.453) | 33 (32–33)/48 | 0.191 (0.191–0.191) |
| M3 | 64.3 (64.1–64.6) | 56 | 0.502 (0.501–0.504) | 31/48 | 0.180 (0.178–0.182) |
| M2t | 57.7 (57.6–57.9) | 56 | 0.453 (0.446–0.459) | 32 (31–33)/48 | 0.187 (0.185–0.187) |
| M3t | 50.6 (50.6–50.6) | 56 | 0.505 (0.502–0.507) | 31 (30–31)/48 | 0.190 (0.189–0.191) |

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

| rank | M0 | M1 | M2 | M3 |
|---|---|---|---|---|
| 1 | MU, Bradfield 27 m, 1.16 (station) **Bradfield stn** | MU, Bradfield 27 m, 1.19 (station) **Bradfield stn** | MU, Bradfield 27 m, 1.66 (station + food) **Bradfield stn** | MU, Bradfield 27 m, 1.75 (station) **Bradfield stn** |
| 2 | MU, Luddenham 182 m, 1.11 (station) | MU, Luddenham 182 m, 1.06 (station) | MU, Luddenham 182 m, 1.39 (station) | MU, Luddenham 182 m, 1.44 (station) |
| 3 | ENZ, Luddenham 585 m, 1.01 (park + food) | RE1, Bradfield 2402 m, 1.05 (sports + park) | ENZ, Luddenham 585 m, 1.36 (food + park) | RE1, Bradfield 2402 m, 1.18 (sports) |
| 4 | MU, Luddenham 204 m, 0.82 (station + food) | RE1, Bradfield 2343 m, 1.05 (sports + park) | ENZ, Bradfield 688 m, 0.96 (park + food) | RE1, Bradfield 2343 m, 1.17 (sports) |
| 5 | MU, Luddenham 302 m, 0.76 (food + park) | RU4, Bradfield 1769 m, 0.73 (sports) | MU, Luddenham 204 m, 0.95 (food + station) | MU, Luddenham 204 m, 0.96 (station + food) |
| 6 | MU, Bradfield 407 m, 0.72 (food + park) | MU, Luddenham 204 m, 0.71 (station + shops) | MU, Luddenham 302 m, 0.90 (food + park) | SP2, Airport Terminal 185 m, 0.93 (station) |
| 7 | ENZ, Bradfield 679 m, 0.70 (park) | ENZ, Bradfield 2511 m, 0.69 (park + sports) | MU, Bradfield 407 m, 0.87 (food + park) | SP2, Airport Business Park 113 m, 0.93 (station) |
| 8 | ENZ, Bradfield 688 m, 0.68 (park) | ENZ, Luddenham 3025 m, 0.64 (park + playground) | MU, Luddenham 497 m, 0.81 (food + park) | ENZ, Luddenham 585 m, 0.89 (food) |
| 9 | MU, Luddenham 497 m, 0.64 (food + park) | RU4, Bradfield 2518 m, 0.62 (park + playground) | MU, Bradfield 673 m, 0.81 (food + shops) | MU, Bradfield 407 m, 0.81 (food + shops) |
| 10 | MU, Luddenham 665 m, 0.62 (park + shops) | MU, Bradfield 381 m, 0.60 (food + shops) | SP2, Airport Terminal 185 m, 0.78 (station) | ENZ, Bradfield 2511 m, 0.79 (park + playground) |

### Aerotropolis top 10 (planned_re1_enz, upper bound)

| rank | M1 | M3 |
|---|---|---|
| 1 | ENZ, Luddenham 3164 m, 1.20 (sports + park) | MU, Bradfield 27 m, 1.75 (station) **Bradfield stn** |
| 2 | ENZ, Luddenham 3157 m, 1.19 (sports + park) | MU, Luddenham 182 m, 1.44 (station) |
| 3 | ENZ, Bradfield 2140 m, 1.19 (sports + park) | ENZ, Luddenham 3164 m, 1.32 (sports) |
| 4 | ENZ, Luddenham 2910 m, 1.19 (sports + park) | ENZ, Luddenham 2842 m, 1.31 (sports) |
| 5 | ENZ, Luddenham 2842 m, 1.19 (sports + park) | ENZ, Luddenham 3157 m, 1.31 (sports) |
| 6 | ENZ, Bradfield 2131 m, 1.19 (sports + park) | ENZ, Luddenham 2910 m, 1.31 (sports) |
| 7 | ENZ, Bradfield 1918 m, 1.19 (sports + park) | ENZ, Bradfield 2140 m, 1.31 (sports) |
| 8 | ENZ, Bradfield 2038 m, 1.19 (sports + park) | ENZ, Luddenham 2824 m, 1.30 (sports) |
| 9 | ENZ, Luddenham 2824 m, 1.19 (sports + park) | ENZ, Bradfield 1918 m, 1.29 (sports) |
| 10 | ENZ, Luddenham 3513 m, 1.19 (sports + park) | ENZ, Bradfield 2038 m, 1.29 (sports) |

### Leppington top 10 (planned_re1)

| rank | M0 | M1 | M2 | M3 |
|---|---|---|---|---|
| 1 | MU1, Leppington 126 m, 1.02 (station) | MU1, Leppington 126 m, 1.17 (station) | MU1, Leppington 126 m, 1.37 (station) | MU1, Leppington 126 m, 1.51 (station) |
| 2 | RE1, Leppington 1004 m, 0.83 (park) | RE1, Leppington 1004 m, 0.95 (park + sports) | RE1, Leppington 1004 m, 0.90 (park) | RE1, Leppington 1004 m, 1.02 (sports) |
| 3 | SP2, Leppington 426 m, 0.80 (food + park) | RE1, Leppington 2795 m, 0.88 (park + sports) | MU1, Leppington 503 m, 0.86 (food + park) | RE1, Leppington 2795 m, 1.01 (sports) |
| 4 | MU1, Leppington 503 m, 0.71 (park + food) | RE1, Leppington 899 m, 0.85 (park + sports) | SP2, Leppington 426 m, 0.86 (food + park) | SP2, Leppington 426 m, 1.00 (food + sports) |
| 5 | RE1, Leppington 646 m, 0.67 (park) | SP2, Leppington 426 m, 0.82 (sports + park) | RE1, Leppington 484 m, 0.73 (park) | RE1, Leppington 899 m, 0.92 (park + sports) |
| 6 | RE1, Leppington 484 m, 0.65 (park) | RE1, Leppington 1436 m, 0.80 (park + sports) | MU1, Leppington 635 m, 0.72 (food + park) | MU1, Leppington 503 m, 0.87 (food + sports) |
| 7 | RE1, Leppington 899 m, 0.60 (park) | RE1, Leppington 484 m, 0.78 (park + sports) | MU1, Leppington 265 m, 0.67 (food) | RE1, Leppington 1436 m, 0.86 (park + sports) |
| 8 | RE1, Leppington 1505 m, 0.58 (park) | RE1, Leppington 646 m, 0.76 (park + sports) | RE1, Leppington 646 m, 0.67 (park) | RE1, Leppington 484 m, 0.83 (sports + playground) |
| 9 | RE1, Leppington 1436 m, 0.57 (park) | R2, Leppington 1410 m, 0.76 (park + sports) | RE1, Leppington 1505 m, 0.65 (park) | RE1, Leppington 646 m, 0.82 (sports + park) |
| 10 | MU1, Leppington 635 m, 0.53 (food + park) | RE1, Leppington 1505 m, 0.73 (park + sports) | RE1, Leppington 1436 m, 0.62 (park) | MU1, Leppington 635 m, 0.79 (food + sports) |

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
