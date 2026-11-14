"""Orquestador: Etapa 1 → 2 → 3 → informe. CONJUNTO (se cablea en la integración de la H8).

Cada etapa es una función con su dueño. Hasta que exista la implementación real, la etapa
lanza NotImplementedError indicando quién la entrega, y `run(..., use_fixtures=True)` usa
los JSON de `fixtures/` para que el otro pueda avanzar.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ledger.config import PROJECT_ROOT, Settings, get_issue
from ledger.models import (
    ChangeTestEvidence,
    FileTriage,
    FragmentVerdict,
    InvarianceEvidence,
    Report,
    TestRunner,
)

FIXTURES_DIR = PROJECT_ROOT / "fixtures"


def stage1_triage(issue_id: str, settings: Settings) -> tuple[FileTriage, ...]:
    """Línea B: ledger/triage (diff.py + rules.py + scope.py), orquestado en ledger/triage/stage.py."""
    from ledger.triage import stage  # import local: así el cableado no toca la cabecera compartida

    return stage.triage_issue(settings, issue_id)


def stage2_change_test(issue_id: str, settings: Settings, runner: TestRunner) -> ChangeTestEvidence:
    """Línea A: ledger/evidence/change_test.py."""
    from ledger.evidence.change_test import generate_change_test

    return generate_change_test(issue_id, settings, runner)


def stage2_invariance(issue_id: str, settings: Settings) -> InvarianceEvidence:
    """Línea A: ledger/evidence/invariance.py + harness/GeneratorProbe."""
    from ledger.evidence.invariance import collect_invariance

    return collect_invariance(settings, issue_id)


def stage3_and_verdicts(
    issue_id: str,
    triage: tuple[FileTriage, ...],
    change_test: ChangeTestEvidence | None,
    invariance: InvarianceEvidence | None,
    runner: TestRunner,
    settings: Settings,
) -> tuple[FragmentVerdict, ...]:
    """Línea B: ledger/crossexam + ledger/verdict.py, orquestado en ledger/crossexam/stage.py."""
    from ledger.crossexam import stage as crossexam_stage  # import local: no toca la cabecera compartida

    return crossexam_stage.judge_issue(issue_id, triage, change_test, invariance, runner, settings)


def render_report(report: Report, out_dir: Path) -> Path:
    """Línea B: ledger/report/render.py. Hasta entonces, vuelca el JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"report-{report.issue_id}.json"
    target.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return target


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def run(issue_id: str, settings: Settings, runner: TestRunner, *, use_fixtures: bool = False) -> Path:
    spec = get_issue(issue_id)

    if use_fixtures:
        triage = tuple(FileTriage.model_validate(t) for t in _load_fixture(f"triage_{issue_id}.json"))
        evidence = _load_fixture(f"evidence_{issue_id}.json")
        change_test = ChangeTestEvidence.model_validate(evidence["change_test"])
        invariance = InvarianceEvidence.model_validate(evidence["invariance"])
    else:
        triage = stage1_triage(issue_id, settings)
        change_test = stage2_change_test(issue_id, settings, runner)
        invariance = stage2_invariance(issue_id, settings)

    try:
        verdicts = stage3_and_verdicts(issue_id, triage, change_test, invariance, runner, settings)
    except NotImplementedError:
        if not use_fixtures:
            raise
        verdicts = ()

    report = Report(
        issue_id=issue_id,
        change_type=spec.change_type,
        branch=spec.branch,
        base_commit=settings.ref(issue_id, "base"),
        pr_commit=settings.ref(issue_id, "pr"),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        triage=triage,
        change_test=change_test,
        invariance=invariance,
        verdicts=verdicts,
    )
    return render_report(report, settings.out_dir)
