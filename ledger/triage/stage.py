"""Etapa 1 completa (B): diff → reglas estáticas (riesgo) + LLM (alcance) → FileTriage por fichero.

`pipeline.stage1_triage` solo delega aquí, para que el cableado en el fichero compartido sea una línea.
"""

from __future__ import annotations

import os

from ledger import llm
from ledger.config import Settings
from ledger.crossexam.concurrency import ordered_map
from ledger.models import FileTriage
from ledger.triage.diff import FileDiff, load_diff
from ledger.triage.rules import assess_risk
from ledger.triage.scope import Complete, classify_scope, load_issue_text

DEFAULT_TRIAGE_WORKERS = 16


def triage_file(issue_text: str, fd: FileDiff, *, complete: Complete = llm.complete, settings: Settings | None = None) -> FileTriage:
    risk = assess_risk(fd)
    scope, justification = classify_scope(issue_text, fd, complete=complete, settings=settings)
    return FileTriage(
        path=fd.path,
        scope=scope,
        risk=risk.risk,
        rule_hits=risk.rule_hits,
        justification=justification,
        touches_public_api=risk.touches_public_api,
    )


def triage_workers() -> int:
    """Ficheros clasificados a la vez (LEDGER_TRIAGE_WORKERS). Solo son llamadas al LLM: el tope real es su semáforo."""
    return max(1, int(os.environ.get("LEDGER_TRIAGE_WORKERS", DEFAULT_TRIAGE_WORKERS)))


def triage_issue(settings: Settings, issue_id: str, *, complete: Complete = llm.complete) -> tuple[FileTriage, ...]:
    issue_text = load_issue_text(settings, issue_id)
    files = load_diff(settings, issue_id)
    # Cada fichero se clasifica por separado: van a la vez, y el resultado conserva el orden del diff.
    return tuple(ordered_map(lambda fd: triage_file(issue_text, fd, complete=complete, settings=settings), files, triage_workers()))
