"""Etapa 1 (B): lee el diff base → PR del repo del reto y lo convierte en `FileDiff` inmutables.

- `parse_diff(text)` es pura: la usan los tests y `rules.py` (diffs de fixture).
- `load_diff(settings, issue_id)` lanza `git diff <base> <pr>` en `settings.msgpack_repo`.

`FileDiff` vive aquí y no en `models.py`: es un detalle interno de la Etapa 1 y no cruza la frontera A ↔ B.
"""

from __future__ import annotations

import subprocess
from typing import Literal

from pydantic import BaseModel, ConfigDict
from unidiff import PatchSet

from ledger.config import Settings

Status = Literal["added", "removed", "modified", "renamed"]

GIT_TIMEOUT_S = 120
_BOM = "﻿"


class DiffError(ValueError):
    """Error al obtener el diff. Hereda de ValueError para que la CLI lo muestre limpio."""


class Hunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    header: str  # "@@ -236,3 +236,3 @@ public class TypeCollector"
    text: str  # el hunk completo, tal cual (para el prompt de alcance y el informe)


class FileDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str  # ruta en el PR (o en la base si el fichero se borra)
    old_path: str | None = None  # solo en renombrados
    status: Status
    binary: bool = False
    hunks: tuple[Hunk, ...] = ()
    added: tuple[str, ...] = ()  # líneas añadidas, sin '+', sin fin de línea ni BOM
    removed: tuple[str, ...] = ()  # líneas quitadas, ídem


def _clean(value: str) -> str:
    return value.rstrip("\r\n").replace(_BOM, "")


def _strip_prefix(path: str) -> str:
    return path[2:] if path.startswith(("a/", "b/")) else path


def _status(pf) -> Status:
    if pf.is_added_file:
        return "added"
    if pf.is_removed_file:
        return "removed"
    if pf.is_rename:
        return "renamed"
    return "modified"


def parse_diff(text: str) -> tuple[FileDiff, ...]:
    """Convierte un diff unificado de git en `FileDiff`, en el mismo orden que el diff."""
    if not text.strip():
        return ()
    result: list[FileDiff] = []
    for pf in PatchSet(text):
        status = _status(pf)
        path = _strip_prefix(pf.source_file if status == "removed" else pf.target_file)
        hunks = tuple(Hunk(header=str(h).splitlines()[0], text=str(h)) for h in pf)
        lines = [line for h in pf for line in h]
        result.append(
            FileDiff(
                path=path,
                old_path=_strip_prefix(pf.source_file) if status == "renamed" else None,
                status=status,
                binary=bool(getattr(pf, "is_binary_file", False)) or (not hunks and "Binary files" in str(pf.patch_info)),
                hunks=hunks,
                added=tuple(_clean(line.value) for line in lines if line.is_added),
                removed=tuple(_clean(line.value) for line in lines if line.is_removed),
            )
        )
    return tuple(result)


def load_diff(settings: Settings, issue_id: str) -> tuple[FileDiff, ...]:
    """`git diff <base> <pr>` del issue, con detección de renombrados."""
    repo = settings.msgpack_repo
    if not (repo / ".git").exists():
        raise DiffError(f"No encuentro el repo del reto en {repo}. Clónalo o ajusta MSGPACK_REPO en .env.")
    base, pr = settings.ref(issue_id, "base"), settings.ref(issue_id, "pr")
    cmd = ["git", "-C", str(repo), "-c", "core.quotepath=false", "diff", "--no-color", "--no-ext-diff", "-M", base, pr]
    try:
        proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_S, check=False)
    except subprocess.TimeoutExpired as exc:
        raise DiffError(f"git diff {base} {pr} superó {GIT_TIMEOUT_S}s") from exc
    if proc.returncode != 0:
        raise DiffError(f"git diff {base} {pr} falló: {proc.stderr.strip()}")
    return parse_diff(proc.stdout)
