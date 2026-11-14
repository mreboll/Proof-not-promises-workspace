"""Etapa 1 completa (B): diff → reglas estáticas (riesgo) + LLM (alcance) → FileTriage por fichero.

`pipeline.stage1_triage` solo delega aquí, para que el cableado en el fichero compartido sea una línea.
"""

from __future__ import annotations

from ledger import llm
from ledger.config import Settings
from ledger.models import FileTriage
from ledger.triage.diff import FileDiff, load_diff
from ledger.triage.rules import assess_risk
from ledger.triage.scope import Complete, classify_scope, load_issue_text


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


def triage_issue(settings: Settings, issue_id: str, *, complete: Complete = llm.complete) -> tuple[FileTriage, ...]:
    issue_text = load_issue_text(settings, issue_id)
    return tuple(triage_file(issue_text, fd, complete=complete, settings=settings) for fd in load_diff(settings, issue_id))
