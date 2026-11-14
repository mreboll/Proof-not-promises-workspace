"""Timeouts de los clientes LLM (petición de A tras el cuelgue de ~1 h en Modal): una llamada colgada
tiene que acabar en excepción y en un reintento acotado, nunca bloquear la demo."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ledger import llm, llm_backends
from ledger.config import load_settings


class ReadTimeout(Exception):
    """Imita httpx.ReadTimeout / openai.APITimeoutError: sin código HTTP, 'Timeout' en el nombre."""


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


def test_gemini_client_is_created_with_a_timeout_in_milliseconds(monkeypatch):
    seen = {}

    class FakeClient:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    from google import genai

    monkeypatch.setattr(genai, "Client", FakeClient)
    llm_backends.gemini_client(replace(load_settings(), gemini_api_key="k"))
    assert seen["http_options"].timeout == llm_backends.LLM_TIMEOUT_S * 1000


def test_nvidia_client_is_created_with_a_timeout_in_seconds(monkeypatch):
    seen = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    import openai

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    llm_backends.nvidia_client(replace(load_settings(), nvidia_api_key="k", nvidia_model="m"))
    assert seen["timeout"] == llm_backends.LLM_TIMEOUT_S


def test_timeout_is_long_enough_for_the_slowest_real_calls():
    assert llm_backends.LLM_TIMEOUT_S >= 240  # gemini-4-hydrogen tardó 215 s en un test del Defensor


def test_a_timeout_is_retried_once_and_then_succeeds():
    calls = []

    def generate(client, model, system, user, schema):
        calls.append(1)
        if len(calls) == 1:
            raise ReadTimeout("read timed out")
        return "ok"

    assert llm._with_retry(generate, None, "m", "s", "u", None) == "ok" and len(calls) == 2


def test_repeated_timeouts_give_up_quickly_with_a_clear_error():
    calls = []

    def generate(client, model, system, user, schema):
        calls.append(1)
        raise ReadTimeout("read timed out")

    with pytest.raises(llm.LLMError, match="timeout"):
        llm._with_retry(generate, None, "m", "s", "u", None)
    assert len(calls) == llm.MAX_TIMEOUT_ATTEMPTS == 2


def test_builtin_timeout_error_counts_as_timeout():
    assert llm._is_timeout(TimeoutError()) and llm._is_timeout(ReadTimeout()) and not llm._is_timeout(ValueError())
