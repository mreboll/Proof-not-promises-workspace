import json

import pytest

from ledger.evidence import regen
from ledger.fakes import FakeTestRunner
from ledger.models import ChangeTestEvidence, ChangeType, InvarianceCase, InvarianceEvidence

FAKE_INV = InvarianceEvidence(cases=(InvarianceCase(id="g", tag="general", base_hash="a", base_hash_rerun="a", pr_hash="a"),))


def fake_change_test(issue_id, settings, runner):
    return ChangeTestEvidence(
        issue_id=issue_id, change_type=ChangeType.BUGFIX, test_name="LedgerX", test_code="//",
        base=runner.run_tests("base", "//", "LedgerX"), pr=runner.run_tests("pr", "//", "LedgerX"),
    )


@pytest.fixture
def stubs(monkeypatch):
    calls = {}
    monkeypatch.setattr(regen, "generate_change_test", lambda i, s, r: calls.setdefault("ct", fake_change_test(i, s, r)))
    monkeypatch.setattr(regen, "collect_invariance", lambda s, i: calls.setdefault("inv", FAKE_INV))
    monkeypatch.setattr(regen, "make_runner", lambda s, i, name: FakeTestRunner())
    return calls


def test_regen_writes_fixture_with_provenance(settings, tmp_path, stubs):
    path = regen.regenerate("2283", settings, runner_name="local", fixtures_dir=tmp_path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "evidence_2283.json"
    assert data["change_test"]["ok"] is True
    assert data["invariance"]["ok"] is True
    prov = data["provenance"]
    assert prov["runner"] == "local" and prov["model_pro"]
    assert prov["command"] == "python -m ledger.evidence.regen --issue 2283 --runner local"


def test_regen_can_skip_the_llm_and_keep_the_previous_change_test(settings, tmp_path, stubs):
    regen.regenerate("2283", settings, runner_name="local", fixtures_dir=tmp_path)
    stubs.clear()

    path = regen.regenerate("2283", settings, runner_name="local", fixtures_dir=tmp_path, only_invariance=True)

    assert "ct" not in stubs  # no se llamó al LLM ni a dotnet para el test del cambio
    assert json.loads(path.read_text(encoding="utf-8"))["change_test"]["test_name"] == "LedgerX"


def test_only_invariance_without_previous_fixture_is_a_clear_error(settings, tmp_path, stubs):
    with pytest.raises(FileNotFoundError, match="evidence_2283.json"):
        regen.regenerate("2283", settings, runner_name="local", fixtures_dir=tmp_path, only_invariance=True)


def test_unknown_issue_is_rejected(settings, tmp_path, stubs):
    with pytest.raises(ValueError):
        regen.regenerate("9999", settings, runner_name="local", fixtures_dir=tmp_path)


def test_cli_parses_arguments(monkeypatch, settings, tmp_path):
    seen = {}
    monkeypatch.setattr(regen, "regenerate", lambda issue, s, **kw: seen.update(issue=issue, **kw) or tmp_path / "x.json")
    monkeypatch.setattr(regen, "load_settings", lambda: settings)

    regen.main(["--issue", "2297", "--runner", "modal", "--only-invariance"])

    assert seen == {"issue": "2297", "runner_name": "modal", "only_invariance": True}
