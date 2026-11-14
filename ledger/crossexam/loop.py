"""Etapa 3 (B): el bucle del interrogatorio. Una objeción solo se cierra con un test que pasa en el PR y
FALLA contra el mutante (`Objection.valid`). Hasta MAX_ROUNDS intentos del Defensor por objeción.

Por objeción:
  1. Se genera el mutante una vez (sin ver el test: así el test no se escribe a medida del parche). Con un
     runner paralelo, la primera respuesta del Defensor se pide a la vez (tampoco ve el mutante).
  2. Ronda: el Defensor escribe el test → runner en el PR → runner contra el mutante.
     Si falla un paso, la siguiente ronda recibe el motivo (salida del build, o la explicación del mutante).
  3. Con un runner paralelo y capacidad de LLM libre, la ronda 1 pide K variantes A LA VEZ (decisión D15): gana la
     válida de índice más bajo; si ninguna lo es, queda UNA ronda con feedback (antes, dos más en serie). Mismo número
     de intentos o más, la mitad de rondas en el camino crítico. Sin capacidad libre (p. ej. 36 objeciones), K = 1.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, NamedTuple

from ledger import llm
from ledger.config import Settings
from ledger.crossexam.concurrency import ordered_map, parallel_enabled
from ledger.crossexam.defensor import DefenseTest, write_test
from ledger.crossexam.fiscal import MAX_OBJECTIONS, raise_objections
from ledger.crossexam.mutant_gen import make_mutant
from ledger.models import Objection, TestRunner, TestRunResult
from ledger.triage.diff import FileDiff
from ledger.triage.scope import Complete

MAX_ROUNDS = 3
VARIANT_ROUNDS = 2  # con varias variantes en la ronda 1: esa ronda + una con feedback
DEFAULT_MAX_VARIANTS = 3

# Rango de cada intento: se queda el mejor de la ronda (a igualdad, el de índice más bajo). Un test rojo en el PR va por
# delante de uno que no prueba nada: es la señal de posible defecto que tiene que ver el humano.
NO_ANSWER, WRONG_CLASS, NOT_GREEN, PROVES_NOTHING, RED_ON_PR, VALID = range(6)
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


def _run_pr_and_maybe_mutant(runner: TestRunner, patch: str, code: str, name: str) -> tuple[TestRunResult, TestRunResult | None]:
    """En secuencia: solo el PR (el mutante se ejecuta después, si el PR sale verde).
    Con un runner paralelo y mutante: los dos A LA VEZ (ejecución especulativa, ~25 s menos por ronda en Modal)."""
    if not (patch and parallel_enabled(runner)):
        return runner.run_tests("pr", code, name), None
    with ThreadPoolExecutor(max_workers=2) as pool:
        pr = pool.submit(runner.run_tests, "pr", code, name)
        mutant = pool.submit(runner.run_against_mutant, "pr", patch, code, name)
        return pr.result(), mutant.result()


def defense_variants(active_objections: int, llm_limit: int) -> int:
    """K variantes por objeción en la ronda 1, solo con capacidad libre: active × (1 mutante + K tests) ≤ tope."""
    ceiling = max(1, int(os.environ.get("LEDGER_DEFENSE_VARIANTS", DEFAULT_MAX_VARIANTS)))
    return max(1, min(ceiling, llm_limit // max(1, active_objections) - 1))


_active_lock = threading.Lock()
_active_objections = 0


def _track_objections(delta: int) -> int:
    """Objeciones en curso en todo el proceso (todos los ficheros): es lo que reparte la capacidad libre."""
    global _active_objections
    with _active_lock:
        _active_objections += delta
        return _active_objections


class Attempt(NamedTuple):
    rank: int
    obj: Objection | None  # None: el Defensor no dio respuesta usable, la objeción queda como estaba
    feedback: str


def _attempt(
    defense: DefenseTest | llm.LLMError, name: str, patch: str, mutant_why: str, runner: TestRunner, base: Objection,
) -> Attempt:
    if isinstance(defense, llm.LLMError):
        return Attempt(NO_ANSWER, None, f"The previous attempt produced no usable answer: {defense}")
    code = defense.test_code
    obj = base.model_copy(update={"test_name": name, "test_code": code, "pr_result": None, "mutant_result": None})
    if f"class {name}" not in code:
        return Attempt(WRONG_CLASS, obj, f"The test class must be named exactly `{name}`; it was not found in your code.")
    pr, speculative_mutant = _run_pr_and_maybe_mutant(runner, patch, code, name)
    obj = obj.model_copy(update={"pr_result": pr})
    if not pr.green:
        # El mutante especulativo (si lo hubo) se descarta: misma semántica que en secuencia.
        feedback = f"Your test did not pass on the pull request (build_ok={pr.build_ok}, failed={pr.failed}). Output:\n{pr.output_tail}"
        return Attempt(RED_ON_PR if pr.red_for_real else NOT_GREEN, obj, feedback)
    mutant = speculative_mutant or runner.run_against_mutant("pr", patch, code, name)
    obj = obj.model_copy(update={"mutant_result": mutant})
    if mutant.red_for_real:
        return Attempt(VALID, obj, "")
    return Attempt(PROVES_NOTHING, obj, (
        "Your test also PASSED against a mutant that breaks the edge case again, so it proves nothing. "
        f"The mutant: {mutant_why or 'breaks the behaviour in the objection'}. Assert that specific behaviour."
    ))


def _best(attempts: Sequence[Attempt]) -> Attempt:
    """El de mayor rango; a igualdad, el de índice más bajo (resultado estable sea cual sea el orden de llegada)."""
    return max(enumerate(attempts), key=lambda pair: (pair[1].rank, -pair[0]))[1]


def _defend(
    issue_text: str, fd: FileDiff, question: str, name: str, patch: str, mutant_why: str, runner: TestRunner,
    style: str, complete: Complete, settings: Settings | None, base: Objection,
    first_round: Sequence[DefenseTest | llm.LLMError] = (),
) -> Objection:
    """`first_round`: respuestas del Defensor ya pedidas a la vez que el mutante (una o varias variantes)."""
    obj, feedback, best_rank = base, "", -1
    rounds = VARIANT_ROUNDS if len(first_round) > 1 else MAX_ROUNDS
    for round_no in range(rounds):
        if round_no == 0 and first_round:
            candidates: Sequence[DefenseTest | llm.LLMError] = first_round
        else:
            try:
                candidates = [write_test(issue_text, fd, question, class_name=name, style_example=style, feedback=feedback, complete=complete, settings=settings)]
            except llm.LLMError as exc:
                candidates = [exc]
        attempts = ordered_map(lambda d: _attempt(d, name, patch, mutant_why, runner, base), candidates, len(candidates))
        best = _best(attempts)
        if best.obj is not None and best.rank >= best_rank:
            # Se informa el mejor intento de TODAS las rondas: una ronda posterior peor no tapa un rojo en el PR.
            obj, best_rank = best.obj, best.rank
        feedback = best.feedback
        if best.rank == VALID:
            break
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
    parallel = parallel_enabled(runner)
    # Con runner paralelo, el fichero reserva su cupo máximo de objeciones ANTES de que conteste el Fiscal: si no, el
    # primero en recibirlas no vería a los demás ficheros y se llevaría variantes que no caben en el tope del LLM.
    reserved = MAX_OBJECTIONS if parallel else 0
    _track_objections(reserved)
    try:
        objections = raise_objections(issue_text, fd, evidence_summary, complete=complete, settings=settings)
    except BaseException:
        _track_objections(-reserved)
        raise
    _track_objections(len(objections) - reserved if parallel else 0)  # la reserva pasa a ser una por objeción real
    if not objections:
        return ()
    source = _safe_read(read_source, fd.path)
    style = _safe_read(read_source, STYLE_EXAMPLE_PATH)[:STYLE_EXAMPLE_CHARS]

    def first_test(question: str, name: str, variant: int, variants: int) -> DefenseTest | llm.LLMError:
        try:
            return write_test(issue_text, fd, question, class_name=name, style_example=style, variant=variant, variants=variants, complete=complete, settings=settings)
        except llm.LLMError as exc:
            return exc

    def examine(numbered: tuple[int, Any]) -> Objection:
        n, fiscal = numbered
        name = test_class_name(issue_id, n)
        first_round: list[DefenseTest | llm.LLMError] = []
        try:
            if parallel:
                # El Defensor nunca ve el mutante: su ronda 1 no depende de él y se pide A LA VEZ, con K variantes si
                # sobra capacidad de LLM. Si al final no hay mutante, esas respuestas se descartan.
                k = defense_variants(_track_objections(0), llm.concurrency_limit("pro", settings))
                with ThreadPoolExecutor(max_workers=k) as pool:
                    futures = [pool.submit(first_test, fiscal.question, name, v, k) for v in range(k)]
                    patch, mutant_why = make_mutant(fd, fiscal.question, source, complete=complete, settings=settings)
                    first_round = [f.result() for f in futures]
            else:
                patch, mutant_why = make_mutant(fd, fiscal.question, source, complete=complete, settings=settings)
            base = Objection(question=fiscal.question, rationale=fiscal.rationale, test_name=name, mutant_patch=patch)
            if not patch:
                # Sin mutante no hay forma de validar ningún test: no se ejecuta dotnet y queda sin cerrar.
                return base.model_copy(update={"rationale": f"{fiscal.rationale} [{mutant_why}]".strip()})
            return _defend(issue_text, fd, fiscal.question, name, patch, mutant_why, runner, style, complete, settings, base, first_round)
        finally:
            if parallel:
                _track_objections(-1)

    # Las objeciones son independientes: con Modal van a la vez; las rondas de cada una siguen en secuencia.
    numbered = list(enumerate(objections, start=1))
    workers = len(objections) if parallel else 1
    return tuple(ordered_map(examine, numbered, workers))
