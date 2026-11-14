"""Etapa 3 (B): el bucle del interrogatorio. Una objeción solo se cierra con un test que pasa en el PR y
FALLA contra el mutante (`Objection.valid`). Hasta MAX_ROUNDS intentos del Defensor por objeción.

Por objeción:
  1. Se genera el mutante una vez (sin ver el test: así el test no se escribe a medida del parche).
  2. Ronda: el Defensor escribe el test → runner en el PR → runner contra el mutante.
     Si falla un paso, la siguiente ronda recibe el motivo (salida del build, o la explicación del mutante).
"""

from __future__ import annotations

from typing import Callable

from ledger import llm
from ledger.config import Settings
from ledger.crossexam.defensor import write_test
from ledger.crossexam.fiscal import raise_objections
from ledger.crossexam.mutant_gen import make_mutant
from ledger.models import Objection, TestRunner
from ledger.triage.diff import FileDiff
from ledger.triage.scope import Complete

MAX_ROUNDS = 3
STYLE_EXAMPLE_PATH = "tests/MessagePack.SourceGenerator.Tests/GenericsFormatterTests.cs"
STYLE_EXAMPLE_CHARS = 3000

ReadSource = Callable[[str], str]


def test_class_name(issue_id: str, n: int) -> str:
    return f"Ledger_{issue_id}_Objection{n}"


test_class_name.__test__ = False  # type: ignore[attr-defined]  # que pytest no la tome por un test


def _safe_read(read_source: ReadSource, path: str) -> str:
    try:
        return read_source(path)
    except Exception:  # noqa: BLE001 - sin fuente no hay mutante; el bucle lo registra como no validable
        return ""


def _defend(
    issue_text: str, fd: FileDiff, question: str, name: str, patch: str, mutant_why: str, runner: TestRunner,
    style: str, complete: Complete, settings: Settings | None, base: Objection,
) -> Objection:
    obj, feedback = base, ""
    for _ in range(MAX_ROUNDS):
        try:
            defense = write_test(issue_text, fd, question, class_name=name, style_example=style, feedback=feedback, complete=complete, settings=settings)
        except llm.LLMError as exc:
            feedback = f"The previous attempt produced no usable answer: {exc}"
            continue
        code = defense.test_code
        obj = obj.model_copy(update={"test_name": name, "test_code": code, "pr_result": None, "mutant_result": None})
        if f"class {name}" not in code:
            feedback = f"The test class must be named exactly `{name}`; it was not found in your code."
            continue
        pr = runner.run_tests("pr", code, name)
        obj = obj.model_copy(update={"pr_result": pr})
        if not pr.green:
            feedback = f"Your test did not pass on the pull request (build_ok={pr.build_ok}, failed={pr.failed}). Output:\n{pr.output_tail}"
            continue
        if not patch:
            break  # sin mutante no se puede validar: la objeción queda sin cerrar
        mutant = runner.run_against_mutant("pr", patch, code, name)
        obj = obj.model_copy(update={"mutant_result": mutant})
        if mutant.red_for_real:
            break
        feedback = (
            "Your test also PASSED against a mutant that breaks the edge case again, so it proves nothing. "
            f"The mutant: {mutant_why or 'breaks the behaviour in the objection'}. Assert that specific behaviour."
        )
    return obj


def cross_examine(
    issue_id: str,
    issue_text: str,
    fd: FileDiff,
    runner: TestRunner,
    *,
    read_source: ReadSource,
    evidence_summary: str = "",
    complete: Complete = llm.complete,
    settings: Settings | None = None,
) -> tuple[Objection, ...]:
    """Interroga un fragmento IN/HIGH. `read_source(path)` devuelve el contenido del fichero en el PR."""
    objections = raise_objections(issue_text, fd, evidence_summary, complete=complete, settings=settings)
    if not objections:
        return ()
    source = _safe_read(read_source, fd.path)
    style = _safe_read(read_source, STYLE_EXAMPLE_PATH)[:STYLE_EXAMPLE_CHARS]
    results = []
    for n, fiscal in enumerate(objections, start=1):
        patch, mutant_why = make_mutant(fd, fiscal.question, source, complete=complete, settings=settings)
        base = Objection(question=fiscal.question, rationale=fiscal.rationale, test_name=test_class_name(issue_id, n), mutant_patch=patch)
        if not patch:
            # Sin mutante no hay forma de validar ningún test: no se gasta Defensor ni dotnet, y queda sin cerrar.
            results.append(base.model_copy(update={"rationale": f"{fiscal.rationale} [{mutant_why}]".strip()}))
            continue
        results.append(_defend(issue_text, fd, fiscal.question, test_class_name(issue_id, n), patch, mutant_why, runner, style, complete, settings, base))
    return tuple(results)
