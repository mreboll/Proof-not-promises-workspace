"""Etapa 3 + veredictos: solo se interroga IN/HIGH con evidencia ok, y los fallos acaban en M7 con motivo."""

from __future__ import annotations

import pytest

from ledger import llm, pipeline
from ledger.config import load_settings
from ledger.crossexam import stage
from ledger.fakes import GREEN, RED, FakeTestRunner
from ledger.models import ChangeTestEvidence, ChangeType, FileTriage, InvarianceCase, InvarianceEvidence, Objection, Risk, Scope, Verdict
from ledger.triage.diff import DiffError, FileDiff

HIGH = FileTriage(path="src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs", scope=Scope.IN, risk=Risk.HIGH)
LOW = FileTriage(path="tests/X.cs", scope=Scope.IN, risk=Risk.LOW)
DOC = FileTriage(path="README.md", scope=Scope.OUT, risk=Risk.LOW, justification="no lo pide")
TRIAGE = (DOC, HIGH, LOW)

CT = ChangeTestEvidence(issue_id="2283", change_type=ChangeType.BUGFIX, test_name="T", test_code="...", base=RED, pr=GREEN)
INV = InvarianceEvidence(cases=(InvarianceCase(id="a", tag="general", base_hash="1", base_hash_rerun="1", pr_hash="1"),))
VALID = Objection(question="¿q?", test_name="Ledger_2283_Objection1", test_code="x", pr_result=GREEN, mutant_patch="p", mutant_result=RED)


@pytest.fixture
def wired(monkeypatch):
    calls = []

    def fake_cross(issue_id, issue_text, fd, runner, **kwargs):
        calls.append((fd.path, kwargs["evidence_summary"]))
        return (VALID,)

    monkeypatch.setattr(stage, "cross_examine", fake_cross)
    monkeypatch.setattr(stage, "load_issue_text", lambda s, i: "# #2283: crash")
    monkeypatch.setattr(stage, "load_diff", lambda s, i: (FileDiff(path=HIGH.path, status="modified"),))
    return calls


def judge(ct=CT, inv=INV):
    return {v.path: v for v in stage.judge_issue("2283", TRIAGE, ct, inv, FakeTestRunner(), load_settings())}


def test_only_in_high_is_cross_examined_and_gets_a_verdict(wired):
    v = judge()
    assert [path for path, _ in wired] == [HIGH.path]
    assert (v[HIGH.path].verdict, v[HIGH.path].objections) == (Verdict.GREEN, (VALID,))
    assert v[LOW.path].verdict is Verdict.GREEN and v[DOC.path].verdict is Verdict.YELLOW


def test_fiscal_receives_the_evidence_summary(wired):
    judge()
    assert "change test `T`" in wired[0][1] and "invariance" in wired[0][1]


def test_failed_evidence_skips_the_crossexam(wired):
    v = judge(ct=CT.model_copy(update={"pr": RED}))
    assert wired == [] and v[HIGH.path].verdict is Verdict.RED and v[HIGH.path].reasons[0].startswith("M3")


@pytest.mark.parametrize("error", [llm.LLMError("sin clave NVIDIA"), DiffError("No encuentro el repo")])
def test_crossexam_failure_refuses_with_the_reason(monkeypatch, wired, error):
    def boom(*a, **k):
        raise error

    monkeypatch.setattr(stage, "cross_examine", boom)
    v = judge()[HIGH.path]
    assert v.verdict is Verdict.RED and v.reasons[0].startswith("M7")
    assert any(str(error) in r for r in v.reasons)


def test_missing_repo_refuses_with_the_reason(monkeypatch, wired):
    def no_repo(s, i):
        raise DiffError("No encuentro el repo del reto")

    monkeypatch.setattr(stage, "load_diff", no_repo)
    v = judge()[HIGH.path]
    assert v.verdict is Verdict.RED and any("No encuentro el repo" in r for r in v.reasons)


def test_pipeline_stage3_delegates_to_judge_issue(monkeypatch):
    sentinel = ()
    monkeypatch.setattr(stage, "judge_issue", lambda *a: sentinel)
    assert pipeline.stage3_and_verdicts("2283", (), None, None, FakeTestRunner(), load_settings()) is sentinel
