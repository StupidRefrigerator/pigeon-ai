"""Fill results_template.md with the generated tables -> results.md."""
import re

from common import OUT, V2

parts = {}
for block in (OUT / "tables.md").read_text().split("\n\n## "):
    head, _, body = block.lstrip("# ").partition("\n")
    parts[head.split(" (")[0].strip()] = body
parts["summary"] = (OUT / "summary_table.md").read_text().strip()
for block in (OUT / "future_tables.md").read_text().split("\n\n### "):
    head, _, body = block.lstrip("# ").partition("\n")
    parts["future " + head.replace(" — F scenario ", " ")] = body
tpl = (V2 / "combos/results_template.md").read_text()
missing = set(re.findall(r"\{\{(.+?)\}\}", tpl)) - set(parts)
assert not missing, (missing, list(parts))
out = re.sub(r"\{\{(.+?)\}\}", lambda m: parts[m.group(1)].strip(), tpl)
(V2 / "combos/results.md").write_text(out)
print("keys:", list(parts))
