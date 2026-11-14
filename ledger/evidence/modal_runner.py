"""`ModalTestRunner`: el mismo Protocol `TestRunner` que `DotnetTestRunner`, pero cada ejecución va
en un Modal Sandbox desechable y SIN RED (decision-log D8): los tests y mutantes escritos por IA son
código no fiable. Se activa con `LEDGER_RUNNER=modal`.

La imagen trae el repo del reto con los worktrees base y PR de cada issue ya compilados, así que en el
sandbox solo hay build incremental y `dotnet test --no-restore`. Como cada sandbox se descarta al
terminar, un mutante se aplica directamente sobre su worktree: no hace falta copia temporal.
API comprobada contra modal 1.6.4: `Sandbox.create`, `sandbox.exec`, `sandbox.filesystem.write_text/read_text`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ledger.config import ISSUES, Settings
from ledger.evidence.dotnet import LEDGER_TEST_DIR, SAFE_TEST_NAME, TEST_PROJECT, TRX_NAME, normalize_patch
from ledger.evidence.trx import build_result
from ledger.models import Side, TestRunResult

APP_NAME = "tieto-ledger"
REPO_URL = "https://github.com/te-industry-tech-office/junction26-messagepack-csharp.git"
SDK_IMAGE = "mcr.microsoft.com/dotnet/sdk:8.0"
REMOTE_ROOT = "/w"
REMOTE_RESULTS = "/tmp/ledger-results"
SANDBOX_TIMEOUT_S = 30 * 60
EXEC_TIMEOUT_S = 15 * 60
_ENV = {
    "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
    "DOTNET_NOLOGO": "1",
    "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
    "DOTNET_CLI_UI_LANGUAGE": "en",
    # Microsoft.CodeAnalysis.Testing descarga ReferenceAssemblies a <temp>/test-packages en tiempo de
    # ejecución. Temp fijo para precalentarlo en la imagen (con red) y reutilizarlo en el sandbox (sin red).
    "TMPDIR": "/opt/ledger-tmp",
}
# Un test existente del repo que resuelve ReferenceAssemblies.Net.Net80: al ejecutarlo en la imagen deja la caché.
WARMUP_FILTER = "FullyQualifiedName~GenericsFormatterTests.NullableFormatter"

SandboxFactory = Callable[..., Any]


def worktree_dir(issue_id: str, side: Side) -> str:
    return f"{REMOTE_ROOT}/{issue_id}/{side}"


def build_image(settings: Settings) -> Any:
    """Imagen con el SDK 8, el repo y los worktrees base/PR de cada issue ya restaurados y compilados."""
    import modal

    prepare = [
        f"mkdir -p {_ENV['TMPDIR']}",
        f"git clone -q -c core.longpaths=true {REPO_URL} /repo",
        "cd /repo && git fetch -q origin '+refs/heads/ju26-*:refs/remotes/origin/ju26-*'",
    ]
    for issue_id in sorted(ISSUES):
        for side in ("base", "pr"):
            wt = worktree_dir(issue_id, side)
            prepare += [
                f"git -C /repo worktree add -q --detach {wt} {settings.ref(issue_id, side)}",
                f"cd {wt} && dotnet build {TEST_PROJECT.as_posix()} -nologo -v q",
            ]
    warm_wt = worktree_dir(sorted(ISSUES)[0], "pr")
    prepare.append(f"cd {warm_wt} && dotnet test {TEST_PROJECT.as_posix()} --no-build --filter {WARMUP_FILTER}")
    return (
        modal.Image.from_registry(SDK_IMAGE, add_python="3.12")
        .apt_install("git")
        .env(_ENV)
        .run_commands(*prepare)
    )


def _default_factory(settings: Settings) -> SandboxFactory:
    def create(**kwargs: Any) -> Any:
        import modal

        app = modal.App.lookup(APP_NAME, create_if_missing=True)
        return modal.Sandbox.create(app=app, image=build_image(settings), timeout=SANDBOX_TIMEOUT_S, **kwargs)

    return create


@dataclass(frozen=True)
class ModalTestRunner:
    settings: Settings
    issue_id: str
    sandbox_factory: SandboxFactory | None = field(default=None, compare=False)

    def run_tests(self, side: Side, test_code: str, test_name: str) -> TestRunResult:
        return self._run(side, test_code, test_name, mutant_patch=None)

    def run_against_mutant(self, side: Side, mutant_patch: str, test_code: str, test_name: str) -> TestRunResult:
        return self._run(side, test_code, test_name, mutant_patch=mutant_patch)

    def _run(self, side: Side, test_code: str, test_name: str, mutant_patch: str | None) -> TestRunResult:
        if not SAFE_TEST_NAME.match(test_name):
            return _failed(f"test_name inválido {test_name!r}: debe ser un identificador C#")
        factory = self.sandbox_factory or _default_factory(self.settings)
        started = time.monotonic()
        sandbox = None
        try:
            sandbox = factory(block_network=True, cpu=4.0)
            return _run_in_sandbox(sandbox, worktree_dir(self.issue_id, side), test_code, test_name, mutant_patch, started)
        except Exception as exc:  # noqa: BLE001 - un fallo de infraestructura es "no hay evidencia", nunca un verde
            return _failed(f"Modal falló: {type(exc).__name__}: {exc}", time.monotonic() - started)
        finally:
            if sandbox is not None:
                sandbox.terminate()


def _run_in_sandbox(sandbox: Any, wt: str, test_code: str, test_name: str, mutant_patch: str | None, started: float) -> TestRunResult:
    ledger_dir = f"{wt}/{LEDGER_TEST_DIR.as_posix()}"
    _sh(sandbox, f"rm -rf {ledger_dir} {REMOTE_RESULTS} && mkdir -p {ledger_dir}")
    sandbox.filesystem.write_text(test_code, f"{ledger_dir}/{test_name}.cs")

    if mutant_patch is not None:
        patch_path = f"{wt}/.ledger-mutant/mutant.patch"
        _sh(sandbox, f"mkdir -p {wt}/.ledger-mutant")
        sandbox.filesystem.write_text(normalize_patch(mutant_patch), patch_path)
        apply = "git apply --recount --whitespace=nowarn"
        # Agrupado: sin llaves, `cd X && A || cd X && B` ejecutaría B siempre (y fallaría: ya aplicado).
        code, out = _sh(sandbox, f"cd {wt} && {{ {apply} {patch_path} || {apply} --ignore-whitespace {patch_path}; }}")
        if code != 0:
            return _failed(f"git apply del mutante falló: {out[-1500:]}", time.monotonic() - started)

    _, output = _sh(
        sandbox,
        f"cd {wt} && dotnet test {TEST_PROJECT.as_posix()} --no-restore "
        f"--filter FullyQualifiedName~{test_name} "
        f"--logger 'trx;LogFileName={TRX_NAME}' --results-directory {REMOTE_RESULTS}",
    )
    try:
        trx_text: str | None = sandbox.filesystem.read_text(f"{REMOTE_RESULTS}/{TRX_NAME}")
    except Exception:  # noqa: BLE001 - sin .trx = la build falló (misma regla que en local)
        trx_text = None
    return build_result(trx_text, output.replace(f"{wt}/", ""), time.monotonic() - started)


def _sh(sandbox: Any, script: str) -> tuple[int, str]:
    proc = sandbox.exec("bash", "-lc", script, timeout=EXEC_TIMEOUT_S)
    code = proc.wait()
    return code, f"{proc.stdout.read()}\n{proc.stderr.read()}".strip()


def _failed(reason: str, duration_s: float = 0.0) -> TestRunResult:
    return TestRunResult(build_ok=False, passed=0, failed=0, output_tail=reason, duration_s=duration_s)
