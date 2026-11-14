"""Peticiones de respaldo (hedging): si una llamada tarda mucho más de lo normal, se lanza otra igual y gana la primera."""

from __future__ import annotations

import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest

from ledger import llm
from ledger.config import load_settings


class ApiError(Exception):
    def __init__(self, code):
        super().__init__(f"code {code}")
        self.code = code


@pytest.fixture
def settings(tmp_path):
    return replace(load_settings(), cache_dir=tmp_path, gemini_api_key="test-key", nvidia_for_all=False)


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    import google.genai.types  # noqa: F401 - la primera importación (~2 s) bloquearía al hilo de respaldo
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)  # backoff de reintentos a 0
    monkeypatch.setenv("LEDGER_HEDGE", "1")  # desactivado por defecto (D16): estos tests lo activan
    monkeypatch.delenv("LEDGER_HEDGE_AFTER_S", raising=False)
    llm._reset_limits()
    llm.reset_llm_stats()
    yield
    llm._reset_limits()
    llm.reset_llm_stats()


class ScriptedModels:
    """Cada llamada sigue el guion por orden: (segundos de espera, respuesta o excepción)."""

    def __init__(self, script):
        self.script = list(script)
        self._lock = threading.Lock()
        self.calls = 0

    def generate_content(self, model, contents, config):
        with self._lock:
            delay, item = self.script[self.calls]
            self.calls += 1
        threading.Event().wait(delay)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(text=item)


def _complete(models, settings):
    return llm.complete("s", "u", client=SimpleNamespace(models=models), settings=settings, use_cache=False)


@pytest.mark.parametrize(
    ("samples", "expected"),
    [([], llm.HEDGE_DEFAULT_S), ([10.0] * 4, llm.HEDGE_DEFAULT_S), ([10.0] * 5, llm.HEDGE_MIN_S), ([60.0] * 9, 120.0), ([500.0] * 9, llm.HEDGE_MAX_S)],
)
def test_hedge_delay_is_twice_the_median_within_bounds(samples, expected):
    assert llm.hedge_delay(samples) == expected


def test_hedge_delay_can_be_fixed_or_disabled(monkeypatch):
    monkeypatch.setenv("LEDGER_HEDGE_AFTER_S", "7")
    assert llm.hedge_delay([60.0] * 9) == 7.0
    monkeypatch.setenv("LEDGER_HEDGE", "0")
    assert llm.hedge_delay([60.0] * 9) is None


def test_a_slow_call_is_hedged_and_the_backup_wins(settings, monkeypatch):
    monkeypatch.setenv("LEDGER_HEDGE_AFTER_S", "0.1")
    models = ScriptedModels([(2.0, "slow"), (0.0, "fast")])

    started = time.monotonic()
    assert _complete(models, settings) == "fast"
    assert time.monotonic() - started < 1.0

    stats = llm.llm_stats()["gemini"]
    assert stats["hedges"] == 1 and stats["hedge_wins"] == 1


def test_a_fast_call_is_never_hedged(settings, monkeypatch):
    monkeypatch.setenv("LEDGER_HEDGE_AFTER_S", "0.5")
    models = ScriptedModels([(0.0, "ok")])

    assert _complete(models, settings) == "ok"
    assert models.calls == 1 and llm.llm_stats()["gemini"]["hedges"] == 0


def test_when_the_backup_fails_the_original_still_answers(settings, monkeypatch):
    monkeypatch.setenv("LEDGER_HEDGE_AFTER_S", "0.1")
    models = ScriptedModels([(0.4, "original"), (0.0, ApiError(400))])

    assert _complete(models, settings) == "original"
    assert llm.llm_stats()["gemini"]["hedge_wins"] == 0


def test_when_both_fail_the_error_is_raised(settings, monkeypatch):
    monkeypatch.setenv("LEDGER_HEDGE_AFTER_S", "0.1")
    models = ScriptedModels([(0.3, ApiError(400)), (0.0, ApiError(400))])

    with pytest.raises(llm.LLMError):
        _complete(models, settings)


def test_disabled_hedging_waits_for_the_slow_call(settings, monkeypatch):
    monkeypatch.setenv("LEDGER_HEDGE", "0")
    models = ScriptedModels([(0.3, "slow"), (0.0, "never")])

    assert _complete(models, settings) == "slow" and models.calls == 1


def test_no_backup_without_spare_capacity(settings, monkeypatch):
    """Con el cupo lleno, un respaldo solo retrasaría a las demás llamadas: se espera a la original."""
    monkeypatch.setenv("LEDGER_HEDGE_AFTER_S", "0.1")
    monkeypatch.setenv("LEDGER_MAX_CONCURRENT_GEMINI", "1")
    llm._reset_limits()
    models = ScriptedModels([(0.5, "original"), (0.0, "backup")])

    assert _complete(models, settings) == "original"
    assert models.calls == 1 and llm.llm_stats()["gemini"]["hedges"] == 0


def test_latency_samples_are_kept_per_model(settings):
    """Las llamadas rápidas de un modelo (triaje flash) no deben bajar el umbral de otro (Defensor pro)."""
    models = ScriptedModels([(0.0, "ok")] * 6)
    for i in range(6):
        llm.complete("s", f"u{i}", role="flash", client=SimpleNamespace(models=models), settings=settings, use_cache=False)

    assert llm.hedge_delay_for(llm.model_for("flash", settings)) == llm.HEDGE_MIN_S
    assert llm.hedge_delay_for(llm.model_for("pro", settings)) == llm.HEDGE_DEFAULT_S


def test_hedging_is_off_by_default(monkeypatch):
    """Cuatro mediciones reales no demostraron que ayude (docs/numeros-evidencia.md): gasto sin beneficio probado."""
    monkeypatch.delenv("LEDGER_HEDGE", raising=False)
    assert llm.hedge_delay([60.0] * 9) is None
