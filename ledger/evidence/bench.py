"""Comparativa reproducible Modal (paralelo, sin red) frente a local (secuencial) con el test del cambio real.

    python -m ledger.evidence.bench --issue 2283

Ejecuta base, PR y un mutante que DESHACE el propio fix del PR (el diff inverso de `src/`) con los dos
runners, imprime la tabla y guarda `out/bench-<issue>.json`. Usa el test de `fixtures/evidence_<issue>.json`.
Sirve para bug fixes cuyo PR solo modifica ficheros existentes de `src/` (p. ej. #2283).
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ledger.config import PROJECT_ROOT, Settings, get_issue, load_settings
from ledger.evidence._proc import git
from ledger.evidence.workspace import resolve_commit
from ledger.models import TestRunner, TestRunResult

Job = Callable[[], TestRunResult]
Results = dict[str, TestRunResult]
EXPECTED = {"base": "red", "pr": "green", "mutant": "red"}


def revert_fix_mutant(settings: Settings, issue_id: str) -> str:
    """Mutante "deshacer el fix": diff del PR a la base, solo en `src/`."""
    pr, base = resolve_commit(settings, issue_id, "pr"), resolve_commit(settings, issue_id, "base")
    return git(settings.msgpack_repo, "diff", pr, base, "--", "src").stdout


def jobs(runner: TestRunner, test_name: str, test_code: str, mutant_patch: str) -> dict[str, Job]:
    return {
        "base": lambda: runner.run_tests("base", test_code, test_name),
        "pr": lambda: runner.run_tests("pr", test_code, test_name),
        "mutant": lambda: runner.run_against_mutant("pr", mutant_patch, test_code, test_name),
    }


def run_parallel(named_jobs: dict[str, Job]) -> tuple[Results, float]:
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(named_jobs)) as pool:
        futures = {name: pool.submit(job) for name, job in named_jobs.items()}
        results = {name: future.result() for name, future in futures.items()}
    return results, time.monotonic() - started


def run_sequential(named_jobs: dict[str, Job]) -> tuple[Results, float]:
    started = time.monotonic()
    results = {name: job() for name, job in named_jobs.items()}
    return results, time.monotonic() - started


def _outcome(result: TestRunResult) -> str:
    return "green" if result.green else "red" if result.red_for_real else "no-evidence"


def matches_expectation(results: Results) -> bool:
    return all(_outcome(results[name]) == expected for name, expected in EXPECTED.items())


def write_report(issue_id: str, modes: dict[str, tuple[Results, float]], out_dir: Path) -> Path:
    data = {
        "issue_id": issue_id,
        "expected": EXPECTED,
        "modes": {
            mode: {
                "wall_s": round(wall, 1),
                "as_expected": matches_expectation(results),
                "results": {name: json.loads(r.model_dump_json()) for name, r in results.items()},
            }
            for mode, (results, wall) in modes.items()
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"bench-{issue_id}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    from ledger.evidence.dotnet import DotnetTestRunner
    from ledger.evidence.modal_runner import ModalTestRunner

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issue", required=True)
    args = parser.parse_args(argv)
    get_issue(args.issue)
    settings = load_settings()
    ct = json.loads((PROJECT_ROOT / "fixtures" / f"evidence_{args.issue}.json").read_text(encoding="utf-8"))["change_test"]
    mutant = revert_fix_mutant(settings, args.issue)

    modal = ModalTestRunner(settings, args.issue)
    modal.run_tests("pr", ct["test_code"], ct["test_name"])  # calentamiento: imagen y arranque fuera de la medida
    modes = {
        "modal": run_parallel(jobs(modal, ct["test_name"], ct["test_code"], mutant)),
        "local": run_sequential(jobs(DotnetTestRunner(settings, args.issue), ct["test_name"], ct["test_code"], mutant)),
    }
    for mode, (results, wall) in modes.items():
        cells = "  ".join(f"{name}={_outcome(r)} ({r.duration_s:.0f}s)" for name, r in results.items())
        print(f"{mode:6s} {wall:5.0f}s  {cells}  {'OK' if matches_expectation(results) else 'UNEXPECTED'}")
    print(f"Informe: {write_report(args.issue, modes, settings.out_dir)}")


if __name__ == "__main__":
    main()
