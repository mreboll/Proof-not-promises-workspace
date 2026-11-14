"""Escala de la Etapa 1 (paso 7 de B): resumen de un triaje masivo. LLM y diff sustituidos por dobles."""

from __future__ import annotations

from ledger.config import load_settings
from ledger.models import Risk, Scope
from ledger.triage import scale
from ledger.triage.diff import FileDiff
from ledger.triage.scope import ScopeAnswer

FILES = (
    FileDiff(path="README.md", status="modified", added=("x",)),
    FileDiff(path="src/MessagePack.SourceGenerator/Transforms/A.cs", status="modified", added=("var a = 1;",)),
    FileDiff(path="src/MessagePack.SourceGenerator/Transforms/B.tt", status="modified", added=("x",)),
    *(FileDiff(path=f"tests/MessagePack.SourceGenerator.Tests/Resources/C{i}/F.g.cs", status="modified") for i in range(5)),
)


def fake_complete(system, user, schema, role, **kwargs):
    scope = Scope.OUT if "File: README.md" in user else Scope.IN
    return ScopeAnswer(scope=scope, justification="j")


def test_summary_counts_files_llm_calls_and_stage1_outcome(monkeypatch):
    monkeypatch.setattr(scale, "load_diff", lambda s, i: FILES)
    triage, summary = scale.run_scale(load_settings(), "2297", complete=fake_complete)
    assert len(triage) == 8
    assert summary["files"] == 8
    assert summary["llm_calls"] == 3 and summary["skipped_llm_by_rule"] == 5
    assert summary["by_risk"] == {"LOW": 6, "MED": 0, "HIGH": 2}
    assert summary["by_scope"] == {"IN": 7, "OUT": 1}
    assert summary["matrix"]["IN"]["HIGH"] == 2 and summary["matrix"]["OUT"]["LOW"] == 1
    assert summary["stage1"] == {"red_out_high": 0, "yellow_out": 1, "to_evidence_low_med": 5, "to_crossexam_high": 2}
    assert summary["human_reads"] == 3  # amarillos de alcance + fragmentos HIGH que pasarán por el interrogatorio
    assert summary["elapsed_s"] >= 0


def test_triage_is_kept_in_diff_order(monkeypatch):
    monkeypatch.setattr(scale, "load_diff", lambda s, i: FILES)
    triage, _ = scale.run_scale(load_settings(), "2297", complete=fake_complete)
    assert [t.path for t in triage] == [f.path for f in FILES]
    assert triage[0].scope is Scope.OUT and triage[1].risk is Risk.HIGH
