"""Política de confianza por área (decisión D17). Funciones puras sobre el `Report` y el `TrackRecord`.

- Área = carpeta del fichero hasta AREA_DEPTH niveles. Regla fija, auditable; no la decide un modelo.
- Nivel: EN PRUEBA por defecto; GANADA tras EARN_AFTER cambios firmados con ficheros aprobados en el área y sin escapes
  desde entonces; RETIRADA si hubo un escape y aún no se han vuelto a ganar EARN_AFTER cambios limpios.
- Efecto: en un área RETIRADA, lo verde pasa a amarillo (TR: una persona lo lee). En las demás, una muestra de lo verde
  va a spot-check humano (SPOT_RATE según el nivel, mínimo 1 y máximo SPOT_MAX por área). La muestra es determinista (hash del issue y la
  ruta): no la elige la IA ni quien firma, y quien audite puede recalcularla.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath

from ledger.models import FragmentVerdict, Report, Verdict
from ledger.trust.record import ChangeEvent, EscapeEvent, TrackRecord

AREA_DEPTH = 3
EARN_AFTER = 5


class Level(str, Enum):
    PROBATION = "probation"
    EARNED = "earned"
    WITHDRAWN = "withdrawn"


SPOT_RATE = {Level.PROBATION: 0.20, Level.EARNED: 0.05}
SPOT_MAX = {Level.PROBATION: 3, Level.EARNED: 1}  # por área: un spot-check es una muestra, no una lectura entera
TRUST_CODE = "TR"


def area_of(path: str) -> str:
    parts = PurePosixPath(path).parent.parts[:AREA_DEPTH]
    return "/".join(parts) if parts else "."


@dataclass(frozen=True)
class AreaTrust:
    area: str
    level: Level
    clean_changes: int  # cambios firmados con ficheros aprobados en el área (en total)
    clean_since_escape: int
    escapes: tuple[EscapeEvent, ...] = ()


def area_trust(record: TrackRecord, area: str) -> AreaTrust:
    clean = since = 0
    escapes: list[EscapeEvent] = []
    for event in record.events:
        if isinstance(event, ChangeEvent) and event.approved.get(area, 0) > 0:
            clean += 1
            since += 1
        elif isinstance(event, EscapeEvent) and event.area == area:
            escapes.append(event)
            since = 0
    if escapes and since < EARN_AFTER:
        level = Level.WITHDRAWN
    elif since >= EARN_AFTER:
        level = Level.EARNED
    else:
        level = Level.PROBATION
    return AreaTrust(area, level, clean, since, tuple(escapes))


def _withdrawn_reason(trust: AreaTrust) -> str:
    last = trust.escapes[-1]
    return (
        f"{TRUST_CODE}: trust withdrawn in {trust.area}: the evidence approved a defect here before "
        f"(#{last.issue_id}, found by {last.found_by}: {last.description}). A human reads this file until "
        f"{EARN_AFTER} clean signed changes ({trust.clean_since_escape} so far)."
    )


def apply_trust(report: Report, record: TrackRecord) -> Report:
    """Lo verde de un área con la confianza retirada pasa a amarillo. Idempotente; lo demás no cambia."""
    trusts = {area: area_trust(record, area) for area in {area_of(v.path) for v in report.verdicts}}

    def adjust(v: FragmentVerdict) -> FragmentVerdict:
        trust = trusts[area_of(v.path)]
        if v.verdict is not Verdict.GREEN or trust.level is not Level.WITHDRAWN:
            return v
        return v.model_copy(update={"verdict": Verdict.YELLOW, "reasons": (_withdrawn_reason(trust), *v.reasons)})

    return report.model_copy(update={"verdicts": tuple(adjust(v) for v in report.verdicts)})


@dataclass(frozen=True)
class SpotCheck:
    path: str
    area: str
    level: Level


def _sample_key(issue_id: str, path: str) -> str:
    return hashlib.sha256(f"{issue_id}:{path}".encode("utf-8")).hexdigest()


def spot_checks(report: Report, record: TrackRecord) -> tuple[SpotCheck, ...]:
    """Ficheros verdes que una persona debe leer enteros para vigilar al revisor de IA (y registrar lo que encuentre)."""
    greens: dict[str, list[str]] = defaultdict(list)
    for v in report.verdicts:
        if v.verdict is Verdict.GREEN:
            greens[area_of(v.path)].append(v.path)
    picked: list[SpotCheck] = []
    for area in sorted(greens):
        trust = area_trust(record, area)
        if trust.level is Level.WITHDRAWN:
            continue  # ya se lee todo (TR)
        paths = sorted(greens[area], key=lambda p: _sample_key(report.issue_id, p))
        k = min(SPOT_MAX[trust.level], max(1, math.ceil(SPOT_RATE[trust.level] * len(paths))))
        picked.extend(SpotCheck(p, area, trust.level) for p in paths[:k])
    return tuple(picked)


@dataclass(frozen=True)
class AreaOutcome:
    area: str
    level: Level
    changes: int
    approved_files: int
    escapes: dict[str, int] = field(default_factory=dict)

    @property
    def escape_rate(self) -> float:
        """Escapes por fichero aprobado por la evidencia: el dato de resultado, no de actividad."""
        return sum(self.escapes.values()) / self.approved_files if self.approved_files else 0.0


def outcomes(record: TrackRecord) -> tuple[AreaOutcome, ...]:
    areas = sorted(
        {a for e in record.events if isinstance(e, ChangeEvent) for a in e.approved}
        | {e.area for e in record.events if isinstance(e, EscapeEvent)}
    )
    rows = []
    for area in areas:
        approved = sum(e.approved.get(area, 0) for e in record.events if isinstance(e, ChangeEvent))
        changes = sum(1 for e in record.events if isinstance(e, ChangeEvent) and e.approved.get(area, 0) > 0)
        found = Counter(e.found_by for e in record.events if isinstance(e, EscapeEvent) and e.area == area)
        rows.append(AreaOutcome(area, area_trust(record, area).level, changes, approved, dict(found)))
    return tuple(rows)
