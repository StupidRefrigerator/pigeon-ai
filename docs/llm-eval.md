# Ask Pigeon (LLM) evals

These evals check that Ask Pigeon, the LLM agent in the web app, turns planning questions into the right tool calls and answers without inventing places or numbers. The random forest's own evals (PR-AUC, Poisson deviance, top-100 hits and others) are in [model.md](model.md#evals).

## How it works

[`app/evals/agent-eval.mts`](../app/evals/agent-eval.mts) sends 10 questions to the real agent (`gpt-6.1-sol`, the same code as `/api/ask`) and records every tool call, its output and the answer. Each answer is graded by code, not by an LLM judge, so every check is a clear pass or fail and the run can be repeated.

Each question runs 3 times to check consistency. The baseline is the same LLM with web search only: no map tools and no project brief.

| Group | Questions | Checks |
|---|---|---|
| Budget | $500k in Blacktown; $1.2M around Liverpool | Calls `plan_sites`; looks up a cost; shows the sites it planned; every site is within 3 km of the place. |
| Constraints | 5 in Parramatta, at least 400 m apart, no toilet yet; 3 near Bondi Beach, at least 800 m apart | Shows the asked number; every site within 3 km; pairwise spacing met; no existing toilet in any picked hexagon. |
| Explain a hexagon | "Why is this spot ranked so high?" (rank 1); "What is around this hexagon…?" (rank 10) | Reads that hexagon with `get_hex`; states its real prediction; at least 90% of numbers in the answer appear in a tool output. |
| Project facts | "How was the model trained and tested?"; "How accurate is it?" | Says 300 trees and 5-fold spatial CV; never claims SEIFA is an input; quotes 85/100 and compares with random. |
| Out of scope | A hospital in Penrith; crime in Redfern | Shows no hexagons; says the map only covers its layers instead of guessing. |

## Results (22 Nov 2026)

| Group | Ask Pigeon (3 runs each) | Baseline (1 run each) |
|---|---|---|
| Budget | 6/6 | 0/2 |
| Constraints | 6/6 | 0/2 |
| Explain a hexagon | 6/6 | 0/2 |
| Project facts | 6/6 | 0/2 |
| Out of scope | 6/6 | 2/2 |
| **Total** | **30/30** | **2/10** |

- Without the map tools and brief, the same LLM cannot name real hexagons and does not know the model's results ("I don't have verified accuracy figures"). It only matches Ask Pigeon on refusing out-of-scope questions.
- Grounding (share of numbers in an answer found in a tool output): 100% for explaining a hexagon and project facts, 92% for constraints, 37% for budgets. Budget answers quote web costs and the user's budget, which this check cannot trace.
- Cost $0.47 for all 30 agent runs; 14.5 s per answer on average, 26 to 51 s for budget questions.
- Full answers, tool calls and checks are in [`app/evals/results.json`](../app/evals/results.json).

## Run it

```sh
cd app
npm install
OPENAI_API_KEY=... npx tsx evals/agent-eval.mts 3   # 3 runs per question; about 8 minutes and $0.50
```

It rewrites `evals/results.json`. Run it again after changing the prompt or project brief (`src/ai/agent.ts`, `src/ai/brief.ts`), the tools (`src/ai/tools.ts`), the LLM (`OPENAI_MODEL`), or the model's predictions.

## Limits

- 2 questions per group is a small set. The answers are graded on behaviour that code can check, not on how clear or useful they read.
- Budget answers depend on the cost figure web search finds; the eval checks that a cost is looked up, not that it is correct.
- Results vary slightly between runs because the LLM is not deterministic.
