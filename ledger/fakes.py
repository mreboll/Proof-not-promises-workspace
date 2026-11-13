"""Dobles de prueba para trabajar en paralelo. B usa FakeTestRunner hasta que A entrega `evidence/dotnet.py`."""

from __future__ import annotations

from dataclasses import dataclass, field

from ledger.models import Side, TestRunResult

GREEN = TestRunResult(build_ok=True, passed=1, failed=0, output_tail="Passed!")
RED = TestRunResult(build_ok=True, passed=0, failed=1, output_tail="Failed: assertion")

# Tests vacíos que "aprueban cualquier cosa": contra el mutante también pasan, así que se rechazan.
TRIVIAL_MARKERS = ("Assert.True(true)", "Assert.Equal(1, 1)")


@dataclass(frozen=True)
class FakeTestRunner:
    """Simula el comportamiento esperado de un PR correcto:

    - En `pr` todo test pasa; en `base`, el test del cambio falla (bug reproducido).
    - Contra el mutante, un test real falla; uno trivial pasa (y por tanto no es válido).
    - `overrides` fuerza resultados por `test_name` para probar los caminos en rojo.
    """

    overrides: dict[str, TestRunResult] = field(default_factory=dict)

    def run_tests(self, side: Side, test_code: str, test_name: str) -> TestRunResult:
        if test_name in self.overrides:
            return self.overrides[test_name]
        return GREEN if side == "pr" else RED

    def run_against_mutant(self, side: Side, mutant_patch: str, test_code: str, test_name: str) -> TestRunResult:
        if any(marker in test_code for marker in TRIVIAL_MARKERS):
            return GREEN
        return RED
