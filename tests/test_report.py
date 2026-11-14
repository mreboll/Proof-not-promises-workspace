"""Informe HTML (B, paso 6): estático, imprimible, autocontenido y con el bloque de firma."""

from __future__ import annotations

import json

import pytest

from ledger.fakes import GREEN, RED
from ledger.models import (
    ChangeTestEvidence,
    ChangeType,
    FileTriage,
    FragmentVerdict,
    InvarianceCase,
    InvarianceEvidence,
    Objection,
    Report,
    Risk,
    Scope,
    Verdict,
)
from ledger.report.render import overall_decision, render_html, write_report

MODELS = {"pro": "nvidia/nemotron-super", "flash": "nvidia/nemotron-lightning", "fiscal": "nvidia/nemotron-super"}

OBJ = Objection(
    question="¿Y si el struct genérico viene anidado?",
    rationale="La evidencia no cubre tipos anidados",
    test_name="Ledger_2283_Objection1",
    test_code='public class Ledger_2283_Objection1 { void T() { var s = "<script>alert(1)</script>"; } }',
    pr_result=GREEN,
    mutant_patch="--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n",
    mutant_result=RED,
)


def make_report(verdicts=None) -> Report:
    triage = (
        FileTriage(path="README.md", scope=Scope.OUT, risk=Risk.LOW, rule_hits=("R-LOW-02: documentación .md",), justification="El issue no pide documentación."),
        FileTriage(path="src/G/CodeAnalysis/TypeCollector.cs", scope=Scope.IN, risk=Risk.HIGH, rule_hits=("R-HIGH-03: namespace núcleo",), justification="Arregla el crash."),
        FileTriage(path="tests/T.cs", scope=Scope.IN, risk=Risk.LOW, rule_hits=("R-LOW-01: ruta tests/",), justification="Test del issue."),
    )
    if verdicts is None:
        verdicts = (
            FragmentVerdict(path="README.md", verdict=Verdict.YELLOW, reasons=("M2: fuera del alcance", "justificación: El issue no pide documentación.")),
            FragmentVerdict(path="src/G/CodeAnalysis/TypeCollector.cs", verdict=Verdict.GREEN, reasons=("M5: riesgo alto superado",), objections=(OBJ,)),
            FragmentVerdict(path="tests/T.cs", verdict=Verdict.GREEN, reasons=("M4: evidencia superada",)),
        )
    return Report(
        issue_id="2283",
        change_type=ChangeType.BUGFIX,
        branch="ju26-issue-2283",
        base_commit="origin/ju26-issue-2283~1",
        pr_commit="origin/ju26-issue-2283",
        generated_at="2026-11-14T10:00:00+00:00",
        triage=triage,
        change_test=ChangeTestEvidence(issue_id="2283", change_type=ChangeType.BUGFIX, test_name="LedgerIssue2283", test_code="class LedgerIssue2283 {}", base=RED, pr=GREEN),
        invariance=InvarianceEvidence(
            cases=(
                InvarianceCase(id="general-int-keys", tag="general", base_hash="aaaa1111", base_hash_rerun="aaaa1111", pr_hash="aaaa1111"),
                InvarianceCase(id="issue-2283-closed-generic", tag="issue-2283", base_hash="bbbb", base_hash_rerun="bbbb", pr_hash="cccc"),
            )
        ),
        verdicts=verdicts,
    )


@pytest.fixture
def html() -> str:
    return render_html(make_report(), models=MODELS, issue_title="#2283: Generator and analyzer crash")


def test_header_has_issue_type_branch_and_commits(html):
    for text in ("#2283: Generator and analyzer crash", "bugfix", "ju26-issue-2283", "origin/ju26-issue-2283~1", "2026-11-14"):
        assert text in html


def test_counters_and_overall_decision(html):
    assert 'data-count="GREEN">2<' in html and 'data-count="YELLOW">1<' in html and 'data-count="RED">0<' in html
    assert "Revisión focalizada" in html


@pytest.mark.parametrize(
    ("verdicts", "expected"),
    [((Verdict.GREEN,), "Aprobable con evidencia"), ((Verdict.GREEN, Verdict.YELLOW), "Revisión focalizada"), ((Verdict.YELLOW, Verdict.RED), "Auditoría manual obligatoria"), ((), "Sin veredictos")],
)
def test_overall_decision_is_the_worst_verdict(verdicts, expected):
    assert overall_decision(tuple(FragmentVerdict(path=f"f{i}", verdict=v) for i, v in enumerate(verdicts)))[0] == expected


def test_human_reads_only_yellow_and_red_first(html):
    must_read = html.split('id="must-read"')[1].split("</section>")[0]
    assert "README.md" in must_read and "TypeCollector.cs" not in must_read


def test_every_file_appears_with_scope_risk_rules_and_reasons(html):
    for text in ("src/G/CodeAnalysis/TypeCollector.cs", "R-HIGH-03: namespace núcleo", "M5: riesgo alto superado", "Arregla el crash."):
        assert text in html


def test_evidence_section_shows_change_test_and_hashes(html):
    assert "LedgerIssue2283" in html and "general-int-keys" in html and "issue-2283-closed-generic" in html
    assert "aaaa1111" in html


def test_crossexam_transcript(html):
    assert "¿Y si el struct genérico viene anidado?" in html and "Ledger_2283_Objection1" in html
    assert "+++ b/x" in html and "objeción cubierta: test válido" in html


def test_code_is_escaped(html):
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_models_per_role_are_named(html):
    assert "nvidia/nemotron-lightning" in html and "nvidia/nemotron-super" in html


def test_signature_block(html):
    assert "REGISTRO DE APROBACIÓN Y RENDICIÓN DE CUENTAS" in html
    assert "Afirmaciones auto-verificadas (Verde): 2/3" in html and "Revisadas manualmente (Amarillo/Rojo): 1/3" in html


def test_is_self_contained(html):
    assert "<html" in html and "http://" not in html.replace("http://www.w3.org", "") and "<link" not in html and "<script" not in html


def _card(html: str, title: str) -> str:
    return html.split(f"<h3>{title}</h3>")[1].split('<div class="card">')[0]


def test_feature_red_in_base_is_explained_not_painted_as_a_failure():
    r = make_report()
    feature = r.model_copy(update={"change_type": ChangeType.FEATURE, "change_test": r.change_test.model_copy(update={"change_type": ChangeType.FEATURE})})
    card = _card(render_html(feature, models=MODELS, issue_title="#2297"), "Test del cambio")
    assert "rojo en base: el test mide algo nuevo" in card
    assert 'class="pill red">rojo' not in card


def test_bugfix_test_green_in_base_says_it_does_not_reproduce_the_bug():
    r = make_report()
    weak = r.model_copy(update={"change_test": r.change_test.model_copy(update={"base": GREEN})})
    card = _card(render_html(weak, models=MODELS, issue_title="#2234"), "Test del cambio")
    assert "pasa también en la base: no reproduce el bug" in card


def test_declared_normalization_is_visible_without_expanding():
    r = make_report()
    norm = "removed [ExcludeFromCodeCoverage] lines (feature #2297)"
    cases = tuple(c.model_copy(update={"normalization": norm}) if c.tag == "general" else c for c in r.invariance.cases)
    html = render_html(r.model_copy(update={"invariance": InvarianceEvidence(cases=cases)}), models=MODELS, issue_title="#2297")
    card = _card(html, "Invarianza de generación")
    assert "Normalización declarada" in card and norm in card and "1 caso" in card


def test_unexpected_diff_says_the_pr_does_more_than_the_issue_asks():
    r = make_report()
    cases = (*r.invariance.cases, InvarianceCase(id="general-duplicate-int-keys-not-suppressed", tag="general", base_hash="a", base_hash_rerun="a", pr_hash="b"))
    card = _card(render_html(r.model_copy(update={"invariance": InvarianceEvidence(cases=cases)}), models=MODELS, issue_title="#2234"), "Invarianza de generación")
    assert "general-duplicate-int-keys-not-suppressed" in card and "más de lo que pide el issue" in card


def test_rerender_from_a_json_report(tmp_path, monkeypatch):
    """`python -m ledger.report.render out/report-2283.json`: HTML desde el JSON de una ejecución con dotnet real."""
    from ledger.report import render

    src = tmp_path / "in" / "report-2283.json"
    src.parent.mkdir()
    src.write_text(make_report().model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(render, "write_report", lambda report, out_dir, **kw: out_dir / f"report-{report.issue_id}.html")
    assert render.main([str(src)]) == src.parent / "report-2283.html"


def test_report_without_verdicts_still_renders():
    html = render_html(make_report(verdicts=()), models=MODELS, issue_title="#2283")
    assert "Sin veredictos" in html and "README.md" in html


def test_write_report_writes_html_and_json(tmp_path):
    path = write_report(make_report(), tmp_path, models=MODELS, issue_title="#2283")
    assert path == tmp_path / "report-2283.html" and path.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert json.loads((tmp_path / "report-2283.json").read_text(encoding="utf-8"))["issue_id"] == "2283"
