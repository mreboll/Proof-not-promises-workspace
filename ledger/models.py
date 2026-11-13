"""Contratos compartidos entre la Línea A (evidencia) y la Línea B (triaje, interrogatorio e informe).

CONJUNTO: cualquier cambio en este fichero se avisa al otro antes de hacer merge.
Todos los modelos son inmutables (frozen); para "cambiar" uno, usa `model_copy(update=...)`.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, computed_field

Side = Literal["base", "pr"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Scope(str, Enum):
    IN = "IN"
    OUT = "OUT"


class Risk(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class Verdict(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class ChangeType(str, Enum):
    BUGFIX = "bugfix"
    FEATURE = "feature"


# --------------------------------------------------------------------------- Etapa 1 (B)


class FileTriage(_Frozen):
    path: str
    scope: Scope
    risk: Risk
    rule_hits: tuple[str, ...] = ()
    justification: str = ""
    touches_public_api: bool = False


# --------------------------------------------------------------------------- Etapa 2 (A)


class TestRunResult(_Frozen):
    __test__ = False  # evita que pytest intente recogerla como clase de test

    build_ok: bool
    passed: int
    failed: int
    output_tail: str = ""
    duration_s: float = 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def green(self) -> bool:
        """Compila, ejecuta al menos un test y no falla ninguno."""
        return self.build_ok and self.passed > 0 and self.failed == 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def red_for_real(self) -> bool:
        """Compila y algún test falla. Un fallo de compilación NO cuenta como 'reproduce el bug'."""
        return self.build_ok and self.failed > 0


class ChangeTestEvidence(_Frozen):
    issue_id: str
    change_type: ChangeType
    test_name: str
    test_code: str
    base: TestRunResult | None
    pr: TestRunResult

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ok(self) -> bool:
        if self.change_type is ChangeType.BUGFIX:
            return self.base is not None and self.base.red_for_real and self.pr.green
        return self.pr.green


class InvarianceCase(_Frozen):
    id: str
    tag: str  # "general" o "issue-<id>"
    base_hash: str
    base_hash_rerun: str
    pr_hash: str
    normalization: str = ""  # normalización declarada aplicada antes del hash (p. ej. #2297)


class InvarianceEvidence(_Frozen):
    cases: tuple[InvarianceCase, ...]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def deterministic(self) -> bool:
        return all(c.base_hash == c.base_hash_rerun for c in self.cases)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def unexpected_diffs(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.cases if c.tag == "general" and c.base_hash != c.pr_hash)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ok(self) -> bool:
        return bool(self.cases) and self.deterministic and not self.unexpected_diffs


# --------------------------------------------------------------------------- Etapa 3 (B)


class Objection(_Frozen):
    question: str
    rationale: str = ""
    test_name: str = ""
    test_code: str = ""
    pr_result: TestRunResult | None = None
    mutant_patch: str = ""
    mutant_result: TestRunResult | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid(self) -> bool:
        """Un test solo cuenta si pasa en el PR y FALLA contra el mutante (antitrampa)."""
        return (
            self.pr_result is not None
            and self.pr_result.green
            and self.mutant_result is not None
            and self.mutant_result.red_for_real
        )


# --------------------------------------------------------------------------- Veredicto e informe (B)


class FragmentVerdict(_Frozen):
    path: str
    verdict: Verdict
    reasons: tuple[str, ...] = ()
    objections: tuple[Objection, ...] = ()


class Report(_Frozen):
    issue_id: str
    change_type: ChangeType
    branch: str
    base_commit: str
    pr_commit: str
    generated_at: str
    triage: tuple[FileTriage, ...]
    change_test: ChangeTestEvidence | None = None
    invariance: InvarianceEvidence | None = None
    verdicts: tuple[FragmentVerdict, ...] = ()


# --------------------------------------------------------------------------- Frontera A ↔ B


class TestRunner(Protocol):
    """Lo implementa A en `ledger/evidence/dotnet.py`. B usa `ledger.fakes.FakeTestRunner` hasta la integración."""

    __test__ = False

    def run_tests(self, side: Side, test_code: str, test_name: str) -> TestRunResult: ...

    def run_against_mutant(
        self, side: Side, mutant_patch: str, test_code: str, test_name: str
    ) -> TestRunResult: ...
