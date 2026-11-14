"""Lo que firma el responsable (reto de Tieto, "What the owner signs"), derivado SOLO del `Report`:

- qué se comprobó, y con qué (reglas, modelo o test);
- qué NO se comprobó, y por qué (objeciones abiertas, negativas a decidir, ficheros verdes que nadie leyó);
- el riesgo residual que acepta al firmar.

Función pura: el mismo informe da siempre el mismo texto. No hay puntuación de confianza: solo hechos contables.
"""

from __future__ import annotations

from ledger.models import ChangeType, InvarianceEvidence, Report, Risk, Scope, Verdict


def _n(n: int, word: str) -> str:
    return f"{n} {word if n == 1 else word + 's'}"


def _guarded_cases(inv: InvarianceEvidence) -> list[str]:
    """Casos que el cambio NO debe alterar (los de fuera del issue)."""
    own = f"issue-{inv.issue_id}"
    return [c.id for c in inv.cases if (c.tag != own if inv.issue_id else c.tag == "general")]


def _checked(report: Report, models: dict[str, str]) -> list[str]:
    triage = report.triage
    lines = [
        f"Scope and risk of {_n(len(triage), 'file')}: risk by static rules (no model), scope by {models.get('flash', '?')} "
        f"against the literal issue text ({sum(t.scope is Scope.OUT for t in triage)} out of scope, "
        f"{sum(t.risk is Risk.HIGH for t in triage)} high risk)."
    ]
    ct = report.change_test
    if ct is not None:
        if ct.change_type is ChangeType.BUGFIX:
            outcome = "red on base, green on PR" if ct.ok else "did NOT go red on base and green on PR"
        else:
            outcome = "green on PR" if ct.ok else "NOT green on PR"
        lines.append(f"Change test `{ct.test_name}`, written by {models.get('pro', '?')} from the issue only (never saw the diff): {outcome}.")
    inv = report.invariance
    if inv is not None:
        guarded = _guarded_cases(inv)
        identical = len(guarded) - len(inv.unexpected_diffs)
        lines.append(
            f"Generation invariance (generated code + diagnostics, base and PR in isolated processes): {identical}/{len(guarded)} "
            f"cases outside the issue identical; base {'deterministic' if inv.deterministic else 'NOT deterministic'} on rerun."
        )
    objections = [o for v in report.verdicts for o in v.objections]
    if objections:
        lines.append(
            f"Cross-examination: {sum(o.valid for o in objections)} of {_n(len(objections), 'objection')} closed by a test that passes "
            f"on the PR and fails against a mutant (Prosecutor {models.get('fiscal', '?')}, Defender {models.get('pro', '?')})."
        )
    return lines


def _not_checked(report: Report) -> list[str]:
    lines: list[str] = []
    if report.change_test is None:
        lines.append("There is no change test: the requirement itself is unverified.")
    if report.invariance is None:
        lines.append("There is no invariance evidence: behaviour outside the issue is unverified.")
    for v in report.verdicts:
        code = v.reasons[0].split(":", 1)[0] if v.reasons else ""
        open_questions = [o.question for o in v.objections if not o.valid]
        if code == "M7":
            lines.append(f"{v.path}: the system refused to decide (high risk without a closed cross-examination).")
        elif code == "M1":
            lines.append(f"{v.path}: out of the issue's scope and high risk; no evidence can approve an unrequested change.")
        elif code == "M2":
            lines.append(f"{v.path}: out of the issue's scope; only the agent's justification backs it, no test covers why it changed.")
        elif code == "M3":
            lines.append(f"{v.path}: the executable evidence failed or is missing.")
        lines.extend(f"  Open question on {v.path}: {q}" for q in open_questions)
    unread = sum(v.verdict is Verdict.GREEN and not v.objections for v in report.verdicts)
    if unread:
        lines.append(f"{_n(unread, 'green file')} not read and not individually tested: approved by the shared evidence above.")
    return lines


def _residual(report: Report) -> list[str]:
    lines: list[str] = []
    if report.invariance is not None:
        lines.append(
            f"Behaviour outside the issue is only as covered as the {_n(len(report.invariance.cases), 'invariance case')}; "
            "the oracle is generated code and diagnostics, not runtime serialization."
        )
    if report.change_test is not None:
        lines.append("The change test and the Defender tests were written by an AI: they cover the edge cases somebody asked about, not all of them.")
    open_count = sum(not o.valid for v in report.verdicts for o in v.objections)
    if open_count:
        lines.append(f"{_n(open_count, 'open objection')}: if I approve, I accept that these questions stay unanswered.")
    return lines


def signoff(report: Report, models: dict[str, str]) -> dict[str, list[str]]:
    return {"checked": _checked(report, models), "not_checked": _not_checked(report), "residual": _residual(report)}
