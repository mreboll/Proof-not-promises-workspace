"""Bloque de firma: lo que el responsable firma según el reto (qué se comprobó y con qué, qué NO y por qué, riesgo residual)."""

from __future__ import annotations

from ledger.fakes import GREEN, RED
from ledger.models import (
    ChangeTestEvidence, ChangeType, FileTriage, FragmentVerdict, InvarianceCase, InvarianceEvidence, Objection, Report, Risk,
    Scope, Verdict,
)
from ledger.report.render import render_html
from ledger.report.signoff import signoff

MODELS = {"flash": "flash-m", "pro": "pro-m", "fiscal": "fiscal-m"}
CT = ChangeTestEvidence(issue_id="1", change_type=ChangeType.BUGFIX, test_name="T", test_code="...", base=RED, pr=GREEN)
INV = InvarianceEvidence(issue_id="1", cases=(
    InvarianceCase(id="g1", tag="general", base_hash="a", base_hash_rerun="a", pr_hash="a"),
    InvarianceCase(id="i1", tag="issue-1", base_hash="b", base_hash_rerun="b", pr_hash="c"),
))
TRIAGE = (
    FileTriage(path="src/Low.cs", scope=Scope.IN, risk=Risk.LOW),
    FileTriage(path="src/High.cs", scope=Scope.IN, risk=Risk.HIGH),
    FileTriage(path="src/Out.cs", scope=Scope.OUT, risk=Risk.HIGH),
)
VALID = Objection(question="q ok", test_name="Ledger_1_Objection1", pr_result=GREEN, mutant_patch="p", mutant_result=RED)
OPEN = Objection(question="does it crash on X?", test_name="Ledger_1_Objection2", pr_result=RED, mutant_patch="p")
VERDICTS = (
    FragmentVerdict(path="src/Low.cs", verdict=Verdict.GREEN, reasons=("M4: in scope",)),
    FragmentVerdict(path="src/High.cs", verdict=Verdict.RED, reasons=("M7: 1 unresolved objection(s)",), objections=(VALID, OPEN)),
    FragmentVerdict(path="src/Out.cs", verdict=Verdict.RED, reasons=("M1: out of scope and high risk",)),
)


def _report(**changes) -> Report:
    base = dict(issue_id="1", change_type=ChangeType.BUGFIX, branch="b", base_commit="x", pr_commit="y", generated_at="t",
                triage=TRIAGE, change_test=CT, invariance=INV, verdicts=VERDICTS)
    return Report(**{**base, **changes})


def test_checked_says_what_was_checked_and_by_what():
    checked = "\n".join(signoff(_report(), MODELS)["checked"])
    assert "3 files" in checked and "static rules" in checked and "flash-m" in checked
    assert "red on base, green on PR" in checked and "pro-m" in checked
    assert "1/1" in checked  # casos de invarianza fuera del issue idénticos
    assert "1 of 2 objections" in checked and "fiscal-m" in checked and "mutant" in checked


def test_not_checked_lists_open_questions_refusals_and_unread_green_files():
    not_checked = "\n".join(signoff(_report(), MODELS)["not_checked"])
    assert "does it crash on X?" in not_checked
    assert "src/High.cs" in not_checked and "refused to decide" in not_checked
    assert "src/Out.cs" in not_checked
    assert "1 green file" in not_checked and "not read" in not_checked


def test_residual_risk_names_the_oracle_limits_and_open_questions():
    residual = "\n".join(signoff(_report(), MODELS)["residual"])
    assert "2 invariance cases" in residual
    assert "runtime" in residual  # el oráculo es el código generado, no la serialización en ejecución
    assert "1 open objection" in residual


def test_missing_evidence_is_said_plainly():
    s = signoff(_report(change_test=None, invariance=None, verdicts=()), MODELS)
    assert any("no change test" in line for line in s["not_checked"])
    assert any("no invariance" in line for line in s["not_checked"])


def test_html_signoff_block_contains_the_three_sections():
    html = render_html(_report(), models=MODELS, issue_title="t")
    for heading in ("What was checked, and by what", "What was NOT checked, and why", "Residual risk I accept"):
        assert heading in html
    assert "does it crash on X?" in html


def test_out_of_scope_low_risk_files_say_only_the_justification_backs_them():
    verdicts = (*VERDICTS, FragmentVerdict(path="src/Doc.cs", verdict=Verdict.YELLOW, reasons=("M2: out of scope, low risk",)))
    not_checked = " | ".join(signoff(_report(verdicts=verdicts), MODELS)["not_checked"])
    assert "src/Doc.cs" in not_checked and "justification" in not_checked
