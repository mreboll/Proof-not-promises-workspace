"""Worktrees del repo del reto: uno persistente por (issue, lado) y desechables para mutantes.

Cada lado vive en su propio directorio (y por tanto en su propio `bin/`/`obj/`), así base y PR
se compilan y ejecutan en procesos separados (decision-log D3).
"""

from __future__ import annotations

import threading

import os
import shutil
import stat
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ledger.config import Settings
from ledger.evidence._proc import git
from ledger.models import Side


def worktree_path(settings: Settings, issue_id: str, side: Side) -> Path:
    return settings.work_dir / issue_id / side


_WORKTREE_LOCK = threading.Lock()


def resolve_commit(settings: Settings, issue_id: str, side: Side) -> str:
    ref = settings.ref(issue_id, side)
    return git(settings.msgpack_repo, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()


def ensure_worktree(settings: Settings, issue_id: str, side: Side) -> Path:
    """Crea o reutiliza `.work/<issue>/<side>` en el commit del lado pedido.

    Si ya existe, conserva `bin/` y `obj/` (builds incrementales) pero devuelve los ficheros
    versionados a su estado original. Los ficheros sin versionar (p. ej. tests generados) los
    gestiona quien los escribe.
    """
    commit = resolve_commit(settings, issue_id, side)
    path = worktree_path(settings, issue_id, side)
    # Un solo hilo a la vez prepara worktrees: dos `checkout --force` del mismo worktree chocan en index.lock
    # (pasó en real con las Etapas 1 y 2 en paralelo, lessons-log H8). Solo cubre los comandos de git, no el build.
    with _WORKTREE_LOCK:
        return _prepare(settings, path, commit)


def _prepare(settings: Settings, path: Path, commit: str) -> Path:
    if _is_worktree(path):
        git(path, "checkout", "-q", "--detach", "--force", commit)
        git(path, "reset", "-q", "--hard", commit)
        return path

    _remove_tree(path)
    git(settings.msgpack_repo, "worktree", "prune")
    path.parent.mkdir(parents=True, exist_ok=True)
    git(settings.msgpack_repo, "worktree", "add", "-q", "--detach", str(path), commit)
    return path


@contextmanager
def disposable_worktree(settings: Settings, issue_id: str, side: Side) -> Iterator[Path]:
    """Worktree temporal (para aplicar un mutante); se borra al salir, incluso si hay excepción."""
    commit = resolve_commit(settings, issue_id, side)
    path = settings.work_dir / issue_id / f"tmp-{side}-{uuid.uuid4().hex[:8]}"
    path.parent.mkdir(parents=True, exist_ok=True)
    git(settings.msgpack_repo, "worktree", "add", "-q", "--detach", str(path), commit)
    try:
        yield path
    finally:
        git(settings.msgpack_repo, "worktree", "remove", "--force", str(path), check=False)
        _remove_tree(path)
        git(settings.msgpack_repo, "worktree", "prune", check=False)


def _is_worktree(path: Path) -> bool:
    return (path / ".git").is_file() and git(path, "rev-parse", "--git-dir", check=False).ok


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_make_writable_and_retry)
    else:  # pragma: no cover
        shutil.rmtree(path, onerror=_make_writable_and_retry)


def _make_writable_and_retry(func, target, _exc) -> None:  # type: ignore[no-untyped-def]
    # En Windows git deja ficheros de solo lectura en .git/objects; rmtree necesita quitar ese bit.
    os.chmod(target, stat.S_IWRITE)
    func(target)
