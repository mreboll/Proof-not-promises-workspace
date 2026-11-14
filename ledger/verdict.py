"""Matriz de veredictos (ARQUITECTURA §2-§3). Función pura: misma entrada, mismo veredicto.

| Fila | Alcance | Riesgo   | Evidencia e interrogatorio                    | Veredicto |
|------|---------|----------|-----------------------------------------------|-----------|
| M1   | OUT     | HIGH     | —                                             | RED       |
| M2   | OUT     | MED/LOW  | — (con la justificación del agente)           | YELLOW    |
| M3   | IN      | cualquier| falta evidencia, o falla test del cambio/invarianza | RED  |
| M4   | IN      | LOW/MED  | evidencia ok                                  | GREEN     |
| M5   | IN      | HIGH     | todas las objeciones con test válido, sin public | GREEN  |
| M6   | IN      | HIGH     | todas válidas, toca public                    | YELLOW    |
| M7   | IN      | HIGH     | alguna objeción sin test válido, o sin interrogatorio | RED "se niega a decidir" |

Huecos que la guía no cubre, resueltos por el lado prudente:
- Sin evidencia (None) → M3: sin pruebas no se aprueba.
- HIGH con `objections=None` (la Etapa 3 no se ejecutó) → M7. Una tupla vacía significa que el
  Fiscal se ejecutó y no objetó nada: pasa, y queda escrito en las razones.

La primera razón siempre empieza por el id de la fila ("M4: ..."), para auditar qué regla decidió.
"""

from __future__ import annotations

from ledger.models import (
    ChangeTestEvidence,
    ChangeType,
    FileTriage,
    FragmentVerdict,
    InvarianceEvidence,
    Objection,
    Risk,
    Scope,
    TestRunResult,
    Verdict,
)

REFUSE = "the system refuses to decide"


def _run(result: TestRunResult | None) -> str:
    if result is None:
        return "not run"
    if not result.build_ok:
        return "does not compile"
    if result.green:
        return f"green ({result.passed} passed)"
    if result.red_for_real:
        return f"red ({result.failed} failed)"
    return "no tests run"


def _change_test_reasons(ct: ChangeTestEvidence | None) -> list[str]:
    if ct is None:
        return ["change test missing"]
    summary = f"change test `{ct.test_name}`: base {_run(ct.base)}, PR {_run(ct.pr)}"
    if ct.ok:
        return [summary]
    problems = []
    if ct.change_type is ChangeType.BUGFIX and not (ct.base and ct.base.red_for_real):
        problems.append("does not reproduce the bug on base")
    if not ct.pr.green:
        problems.append("does not pass on the PR")
    return [f"{summary} → {', '.join(problems)}"]


def _invariance_reasons(inv: InvarianceEvidence | None) -> list[str]:
    if inv is None:
        return ["invariance evidence missing"]
    if not inv.cases:
        return ["invariance has no cases"]
    reasons = []
    if not inv.deterministic:
        unstable = [c.id for c in inv.cases if c.base_hash != c.base_hash_rerun]
        reasons.append(f"base is not deterministic (cases: {', '.join(unstable)})")
    if inv.unexpected_diffs:
        reasons.append(f"output changes outside the issue's scope in: {', '.join(inv.unexpected_diffs)}")
    if not reasons:
        general = sum(c.tag == "general" for c in inv.cases)
        reasons.append(f"invariance: deterministic, {general} general cases identical")
    return reasons


def defensor_test_fails_on_pr(o: Objection) -> bool:
    """El test del Defensor compila y falla en el PR: quizá el Fiscal tenga razón y el defecto sea del PR."""
    return o.pr_result is not None and o.pr_result.red_for_real


def _unresolved_reason(o: Objection) -> str:
    if defensor_test_fails_on_pr(o):
        return f"objection “{o.question}”: the Defender's test fails on the PR → possible defect in the PR, check the test output"
    return f"objection without a valid test: “{o.question}”"


def evidence_lines(change_test: ChangeTestEvidence | None, invariance: InvarianceEvidence | None) -> list[str]:
    """Resumen legible de la evidencia de la Etapa 2 (lo usan las razones del veredicto y el Fiscal)."""
    return _change_test_reasons(change_test) + _invariance_reasons(invariance)


def _verdict(triage: FileTriage, verdict: Verdict, row: str, why: str, extra: list[str], objections: tuple[Objection, ...] = ()) -> FragmentVerdict:
    return FragmentVerdict(path=triage.path, verdict=verdict, reasons=(f"{row}: {why}", *extra), objections=objections)


def decide(
    triage: FileTriage,
    change_test: ChangeTestEvidence | None,
    invariance: InvarianceEvidence | None,
    objections: tuple[Objection, ...] | None = None,
) -> FragmentVerdict:
    scope, risk = triage.scope, triage.risk

    if scope is Scope.OUT:
        if risk is Risk.HIGH:
            return _verdict(triage, Verdict.RED, "M1", "out of the issue's scope and high risk", [*triage.rule_hits])
        return _verdict(triage, Verdict.YELLOW, "M2", f"out of scope, {risk.value} risk: review the justification", [f"justification: {triage.justification}"])

    evidence = evidence_lines(change_test, invariance)
    evidence_ok = change_test is not None and change_test.ok and invariance is not None and invariance.ok
    if not evidence_ok:
        if change_test is not None and not change_test.ok and invariance is not None and invariance.ok:
            # Caso #2129: sigue ROJO (sin prueba no se aprueba), pero el oráculo diferencial orienta al humano.
            evidence.append("the differential evidence shows no regressions; check the generated test before the code")
        return _verdict(triage, Verdict.RED, "M3", "executable evidence fails or is missing", evidence)

    if risk is not Risk.HIGH:
        return _verdict(triage, Verdict.GREEN, "M4", f"in scope, {risk.value} risk, evidence passed", evidence)

    if objections is None:
        return _verdict(triage, Verdict.RED, "M7", f"high risk without cross-examination: {REFUSE}", evidence)

    unresolved = [o for o in objections if not o.valid]
    if unresolved:
        questions = [_unresolved_reason(o) for o in unresolved]
        return _verdict(triage, Verdict.RED, "M7", f"{len(unresolved)} unresolved objection(s): {REFUSE}", questions + evidence, objections)

    crossexam = [f"{len(objections)} Prosecutor objection(s) covered by tests that fail against their mutant"] if objections else ["the Prosecutor raised no objections"]
    if triage.touches_public_api:
        return _verdict(triage, Verdict.YELLOW, "M6", "behaviour proven; touches public API: review only the signature design", crossexam + evidence, objections)
    return _verdict(triage, Verdict.GREEN, "M5", "high risk passed the cross-examination", crossexam + evidence, objections)
