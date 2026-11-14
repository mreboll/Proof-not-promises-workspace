"""Etapa 1 completa: diff → reglas + alcance → FileTriage. LLM y diff sustituidos por dobles."""

from __future__ import annotations

from ledger import pipeline
from ledger.config import load_settings
from ledger.models import Risk, Scope
from ledger.triage import stage
from ledger.triage.diff import FileDiff
from ledger.triage.scope import ScopeAnswer

FILES = (
    FileDiff(path="README.md", status="modified", added=("nota",)),
    FileDiff(path="src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs", status="modified", added=("    public int X;",)),
    FileDiff(path="tests/MessagePack.SourceGenerator.Tests/Resources/A/Formatters.B.g.cs", status="modified"),
)


class FakeComplete:
    def __init__(self):
        self.paths: list[str] = []

    def __call__(self, system, user, schema, role, **kwargs):
        path = next(line.removeprefix("File: ").split(" ")[0] for line in user.splitlines() if line.startswith("File: "))
        self.paths.append(path)
        scope = "OUT" if path.endswith(".md") else "IN"
        return ScopeAnswer(scope=scope, justification=f"motivo de {path}")


def _run(monkeypatch):
    monkeypatch.setattr(stage, "load_diff", lambda settings, issue_id: FILES)
    fake = FakeComplete()
    return stage.triage_issue(load_settings(), "2283", complete=fake), fake


def test_combines_rules_and_scope_in_diff_order(monkeypatch):
    triage, _ = _run(monkeypatch)
    assert [t.path for t in triage] == [f.path for f in FILES]
    readme, collector, snapshot = triage
    assert (readme.scope, readme.risk, readme.justification) == (Scope.OUT, Risk.LOW, "motivo de README.md")
    assert (collector.scope, collector.risk, collector.touches_public_api) == (Scope.IN, Risk.HIGH, True)
    assert any(h.startswith("R-HIGH-03") for h in collector.rule_hits)
    assert (snapshot.scope, snapshot.risk) == (Scope.IN, Risk.LOW)


def test_snapshots_do_not_call_the_llm(monkeypatch):
    _, fake = _run(monkeypatch)
    assert fake.paths == ["README.md", "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs"]


def test_pipeline_stage1_delegates_to_triage_issue(monkeypatch):
    sentinel = ()
    monkeypatch.setattr(stage, "triage_issue", lambda settings, issue_id: sentinel)
    assert pipeline.stage1_triage("2283", load_settings()) is sentinel
