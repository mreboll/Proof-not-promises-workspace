"""Medidas de uso del LLM por proveedor: el dato para encontrar el límite de concurrencia (pico real, 429, espera)."""

from __future__ import annotations

import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from ledger import llm
from ledger.config import load_settings


class Answer(BaseModel):
    reply: str


class ApiError(Exception):
    def __init__(self, code):
        super().__init__(f"code {code}")
        self.code = code


@pytest.fixture
def settings(tmp_path):
    return replace(load_settings(), cache_dir=tmp_path, gemini_api_key="test-key", nvidia_for_all=False)


@pytest.fixture(autouse=True)
def clean_stats(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)
    llm._reset_limits()
    llm.reset_llm_stats()
    yield
    llm._reset_limits()
    llm.reset_llm_stats()


class FakeModels:
    def __init__(self, responses, delay=0.0):
        self.responses = list(responses)
        self.delay = delay
        self._lock = threading.Lock()

    def generate_content(self, model, contents, config):
        threading.Event().wait(self.delay)  # time.sleep está anulado por el fixture
        with self._lock:
            item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(text=item)


def test_stats_count_requests_and_retryable_errors(settings):
    models = FakeModels([ApiError(429), ApiError(503), '{"reply": "ok"}'])
    llm.complete("s", "u", Answer, client=SimpleNamespace(models=models), settings=settings)

    gemini = llm.llm_stats()["gemini"]
    assert gemini["requests"] == 3
    assert gemini["ok"] == 1
    assert gemini["errors"] == {"429": 1, "503": 1}
    assert gemini["timeouts"] == 0


def test_cache_hits_do_not_count_as_requests(settings):
    models = FakeModels(['{"reply": "ok"}'])
    client = SimpleNamespace(models=models)
    llm.complete("s", "u", Answer, client=client, settings=settings)
    llm.complete("s", "u", Answer, client=client, settings=settings)

    gemini = llm.llm_stats()["gemini"]
    assert gemini["requests"] == 1 and llm.llm_stats()["cache_hits"] == 1


def test_stats_record_real_peak_and_time_waiting_for_a_slot(settings, monkeypatch):
    monkeypatch.setenv("LEDGER_MAX_CONCURRENT_GEMINI", "2")
    llm._reset_limits()
    models = FakeModels(['{"reply": "ok"}'] * 4, delay=0.1)
    client = SimpleNamespace(models=models)

    threads = [
        threading.Thread(target=llm.complete, args=("s", f"u{i}", Answer), kwargs={"client": client, "settings": settings})
        for i in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    gemini = llm.llm_stats()["gemini"]
    assert gemini["peak"] == 2 and gemini["limit"] == 2
    assert gemini["wait_s"] > 0.1  # dos llamadas esperaron un hueco
    assert gemini["max_latency_s"] >= 0.1


def test_reset_clears_everything(settings):
    llm.complete("s", "u", Answer, client=SimpleNamespace(models=FakeModels(['{"reply": "ok"}'])), settings=settings)
    llm.reset_llm_stats()
    assert llm.llm_stats()["gemini"]["requests"] == 0 and llm.llm_stats()["cache_hits"] == 0
