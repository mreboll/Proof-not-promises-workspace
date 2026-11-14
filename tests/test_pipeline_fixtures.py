import json
from dataclasses import replace

from ledger import pipeline
from ledger.config import load_settings
from ledger.fakes import FakeTestRunner


def test_fixture_run_writes_report(tmp_path, monkeypatch):
    # Sin red: la Etapa 3 real llamaría a Nemotron. El Fiscal "no objeta" y el fichero HIGH pasa por M5.
    monkeypatch.setattr("ledger.crossexam.stage.cross_examine", lambda *a, **k: ())
    settings = replace(load_settings(), out_dir=tmp_path)
    path = pipeline.run("2283", settings, FakeTestRunner(), use_fixtures=True)
    assert path.suffix == ".html" and "REGISTRO DE APROBACIÓN" in path.read_text(encoding="utf-8")
    report = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    assert report["issue_id"] == "2283"
    assert report["change_test"]["ok"] is True
    assert report["invariance"]["ok"] is True
    assert report["base_commit"] == "origin/ju26-issue-2283~1"
    assert len(report["triage"]) == 4
    assert len(report["verdicts"]) == 4


def test_fake_runner_rejects_trivial_test():
    runner = FakeTestRunner()
    assert runner.run_against_mutant("pr", "patch", "Assert.True(true);", "t").green
    assert runner.run_against_mutant("pr", "patch", "Assert.Empty(diagnostics);", "t").red_for_real
