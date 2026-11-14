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

REFUSE = "el sistema se niega a decidir"


def _run(result: TestRunResult | None) -> str:
    if result is None:
        return "no ejecutado"
    if not result.build_ok:
        return "no compila"
    if result.green:
        return f"verde ({result.passed} ok)"
    if result.red_for_real:
        return f"rojo ({result.failed} fallan)"
    return "sin tests ejecutados"


def _change_test_reasons(ct: ChangeTestEvidence | None) -> list[str]:
    if ct is None:
        return ["falta el test del cambio"]
    summary = f"test del cambio `{ct.test_name}`: base {_run(ct.base)}, PR {_run(ct.pr)}"
    if ct.ok:
        return [summary]
    problems = []
    if ct.change_type is ChangeType.BUGFIX and not (ct.base and ct.base.red_for_real):
        problems.append("no reproduce el bug en base")
    if not ct.pr.green:
        problems.append("no pasa en el PR")
    return [f"{summary} → {', '.join(problems)}"]


def _invariance_reasons(inv: InvarianceEvidence | None) -> list[str]:
    if inv is None:
        return ["falta la evidencia de invarianza"]
    if not inv.cases:
        return ["invarianza sin casos"]
    reasons = []
    if not inv.deterministic:
        unstable = [c.id for c in inv.cases if c.base_hash != c.base_hash_rerun]
        reasons.append(f"la base no es determinista (casos: {', '.join(unstable)})")
    if inv.unexpected_diffs:
        reasons.append(f"diferencias fuera del alcance del issue en: {', '.join(inv.unexpected_diffs)}")
    if not reasons:
        general = sum(c.tag == "general" for c in inv.cases)
        reasons.append(f"invarianza: determinista, {general} casos generales idénticos")
    return reasons


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
            return _verdict(triage, Verdict.RED, "M1", "fuera del alcance del issue y riesgo alto", [*triage.rule_hits])
        return _verdict(triage, Verdict.YELLOW, "M2", f"fuera del alcance, riesgo {risk.value}: revisar la justificación", [f"justificación: {triage.justification}"])

    evidence = evidence_lines(change_test, invariance)
    evidence_ok = change_test is not None and change_test.ok and invariance is not None and invariance.ok
    if not evidence_ok:
        if change_test is not None and not change_test.ok and invariance is not None and invariance.ok:
            # Caso #2129: sigue ROJO (sin prueba no se aprueba), pero el oráculo diferencial orienta al humano.
            evidence.append("la evidencia diferencial no muestra regresiones; revisa el test generado antes que el código")
        return _verdict(triage, Verdict.RED, "M3", "la evidencia ejecutable falla o falta", evidence)

    if risk is not Risk.HIGH:
        return _verdict(triage, Verdict.GREEN, "M4", f"en alcance, riesgo {risk.value}, evidencia superada", evidence)

    if objections is None:
        return _verdict(triage, Verdict.RED, "M7", f"riesgo alto sin interrogatorio: {REFUSE}", evidence)

    unresolved = [o for o in objections if not o.valid]
    if unresolved:
        questions = [f"objeción sin test válido: «{o.question}»" for o in unresolved]
        return _verdict(triage, Verdict.RED, "M7", f"{len(unresolved)} objeción(es) sin resolver: {REFUSE}", questions + evidence, objections)

    crossexam = [f"{len(objections)} objeción(es) del Fiscal cubiertas por tests que fallan contra el mutante"] if objections else ["el Fiscal no planteó objeciones"]
    if triage.touches_public_api:
        return _verdict(triage, Verdict.YELLOW, "M6", "comportamiento probado; toca API public: validar solo el diseño de la firma", crossexam + evidence, objections)
    return _verdict(triage, Verdict.GREEN, "M5", "riesgo alto superado en el interrogatorio", crossexam + evidence, objections)
