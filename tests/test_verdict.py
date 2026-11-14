"""Matriz de veredictos (ARQUITECTURA §2-§3, PERSONA-B paso 4). Un test por fila, más los huecos de la tabla."""

from __future__ import annotations

import pytest

from ledger.fakes import GREEN, RED
from ledger.models import (
    ChangeTestEvidence,
    ChangeType,
    FileTriage,
    InvarianceCase,
    InvarianceEvidence,
    Objection,
    Risk,
    Scope,
    TestRunResult,
    Verdict,
)
from ledger.verdict import decide

BUILD_FAIL = TestRunResult(build_ok=False, passed=0, failed=0, output_tail="error CS0246")

GOOD_TEST = ChangeTestEvidence(issue_id="2283", change_type=ChangeType.BUGFIX, test_name="T", test_code="...", base=RED, pr=GREEN)
BAD_TEST = GOOD_TEST.model_copy(update={"pr": RED})
GOOD_INV = InvarianceEvidence(
    cases=(
        InvarianceCase(id="int-keys", tag="general", base_hash="a", base_hash_rerun="a", pr_hash="a"),
        InvarianceCase(id="issue", tag="issue-2283", base_hash="b", base_hash_rerun="b", pr_hash="c"),
    )
)
BAD_INV = InvarianceEvidence(cases=(InvarianceCase(id="int-keys", tag="general", base_hash="a", base_hash_rerun="a", pr_hash="z"),))
NON_DETERMINISTIC = InvarianceEvidence(cases=(InvarianceCase(id="dict", tag="general", base_hash="a", base_hash_rerun="b", pr_hash="a"),))

VALID = Objection(question="¿Y con un buffer vacío?", test_name="Empty", test_code="Assert.Empty(x)", pr_result=GREEN, mutant_result=RED)
TRIVIAL = Objection(question="¿Y con tipos anidados de otro ensamblado?", test_name="Nested", test_code="Assert.True(true)", pr_result=GREEN, mutant_result=GREEN)


def tri(scope: Scope, risk: Risk, public: bool = False, justification: str = "justificación del agente") -> FileTriage:
    return FileTriage(path="src/X.cs", scope=scope, risk=risk, justification=justification, touches_public_api=public)


def row(v) -> str:
    return v.reasons[0].split(":")[0]


# --------------------------------------------------------------------------- filas de la matriz


def test_m1_out_high_is_red_even_with_good_evidence():
    v = decide(tri(Scope.OUT, Risk.HIGH), GOOD_TEST, GOOD_INV, (VALID,))
    assert (v.verdict, row(v)) == (Verdict.RED, "M1")


@pytest.mark.parametrize("risk", [Risk.MED, Risk.LOW])
def test_m2_out_med_or_low_is_yellow_with_justification(risk):
    v = decide(tri(Scope.OUT, risk, justification="documenta el cambio"), GOOD_TEST, GOOD_INV)
    assert (v.verdict, row(v)) == (Verdict.YELLOW, "M2")
    assert any("documenta el cambio" in r for r in v.reasons)


@pytest.mark.parametrize("risk", [Risk.LOW, Risk.MED, Risk.HIGH])
@pytest.mark.parametrize(("test", "inv"), [(BAD_TEST, GOOD_INV), (GOOD_TEST, BAD_INV)])
def test_m3_in_with_failed_evidence_is_red(risk, test, inv):
    v = decide(tri(Scope.IN, risk), test, inv, (VALID,))
    assert (v.verdict, row(v)) == (Verdict.RED, "M3")


@pytest.mark.parametrize("risk", [Risk.LOW, Risk.MED])
def test_m4_in_low_or_med_with_good_evidence_is_green(risk):
    v = decide(tri(Scope.IN, risk), GOOD_TEST, GOOD_INV)
    assert (v.verdict, row(v)) == (Verdict.GREEN, "M4")


def test_m5_in_high_all_objections_valid_no_public_is_green():
    v = decide(tri(Scope.IN, Risk.HIGH), GOOD_TEST, GOOD_INV, (VALID, VALID))
    assert (v.verdict, row(v)) == (Verdict.GREEN, "M5")
    assert v.objections == (VALID, VALID)


def test_m6_in_high_all_objections_valid_with_public_is_yellow():
    v = decide(tri(Scope.IN, Risk.HIGH, public=True), GOOD_TEST, GOOD_INV, (VALID,))
    assert (v.verdict, row(v)) == (Verdict.YELLOW, "M6")


def test_m7_in_high_unresolved_objection_refuses_and_quotes_the_fiscal():
    v = decide(tri(Scope.IN, Risk.HIGH), GOOD_TEST, GOOD_INV, (VALID, TRIVIAL))
    assert (v.verdict, row(v)) == (Verdict.RED, "M7")
    assert any("se niega a decidir" in r for r in v.reasons)
    assert any(TRIVIAL.question in r for r in v.reasons)
    assert not any(VALID.question in r for r in v.reasons)


# --------------------------------------------------------------------------- huecos de la tabla (decisión prudente)


@pytest.mark.parametrize(("test", "inv"), [(None, GOOD_INV), (GOOD_TEST, None), (None, None)])
def test_in_without_evidence_is_red(test, inv):
    v = decide(tri(Scope.IN, Risk.LOW), test, inv)
    assert (v.verdict, row(v)) == (Verdict.RED, "M3")
    assert any("falta" in r for r in v.reasons)


def test_in_high_without_crossexam_refuses():
    v = decide(tri(Scope.IN, Risk.HIGH), GOOD_TEST, GOOD_INV, None)
    assert (v.verdict, row(v)) == (Verdict.RED, "M7")


def test_in_high_fiscal_raised_nothing_passes_and_says_so():
    v = decide(tri(Scope.IN, Risk.HIGH), GOOD_TEST, GOOD_INV, ())
    assert (v.verdict, row(v)) == (Verdict.GREEN, "M5")
    assert any("no planteó objeciones" in r for r in v.reasons)


def test_bugfix_whose_test_does_not_compile_in_base_is_not_a_reproduction():
    no_repro = GOOD_TEST.model_copy(update={"base": BUILD_FAIL})
    v = decide(tri(Scope.IN, Risk.LOW), no_repro, GOOD_INV)
    assert v.verdict is Verdict.RED
    assert any("base" in r for r in v.reasons)


def test_non_deterministic_base_is_red():
    v = decide(tri(Scope.IN, Risk.LOW), GOOD_TEST, NON_DETERMINISTIC)
    assert v.verdict is Verdict.RED
    assert any("determinista" in r for r in v.reasons)


def test_unexpected_diff_names_the_case():
    v = decide(tri(Scope.IN, Risk.LOW), GOOD_TEST, BAD_INV)
    assert any("int-keys" in r for r in v.reasons)


def test_defensor_test_failing_on_the_pr_is_flagged_as_a_possible_defect():
    """El test del Defensor compila y FALLA en el PR: puede que el Fiscal tenga razón y el defecto sea del PR."""
    defect = Objection(question="¿Y la línea 735?", test_name="T", test_code="x", pr_result=RED, mutant_result=None)
    v = decide(tri(Scope.IN, Risk.HIGH), GOOD_TEST, GOOD_INV, (VALID, defect))
    assert (v.verdict, row(v)) == (Verdict.RED, "M7")
    flagged = [r for r in v.reasons if "¿Y la línea 735?" in r]
    assert flagged and "falla en el PR" in flagged[0] and "posible defecto" in flagged[0]


def test_defensor_test_that_does_not_compile_is_not_called_a_defect():
    broken = Objection(question="¿Y si no compila?", test_name="T", test_code="x", pr_result=BUILD_FAIL)
    v = decide(tri(Scope.IN, Risk.HIGH), GOOD_TEST, GOOD_INV, (broken,))
    assert not any("posible defecto" in r for r in v.reasons)


def test_failed_change_test_with_clean_invariance_points_the_human_at_the_test():
    """Caso #2129: el test generado falla en el PR pero la invarianza no ve regresiones → sigue ROJO, con pista."""
    v = decide(tri(Scope.IN, Risk.MED), BAD_TEST, GOOD_INV)
    assert (v.verdict, row(v)) == (Verdict.RED, "M3")
    assert any("no muestra regresiones" in r and "revisa el test generado" in r for r in v.reasons)


def test_no_test_hint_when_the_invariance_also_fails():
    v = decide(tri(Scope.IN, Risk.MED), BAD_TEST, BAD_INV)
    assert not any("revisa el test generado" in r for r in v.reasons)


def test_feature_only_needs_green_on_pr():
    feature = ChangeTestEvidence(issue_id="2297", change_type=ChangeType.FEATURE, test_name="T", test_code="...", base=None, pr=GREEN)
    assert decide(tri(Scope.IN, Risk.MED), feature, GOOD_INV).verdict is Verdict.GREEN


def test_out_files_do_not_carry_objections():
    assert decide(tri(Scope.OUT, Risk.LOW), GOOD_TEST, GOOD_INV, (VALID,)).objections == ()


def test_verdict_keeps_path_and_is_pure():
    t = tri(Scope.IN, Risk.MED)
    a, b = decide(t, GOOD_TEST, GOOD_INV), decide(t, GOOD_TEST, GOOD_INV)
    assert a == b and a.path == "src/X.cs"
