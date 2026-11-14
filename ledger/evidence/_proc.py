"""Ejecución de procesos externos (git, dotnet) con timeout obligatorio y salida capturada."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT_S = 15 * 60
GIT_TIMEOUT_S = 5 * 60

# dotnet sin telemetría ni banner; la salida localizada (es-ES) no se parsea, solo el .trx.
_DOTNET_ENV = {
    "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
    "DOTNET_NOLOGO": "1",
    "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
    # Mensajes en inglés: legibles para el LLM al reintentar y sin mojibake de la consola de Windows.
    "DOTNET_CLI_UI_LANGUAGE": "en",
    "VSLANG": "1033",
}


@dataclass(frozen=True)
class ProcResult:
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def combined(self) -> str:
        return f"{self.stdout}\n{self.stderr}".strip()


class ProcError(RuntimeError):
    def __init__(self, cmd: list[str], result: ProcResult) -> None:
        super().__init__(f"{' '.join(cmd)} → código {result.returncode}: {result.combined[-2000:]}")
        self.result = result


def run(cmd: list[str], cwd: Path, *, timeout_s: float = DEFAULT_TIMEOUT_S, check: bool = False) -> ProcResult:
    """Ejecuta `cmd`. Un timeout no lanza excepción: devuelve `timed_out=True` para que el llamante decida."""
    started = time.monotonic()
    env = {**os.environ, **_DOTNET_ENV}
    try:
        done = subprocess.run(
            cmd, cwd=cwd, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout_s,
        )
        result = ProcResult(done.returncode, done.stdout, done.stderr, time.monotonic() - started)
    except subprocess.TimeoutExpired as exc:
        result = ProcResult(
            -1, _as_text(exc.stdout), _as_text(exc.stderr) + f"\n[timeout tras {timeout_s:.0f}s]",
            time.monotonic() - started, timed_out=True,
        )
    if check and not result.ok:
        raise ProcError(cmd, result)
    return result


def git(repo: Path, *args: str, check: bool = True) -> ProcResult:
    return run(["git", "-c", "core.longpaths=true", *args], repo, timeout_s=GIT_TIMEOUT_S, check=check)


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
