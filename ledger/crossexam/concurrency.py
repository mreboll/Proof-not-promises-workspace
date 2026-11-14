"""Paralelismo de la Etapa 3: solo con runners que lo declaran seguros (Modal: un sandbox por ejecución).

El runner local NO lo es: dos ejecuciones sobre el mismo worktree se pisan `Ledger/`, así que en local la
Etapa 3 sigue en secuencia. Los resultados se devuelven siempre en el orden de entrada: el informe no
depende de qué tarea terminó antes.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

T = TypeVar("T")
R = TypeVar("R")

DEFAULT_FILE_WORKERS = 12


def parallel_enabled(runner: Any) -> bool:
    return bool(getattr(runner, "parallel_safe", False))


def file_workers() -> int:
    """Ficheros interrogados a la vez (LEDGER_CROSSEXAM_WORKERS). Los topes reales los ponen los semáforos de LLM y Modal."""
    return max(1, int(os.environ.get("LEDGER_CROSSEXAM_WORKERS", DEFAULT_FILE_WORKERS)))


def ordered_map(fn: Callable[[T], R], items: Iterable[T], workers: int) -> list[R]:
    items = list(items)
    if workers <= 1 or len(items) <= 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        return list(pool.map(fn, items))  # map conserva el orden de entrada
