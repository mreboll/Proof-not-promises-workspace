"""Etapa 3 en paralelo (solo con runners seguros para paralelo, p. ej. Modal) y topes de concurrencia."""

from __future__ import annotations

import threading
import time
from dataclasses import replace

import pytest

from ledger import llm
from ledger.config import load_settings
from ledger.crossexam import loop, stage
from ledger.crossexam.concurrency import ordered_map, parallel_enabled
from ledger.crossexam.defensor import DefenseTest
from ledger.crossexam.fiscal import FiscalObjection, Objections
from ledger.crossexam.mutant_gen import MutantEdit
from ledger.fakes import GREEN, RED
from ledger.models import ChangeTestEvidence, ChangeType, FileTriage, InvarianceCase, InvarianceEvidence, Objection, Risk, Scope
from ledger.triage.diff import FileDiff, Hunk

DELAY = 0.15


class Gauge:
    """Cuenta cuántas llamadas hay en curso a la vez."""

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


# --------------------------------------------------------------------------- utilidades


def test_ordered_map_keeps_order_and_overlaps_with_workers():
    gauge = Gauge()

    def slow(x: int) -> int:
        with gauge:
            time.sleep(DELAY * (4 - x) / 3)  # el primero es el más lento
        return x * 10

    assert ordered_map(slow, [1, 2, 3], workers=3) == [10, 20, 30]
    assert gauge.peak == 3


def test_ordered_map_is_sequential_with_one_worker():
    gauge = Gauge()

    def slow(x: int) -> int:
        with gauge:
            time.sleep(0.01)
        return x

    assert ordered_map(slow, [1, 2, 3], workers=1) == [1, 2, 3]
    assert gauge.peak == 1


def test_parallel_only_for_runners_that_declare_it():
    from ledger.evidence.dotnet import DotnetTestRunner
    from ledger.evidence.modal_runner import ModalTestRunner

    s = load_settings()
    assert parallel_enabled(ModalTestRunner(s, "2283"))
    assert not parallel_enabled(DotnetTestRunner(s, "2283"))  # se pisaría el mismo worktree
    assert not parallel_enabled(object())


# --------------------------------------------------------------------------- stage: ficheros en paralelo

CT = ChangeTestEvidence(issue_id="2283", change_type=ChangeType.BUGFIX, test_name="T", test_code="...", base=RED, pr=GREEN)
INV = InvarianceEvidence(cases=(InvarianceCase(id="a", tag="general", base_hash="1", base_hash_rerun="1", pr_hash="1"),))
FILES = [FileTriage(path=f"src/T{i}.cs", scope=Scope.IN, risk=Risk.HIGH) for i in range(3)]
LOW = FileTriage(path="tests/X.cs", scope=Scope.IN, risk=Risk.LOW)
TRIAGE = (FILES[0], LOW, FILES[1], FILES[2])


class ParallelRunner:
    parallel_safe = True

    def run_tests(self, side, test_code, test_name):  # pragma: no cover - no se llama en estos tests
        raise AssertionError


class SequentialRunner(ParallelRunner):
    parallel_safe = False


@pytest.fixture
def slow_cross(monkeypatch):
    gauge = Gauge()

    def fake_cross(issue_id, issue_text, fd, runner, **kwargs):
        with gauge:
            time.sleep(DELAY)
        return (Objection(question=fd.path, test_name="Ledger_x", pr_result=GREEN, mutant_patch="p", mutant_result=RED),)

    monkeypatch.setattr(stage, "cross_examine", fake_cross)
    monkeypatch.setattr(stage, "load_issue_text", lambda s, i: "# issue")
    monkeypatch.setattr(stage, "load_diff", lambda s, i: tuple(FileDiff(path=f.path, status="modified") for f in FILES))
    return gauge


def test_files_are_cross_examined_in_parallel_and_verdicts_keep_triage_order(slow_cross):
    verdicts = stage.judge_issue("2283", TRIAGE, CT, INV, ParallelRunner(), load_settings())

    assert slow_cross.peak == 3
    assert [v.path for v in verdicts] == [t.path for t in TRIAGE]
    assert [v.objections[0].question for v in verdicts if v.objections] == [f.path for f in FILES]


def test_local_runner_keeps_the_crossexam_sequential(slow_cross):
    stage.judge_issue("2283", TRIAGE, CT, INV, SequentialRunner(), load_settings())
    assert slow_cross.peak == 1


# --------------------------------------------------------------------------- loop: objeciones y ejecución especulativa

PATH = "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs"
SOURCE = "class TypeCollector\n{\n    void A()\n    {\n        var r = refs.FirstOrDefault();\n    }\n}\n"
FD = FileDiff(path=PATH, status="modified", hunks=(Hunk(header="@@ -3,3 +3,3 @@", text="@@\n"),), added=(), removed=())
EDIT = MutantEdit(find="refs.FirstOrDefault()", replace="refs[0]", explanation="vuelve a indexar [0]")


class ThreadSafeComplete:
    def __init__(self, n_objections: int) -> None:
        self.n = n_objections

    def __call__(self, system, user, schema, role, **kwargs):
        if schema is Objections:
            return Objections(objections=[FiscalObjection(question=f"q{i}", rationale="") for i in range(1, self.n + 1)])
        if schema is MutantEdit:
            return EDIT
        if schema is DefenseTest:
            name = next(line.split("`")[1] for line in user.splitlines() if "class must be named" in line)
            return DefenseTest(test_name=name, test_code=f"public class {name} {{ }}")
        raise AssertionError(schema)


class TimedRunner:
    """Registra los intervalos de cada ejecución; el PR puede ser verde o rojo."""

    def __init__(self, parallel_safe: bool, pr_result=GREEN) -> None:
        self.parallel_safe = parallel_safe
        self.pr_result = pr_result
        self.gauge = Gauge()
        self.spans: list[tuple[str, str, float, float]] = []
        self._lock = threading.Lock()

    def _timed(self, kind: str, name: str, result):
        start = time.monotonic()
        with self.gauge:
            time.sleep(DELAY)
        with self._lock:
            self.spans.append((kind, name, start, time.monotonic()))
        return result

    def run_tests(self, side, test_code, test_name):
        return self._timed("pr", test_name, self.pr_result)

    def run_against_mutant(self, side, mutant_patch, test_code, test_name):
        return self._timed("mutant", test_name, RED)


def _cross(runner, n_objections=3):
    return loop.cross_examine("2283", "# issue", FD, runner, read_source=lambda p: SOURCE, complete=ThreadSafeComplete(n_objections))


def test_objections_run_in_parallel_and_keep_their_order():
    runner = TimedRunner(parallel_safe=True)

    results = _cross(runner)

    assert [o.test_name for o in results] == ["Ledger_2283_Objection1", "Ledger_2283_Objection2", "Ledger_2283_Objection3"]
    assert all(o.valid for o in results)
    assert runner.gauge.peak >= 3


def test_pr_and_mutant_run_speculatively_at_the_same_time():
    runner = TimedRunner(parallel_safe=True)

    _cross(runner, n_objections=1)

    (pr,) = [s for s in runner.spans if s[0] == "pr"]
    (mut,) = [s for s in runner.spans if s[0] == "mutant"]
    assert pr[2] < mut[3] and mut[2] < pr[3]  # los intervalos se solapan


def test_speculative_mutant_result_is_discarded_when_pr_is_not_green():
    """Misma semántica que en secuencia: si el test no pasa en el PR, la objeción no guarda resultado del mutante."""
    runner = TimedRunner(parallel_safe=True, pr_result=RED)

    (obj,) = _cross(runner, n_objections=1)

    assert obj.pr_result is not None and not obj.pr_result.green
    assert obj.mutant_result is None and not obj.valid


def test_sequential_runner_never_overlaps_and_skips_mutant_after_red_pr():
    runner = TimedRunner(parallel_safe=False, pr_result=RED)

    _cross(runner, n_objections=2)

    assert runner.gauge.peak == 1
    assert all(kind == "pr" for kind, *_ in runner.spans)


# --------------------------------------------------------------------------- tope de llamadas concurrentes al LLM


def test_llm_calls_are_capped_per_provider(monkeypatch):
    gauge = Gauge()

    def fake_generate(client, model, system, user, schema):
        with gauge:
            time.sleep(DELAY)
        return "ok"

    monkeypatch.setenv("LEDGER_MAX_CONCURRENT_GEMINI", "2")
    monkeypatch.setattr(llm, "gemini_generate", fake_generate)
    llm._reset_limits()
    settings = replace(load_settings(), nvidia_for_all=False)

    threads = [
        threading.Thread(target=llm.complete, args=("s", f"u{i}"), kwargs={"role": "pro", "client": object(), "settings": settings, "use_cache": False})
        for i in range(6)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert gauge.peak == 2
    llm._reset_limits()
