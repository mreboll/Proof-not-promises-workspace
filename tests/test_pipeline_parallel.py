"""Etapas 1 y 2 a la vez (solo con un runner paralelo) y triaje fichero a fichero en paralelo."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from ledger import pipeline
from ledger.config import load_settings
from ledger.fakes import GREEN, RED
from ledger.models import ChangeTestEvidence, ChangeType, InvarianceCase, InvarianceEvidence, Scope
from ledger.triage import stage as triage_stage
from ledger.triage.diff import FileDiff

DELAY = 0.15


class Gauge:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active = 0
        self.peak = 0

    def __enter__(self) -> None:
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)

    def __exit__(self, *exc) -> None:
        with self._lock:
            self.active -= 1


CT = ChangeTestEvidence(issue_id="2283", change_type=ChangeType.BUGFIX, test_name="T", test_code="...", base=RED, pr=GREEN)
INV = InvarianceEvidence(cases=(InvarianceCase(id="a", tag="general", base_hash="1", base_hash_rerun="1", pr_hash="1"),))


class Runner:
    def __init__(self, parallel_safe: bool) -> None:
        self.parallel_safe = parallel_safe


def _patch_stages(monkeypatch, gauge: Gauge) -> dict:
    seen: dict = {}

    def slow(result):
        def stage(*args, **kwargs):
            with gauge:
                time.sleep(DELAY)
            return result
        return stage

    monkeypatch.setattr(pipeline, "stage1_triage", slow(()))
    monkeypatch.setattr(pipeline, "stage2_change_test", slow(CT))
    monkeypatch.setattr(pipeline, "stage2_invariance", slow(INV))

    def stage3(issue_id, triage, change_test, invariance, runner, settings):
        seen.update(triage=triage, change_test=change_test, invariance=invariance)
        return ()

    monkeypatch.setattr(pipeline, "stage3_and_verdicts", stage3)
    monkeypatch.setattr(pipeline, "render_report", lambda report, out: Path("report.html"))
    return seen


def test_stage1_and_stage2_run_at_the_same_time_with_a_parallel_runner(monkeypatch):
    gauge = Gauge()
    seen = _patch_stages(monkeypatch, gauge)

    pipeline.run("2283", load_settings(), Runner(parallel_safe=True))

    assert gauge.peak == 3
    assert seen == {"triage": (), "change_test": CT, "invariance": INV}


def test_local_runner_keeps_stages_sequential(monkeypatch):
    """En local, el test del cambio y la invarianza comparten worktrees en .work/: nunca a la vez."""
    gauge = Gauge()
    _patch_stages(monkeypatch, gauge)

    pipeline.run("2283", load_settings(), Runner(parallel_safe=False))

    assert gauge.peak == 1


def test_triage_classifies_files_in_parallel_and_keeps_diff_order(monkeypatch):
    gauge = Gauge()
    files = tuple(FileDiff(path=f"src/F{i}.cs", status="modified") for i in range(5))

    def slow_scope(issue_text, fd, **kwargs):
        with gauge:
            time.sleep(DELAY * (5 - int(fd.path[5])) / 5)  # el primero es el más lento
        return Scope.IN, fd.path

    monkeypatch.setattr(triage_stage, "load_issue_text", lambda s, i: "# issue")
    monkeypatch.setattr(triage_stage, "load_diff", lambda s, i: files)
    monkeypatch.setattr(triage_stage, "classify_scope", slow_scope)

    result = triage_stage.triage_issue(load_settings(), "2283")

    assert [t.path for t in result] == [f.path for f in files]
    assert [t.justification for t in result] == [f.path for f in files]
    assert gauge.peak == 5
