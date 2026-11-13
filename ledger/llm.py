"""Acceso único a los LLM, enrutado por rol. CONJUNTO.

Roles (qué modelo hace qué; es parte del concepto, ver docs/decision-log.md D7):
- "pro"    → Gemini pro: test independiente del cambio, Defensor y mutantes.
- "flash"  → Gemini flash: triaje de alcance por fichero (masivo en el PR de 237 ficheros).
- "fiscal" → NVIDIA Nemotron 3.5 Super VL: el Fiscal. Que sea otra familia de modelos evita que
             acusación y defensa compartan los mismos puntos ciegos.

`complete()` devuelve texto o, con `schema`, una instancia validada. temperature=0, caché en disco
por hash del prompt, reintentos con backoff ante 429/5xx y una reparación si el JSON no valida.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar, overload

from pydantic import BaseModel, ValidationError

from ledger.config import Settings, load_settings
from ledger.llm_backends import (
    LLMError,
    gemini_client,
    gemini_generate,
    nvidia_client,
    nvidia_generate,
)

__all__ = ["LLMError", "Role", "complete"]

Role = Literal["pro", "flash", "fiscal"]
T = TypeVar("T", bound=BaseModel)
Generate = Callable[[Any, str, str, str, "type[BaseModel] | None"], str]

RETRYABLE_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 5
BACKOFF_BASE_S = 2.0


def _route(role: Role, settings: Settings) -> tuple[str, Callable[[Settings], Any], Generate]:
    if role == "fiscal":
        return settings.nvidia_model, nvidia_client, nvidia_generate
    model = settings.model_pro if role == "pro" else settings.model_flash
    return model, gemini_client, gemini_generate


def _cache_key(model: str, system: str, user: str, schema_name: str) -> str:
    payload = json.dumps([model, system, user, schema_name], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _status_code(exc: Exception) -> int | None:
    for attr in ("code", "status_code"):  # google-genai usa .code; openai usa .status_code
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def _with_retry(generate: Generate, client: Any, model: str, system: str, user: str, schema: type[BaseModel] | None) -> str:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return generate(client, model, system, user, schema)
        except LLMError:
            raise
        except Exception as exc:
            code = _status_code(exc)
            if code not in RETRYABLE_CODES or attempt == MAX_ATTEMPTS:
                raise LLMError(f"{model} falló ({code}): {exc}") from exc
            time.sleep(BACKOFF_BASE_S**attempt)
    raise LLMError("inalcanzable")


def _parse_or_repair(text: str, schema: type[T], regenerate: Callable[[str], str]) -> tuple[T, str]:
    """Valida el JSON; si falla, pide UNA corrección pasando el error al modelo."""
    try:
        return schema.model_validate_json(text), text
    except ValidationError as first_error:
        repaired = regenerate(f"Your previous answer was invalid JSON for the schema: {first_error}. Previous answer:\n{text}")
        try:
            return schema.model_validate_json(repaired), repaired
        except ValidationError as exc:
            raise LLMError(f"JSON inválido tras reparar: {exc}") from exc


@overload
def complete(system: str, user: str, schema: None = None, role: Role = "pro", *, client: Any = None, settings: Settings | None = None, use_cache: bool = True) -> str: ...
@overload
def complete(system: str, user: str, schema: type[T], role: Role = "pro", *, client: Any = None, settings: Settings | None = None, use_cache: bool = True) -> T: ...


def complete(
    system: str,
    user: str,
    schema: type[BaseModel] | None = None,
    role: Role = "pro",
    *,
    client: Any = None,
    settings: Settings | None = None,
    use_cache: bool = True,
) -> Any:
    settings = settings or load_settings()
    model, make_client, generate = _route(role, settings)
    schema_name = schema.__name__ if schema else ""
    cache_file: Path = settings.cache_dir / "llm" / f"{_cache_key(model, system, user, schema_name)}.txt"

    if use_cache and cache_file.exists():
        text = cache_file.read_text(encoding="utf-8")
        return schema.model_validate_json(text) if schema else text

    active_client = client or make_client(settings)
    text = _with_retry(generate, active_client, model, system, user, schema)
    result: Any = text
    if schema:
        result, text = _parse_or_repair(
            text, schema, lambda fix: _with_retry(generate, active_client, model, system, f"{user}\n\n{fix}", schema)
        )

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(text, encoding="utf-8")
    return result
