"""Regenera `fixtures/evidence_<issue>.json` con el motor real: la evidencia se puede volver a obtener.

    python -m ledger.evidence.regen --issue 2283                 # test del cambio + invarianza, dotnet local
    python -m ledger.evidence.regen --issue 2283 --runner modal  # el código de la IA va a Modal Sandboxes
    python -m ledger.evidence.regen --issue 2297 --only-invariance  # sin LLM: conserva el test del cambio anterior

Cada fixture guarda su procedencia (comando, runner, modelo `pro`, fecha) para que el informe diga la verdad.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ledger.config import PROJECT_ROOT, Settings, get_issue, load_settings
from ledger.evidence.change_test import generate_change_test
from ledger.evidence.invariance import collect_invariance
from ledger.llm import model_for
from ledger.models import TestRunner

FIXTURES_DIR = PROJECT_ROOT / "fixtures"
RUNNERS = ("local", "modal")


def make_runner(settings: Settings, issue_id: str, name: str) -> TestRunner:
    if name == "modal":
        from ledger.evidence.modal_runner import ModalTestRunner

        return ModalTestRunner(settings, issue_id)
    from ledger.evidence.dotnet import DotnetTestRunner

    return DotnetTestRunner(settings, issue_id)


def regenerate(
    issue_id: str,
    settings: Settings,
    *,
    runner_name: str = "local",
    only_invariance: bool = False,
    fixtures_dir: Path = FIXTURES_DIR,
) -> Path:
    get_issue(issue_id)  # ValueError si el issue no existe
    target = fixtures_dir / f"evidence_{issue_id}.json"

    if only_invariance:
        if not target.exists():
            raise FileNotFoundError(f"{target.name} no existe: ejecuta primero sin --only-invariance")
        change_test = json.loads(target.read_text(encoding="utf-8"))["change_test"]
    else:
        evidence = generate_change_test(issue_id, settings, make_runner(settings, issue_id, runner_name))
        change_test = json.loads(evidence.model_dump_json())

    invariance = json.loads(collect_invariance(settings, issue_id).model_dump_json())
    command = f"python -m ledger.evidence.regen --issue {issue_id} --runner {runner_name}"
    data = {
        "provenance": {
            "command": command + (" --only-invariance" if only_invariance else ""),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "runner": runner_name,
            "model_pro": model_for("pro", settings),
            "change_test": "kept from previous fixture" if only_invariance else "regenerated",
        },
        "change_test": change_test,
        "invariance": invariance,
    }
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issue", required=True)
    parser.add_argument("--runner", choices=RUNNERS, default="local")
    parser.add_argument("--only-invariance", action="store_true")
    args = parser.parse_args(argv)
    path = regenerate(args.issue, load_settings(), runner_name=args.runner, only_invariance=args.only_invariance)
    print(f"Evidencia: {path}")


if __name__ == "__main__":
    main()
