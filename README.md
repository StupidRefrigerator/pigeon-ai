# PIGEON-AI

Pigeon AI predicts where Sydney's next public infrastructure should go, from a bird's-eye view of the city. Public toilets are the first layer and water fountains (bubblers) the second.

**Live app:** https://pigeon-ai.vercel.app

## Contributions

The work was split roughly evenly, with each of us owning one part of the system.

**Jimmy (Aranchai Khanijow): data**
- Sourced the public datasets: ABS Census 2021 and SEIFA, OpenStreetMap, the National Public Toilet Map and council records.
- Cleaned them and built the H3 hexagon dataset of 16,228 hexagons and 45 inputs.
- Built the V1–V10 comparison page.

**Summit Setia: model**
- Built the random forest (300 trees) that predicts the expected toilet count per hexagon.
- Set up 5-fold spatial cross-validation and the evals: PR-AUC, Poisson deviance, top-100 hits, council-planned sites and growth suburbs.
- Added SHAP explanations and ran the V11–V12 experiments that chose the final model.

**Oscar: LLM**
- Built Ask Pigeon, an LLM agent (OpenAI's `gpt-6.1-sol`) that answers planning questions about the map.
- Designed its tools, which read the model's held-out predictions, and its web search for costs and council plans.
- Wrote its prompt and project brief, and tested it.

Commit counts don't tell the whole story. Some work was done in pairs or outside the repo, such as sourcing data, the slides and the pitch. Some was committed from one person's account, for example the Ask Pigeon code, which went in under Summit's account.

## How it works

1. Sydney is split into 16,228 hexagons of about 0.1 km² each.
2. A random forest predicts how many toilets each hexagon would normally have, from what is around it (people, shops, transport, parks, sports grounds, beaches).
3. Where the prediction is at least 1 more than the real count, that hexagon is short of toilets.
4. The 100 biggest gaps are the suggested list.

Every prediction comes from a model that never saw that part of Sydney, so a hexagon's own toilets can't hide its gap.

**V12 results:** PR-AUC 0.569 (random is 0.118). 677 of the top 1,000 predictions have a toilet. 2,625 toilets predicted vs 2,570 real. 30 of 42 council-planned sites are flagged.

## Evals

- **Model (random forest):** PR-AUC, Poisson deviance, top-100 hits, calibration, fairness and stability, all on held-out predictions from 5-fold spatial cross-validation, with baselines. See [docs/model.md](docs/model.md#evals); results are in `data/model/metrics.csv`. Tests on real places the model never trained on (council-planned sites, growth suburbs, Bradfield) are in [docs/findings.md](docs/findings.md).
- **LLM (Ask Pigeon):** 10 planning questions, 3 runs each, graded by code against a baseline LLM without our tools. See [docs/llm-eval.md](docs/llm-eval.md); the script is `app/evals/agent-eval.mts`.

## Quick start

```sh
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/train_model.py      # about 2.5 minutes
```

`python scripts/train_model.py --target bubblers` trains the same forest, with the same 45 inputs, on water fountains and writes to `data/model/bubblers/`. `PYTHONPATH=src python experiments/bubblers/growth_future.py` scores the growth suburbs and future areas for it. Each layer is one entry in `TARGETS` in `src/pigeon_ai/model.py`.

**Water fountain results (B1, seed 0):** PR-AUC 0.529 (random is 0.095). 89 of the top 100 and 589 of the top 1,000 predictions have a fountain. Deviance 0.408 vs 0.771 for predicting the average everywhere. Council fountain records are thin in western Sydney (see [DATA.md](DATA.md)), so predictions there are less checked.

You don't need to train to use the results. The final V12 results are committed in `data/model/` (`recommendations.csv` is the suggested list).

Web app: see [app/README.md](app/README.md).

## Folders

```text
app/         Web app (TanStack Start, deck.gl, OpenAI, Vercel)
data/        Processed features and V12 results (committed); raw data is on Drive
src/         Python package (pigeon_ai)
scripts/     Command-line entry points
experiments/ V2 and future-area experiments
docs/        Details
```

## More detail

- [docs/model.md](docs/model.md): inputs, training, evals, the suggested list and reviewing candidates.
- [docs/findings.md](docs/findings.md): every experiment and result.
- [docs/llm-eval.md](docs/llm-eval.md): Ask Pigeon (LLM) evals.
- [docs/model-decisions.md](docs/model-decisions.md): design decisions and trade-offs.
- [data/README.md](data/README.md): how the dataset is built.
- [DATA.md](DATA.md): getting the raw data from Drive.
- [docs/comparison-page.md](docs/comparison-page.md): the older V1–V10 comparison tools.
