import json
from dataclasses import replace

from ledger import pipeline
from ledger.config import load_settings
from ledger.fakes import FakeTestRunner


def test_fixture_run_writes_report(tmp_path):
    settings = replace(load_settings(), out_dir=tmp_path)
    path = pipeline.run("2283", settings, FakeTestRunner(), use_fixtures=True)
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["issue_id"] == "2283"
    assert report["change_test"]["ok"] is True
    assert report["invariance"]["ok"] is True
    assert report["base_commit"] == "origin/ju26-issue-2283~1"
    assert len(report["triage"]) == 4


def test_fake_runner_rejects_trivial_test():
    runner = FakeTestRunner()
    assert runner.run_against_mutant("pr", "patch", "Assert.True(true);", "t").green
    assert runner.run_against_mutant("pr", "patch", "Assert.Empty(diagnostics);", "t").red_for_real
