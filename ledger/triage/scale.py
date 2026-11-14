"""Escala de la Etapa 1 (paso 7 de B): triaje masivo con números reales para el pitch.

    python -m ledger.triage.scale 2297

Escribe fixtures/triage_<id>.json (para `ledger run --fixtures`) y out/scale-<id>.json (el resumen).
`llm_calls` cuenta las peticiones al rol "flash"; las que ya estaban en caché no gastan cuota, por eso
también se cuentan los ficheros nuevos en .cache/llm (`api_calls_new`).
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

from ledger import llm
from ledger.config import PROJECT_ROOT, Settings, load_settings
from ledger.models import FileTriage, Risk, Scope
from ledger.triage.diff import load_diff
from ledger.triage.scope import Complete, load_issue_text
from ledger.triage.stage import triage_file


def _cache_size(settings: Settings) -> int:
    folder = settings.cache_dir / "llm"
    return len(list(folder.glob("*.txt"))) if folder.exists() else 0


def run_scale(settings: Settings, issue_id: str, *, complete: Complete = llm.complete, progress: bool = False) -> tuple[tuple[FileTriage, ...], dict[str, Any]]:
    calls = 0

    def counted(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        if progress:
            print(f"  LLM {calls}: {args[1].split('File: ')[1].splitlines()[0]}", file=sys.stderr, flush=True)
        return complete(*args, **kwargs)

    cache_before = _cache_size(settings)
    started = time.perf_counter()
    issue_text = load_issue_text(settings, issue_id)
    files = load_diff(settings, issue_id)
    triage = tuple(triage_file(issue_text, fd, complete=counted, settings=settings) for fd in files)
    elapsed = time.perf_counter() - started

    def count(scope: Scope | None = None, risk: Risk | None = None) -> int:
        return sum((scope is None or t.scope is scope) and (risk is None or t.risk is risk) for t in triage)

    stage1 = {
        "red_out_high": count(Scope.OUT, Risk.HIGH),
        "yellow_out": count(Scope.OUT, Risk.MED) + count(Scope.OUT, Risk.LOW),
        "to_evidence_low_med": count(Scope.IN, Risk.LOW) + count(Scope.IN, Risk.MED),
        "to_crossexam_high": count(Scope.IN, Risk.HIGH),
    }
    summary = {
        "issue_id": issue_id,
        "files": len(triage),
        "elapsed_s": round(elapsed, 2),
        "llm_calls": calls,
        "skipped_llm_by_rule": len(triage) - calls,
        "api_calls_new": _cache_size(settings) - cache_before,
        "flash_model": llm.model_for("flash", settings),
        "by_risk": {r.value: count(risk=r) for r in Risk},
        "by_scope": {s.value: count(scope=s) for s in Scope},
        "matrix": {s.value: {r.value: count(s, r) for r in Risk} for s in Scope},
        "stage1": stage1,
        "human_reads": stage1["red_out_high"] + stage1["yellow_out"] + stage1["to_crossexam_high"],
        "public_api_files": sum(t.touches_public_api for t in triage),
    }
    return triage, summary


def main(issue_id: str) -> None:
    settings = load_settings()
    triage, summary = run_scale(settings, issue_id, progress=True)
    fixture = PROJECT_ROOT / "fixtures" / f"triage_{issue_id}.json"
    fixture.write_text(json.dumps([t.model_dump(mode="json") for t in triage], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    settings.out_dir.mkdir(parents=True, exist_ok=True)
    (settings.out_dir / f"scale-{issue_id}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2297")
