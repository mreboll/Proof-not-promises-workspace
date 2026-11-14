"""Barrido de capacidad: utilidades puras (la ejecución real necesita Modal y claves)."""

from __future__ import annotations

import pytest

from ledger.evidence import capacity
from ledger.fakes import GREEN, RED
from ledger.models import TestRunResult


def test_parse_levels_sorts_and_dedups():
    assert capacity.parse_levels("8,1,4,8") == [1, 4, 8]


@pytest.mark.parametrize("bad", ["", "0", "a,2", "-1"])
def test_parse_levels_rejects_garbage(bad):
    with pytest.raises(ValueError):
        capacity.parse_levels(bad)


def test_summarize_level_counts_ok_and_computes_throughput():
    row = capacity.summarize_level(4, wall_s=10.0, latencies=[2.0, 4.0, 6.0, 8.0], ok=3)
    assert row == {"n": 4, "wall_s": 10.0, "ok": 3, "failed": 1, "p50_s": 5.0, "max_s": 8.0, "per_min": 18.0}


def test_runner_job_is_ok_only_with_real_green():
    infra = TestRunResult(build_ok=False, passed=0, failed=0, output_tail="NuGet", duration_s=1.0)
    assert capacity.run_ok(GREEN) and not capacity.run_ok(RED) and not capacity.run_ok(infra)


def test_knee_is_the_last_level_that_still_scales():
    rows = [
        {"n": 1, "per_min": 2.0, "failed": 0},
        {"n": 8, "per_min": 15.0, "failed": 0},
        {"n": 16, "per_min": 16.0, "failed": 0},  # +7 %: ya no compensa
        {"n": 32, "per_min": 10.0, "failed": 3},
    ]
    assert capacity.knee(rows) == 8


def test_knee_ignores_levels_with_failures():
    rows = [{"n": 1, "per_min": 2.0, "failed": 0}, {"n": 4, "per_min": 8.0, "failed": 1}]
    assert capacity.knee(rows) == 1
