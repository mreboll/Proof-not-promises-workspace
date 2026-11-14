"""Barrido de capacidad: ¿hasta cuántas ejecuciones a la vez sigue escalando cada recurso de la Etapa 3?

    python -m ledger.evidence.capacity modal 1,4,8,16,32,60          # N sandboxes a la vez (test real de #2283)
    python -m ledger.evidence.capacity llm pro 1,4,8,16,32           # N llamadas a la vez a Gemini pro (sin caché)
    python -m ledger.evidence.capacity llm fiscal 1,4,8,16           # ídem con Nemotron

Cada recurso se mide por separado, con trabajo idéntico en cada nivel, para que la curva no dependa de qué
objeciones invente el LLM ese día. Por nivel: tiempo total, latencias, fallos y rendimiento (trabajos/min).
El "codo" es el último nivel sin fallos cuyo rendimiento aún mejora ≥ 20 % frente al anterior: ese es el tope
recomendado (LEDGER_MODAL_MAX_SANDBOXES, LEDGER_MAX_CONCURRENT_GEMINI / _NVIDIA). Guarda out/capacity-<recurso>.json.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ledger.config import PROJECT_ROOT, load_settings
from ledger.models import TestRunResult

MIN_GAIN = 1.2  # un nivel "compensa" si da al menos un 20 % más de trabajos por minuto que el anterior
BENCH_ISSUE = "2283"
PING_SYSTEM = "You are a load probe. Answer with exactly the single word OK."


def parse_levels(raw: str) -> list[int]:
    try:
        levels = sorted({int(part) for part in raw.split(",")})
    except ValueError as exc:
        raise ValueError(f"niveles inválidos {raw!r}: usa enteros separados por comas, p. ej. 1,4,8") from exc
    if not levels or levels[0] < 1:
        raise ValueError(f"niveles inválidos {raw!r}: deben ser ≥ 1")
    return levels


def run_ok(result: TestRunResult) -> bool:
    """Solo cuenta un verde real: un fallo de build/infra o un rojo es un trabajo fallido."""
    return result.green


def summarize_level(n: int, *, wall_s: float, latencies: list[float], ok: int) -> dict[str, Any]:
    return {
        "n": n,
        "wall_s": round(wall_s, 1),
        "ok": ok,
        "failed": n - ok,
        "p50_s": round(statistics.median(latencies), 1),
        "max_s": round(max(latencies), 1),
        "per_min": round(ok * 60 / wall_s, 1) if wall_s > 0 else 0.0,
    }


def knee(rows: list[dict[str, Any]]) -> int:
    """Último nivel sin fallos que todavía mejora el rendimiento en ≥ MIN_GAIN respecto al nivel bueno anterior."""
    best: dict[str, Any] | None = None
    for row in rows:
        if row["failed"]:
            continue
        if best is None or row["per_min"] >= best["per_min"] * MIN_GAIN:
            best = row
    return best["n"] if best else 0


def _burst(n: int, job: Callable[[int], tuple[bool, float]]) -> dict[str, Any]:
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=n) as pool:
        outcomes = list(pool.map(job, range(n)))
    wall = time.monotonic() - started
    return summarize_level(n, wall_s=wall, latencies=[lat for _, lat in outcomes], ok=sum(1 for good, _ in outcomes if good))


def sweep_modal(levels: list[int]) -> dict[str, Any]:
    from ledger.evidence import modal_runner
    from ledger.evidence.modal_runner import ModalTestRunner

    os.environ["LEDGER_MODAL_MAX_SANDBOXES"] = str(max(levels))  # el semáforo no debe ser el que limita
    settings = load_settings()
    ct = json.loads((PROJECT_ROOT / "fixtures" / f"evidence_{BENCH_ISSUE}.json").read_text(encoding="utf-8"))["change_test"]
    runner = ModalTestRunner(settings, BENCH_ISSUE)
    runner.run_tests("pr", ct["test_code"], ct["test_name"])  # calentamiento: imagen y arranque fuera de la medida

    def job(_: int) -> tuple[bool, float]:
        result = runner.run_tests("pr", ct["test_code"], ct["test_name"])
        return run_ok(result), result.duration_s

    rows = []
    for n in levels:
        modal_runner.reset_sandbox_stats()
        row = {**_burst(n, job), "sandbox_peak": modal_runner.sandbox_stats()["peak"]}
        rows.append(row)
        print(json.dumps(row), flush=True)
    return {"resource": "modal", "job": f"test del cambio de #{BENCH_ISSUE} en el PR (cpu=4)", "levels": rows, "knee": knee(rows)}


def sweep_llm(role: str, levels: list[int]) -> dict[str, Any]:
    from ledger import llm

    provider = "nvidia" if role == "fiscal" else "gemini"
    os.environ[f"LEDGER_MAX_CONCURRENT_{provider.upper()}"] = str(max(levels))
    llm._reset_limits()
    settings = load_settings()
    model = llm.model_for(role, settings)  # type: ignore[arg-type]

    def job(_: int) -> tuple[bool, float]:
        started = time.monotonic()
        try:  # prompt único (nonce) y sin caché: cada llamada llega de verdad al proveedor
            llm.complete(PING_SYSTEM, f"Probe {uuid.uuid4()}", role=role, settings=settings, use_cache=False)  # type: ignore[arg-type]
            return True, time.monotonic() - started
        except llm.LLMError:
            return False, time.monotonic() - started

    rows = []
    for n in levels:
        llm.reset_llm_stats()
        row = _burst(n, job)
        stats = llm.llm_stats()[provider]
        row.update(errors=stats["errors"], timeouts=stats["timeouts"], requests=stats["requests"])
        rows.append(row)
        print(json.dumps(row), flush=True)
    return {"resource": f"llm-{role}", "model": model, "job": "ping de una palabra (latencia de cola y 429, no de prompts largos)", "levels": rows, "knee": knee(rows)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="resource", required=True)
    sub.add_parser("modal").add_argument("levels", type=parse_levels)
    llm_p = sub.add_parser("llm")
    llm_p.add_argument("role", choices=["pro", "flash", "fiscal"])
    llm_p.add_argument("levels", type=parse_levels)
    args = parser.parse_args(argv)

    result = sweep_modal(args.levels) if args.resource == "modal" else sweep_llm(args.role, args.levels)
    out = load_settings().out_dir
    out.mkdir(parents=True, exist_ok=True)
    path: Path = out / f"capacity-{result['resource']}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"codo: {result['knee']}  ·  {path}")


if __name__ == "__main__":
    main()
