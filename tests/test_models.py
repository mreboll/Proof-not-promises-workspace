import pytest
from pydantic import ValidationError

from ledger.fakes import GREEN, RED
from ledger.models import (
    ChangeTestEvidence,
    ChangeType,
    InvarianceCase,
    InvarianceEvidence,
    Objection,
    TestRunResult,
)

BUILD_FAIL = TestRunResult(build_ok=False, passed=0, failed=0, output_tail="CS0246")


def _change(change_type: ChangeType, base: TestRunResult | None, pr: TestRunResult) -> ChangeTestEvidence:
    return ChangeTestEvidence(issue_id="2283", change_type=change_type, test_name="t", test_code="", base=base, pr=pr)


def test_bugfix_ok_when_test_fails_on_base_and_passes_on_pr():
    assert _change(ChangeType.BUGFIX, RED, GREEN).ok


def test_bugfix_not_ok_when_base_does_not_compile():
    # Un error de compilación en la base no demuestra que el bug se reproduzca.
    assert not _change(ChangeType.BUGFIX, BUILD_FAIL, GREEN).ok


def test_bugfix_not_ok_when_test_already_passes_on_base():
    assert not _change(ChangeType.BUGFIX, GREEN, GREEN).ok


def test_feature_ok_only_needs_green_pr():
    assert _change(ChangeType.FEATURE, None, GREEN).ok
    assert not _change(ChangeType.FEATURE, None, RED).ok


def _case(case_id: str, tag: str, base: str, rerun: str, pr: str) -> InvarianceCase:
    return InvarianceCase(id=case_id, tag=tag, base_hash=base, base_hash_rerun=rerun, pr_hash=pr)


def test_invariance_ok_when_only_issue_cases_differ():
    ev = InvarianceEvidence(cases=(_case("a", "general", "1", "1", "1"), _case("b", "issue-2283", "2", "2", "3")))
    assert ev.deterministic and ev.unexpected_diffs == () and ev.ok


def test_invariance_flags_general_case_that_changes():
    ev = InvarianceEvidence(cases=(_case("a", "general", "1", "1", "9"),))
    assert ev.unexpected_diffs == ("a",) and not ev.ok


def test_invariance_with_issue_id_flags_a_case_of_another_issue_that_changes():
    """Propuesta de A: si el PR de #2297 cambia un caso de #2129, también es una diferencia inesperada."""
    ev = InvarianceEvidence(
        issue_id="2297",
        cases=(_case("own", "issue-2297", "1", "1", "2"), _case("other", "issue-2129", "3", "3", "4"), _case("g", "general", "5", "5", "5")),
    )
    assert ev.unexpected_diffs == ("other",) and not ev.ok


def test_invariance_with_issue_id_allows_its_own_cases_to_change():
    ev = InvarianceEvidence(issue_id="2283", cases=(_case("own", "issue-2283", "1", "1", "2"), _case("g", "general", "5", "5", "5")))
    assert ev.unexpected_diffs == () and ev.ok


def test_invariance_without_issue_id_keeps_the_old_behaviour():
    ev = InvarianceEvidence(cases=(_case("other", "issue-2129", "3", "3", "4"),))
    assert ev.issue_id == "" and ev.unexpected_diffs == ()


def test_invariance_not_ok_when_base_is_nondeterministic():
    ev = InvarianceEvidence(cases=(_case("a", "general", "1", "2", "1"),))
    assert not ev.deterministic and not ev.ok


def test_invariance_not_ok_without_cases():
    assert not InvarianceEvidence(cases=()).ok


def test_objection_valid_requires_failing_mutant():
    assert Objection(question="q", pr_result=GREEN, mutant_result=RED).valid
    assert not Objection(question="q", pr_result=GREEN, mutant_result=GREEN).valid
    assert not Objection(question="q", pr_result=GREEN, mutant_result=None).valid


def test_models_are_immutable():
    with pytest.raises(ValidationError):
        GREEN.passed = 5  # type: ignore[misc]


def test_computed_fields_are_serialized():
    dumped = _change(ChangeType.BUGFIX, RED, GREEN).model_dump()
    assert dumped["ok"] is True and dumped["pr"]["green"] is True
