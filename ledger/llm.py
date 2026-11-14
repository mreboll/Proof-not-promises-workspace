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
import os
import queue
import statistics
import threading
import time
from collections import deque
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
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
    if settings.nvidia_for_all:
        # Modo temporal sin Gemini (LEDGER_NVIDIA_FOR_ALL=1). Rompe D7: Fiscal y Defensor comparten familia.
        model = settings.nvidia_model if role == "pro" else settings.nvidia_model_fast
        return model, nvidia_client, nvidia_generate
    model = settings.model_pro if role == "pro" else settings.model_flash
    return model, gemini_client, gemini_generate


def model_for(role: Role, settings: Settings | None = None) -> str:
    """Modelo que atenderá un rol con la configuración actual (para logs, CLI e informe)."""
    return _route(role, settings or load_settings())[0]


def _cache_key(model: str, system: str, user: str, schema_name: str) -> str:
    payload = json.dumps([model, system, user, schema_name], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Peticiones simultáneas por proveedor (la Etapa 3 en paralelo lanza decenas de tareas). Configurable:
# LEDGER_MAX_CONCURRENT_GEMINI / LEDGER_MAX_CONCURRENT_NVIDIA. Subir el de Gemini solo si no aparecen 429.
# Medido con ledger.evidence.capacity (docs/numeros-evidencia.md): Gemini pro escala sin 429 hasta 48 y se hunde en 64;
# 32 deja margen porque los prompts reales pesan mucho más que un ping. Nemotron escala de sobra hasta 32.
DEFAULT_CONCURRENCY = {"gemini": 32, "nvidia": 16}
_limits: dict[str, threading.BoundedSemaphore] = {}
_limits_lock = threading.Lock()


def _semaphore(provider: str) -> threading.BoundedSemaphore:
    with _limits_lock:
        if provider not in _limits:
            size = int(os.environ.get(f"LEDGER_MAX_CONCURRENT_{provider.upper()}", DEFAULT_CONCURRENCY[provider]))
            _limits[provider] = threading.BoundedSemaphore(max(1, size))
        return _limits[provider]


@contextmanager
def _limit(provider: str | None) -> Iterator[None]:
    if provider is None:
        yield
        return
    with _semaphore(provider):
        yield


def concurrency_limit(role: Role, settings: Settings | None = None) -> int:
    """Tope de peticiones simultáneas del proveedor que atiende `role` (para repartir capacidad libre)."""
    provider = _provider(_route(role, settings or load_settings())[1])
    return int(os.environ.get(f"LEDGER_MAX_CONCURRENT_{provider.upper()}", DEFAULT_CONCURRENCY[provider]))


def _reset_limits() -> None:
    """Para tests: vuelve a leer los topes del entorno."""
    with _limits_lock:
        _limits.clear()


# Medidas por proveedor para encontrar el límite de concurrencia (ledger.evidence.capacity / measure):
# peticiones reales, errores reintentables por código, pico en vuelo, tiempo esperando hueco y latencia máxima.
_stats_lock = threading.Lock()
_stats: dict[str, dict[str, Any]] = {}
_cache_hits = 0
_in_flight: dict[str, int] = {}
_latencies: dict[str, deque[float]] = {}  # por modelo
_slot_hook = threading.local()


def _provider_stats(provider: str) -> dict[str, Any]:
    if provider not in _stats:
        _stats[provider] = {
            "requests": 0, "ok": 0, "errors": {}, "timeouts": 0, "peak": 0, "wait_s": 0.0, "max_latency_s": 0.0,
            "hedges": 0, "hedge_wins": 0,
        }
    return _stats[provider]


def _record(provider: str, **changes: Any) -> None:
    with _stats_lock:
        stats = _provider_stats(provider)
        for key, value in changes.items():
            if key == "error":
                stats["errors"][value] = stats["errors"].get(value, 0) + 1
            elif key == "max_latency_s":
                stats[key] = max(stats[key], value)
            else:
                stats[key] += value


@contextmanager
def _measured_slot(provider: str | None, model: str = "") -> Iterator[None]:
    """Ocupa el hueco del proveedor y anota espera, pico y latencia de la petición (latencia por modelo)."""
    if provider is None:
        yield
        return
    waited = time.monotonic()
    with _limit(provider):
        started = time.monotonic()
        slot_taken = getattr(_slot_hook, "event", None)
        if slot_taken is not None:
            slot_taken.set()  # el reloj del respaldo empieza ahora, no mientras se espera hueco
        with _stats_lock:
            stats = _provider_stats(provider)
            stats["requests"] += 1
            stats["wait_s"] += started - waited
            _in_flight[provider] = _in_flight.get(provider, 0) + 1
            stats["peak"] = max(stats["peak"], _in_flight[provider])
        try:
            yield
        finally:
            latency = time.monotonic() - started
            with _stats_lock:
                _in_flight[provider] -= 1
                _latencies.setdefault(model or provider, deque(maxlen=LATENCY_SAMPLES)).append(latency)
            _record(provider, max_latency_s=latency)


def llm_stats() -> dict[str, Any]:
    """Copia de las medidas; incluye el tope configurado de cada proveedor."""
    with _stats_lock:
        out: dict[str, Any] = {}
        for provider in DEFAULT_CONCURRENCY:
            stats = dict(_provider_stats(provider))
            stats["errors"] = dict(stats["errors"])
            stats["wait_s"] = round(stats["wait_s"], 2)
            stats["max_latency_s"] = round(stats["max_latency_s"], 2)
            stats["limit"] = int(os.environ.get(f"LEDGER_MAX_CONCURRENT_{provider.upper()}", DEFAULT_CONCURRENCY[provider]))
            out[provider] = stats
        out["cache_hits"] = _cache_hits
        return out


def reset_llm_stats() -> None:
    global _cache_hits
    with _stats_lock:
        _stats.clear()
        _in_flight.clear()
        _latencies.clear()
        _cache_hits = 0


# Peticiones de respaldo (hedging, decisión D16). En las ejecuciones reales, el tiempo total lo marcaba UNA llamada
# rezagada (hasta 300 s o un 504 y su reintento) cuando todo lo demás ya había terminado. Si una llamada tarda más del
# doble de la mediana de SU MODELO y queda hueco libre en el cupo, se lanza otra igual y gana la primera respuesta válida. Solo cuesta tokens en
# los rezagados. DESACTIVADO por defecto: en 4 mediciones reales no se pudo separar su efecto del ruido de latencia
# de Gemini (docs/numeros-evidencia.md). LEDGER_HEDGE=1 lo activa; LEDGER_HEDGE_AFTER_S fija el umbral.
HEDGE_DEFAULT_S = 150.0  # sin muestras suficientes todavía
HEDGE_MIN_S = 45.0
HEDGE_MAX_S = 240.0
HEDGE_FACTOR = 2.0
HEDGE_MIN_SAMPLES = 5
LATENCY_SAMPLES = 200


def hedge_delay(samples: Sequence[float]) -> float | None:
    """Segundos a esperar antes de lanzar la petición de respaldo; None si el hedging está desactivado."""
    if os.environ.get("LEDGER_HEDGE", "0") != "1":
        return None
    fixed = os.environ.get("LEDGER_HEDGE_AFTER_S")
    if fixed:
        return float(fixed)
    if len(samples) < HEDGE_MIN_SAMPLES:
        return HEDGE_DEFAULT_S
    return min(HEDGE_MAX_S, max(HEDGE_MIN_S, HEDGE_FACTOR * statistics.median(samples)))


SPARE_POLL_S = 5.0


def hedge_delay_for(model: str) -> float | None:
    with _stats_lock:
        samples = list(_latencies.get(model, ()))
    return hedge_delay(samples)


def _spare_capacity(provider: str) -> bool:
    limit = int(os.environ.get(f"LEDGER_MAX_CONCURRENT_{provider.upper()}", DEFAULT_CONCURRENCY[provider]))
    with _stats_lock:
        return _in_flight.get(provider, 0) < limit


def _hedged(provider: str | None, model: str, call: Callable[[], str]) -> str:
    """Lanza `call`; si tarda más que `hedge_delay_for(model)` desde que OCUPA su hueco y hay hueco libre, lanza un
    respaldo y devuelve la primera respuesta válida. Con el cupo lleno no hay respaldo: solo retrasaría a las demás."""
    delay = hedge_delay_for(model) if provider else None
    if delay is None:
        return call()

    results: queue.Queue[tuple[str, bool, Any]] = queue.Queue()

    def run(tag: str, slot_taken: threading.Event) -> None:
        _slot_hook.event = slot_taken
        try:
            results.put((tag, True, call()))
        except BaseException as exc:  # noqa: BLE001 - se devuelve al hilo que espera, que decide
            results.put((tag, False, exc))

    def settle(ok: bool, value: Any) -> str:
        if ok:
            return value
        raise value

    # Hilos daemon: la llamada que pierde sigue hasta su propio timeout, pero nadie la espera.
    slot_taken = threading.Event()
    threading.Thread(target=run, args=("original", slot_taken), daemon=True).start()
    while not slot_taken.is_set():  # mientras espera hueco, el reloj del respaldo no corre
        try:
            _, ok, value = results.get(timeout=1.0)
            return settle(ok, value)
        except queue.Empty:
            continue
    deadline = time.monotonic() + delay
    while True:
        try:
            _, ok, value = results.get(timeout=max(0.0, deadline - time.monotonic()))
            return settle(ok, value)
        except queue.Empty:
            if _spare_capacity(provider):  # type: ignore[arg-type]
                break
            deadline = time.monotonic() + SPARE_POLL_S

    _record(provider, hedges=1)  # type: ignore[arg-type]
    threading.Thread(target=run, args=("hedge", threading.Event()), daemon=True).start()
    first_error: BaseException | None = None
    for _ in range(2):
        tag, ok, value = results.get()
        if ok:
            if tag == "hedge":
                _record(provider, hedge_wins=1)  # type: ignore[arg-type]
            return value
        first_error = first_error or value
    raise first_error  # type: ignore[misc]


def _count_cache_hit() -> None:
    global _cache_hits
    with _stats_lock:
        _cache_hits += 1


def _provider(make_client: Callable[[Settings], Any]) -> str:
    return "nvidia" if make_client is nvidia_client else "gemini"


MAX_TIMEOUT_ATTEMPTS = 2


def _is_timeout(exc: BaseException) -> bool:
    """httpx.TimeoutException (google-genai), openai.APITimeoutError (Nemotron) o TimeoutError de Python."""
    return isinstance(exc, TimeoutError) or any("Timeout" in cls.__name__ for cls in type(exc).__mro__)


def _status_code(exc: Exception) -> int | None:
    for attr in ("code", "status_code"):  # google-genai usa .code; openai usa .status_code
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def _with_retry(
    generate: Generate, client: Any, model: str, system: str, user: str, schema: type[BaseModel] | None,
    *, provider: str | None = None,
) -> str:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with _measured_slot(provider, model):  # el hueco se ocupa solo durante la petición, no durante el backoff
                text = generate(client, model, system, user, schema)
            if provider:
                _record(provider, ok=1)
            return text
        except LLMError:
            raise
        except Exception as exc:
            if provider:
                if _is_timeout(exc):
                    _record(provider, timeouts=1)
                else:
                    _record(provider, error=str(_status_code(exc)))
            if _is_timeout(exc):
                # Un timeout ya ha costado LLM_TIMEOUT_S: un solo reintento, no MAX_ATTEMPTS (serían ~25 min).
                if attempt >= MAX_TIMEOUT_ATTEMPTS:
                    raise LLMError(f"{model} timeout tras {attempt} intentos: {exc}") from exc
                time.sleep(BACKOFF_BASE_S**attempt)
                continue
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
        _count_cache_hit()
        text = cache_file.read_text(encoding="utf-8")
        return schema.model_validate_json(text) if schema else text

    active_client = client or make_client(settings)
    provider = _provider(make_client)
    text = _hedged(provider, model, lambda: _with_retry(generate, active_client, model, system, user, schema, provider=provider))
    result: Any = text
    if schema:
        result, text = _parse_or_repair(
            text, schema,
            lambda fix: _with_retry(generate, active_client, model, system, f"{user}\n\n{fix}", schema, provider=provider),
        )

    _atomic_write(cache_file, text)
    return result


REPLACE_ATTEMPTS = 5


def _atomic_write(path: Path, text: str) -> None:
    """Con la Etapa 3 en paralelo, otro hilo podría leer el fichero a medio escribir: se escribe un temporal y se
    renombra. En Windows el renombrado falla si otro hilo tiene el destino abierto en ese instante: se reintenta, y si
    sigue bloqueado pero el fichero ya existe, otro hilo guardó la respuesta a ese mismo prompt y basta con ella."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(1, REPLACE_ATTEMPTS + 1):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS:
                if path.exists():
                    tmp.unlink(missing_ok=True)
                    return
                raise
            time.sleep(0.05 * attempt)
