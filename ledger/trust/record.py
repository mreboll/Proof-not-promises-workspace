"""El historial (track record): lo que pasó DESPUÉS de cada firma, en un JSON versionado en el repo.

Dos tipos de evento, en orden:
- `change`: una persona con nombre firmó un cambio; cuántos ficheros aprobó la evidencia en cada área y cuántos leyó.
- `escape`: algo que la evidencia aprobó resultó estar mal (lo encontró un spot-check, un revert, un incidente o una
  nueva ejecución). Es el dato que retira la confianza de un área.

Inmutable: `add` devuelve un historial nuevo. Nada aquí lo escribe un modelo: lo registran personas con la CLI.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from ledger.config import PROJECT_ROOT
from ledger.models import FragmentVerdict, Report, Verdict

DEFAULT_RECORD = PROJECT_ROOT / "trust" / "track_record.json"
FoundBy = Literal["spot-check", "revert", "incident", "rerun"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class ChangeEvent(_Frozen):
    kind: Literal["change"] = "change"
    issue_id: str
    date: str
    owner: str
    approved: dict[str, int] = Field(default_factory=dict)  # área → ficheros aprobados por la evidencia (verdes)
    reviewed: dict[str, int] = Field(default_factory=dict)  # área → ficheros que leyó una persona (amarillos/rojos)


class EscapeEvent(_Frozen):
    kind: Literal["escape"] = "escape"
    issue_id: str
    date: str
    area: str
    path: str
    found_by: FoundBy
    description: str
    source: str = ""  # dónde se puede comprobar (fichero, commit, incidente)


Event = Annotated[Union[ChangeEvent, EscapeEvent], Field(discriminator="kind")]


class TrackRecord(_Frozen):
    events: tuple[Event, ...] = ()


def add(record: TrackRecord, event: ChangeEvent | EscapeEvent) -> TrackRecord:
    return TrackRecord(events=(*record.events, event))


def change_from_report(report: Report, *, owner: str, date: str) -> ChangeEvent:
    from ledger.trust.policy import area_of  # import local: policy depende de este módulo

    from ledger.trust.policy import TRUST_CODE

    def evidence_approved(v: FragmentVerdict) -> bool:
        # T1: la evidencia lo aprobó y una persona lo leyó por la confianza retirada. Cuenta como aprobado: si no,
        # un área retirada nunca podría volver a ganarse (sus verdes siempre salen T1).
        return v.verdict is Verdict.GREEN or bool(v.reasons and v.reasons[0].startswith(f"{TRUST_CODE}:"))

    approved = Counter(area_of(v.path) for v in report.verdicts if evidence_approved(v))
    reviewed = Counter(area_of(v.path) for v in report.verdicts if v.verdict is not Verdict.GREEN)
    return ChangeEvent(issue_id=report.issue_id, date=date, owner=owner, approved=dict(approved), reviewed=dict(reviewed))


def load_record(path: Path = DEFAULT_RECORD) -> TrackRecord:
    if not path.exists():
        return TrackRecord()
    return TrackRecord.model_validate_json(path.read_text(encoding="utf-8"))


def save_record(record: TrackRecord, path: Path = DEFAULT_RECORD) -> None:
    """Escritura atómica: un historial a medio escribir haría perder la memoria de los escapes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
