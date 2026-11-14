"""Genera src/data/video-data.json desde ../fixtures (y el informe HTML real en public/): ninguna cifra se teclea a mano.

    python scripts/make_data.py        (con el python del repo: ../.venv/Scripts/python)
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
FIX = REPO / "fixtures"

from ledger.models import Report  # noqa: E402
from ledger.report.render import write_report  # noqa: E402
from ledger.trust.policy import spot_checks  # noqa: E402
from ledger.trust.record import load_record  # noqa: E402


def load(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


triage = load("triage_2297.json")
measure = load("measure_2297_par_v1.json")
runs = [load(f"measure_2297_par_v{i}.json")["wall_s"] for i in range(1, 5)]
capacity = load("capacity_modal.json")
report = Report.model_validate_json((FIX / "report_2297_modal.json").read_text(encoding="utf-8"))


def outcome(o) -> str:
    if o.valid:
        return "valid"
    if o.pr_result is not None and o.pr_result.red_for_real:
        return "red"
    return "nothing"


objections = [(v.path, o) for v in report.verdicts for o in v.objections]
outcomes = [outcome(o) for _, o in objections]
sample_path, sample = next((p, o) for p, o in objections if o.question)
refused = next(v for v in report.verdicts if v.path.endswith("CompositeResolverTemplate.cs"))
refused_open = next(o for o in refused.objections if outcome(o) == "red")
picks = spot_checks(report, load_record())

readme = (REPO / "README.md").read_text(encoding="utf-8")
team_section = readme.split("## Team", 1)[1].split("\n## ", 1)[0]
team_rows = re.findall(r"^\| \*\*(.+?)\*\* \|", team_section, re.M)
lessons = sum(1 for line in (REPO / "docs" / "lessons-log.md").read_text(encoding="utf-8").splitlines() if line.startswith("| H"))
cost = re.search(r"\*\*(\d+,\d+) \$ en créditos\*\*", (REPO / "docs" / "numeros-evidencia.md").read_text(encoding="utf-8"))
modal60 = next(r for r in capacity["levels"] if r["n"] == max(x["n"] for x in capacity["levels"]))

data = {
    "files": len(triage),
    "lowIn": sum(1 for t in triage if t["scope"] == "IN" and t["risk"] in ("LOW", "MED")),
    "highIn": sum(1 for t in triage if t["scope"] == "IN" and t["risk"] == "HIGH"),
    "outOfScope": sum(1 for t in triage if t["scope"] == "OUT"),
    "snapshots": sum(1 for t in triage if re.search(r"Resources/.*\.g\.cs$", t["path"])),
    "corpusCases": len(list((REPO / "harness" / "corpus").glob("*.cs"))),
    # La invarianza cuenta solo los casos generales ("N general cases identical" en los informes).
    "generalCases": len(list((REPO / "harness" / "corpus").glob("general-*.cs"))),
    "objections": measure["objections"],
    "objectionOutcomes": outcomes,
    "outcomeCounts": dict(Counter(outcomes)),
    "sandboxesTotal": measure["sandboxes"]["total"],
    "sandboxPeak": measure["sandboxes"]["peak"],
    "rateLimitErrors": measure["llm"]["gemini"]["errors"].get("429", 0),
    "parallelMinutes": round(measure["wall_s"] / 60),
    "parallelRangeMin": [round(min(runs) / 60), round(max(runs) / 60)],
    "capacityMax": {"n": modal60["n"], "failed": modal60["failed"], "wall_s": modal60["wall_s"]},
    "needHumanMax": sum(1 for t in triage if t["risk"] == "HIGH" or t["scope"] == "OUT"),
    "needHuman": sum(1 for v in report.verdicts if v.verdict.value != "GREEN"),
    "verdictCounts": dict(Counter(v.verdict.value for v in report.verdicts)),
    "sampleObjection": sample.question,
    "sampleObjectionFile": sample_path.split("/")[-1],
    "refusedFile": refused.path.split("/")[-1],
    "refusedQuestion": refused_open.question,
    "refusedRedTests": sum(1 for o in refused.objections if outcome(o) == "red"),
    "spotChecks": len(picks),
    "spotCheckFiles": ["/".join(p.path.split("/")[-2:]) for p in picks],
    "lessons": lessons,
    "modalCostUsd": cost.group(1).replace(",", ".") if cost else "?",
    "team": team_rows,
    "repo": "github.com/mreboll/Proof-not-promises",
}
target = HERE.parent / "src" / "data" / "video-data.json"
target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# El informe real de ESTA ejecución, para el plano del producto (se sirve desde public/).
models = {"flash": "gemini-3.8-flash", "pro": "gemini-4-hydrogen", "fiscal": "nvidia/nemotron-3.5-super-vl-120b-a12b"}
html = write_report(report, HERE.parent / "out" / "report", models=models, issue_title="#2297: Add ExcludeFromCodeCoverage attribute to generated code")
(HERE.parent / "public" / "report-2297.html").write_text(html.read_text(encoding="utf-8"), encoding="utf-8")
print(json.dumps({k: v for k, v in data.items() if k != "objectionOutcomes"}, indent=1, ensure_ascii=False))
