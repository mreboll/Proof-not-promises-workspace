"""`DotnetTestRunner`: implementación local del Protocol `TestRunner` (ver `ledger/models.py`).

Cada test generado se escribe en `tests/MessagePack.SourceGenerator.Tests/Ledger/<test_name>.cs`
dentro del worktree del lado pedido y se ejecuta con `dotnet test --filter ... --logger trx`.

Limitación conocida: dos ejecuciones simultáneas sobre el MISMO worktree se pisan `Ledger/`. El pipeline
llama en secuencia; para paralelo está `ModalTestRunner` (un sandbox por ejecución).
Aquí el código escrito por IA (tests y mutantes) se ejecuta en esta máquina sin aislamiento: por eso los
mutantes se limitan a `src/**/*.cs` y, para código no fiable, el runner recomendado es Modal (D8).
"""

from __future__ import annotations

import re
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from ledger.config import Settings
from ledger.evidence._proc import DEFAULT_TIMEOUT_S, ProcResult, git, run
from ledger.evidence.trx import build_result
from ledger.evidence.workspace import disposable_worktree, ensure_worktree
from ledger.models import Side, TestRunResult

TEST_PROJECT = Path("tests/MessagePack.SourceGenerator.Tests")
LEDGER_TEST_DIR = TEST_PROJECT / "Ledger"
RESULTS_DIR = Path(".ledger-results")
TRX_NAME = "ledger.trx"
# test_name acaba en un nombre de fichero y en un filtro de dotnet: solo un identificador C#, y con el
# prefijo `Ledger` (ningún test del repo lo contiene), para que el filtro nunca ejecute tests existentes.
SAFE_TEST_NAME = re.compile(r"^Ledger[A-Za-z0-9_]{0,120}$")
# Un mutante solo puede romper código C# del producto: ni tests, ni ficheros de build, ni ficheros nuevos.
_MUTANT_ALLOWED = re.compile(r"^src/[^\s]+\.cs$")
_PATCH_PATH = re.compile(r"^(?:--- |\+\+\+ )(\S+)", re.MULTILINE)


def exact_test_filter(test_name: str) -> str:
    """Filtro exacto: con punto final solo coincide la clase `test_name`, no cualquier nombre que la contenga."""
    return f"FullyQualifiedName~{test_name}."


def mutant_patch_problem(patch: str) -> str | None:
    """None si el parche solo modifica `src/**/*.cs` existentes; si no, el motivo para rechazarlo."""
    paths = _PATCH_PATH.findall(normalize_patch(patch))
    if not paths:
        return "mutant patch has no file headers (--- a/... / +++ b/...)"
    for raw in paths:
        path = raw.removeprefix("a/").removeprefix("b/")
        if raw == "/dev/null" or not _MUTANT_ALLOWED.match(path):
            return f"mutant patch may only modify existing src/**/*.cs files, not {raw!r}"
    return None


def run_in_worktree(worktree: Path, test_code: str, test_name: str, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> TestRunResult:
    if not SAFE_TEST_NAME.match(test_name):
        return _refused(f"test_name inválido {test_name!r}: debe ser un identificador C# que empiece por 'Ledger'")

    _write_test(worktree, test_code, test_name)
    results = worktree / RESULTS_DIR / uuid.uuid4().hex[:8]
    cmd = [
        "dotnet", "test", str(TEST_PROJECT),
        "--filter", exact_test_filter(test_name),
        "--logger", f"trx;LogFileName={TRX_NAME}",
        "--results-directory", str(results),
    ]
    proc = run(cmd, worktree, timeout_s=timeout_s)
    if proc.timed_out:
        shutil.rmtree(results, ignore_errors=True)
        return TestRunResult(build_ok=False, passed=0, failed=0, output_tail=f"timeout tras {timeout_s:.0f}s", duration_s=proc.duration_s)

    trx_file = results / TRX_NAME
    trx_text = _relativize(trx_file.read_text(encoding="utf-8-sig"), worktree) if trx_file.exists() else None
    shutil.rmtree(results, ignore_errors=True)
    return build_result(trx_text, _relativize(proc.combined, worktree), proc.duration_s)


@dataclass(frozen=True)
class DotnetTestRunner:
    settings: Settings
    issue_id: str
    timeout_s: float = DEFAULT_TIMEOUT_S

    def run_tests(self, side: Side, test_code: str, test_name: str) -> TestRunResult:
        worktree = ensure_worktree(self.settings, self.issue_id, side)
        return run_in_worktree(worktree, test_code, test_name, timeout_s=self.timeout_s)

    def run_against_mutant(self, side: Side, mutant_patch: str, test_code: str, test_name: str) -> TestRunResult:
        problem = mutant_patch_problem(mutant_patch)
        if problem:
            return _refused(problem)
        started = time.monotonic()
        with disposable_worktree(self.settings, self.issue_id, side) as worktree:
            patch_file = worktree / RESULTS_DIR / "mutant.patch"
            patch_file.parent.mkdir(parents=True, exist_ok=True)
            patch_file.write_text(normalize_patch(mutant_patch), encoding="utf-8", newline="\n")
            applied = _apply_patch(worktree, patch_file)
            if not applied.ok:
                return _refused(f"git apply del mutante falló: {applied.combined[-1500:]}", time.monotonic() - started)
            return run_in_worktree(worktree, test_code, test_name, timeout_s=self.timeout_s)


def _write_test(worktree: Path, test_code: str, test_name: str) -> None:
    ledger_dir = worktree / LEDGER_TEST_DIR
    if ledger_dir.exists():
        shutil.rmtree(ledger_dir)  # un test roto de una ejecución anterior rompería esta build
    ledger_dir.mkdir(parents=True)
    (ledger_dir / f"{test_name}.cs").write_text(test_code, encoding="utf-8")


def _relativize(output: str, worktree: Path) -> str:
    """Quita la ruta absoluta del worktree: errores más cortos y sin rutas locales en el informe."""
    root = str(worktree.resolve())
    return output.replace(root + "\\", "").replace(root + "/", "").replace(root, ".")


def _refused(reason: str, duration_s: float = 0.0) -> TestRunResult:
    return TestRunResult(build_ok=False, passed=0, failed=0, output_tail=reason, duration_s=duration_s)


def normalize_patch(patch: str) -> str:
    """LF como los blobs de git (git apply convierte al final de línea del checkout) y salto final."""
    text = patch.replace("\r\n", "\n")
    return text if text.endswith("\n") else text + "\n"


def _apply_patch(worktree: Path, patch_file: Path) -> ProcResult:
    """Primero estricto; si falla, tolerando espacios en el contexto (parches escritos por el LLM)."""
    base_args = ("apply", "--recount", "--whitespace=nowarn")
    strict = git(worktree, *base_args, str(patch_file), check=False)
    if strict.ok:
        return strict
    return git(worktree, *base_args, "--ignore-whitespace", str(patch_file), check=False)
