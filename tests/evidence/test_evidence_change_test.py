from dataclasses import dataclass, field

import pytest

from ledger.evidence.change_test import GeneratedTest, build_user_prompt, generate_change_test
from ledger.fakes import GREEN, RED, FakeTestRunner
from ledger.models import ChangeType, TestRunResult

ISSUE = "# Generator crashes on closed generic struct from referenced assembly\n\nRepro: ..."
TEMPLATE = "public class GenericsFormatterTests { /* estilo */ }"
BUILD_FAIL = TestRunResult(build_ok=False, passed=0, failed=0, output_tail="BUILD FAILED\nT.cs(3,1): error CS0246: 'Foo' not found")


@dataclass
class ScriptedLLM:
    answers: list[GeneratedTest]
    calls: list[tuple[str, str, type, str]] = field(default_factory=list)

    def __call__(self, system, user, schema, role):
        self.calls.append((system, user, schema, role))
        return self.answers[len(self.calls) - 1]


@dataclass
class ScriptedRunner:
    """Devuelve resultados en orden por lado y registra las llamadas."""

    by_side: dict[str, list[TestRunResult]]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def run_tests(self, side, test_code, test_name):
        self.calls.append((side, test_code))
        return self.by_side[side].pop(0)

    def run_against_mutant(self, side, mutant_patch, test_code, test_name):  # pragma: no cover
        raise AssertionError("change_test no usa mutantes")


T1 = GeneratedTest(test_name="LedgerIssue2283Test", test_code="public class LedgerIssue2283Test { }")
T2 = GeneratedTest(test_name="LedgerIssue2283Test", test_code="public class LedgerIssue2283Test { /* v2 */ }")


def run(settings, llm, runner, issue_id="2283"):
    return generate_change_test(issue_id, settings, runner, issue_text=ISSUE, template=TEMPLATE, complete=llm)


def test_prompt_contains_issue_and_template_only(settings):
    prompt = build_user_prompt(ISSUE, TEMPLATE)
    assert ISSUE in prompt and TEMPLATE in prompt
    assert "diff --git" not in prompt


def test_bugfix_red_on_base_green_on_pr_is_ok(settings):
    llm = ScriptedLLM([T1])

    evidence = run(settings, llm, FakeTestRunner())

    assert evidence.ok
    assert evidence.change_type is ChangeType.BUGFIX
    assert evidence.base.red_for_real and evidence.pr.green
    assert evidence.test_name == "LedgerIssue2283Test"
    _, user, schema, role = llm.calls[0]
    assert schema is GeneratedTest and role == "pro" and ISSUE in user


def test_compile_failure_on_pr_is_retried_once_with_the_error(settings):
    llm = ScriptedLLM([T1, T2])
    runner = ScriptedRunner({"pr": [BUILD_FAIL, GREEN], "base": [RED]})

    evidence = run(settings, llm, runner)

    assert len(llm.calls) == 2
    assert "error CS0246" in llm.calls[1][1]
    assert T1.test_code in llm.calls[1][1]
    assert evidence.test_code == T2.test_code
    assert evidence.ok


def test_second_compile_failure_is_returned_as_is(settings):
    llm = ScriptedLLM([T1, T2])
    runner = ScriptedRunner({"pr": [BUILD_FAIL, BUILD_FAIL], "base": [BUILD_FAIL]})

    evidence = run(settings, llm, runner)

    assert len(llm.calls) == 2
    assert not evidence.ok
    assert not evidence.pr.build_ok


@pytest.mark.parametrize(
    "infra_failure",
    [
        TestRunResult(build_ok=False, passed=0, failed=1, output_tail="INFRA: test failed for infrastructure reasons"),
        TestRunResult(build_ok=False, passed=0, failed=0, output_tail="timeout tras 900s"),
        TestRunResult(build_ok=False, passed=0, failed=0, output_tail="Modal falló: ConnectionError"),
    ],
)
def test_infrastructure_failures_do_not_spend_the_llm_retry(settings, infra_failure):
    """Reescribir el test no arregla la red, un timeout ni Modal caído: no se reintenta con el LLM."""
    llm = ScriptedLLM([T1, T2])
    runner = ScriptedRunner({"pr": [infra_failure], "base": [RED]})

    evidence = run(settings, llm, runner)

    assert len(llm.calls) == 1
    assert not evidence.ok


def test_test_that_passes_on_base_does_not_prove_a_bugfix(settings):
    runner = ScriptedRunner({"pr": [GREEN], "base": [GREEN]})

    evidence = run(settings, ScriptedLLM([T1]), runner)

    assert not evidence.ok


def test_feature_only_needs_pr_green_but_records_base_as_extra_evidence(settings):
    runner = ScriptedRunner({"pr": [GREEN], "base": [RED]})

    evidence = run(settings, ScriptedLLM([T1]), runner, issue_id="2297")

    assert evidence.change_type is ChangeType.FEATURE
    assert evidence.ok
    assert evidence.base is not None and evidence.base.red_for_real  # el test mide algo nuevo
    assert [side for side, _ in runner.calls] == ["pr", "base"]


def test_feature_is_ok_even_if_test_does_not_compile_on_base(settings):
    """Una feature puede usar API nueva que en la base no existe: eso no invalida la evidencia."""
    runner = ScriptedRunner({"pr": [GREEN], "base": [BUILD_FAIL]})

    evidence = run(settings, ScriptedLLM([T1]), runner, issue_id="2297")

    assert evidence.ok and not evidence.base.build_ok


def test_missing_issue_file_is_a_clear_error(settings, tmp_path):
    from dataclasses import replace

    empty = replace(settings, issues_dir=tmp_path / "no-issues")
    with pytest.raises(FileNotFoundError, match="2283.md"):
        generate_change_test("2283", empty, FakeTestRunner(), template=TEMPLATE, complete=ScriptedLLM([T1]))
