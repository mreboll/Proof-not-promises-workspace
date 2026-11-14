"""Del `.trx` de `dotnet test` (y la salida de build) a `TestRunResult`.

Común a `DotnetTestRunner` y al runner de Modal. No se parsea la salida de consola de dotnet:
viene localizada (en este equipo, en español) y su exit code mezcla "no compila" con "falla un test".
Regla: si hay `.trx`, compiló; si no lo hay, la build falló.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from ledger.models import TestRunResult

_NS = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
_COMPILE_ERROR = re.compile(r"^.*\berror (?:CS|MSB|NU)\d{4}\b.*$", re.MULTILINE)
_FAILED_COUNTERS = ("failed", "error", "timeout", "aborted")
# Excepciones que indican que el test no pudo ni ejecutarse de verdad (sin red, NuGet caído...).
_INFRA_MARKERS = (
    "System.Net.Http.HttpRequestException",
    "System.Net.Sockets.SocketException",
    "NuGet.Protocol.Core.Types.FatalProtocolException",
)
MAX_TAIL_CHARS = 4000
MAX_FAILURE_MESSAGE_CHARS = 800


@dataclass(frozen=True)
class TrxSummary:
    total: int
    passed: int
    failed: int
    failures: tuple[str, ...]  # "<testName>: <mensaje>"


def parse_trx(text: str) -> TrxSummary:
    root = ET.fromstring(text)
    counters = root.find("t:ResultSummary/t:Counters", _NS)
    if counters is None:
        raise ValueError("el .trx no tiene ResultSummary/Counters")
    count = lambda name: int(counters.get(name, "0"))  # noqa: E731
    failures = tuple(
        f"{r.get('testName', '?')}: {_message(r)}"
        for r in root.iterfind("t:Results/t:UnitTestResult", _NS)
        if r.get("outcome") not in ("Passed", "NotExecuted")
    )
    return TrxSummary(
        total=count("total"),
        passed=count("passed"),
        failed=sum(count(name) for name in _FAILED_COUNTERS),
        failures=failures,
    )


def extract_compile_errors(build_output: str) -> tuple[str, ...]:
    """Líneas `error CSxxxx` (y MSB/NU) sin duplicados, en orden de aparición."""
    seen: dict[str, None] = {}
    for line in _COMPILE_ERROR.findall(build_output):
        seen.setdefault(line.strip(), None)
    return tuple(seen)


def build_result(trx_text: str | None, build_output: str, duration_s: float) -> TestRunResult:
    if trx_text is None:
        errors = extract_compile_errors(build_output)
        detail = "\n".join(errors) if errors else build_output[-MAX_TAIL_CHARS:]
        return TestRunResult(build_ok=False, passed=0, failed=0, output_tail=_clip(f"BUILD FAILED\n{detail}"), duration_s=duration_s)
    try:
        summary = parse_trx(trx_text)
    except (ET.ParseError, ValueError) as exc:
        return TestRunResult(build_ok=False, passed=0, failed=0, output_tail=f"trx ilegible: {exc}", duration_s=duration_s)
    if any(marker in failure for failure in summary.failures for marker in _INFRA_MARKERS):
        # Un fallo de red/descarga no dice nada del código: no puede contar como "reproduce el bug".
        return TestRunResult(
            build_ok=False, passed=summary.passed, failed=summary.failed,
            output_tail=_clip(f"INFRA: test failed for infrastructure reasons (network/package download)\n{_describe(summary)}"),
            duration_s=duration_s,
        )
    return TestRunResult(
        build_ok=True,
        passed=summary.passed,
        failed=summary.failed,
        output_tail=_clip(_describe(summary)),
        duration_s=duration_s,
    )


def _describe(summary: TrxSummary) -> str:
    if summary.total == 0:
        return "no test matched the filter (0 executed)"
    head = f"{summary.passed} passed, {summary.failed} failed (of {summary.total})"
    return "\n".join((head, *summary.failures))


def _message(result: ET.Element) -> str:
    node = result.find("t:Output/t:ErrorInfo/t:Message", _NS)
    text = (node.text or "") if node is not None else ""
    return text.replace("\r", "").strip()[:MAX_FAILURE_MESSAGE_CHARS]


def _clip(text: str) -> str:
    return text if len(text) <= MAX_TAIL_CHARS else text[:MAX_TAIL_CHARS] + "\n…"
