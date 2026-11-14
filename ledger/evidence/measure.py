"""Mide el pipeline completo en Modal con la caché del LLM VACÍA, en modo secuencial o paralelo.

Uso: python -m ledger.evidence.measure <issue> <seq|par> <out_dir>

Cada modo usa una caché del LLM nueva en <out_dir>/<issue>-<modo>/cache: comparación justa (si la caché
está caliente, el LLM tarda 0 y solo se mediría Modal). Guarda <out_dir>/<issue>-<modo>/summary.json.
"""

import json
import os
import sys
import time
import warnings
from dataclasses import replace
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

from ledger import llm, pipeline  # noqa: E402
from ledger.config import load_settings  # noqa: E402
from ledger.evidence import modal_runner  # noqa: E402
from ledger.evidence.modal_runner import ModalTestRunner  # noqa: E402

issue, mode, out_dir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
run_dir = out_dir / f"{issue}-{mode}"
run_dir.mkdir(parents=True, exist_ok=True)

if mode == "seq":
    ModalTestRunner.parallel_safe = False  # mismo runner, sin paralelismo: la referencia "antes"

settings = replace(load_settings(), cache_dir=run_dir / "cache", out_dir=run_dir / "out")
modal_runner.reset_sandbox_stats()
llm.reset_llm_stats()
started = time.monotonic()
report_path = pipeline.run(issue, settings, ModalTestRunner(settings, issue))
wall = time.monotonic() - started

report = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
objections = [o for v in report["verdicts"] for o in v["objections"]]
summary = {
    "issue": issue,
    "mode": mode,
    "wall_s": round(wall, 1),
    "sandboxes": modal_runner.sandbox_stats(),
    "llm": llm.llm_stats(),
    "config": {k: os.environ.get(k, "default") for k in (
        "LEDGER_CROSSEXAM_WORKERS", "LEDGER_MODAL_MAX_SANDBOXES", "LEDGER_MAX_CONCURRENT_GEMINI", "LEDGER_MAX_CONCURRENT_NVIDIA")},
    "files_cross_examined": sum(1 for v in report["verdicts"] if v["objections"]),
    "objections": len(objections),
    "objections_valid": sum(1 for o in objections if o["valid"]),
    "verdicts": {v["path"]: v["verdict"] for v in report["verdicts"] if v["verdict"] != "GREEN"},
}
(run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
