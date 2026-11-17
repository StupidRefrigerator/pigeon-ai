"""Build app/src/data/infra/toilets/references.json: council toilet plans (from experiments/gov/planned_sites.csv)."""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
rows = list(csv.DictReader(open(ROOT / "experiments/gov/planned_sites.csv", encoding="utf-8")))
docs = defaultdict(lambda: {"sites": 0})
for r in rows:
    d = docs[(r["council"], r["document"], r["url"])]
    d.update(council=r["council"], document=r["document"], url=r["url"])
    d["sites"] += 1
out = sorted(docs.values(), key=lambda d: (d["council"], d["document"]))
dest = ROOT / "app/src/data/infra/toilets/references.json"
dest.write_text(json.dumps({"councilSites": len(rows), "councilDocs": out}, indent=1, ensure_ascii=False) + "\n")
print(f"{len(rows)} sites, {len(out)} documents -> {dest.relative_to(ROOT)}")
