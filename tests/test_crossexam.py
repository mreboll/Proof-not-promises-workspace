"""Etapa 3 (B): Fiscal (Nemotron), Defensor, mutantes y bucle antitrampa. LLM y dotnet sustituidos por dobles."""

from __future__ import annotations

import pytest

from ledger.crossexam.defensor import DefenseTest, write_test
from ledger.crossexam.fiscal import MAX_OBJECTIONS, FiscalObjection, Objections, raise_objections
from ledger.crossexam.loop import MAX_ROUNDS, cross_examine, test_class_name
from ledger.crossexam.mutant_gen import MAX_MUTANT_ATTEMPTS, MutantEdit, MutantError, build_patch, make_mutant
from ledger.fakes import GREEN, RED, FakeTestRunner
from ledger.triage.diff import FileDiff, Hunk

PATH = "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs"
SOURCE = "class TypeCollector\n{\n    void A()\n    {\n        var r = refs.FirstOrDefault();\n    }\n}\n"
FD = FileDiff(
    path=PATH,
    status="modified",
    hunks=(Hunk(header="@@ -3,3 +3,3 @@", text="@@ -3,3 +3,3 @@\n     void A()\n-        var r = refs[0];\n+        var r = refs.FirstOrDefault();\n"),),
    added=("        var r = refs.FirstOrDefault();",),
    removed=("        var r = refs[0];",),
)
ISSUE = "# #2283: crash with IndexOutOfRangeException"
GOOD_EDIT = MutantEdit(find="refs.FirstOrDefault()", replace="refs[0]", explanation="vuelve a indexar [0]")


def real_test(name: str) -> DefenseTest:
    return DefenseTest(test_name=name, test_code=f"public class {name} {{ [Fact] public void T() => Assert.Empty(diagnostics); }}")


def trivial_test(name: str) -> DefenseTest:
    return DefenseTest(test_name=name, test_code=f"public class {name} {{ [Fact] public void T() => Assert.True(true); }}")


class FakeComplete:
    """Responde según el esquema pedido. `tests` es una cola de fábricas name -> DefenseTest."""

    def __init__(self, objections=None, tests=None, edits=None):
        self.objections = objections if objections is not None else [FiscalObjection(question="¿Y con un struct genérico de metadata?", rationale="r")]
        self.tests = list(tests or [real_test])
        self.edits = list(edits or [GOOD_EDIT])
        self.calls: list[dict] = []

    def __call__(self, system, user, schema, role, **kwargs):
        self.calls.append({"system": system, "user": user, "schema": schema, "role": role})
        if schema is Objections:
            return Objections(objections=self.objections)
        if schema is MutantEdit:
            return self.edits.pop(0) if len(self.edits) > 1 else self.edits[0]
        if schema is DefenseTest:
            factory = self.tests.pop(0) if len(self.tests) > 1 else self.tests[0]
            name = next(line.split("`")[1] for line in user.splitlines() if "class must be named" in line)
            return factory(name)
        raise AssertionError(schema)

    def roles(self, schema) -> list[str]:
        return [c["role"] for c in self.calls if c["schema"] is schema]


def run(fake: FakeComplete, runner=None):
    return cross_examine("2283", ISSUE, FD, runner or FakeTestRunner(), read_source=lambda path: SOURCE, complete=fake, evidence_summary="test del cambio ok")


# --------------------------------------------------------------------------- Fiscal


def test_fiscal_uses_the_fiscal_role_and_sees_issue_diff_and_evidence():
    fake = FakeComplete()
    raise_objections(ISSUE, FD, "test del cambio: verde", complete=fake)
    call = fake.calls[0]
    assert call["role"] == "fiscal" and call["schema"] is Objections
    assert ISSUE in call["user"] and "FirstOrDefault" in call["user"] and "test del cambio: verde" in call["user"]


def test_fiscal_is_capped_at_three_and_drops_empty_questions():
    many = [FiscalObjection(question=f"q{i}", rationale="") for i in range(5)]
    fake = FakeComplete(objections=[FiscalObjection(question="  ", rationale=""), *many])
    got = raise_objections(ISSUE, FD, "", complete=fake)
    assert [o.question for o in got] == ["q0", "q1", "q2"] and MAX_OBJECTIONS == 3


# --------------------------------------------------------------------------- Defensor


def test_defensor_uses_pro_role_and_only_returns_a_test():
    fake = FakeComplete()
    out = write_test(ISSUE, FD, "¿y si...?", class_name="Ledger_2283_Obj1", style_example="// estilo", complete=fake)
    assert fake.calls[0]["role"] == "pro" and fake.calls[0]["schema"] is DefenseTest
    assert set(DefenseTest.model_fields) == {"test_name", "test_code"}
    assert "Ledger_2283_Obj1" in out.test_code


def test_defensor_gets_the_roslyn_api_sheet_from_the_change_test_agent():
    from ledger.crossexam.defensor import ROSLYN_GUIDE, SYSTEM

    assert "GetAnalyzerDiagnosticsAsync" in ROSLYN_GUIDE and "RunGeneratorsAndUpdateCompilation" in ROSLYN_GUIDE
    assert "LedgerIssue" not in ROSLYN_GUIDE  # la regla de nombres del agente de A no aplica al Defensor
    assert ROSLYN_GUIDE in SYSTEM


def test_defensor_prompt_carries_feedback_from_previous_round():
    fake = FakeComplete()
    write_test(ISSUE, FD, "q", class_name="C", style_example="", feedback="falló en el PR: CS0103", complete=fake)
    assert "falló en el PR: CS0103" in fake.calls[0]["user"]


# --------------------------------------------------------------------------- mutantes


def test_build_patch_is_a_valid_unified_diff_of_the_real_source():
    patch = build_patch(PATH, SOURCE, "refs.FirstOrDefault()", "refs[0]")
    assert patch.startswith(f"--- a/{PATH}\n+++ b/{PATH}\n@@")
    assert "-        var r = refs.FirstOrDefault();" in patch and "+        var r = refs[0];" in patch


@pytest.mark.parametrize(("find", "replace", "msg"), [("noexiste", "x", "not found"), ("    ", "x", "times"), ("refs[0]x", "refs[0]x", "not found"), ("refs", "refs", "change")])
def test_build_patch_rejects_bad_edits(find, replace, msg):
    with pytest.raises(MutantError, match=msg):
        build_patch(PATH, SOURCE, find, replace)


def test_make_mutant_retries_once_with_the_error_then_succeeds():
    fake = FakeComplete(edits=[MutantEdit(find="nope", replace="x", explanation=""), GOOD_EDIT])
    patch, explanation = make_mutant(FD, "q", SOURCE, complete=fake)
    assert patch and explanation == "vuelve a indexar [0]"
    assert len(fake.roles(MutantEdit)) == 2 and "not found" in fake.calls[1]["user"]


def test_make_mutant_gives_up_after_three_bad_edits():
    fake = FakeComplete(edits=[MutantEdit(find="nope", replace="x", explanation="")])
    patch, reason = make_mutant(FD, "q", SOURCE, complete=fake)
    assert patch == "" and "not found" in reason
    assert len(fake.roles(MutantEdit)) == MAX_MUTANT_ATTEMPTS == 3


def test_ambiguous_find_error_shows_each_occurrence_with_context():
    source = "class C\n{\n    void A() { Foo(); }\n    void B() { Foo(); }\n}\n"
    with pytest.raises(MutantError) as err:
        build_patch(PATH, source, "Foo();", "Bar();")
    message = str(err.value)
    assert "2 times" in message and "void A()" in message and "void B()" in message


def test_ambiguous_find_is_fixed_on_a_later_attempt():
    source = "class C\n{\n    void A() { Foo(); }\n    void B() { Foo(); }\n}\n"
    fake = FakeComplete(edits=[MutantEdit(find="Foo();", replace="Bar();"), MutantEdit(find="void B() { Foo(); }", replace="void B() { Bar(); }", explanation="ok")])
    patch, _ = make_mutant(FD, "q", source, complete=fake)
    assert "+    void B() { Bar(); }" in patch and "void A() { Foo(); }" in patch


def test_mutant_generator_sees_code_but_not_the_defense_test():
    fake = FakeComplete()
    make_mutant(FD, "q", SOURCE, complete=fake)
    assert fake.calls[0]["role"] == "pro" and "FirstOrDefault" in fake.calls[0]["user"] and "[Fact]" not in fake.calls[0]["user"]


# --------------------------------------------------------------------------- bucle y antitrampa


def test_real_test_is_valid_on_first_round():
    fake = FakeComplete()
    (obj,) = run(fake)
    assert obj.valid and obj.pr_result.green and obj.mutant_result.red_for_real
    assert obj.test_name == test_class_name("2283", 1) and obj.mutant_patch
    assert len(fake.roles(DefenseTest)) == 1


def test_trivial_assert_true_is_rejected_after_all_rounds():
    fake = FakeComplete(tests=[trivial_test])
    (obj,) = run(fake)
    assert not obj.valid and obj.mutant_result.green
    assert len(fake.roles(DefenseTest)) == MAX_ROUNDS == 3


def test_second_round_recovers_and_gets_mutant_feedback_without_the_patch():
    fake = FakeComplete(tests=[trivial_test, real_test])
    (obj,) = run(fake)
    assert obj.valid
    second = [c for c in fake.calls if c["schema"] is DefenseTest][1]["user"]
    assert "mutant" in second.lower() and "vuelve a indexar [0]" in second
    assert "+++ b/" not in second  # el Defensor nunca ve el parche del mutante


def test_test_failing_on_pr_is_retried_with_its_output():
    name = test_class_name("2283", 1)
    failing = FakeTestRunner(overrides={name: RED})
    fake = FakeComplete()
    (obj,) = run(fake, failing)
    assert not obj.valid and obj.mutant_result is None
    later = [c["user"] for c in fake.calls if c["schema"] is DefenseTest][1:]
    assert later and all(RED.output_tail in u for u in later)


def test_wrong_class_name_costs_a_round_without_running_dotnet():
    calls = []

    class SpyRunner(FakeTestRunner):
        def run_tests(self, side, test_code, test_name):
            calls.append(test_name)
            return super().run_tests(side, test_code, test_name)

    fake = FakeComplete(tests=[lambda n: real_test("Otro"), real_test])
    (obj,) = run(fake, SpyRunner())
    assert obj.valid and calls == [test_class_name("2283", 1)]


def test_without_mutant_the_objection_cannot_be_validated():
    fake = FakeComplete(edits=[MutantEdit(find="nope", replace="x", explanation="")])
    (obj,) = run(fake)
    assert not obj.valid and obj.mutant_patch == "" and obj.pr_result is None


def test_each_objection_gets_its_own_class_name():
    fake = FakeComplete(objections=[FiscalObjection(question="a", rationale=""), FiscalObjection(question="b", rationale="")])
    objs = run(fake)
    assert [o.test_name for o in objs] == [test_class_name("2283", 1), test_class_name("2283", 2)]
    assert all(o.valid for o in objs)


def test_no_objections_means_empty_tuple():
    assert run(FakeComplete(objections=[])) == ()


def test_fake_runner_green_red_sanity():
    assert GREEN.green and RED.red_for_real
