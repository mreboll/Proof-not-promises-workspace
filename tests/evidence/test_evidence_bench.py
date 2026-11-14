import json
import threading
import time

from ledger.evidence import bench
from ledger.fakes import GREEN, RED
from ledger.models import TestRunResult


class SlowRunner:
    """Cada ejecución tarda `delay` s; registra los hilos para comprobar el paralelismo."""

    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.threads: set[int] = set()
        self.mutants: list[str] = []

    def run_tests(self, side, test_code, test_name) -> TestRunResult:
        self.threads.add(threading.get_ident())
        time.sleep(self.delay)
        return GREEN if side == "pr" else RED

    def run_against_mutant(self, side, mutant_patch, test_code, test_name) -> TestRunResult:
        self.threads.add(threading.get_ident())
        self.mutants.append(mutant_patch)
        time.sleep(self.delay)
        return RED


def test_parallel_run_overlaps_and_sequential_does_not():
    jobs = bench.jobs(SlowRunner(), "LedgerT", "//", "--- a/src/A.cs\n")

    par_results, par_wall = bench.run_parallel(jobs)
    seq_results, seq_wall = bench.run_sequential(bench.jobs(SlowRunner(), "LedgerT", "//", "--- a/src/A.cs\n"))

    assert set(par_results) == set(seq_results) == {"base", "pr", "mutant"}
    assert par_wall < 0.45 and seq_wall >= 0.6


def test_expected_outcome_for_a_correct_bugfix():
    results = {"base": RED, "pr": GREEN, "mutant": RED}
    assert bench.matches_expectation(results)
    assert not bench.matches_expectation({**results, "mutant": GREEN})


def test_revert_mutant_is_the_reverse_diff_of_the_pr_sources(settings, fake_repo):
    patch = bench.revert_fix_mutant(settings, "2283")

    assert "--- a/src/Mutable.cs" in patch
    assert "-pr" in patch and "+base" in patch  # deshace el cambio del PR
    assert "file.txt" not in patch  # solo src/


def test_report_is_written_as_json(tmp_path):
    results = {"local": ({"base": RED, "pr": GREEN, "mutant": RED}, 54.0), "modal": ({"base": RED, "pr": GREEN, "mutant": RED}, 29.0)}

    path = bench.write_report("2283", results, tmp_path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["issue_id"] == "2283"
    assert data["modes"]["modal"]["wall_s"] == 29.0
    assert data["modes"]["local"]["results"]["pr"]["green"] is True
    assert data["modes"]["modal"]["as_expected"] is True
