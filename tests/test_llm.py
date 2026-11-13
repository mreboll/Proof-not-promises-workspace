from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from ledger import llm
from ledger.config import load_settings


class Answer(BaseModel):
    reply: str


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_content(self, model, contents, config):
        self.calls += 1
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(text=item)


class ApiError(Exception):
    def __init__(self, code):
        super().__init__(f"code {code}")
        self.code = code


@pytest.fixture
def settings(tmp_path):
    return replace(load_settings(), cache_dir=tmp_path, gemini_api_key="test-key")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)


def test_parses_structured_output(settings):
    client = SimpleNamespace(models=FakeModels(['{"reply": "pong"}']))
    assert llm.complete("s", "u", Answer, client=client, settings=settings) == Answer(reply="pong")


def test_second_call_hits_disk_cache(settings):
    models = FakeModels(['{"reply": "pong"}'])
    client = SimpleNamespace(models=models)
    llm.complete("s", "u", Answer, client=client, settings=settings)
    llm.complete("s", "u", Answer, client=client, settings=settings)
    assert models.calls == 1


def test_retries_on_429_then_succeeds(settings):
    models = FakeModels([ApiError(429), '{"reply": "ok"}'])
    result = llm.complete("s", "u", Answer, client=SimpleNamespace(models=models), settings=settings)
    assert result.reply == "ok" and models.calls == 2


def test_does_not_retry_on_400(settings):
    models = FakeModels([ApiError(400)])
    with pytest.raises(llm.LLMError):
        llm.complete("s", "u", Answer, client=SimpleNamespace(models=models), settings=settings)
    assert models.calls == 1


def test_missing_key_gives_clear_error(settings):
    with pytest.raises(llm.LLMError, match="GEMINI_API_KEY"):
        llm.complete("s", "u", settings=replace(settings, gemini_api_key=""), use_cache=False)
