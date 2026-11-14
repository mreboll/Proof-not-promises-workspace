"""Informes de la demo para el jurado, regenerables desde los fixtures del repo:

    python -m ledger.report.demo            # escribe demo/*.html y demo/index.html

- Ejecuciones grabadas (#2283 con dotnet y con Modal): las Etapas 1-3 son reales. Se recalculan los veredictos
  con la matriz actual y, si la ejecución generó texto en español, se traduce SOLO ese texto (con aviso).
- Fixtures (#2234, #2297, #2129): Etapas 1 y 2 reales (reglas, triaje con Gemini, evidencia con dotnet de A).
  La Etapa 3 no se inventa: no se ejecutó, el informe lo dice y los ficheros de riesgo alto quedan en rojo.

Los modelos de cada informe son los de la ejecución que lo produjo, no los del .env de quien lo regenera.
"""

from __future__ import annotations

import html
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ledger.config import PROJECT_ROOT, get_issue, load_settings
from ledger.models import ChangeTestEvidence, FileTriage, InvarianceEvidence, Report, Verdict
from ledger.report.render import TRANSLATED_NOTICE, _context, recompute_verdicts, render_html, translate_llm_text
from ledger.trust.policy import apply_trust
from ledger.trust.record import load_record
from ledger.verdict import decide

FIXTURES = PROJECT_ROOT / "fixtures"
DEFAULT_OUT = PROJECT_ROOT / "demo"

NEMOTRON_SUPER = "nvidia/nemotron-3.5-super-vl-120b-a12b"
RUN_2283 = {"flash": "gemini-3.5-flash", "pro": "gemini-4-hydrogen", "fiscal": NEMOTRON_SUPER}  # según A
NOT_RUN = "— (Stage 3 not run)"

FIXTURE_NOTICE = (
    "Stages 1 and 2 are real (static risk rules, Gemini scope triage, change test and generation invariance run with dotnet). "
    "Stage 3 (cross-examination) was not run for this report, so high-risk files stay red: without it the system refuses "
    "to decide. The #2283 reports show a full run."
)


@dataclass(frozen=True)
class DemoSpec:
    slug: str
    issue_id: str
    blurb: str
    models: dict[str, str] = field(default_factory=dict)
    tag: str = "stages 1–2 · fixtures"
    recorded: str = ""  # fichero de fixtures/ con un informe grabado; vacío = construir desde triage_ + evidence_
    translate: bool = False


DEMOS: tuple[DemoSpec, ...] = (
    DemoSpec(
        "2283-dotnet", "2283",
        "Bug fix, full pipeline with real dotnet. The Prosecutor's questions led to Defender tests that fail on the PR: "
        "the AI fix moves the crash instead of removing it, although its own test and the invariance check were green.",
        RUN_2283, tag="full run · local dotnet", recorded="report_2283_dotnet.json", translate=True,
    ),
    DemoSpec(
        "2283-modal", "2283",
        "Same PR, full pipeline with every piece of AI-written code run in network-less Modal sandboxes "
        "(11 min). Two of three objections closed by valid tests; one stays open, so the system refuses to decide.",
        RUN_2283, tag="full run · Modal sandboxes", recorded="report_2283_modal.json",
    ),
    DemoSpec(
        "2234", "2234",
        "Bug fix from a one-sentence issue: the independent test also passes on base, and the invariance check shows "
        "the fix changes behaviour outside the issue. Red for two real reasons.",
        {"flash": "gemini-3.8-flash", "pro": NEMOTRON_SUPER, "fiscal": NOT_RUN},
    ),
    DemoSpec(
        "2297", "2297",
        "Feature touching 237 files: the evidence approves 223 low-risk files unread, at most 14 need a human, and the "
        "scope check flags an unrequested change in TransformUtilities.cs. Declared normalization shown in the report.",
        {"flash": "gemini-3.8-flash", "pro": "gemini-3.8-flash", "fiscal": NOT_RUN},
    ),
    DemoSpec(
        "2129", "2129",
        "Feature where the AI's own change test was wrong: the system does not approve, and the independent invariance "
        "oracle shows no regressions, pointing the human at the test instead of the code.",
        {"flash": "gemini-3.8-flash", "pro": "gemini-3.8-flash", "fiscal": NOT_RUN},
    ),
)


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def from_fixtures(issue_id: str) -> Report:
    """Etapas 1 y 2 reales desde fixtures; sin Etapa 3 (objeciones = None → M7 para lo que la necesitaría)."""
    spec, settings = get_issue(issue_id), load_settings()
    triage = tuple(FileTriage.model_validate(t) for t in _load(f"triage_{issue_id}.json"))
    evidence = _load(f"evidence_{issue_id}.json")
    change_test = ChangeTestEvidence.model_validate(evidence["change_test"])
    invariance = InvarianceEvidence.model_validate(evidence["invariance"])
    return Report(
        issue_id=issue_id,
        change_type=spec.change_type,
        branch=spec.branch,
        base_commit=settings.ref(issue_id, "base"),
        pr_commit=settings.ref(issue_id, "pr"),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        triage=triage,
        change_test=change_test,
        invariance=invariance,
        verdicts=tuple(decide(t, change_test, invariance, None) for t in triage),
    )


def _report(d: DemoSpec, translate: Callable[..., Report]) -> tuple[Report, str]:
    if not d.recorded:
        return apply_trust(from_fixtures(d.issue_id), load_record()), FIXTURE_NOTICE
    report = Report.model_validate(_load(d.recorded))
    notice = ""
    if d.translate:
        report, notice = translate(report), TRANSLATED_NOTICE
    return apply_trust(recompute_verdicts(report), load_record()), notice


def _index(rows: list[tuple[DemoSpec, Report, str]]) -> str:
    items = []
    for d, report, title in rows:
        counts = Counter(v.verdict for v in report.verdicts)
        tally = " · ".join(f"{counts[k]} {k.value.lower()}" for k in (Verdict.GREEN, Verdict.YELLOW, Verdict.RED))
        items.append(
            f'<li><a href="{d.slug}.html">{html.escape(title)}</a>'
            f'<span class="tag">{html.escape(d.tag)}</span><p>{html.escape(d.blurb)}</p><p class="tally">{tally}</p></li>'
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Proof, not promises: demo reports</title>
<style>
:root {{ --paper: #f6f4ef; --sheet: #fffdf9; --ink: #1c2330; --ink-2: #4a5363; --rule: #e3ded3; --accent: #2b4f8c; }}
@media (prefers-color-scheme: dark) {{ :root {{ --paper: #12151b; --sheet: #191d25; --ink: #e9ecf1; --ink-2: #a3acba; --rule: #2a303b; --accent: #8fb0ff; }} }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font: 15px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
main {{ max-width: 860px; margin: 0 auto; padding: 40px 16px 64px; }}
h1 {{ font: 600 30px/1.2 "Iowan Old Style", Charter, Georgia, serif; margin: 6px 0 8px; }}
.eyebrow {{ font: 600 11.5px/1.4 system-ui, sans-serif; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-2); }}
.lede {{ color: var(--ink-2); }}
ul {{ list-style: none; padding: 0; }}
li {{ background: var(--sheet); border: 1px solid var(--rule); border-radius: 12px; padding: 16px 18px; margin: 12px 0; }}
li a {{ font: 600 17px/1.35 "Iowan Old Style", Charter, Georgia, serif; color: var(--accent); }}
li p {{ margin: 6px 0 0; color: var(--ink-2); }}
.tag {{ font: 12px ui-monospace, Consolas, monospace; margin-left: 10px; color: var(--ink-2); }}
.tally {{ font: 12.5px ui-monospace, Consolas, monospace; }}
</style>
</head>
<body>
<main>
<div class="eyebrow">Evidence Ledger · Tieto — Earned Trust in AI Code</div>
<h1>Proof, not promises: demo reports</h1>
<p class="lede">One sign-off report per real AI-written pull request. Each report says what is proven, what a human must read, and why.</p>
<ul>
{chr(10).join(items)}
</ul>
</main>
</body>
</html>
"""


def build_demo(out_dir: Path = DEFAULT_OUT, *, translate: Callable[..., Report] = translate_llm_text) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written, rows = [], []
    for d in DEMOS:
        report, notice = _report(d, translate)
        _, title = _context(d.issue_id)
        target = out_dir / f"{d.slug}.html"
        target.write_text(render_html(report, models=d.models, issue_title=title, notice=notice), encoding="utf-8")
        written.append(target)
        rows.append((d, report, title))
    (out_dir / "index.html").write_text(_index(rows), encoding="utf-8")
    return written


if __name__ == "__main__":
    for path in build_demo(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT):
        print(path)
