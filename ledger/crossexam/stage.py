"""Etapa 3 + veredictos (B): interroga los fragmentos IN/HIGH y aplica la matriz a todos los ficheros.

`pipeline.stage3_and_verdicts` solo delega aquí. Solo se interroga lo que lo necesita: IN y HIGH, y
solo si la evidencia de la Etapa 2 pasó (si no, el veredicto ya es M3 y el interrogatorio sería gasto).

Si el interrogatorio no puede ejecutarse (sin repo, sin clave, el LLM falla), el fichero queda en M7
"se niega a decidir" con el motivo en las razones: el pipeline nunca se cae por esto.
"""

from __future__ import annotations

from ledger import llm
from ledger.config import Settings
from ledger.crossexam.loop import cross_examine
from ledger.fakes import FakeTestRunner
from ledger.models import ChangeTestEvidence, FileTriage, FragmentVerdict, InvarianceEvidence, Risk, Scope, TestRunner
from ledger.triage.diff import load_diff, read_file_at
from ledger.triage.scope import Complete, load_issue_text
from ledger.verdict import decide, evidence_lines

MAX_ERROR_CHARS = 300


def _needs_crossexam(t: FileTriage) -> bool:
    return t.scope is Scope.IN and t.risk is Risk.HIGH


def _short(exc: Exception) -> str:
    return str(exc)[:MAX_ERROR_CHARS]


def judge_issue(
    issue_id: str,
    triage: tuple[FileTriage, ...],
    change_test: ChangeTestEvidence | None,
    invariance: InvarianceEvidence | None,
    runner: TestRunner,
    settings: Settings,
    *,
    complete: Complete = llm.complete,
) -> tuple[FragmentVerdict, ...]:
    evidence_ok = bool(change_test and change_test.ok and invariance and invariance.ok)
    targets = [t for t in triage if _needs_crossexam(t)] if evidence_ok else []

    issue_text, diffs, setup_error = "", {}, ""
    if targets and isinstance(runner, FakeTestRunner):
        # Con el runner falso ningún test se ejecuta: "validar" objeciones así sería aprobar sin prueba.
        setup_error = "Stage 3 needs a real test runner (dotnet or Modal); the fake runner cannot validate any test"
    elif targets:
        try:
            issue_text = load_issue_text(settings, issue_id)
            diffs = {fd.path: fd for fd in load_diff(settings, issue_id)}
        except ValueError as exc:
            setup_error = _short(exc)

    summary = "\n".join(evidence_lines(change_test, invariance))
    verdicts = []
    for t in triage:
        objections, note = None, ""
        if t in targets:
            fd = diffs.get(t.path)
            if setup_error or fd is None:
                note = f"cross-examination not run: {setup_error or 'the file is not in the diff'}"
            else:
                try:
                    objections = cross_examine(
                        issue_id, issue_text, fd, runner,
                        read_source=lambda path: read_file_at(settings, issue_id, "pr", path),
                        evidence_summary=summary, complete=complete, settings=settings,
                    )
                except (llm.LLMError, ValueError) as exc:
                    note = f"cross-examination not run: {_short(exc)}"
        verdict = decide(t, change_test, invariance, objections)
        if note:
            verdict = verdict.model_copy(update={"reasons": (*verdict.reasons, note)})
        verdicts.append(verdict)
    return tuple(verdicts)
