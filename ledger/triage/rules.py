"""Etapa 1 (B), eje B: riesgo por reglas estáticas. Sin LLM y 100 % auditable (decision-log D1).

El riesgo de un fichero es el MÁXIMO de las reglas que se disparan, y cada regla disparada queda
en `rule_hits` con su id, su descripción y, si es de línea, la línea que la disparó. Mismo diff,
mismo riesgo, siempre.

Alcance de las reglas de línea: solo código de producción C# (`src/**/*.cs`), ignorando comentarios
y literales de cadena. Así los `public async Task` de los tests y el texto que emiten las plantillas
T4 (`.tt`) no cuentan como cambios de API pública.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict

from ledger.models import Risk
from ledger.triage.diff import FileDiff

_SRC_CS = r"^src/.*\.cs$"
SNAPSHOT_PATH = r"^tests/.*/Resources/.*\.g\.cs$"  # también lo usa scope.py para no gastar LLM


@dataclass(frozen=True)
class Rule:
    id: str
    risk: Risk
    description: str
    path_regex: str | None = None  # si hay line_regex, restringe a qué ficheros se aplica
    line_regex: str | None = None  # se evalúa sobre líneas añadidas Y quitadas
    public_api: bool = False  # si se dispara, el fichero toca la API pública
    _path: re.Pattern[str] | None = field(init=False, repr=False, compare=False, default=None)
    _line: re.Pattern[str] | None = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_path", re.compile(self.path_regex) if self.path_regex else None)
        object.__setattr__(self, "_line", re.compile(self.line_regex) if self.line_regex else None)


RULES: tuple[Rule, ...] = (
    Rule("R-LOW-01", Risk.LOW, "ruta tests/", path_regex=r"^tests/"),
    Rule("R-LOW-02", Risk.LOW, "documentación .md", path_regex=r"\.md$"),
    Rule("R-LOW-03", Risk.LOW, "proyecto .csproj", path_regex=r"\.csproj$"),
    Rule("R-LOW-04", Risk.LOW, ".editorconfig", path_regex=r"(^|/)\.editorconfig$"),
    Rule("R-LOW-05", Risk.LOW, "snapshot de código generado (Resources/**.g.cs)", path_regex=SNAPSHOT_PATH),
    Rule("R-MED-01", Risk.MED, "código de producción en src/ (lógica private/internal)", path_regex=r"^src/.*\.(cs|tt)$"),
    Rule(
        "R-HIGH-01",
        Risk.HIGH,
        "firma public añadida o quitada (contrato de API)",
        path_regex=_SRC_CS,
        line_regex=r"^\s*(?:\[[^\]]*\]\s*)*public\b",
        public_api=True,
    ),
    Rule("R-HIGH-02", Risk.HIGH, "memoria: Span<T>, unsafe o stackalloc", path_regex=_SRC_CS, line_regex=r"(?:ReadOnly)?Span<|\bunsafe\b|\bstackalloc\b"),
    Rule(
        "R-HIGH-03",
        Risk.HIGH,
        "namespace núcleo del generador (CodeAnalysis/Transforms)",
        path_regex=r"^src/MessagePack\.SourceGenerator/(CodeAnalysis|Transforms)/",
    ),
)

DEFAULT_RULE = Rule("R-DEFAULT", Risk.MED, "ninguna regla específica: MED por prudencia")

_ORDER = {Risk.LOW: 0, Risk.MED: 1, Risk.HIGH: 2}
_COMMENT = re.compile(r"^\s*(//|/\*|\*)")
_STRING = re.compile(r'@?"(?:\\.|""|[^"\\])*"')
_MAX_QUOTE = 80


class RiskAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    risk: Risk
    rule_hits: tuple[str, ...]
    touches_public_api: bool = False


def _code(line: str) -> str | None:
    """La línea sin literales de cadena, o None si es un comentario."""
    if _COMMENT.match(line):
        return None
    return _STRING.sub('""', line)


def _first_match(rule: Rule, fd: FileDiff) -> str | None:
    assert rule._line is not None
    for sign, lines in (("+", fd.added), ("-", fd.removed)):
        for line in lines:
            code = _code(line)
            if code is not None and rule._line.search(code):
                return f"{sign}`{line.strip()[:_MAX_QUOTE]}`"
    return None


def _fires(rule: Rule, fd: FileDiff) -> tuple[bool, str]:
    if rule._path and not rule._path.search(fd.path):
        return False, ""
    if rule._line is None:
        return True, ""
    quote = _first_match(rule, fd)
    return quote is not None, quote or ""


def _hit(rule: Rule, quote: str = "") -> str:
    return f"{rule.id}: {rule.description}" + (f" → {quote}" if quote else "")


def assess_risk(fd: FileDiff) -> RiskAssessment:
    hits: list[str] = []
    fired: list[Rule] = []
    for rule in RULES:
        ok, quote = _fires(rule, fd)
        if ok:
            fired.append(rule)
            hits.append(_hit(rule, quote))
    if not fired:
        fired, hits = [DEFAULT_RULE], [_hit(DEFAULT_RULE)]
    return RiskAssessment(
        risk=max((r.risk for r in fired), key=_ORDER.__getitem__),
        rule_hits=tuple(hits),
        touches_public_api=any(r.public_api for r in fired),
    )
