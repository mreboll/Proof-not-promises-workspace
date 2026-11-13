from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from ledger import llm
from ledger.config import load_settings
from ledger.llm_backends import clean_json_text


class Objections(BaseModel):
    questions: list[str]


def _completion(content: str) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeChat:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, model, temperature, messages):
        self.requests.append({"model": model, "messages": messages})
        return _completion(self.responses.pop(0))


def _client(chat: FakeChat) -> SimpleNamespace:
    return SimpleNamespace(chat=SimpleNamespace(completions=chat))


@pytest.fixture
def settings(tmp_path):
    return replace(load_settings(), cache_dir=tmp_path, nvidia_api_key="k", nvidia_model="nvidia/test-nemotron")


def test_clean_json_strips_think_block_and_fences():
    raw = '<think>let me reason</think>\n```json\n{"questions": ["null?"]}\n```'
    assert clean_json_text(raw) == '{"questions": ["null?"]}'


def test_fiscal_role_routes_to_nemotron_with_schema_in_prompt(settings):
    chat = FakeChat(['<think>x</think>{"questions": ["What if the type is generic?"]}'])
    result = llm.complete("You are the prosecutor.", "diff...", Objections, "fiscal", client=_client(chat), settings=settings)
    assert result.questions == ["What if the type is generic?"]
    assert chat.requests[0]["model"] == "nvidia/test-nemotron"
    assert "JSON Schema" in chat.requests[0]["messages"][0]["content"]


def test_invalid_json_is_repaired_once(settings):
    chat = FakeChat(["not json", '{"questions": []}'])
    result = llm.complete("s", "u", Objections, "fiscal", client=_client(chat), settings=settings)
    assert result.questions == [] and len(chat.requests) == 2
    assert "invalid JSON" in chat.requests[1]["messages"][1]["content"]


def test_gives_up_after_failed_repair(settings):
    chat = FakeChat(["nope", "still nope"])
    with pytest.raises(llm.LLMError, match="tras reparar"):
        llm.complete("s", "u", Objections, "fiscal", client=_client(chat), settings=settings)


def test_missing_nvidia_model_gives_clear_error(settings):
    with pytest.raises(llm.LLMError, match="NVIDIA_MODEL"):
        llm.complete("s", "u", role="fiscal", settings=replace(settings, nvidia_model=""), use_cache=False)


def test_retries_on_openai_style_status_code(settings, monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)

    class RateLimited(Exception):
        status_code = 429

    class FlakyChat(FakeChat):
        def create(self, model, temperature, messages):
            if not self.requests:
                self.requests.append({})
                raise RateLimited()
            return super().create(model, temperature, messages)

    chat = FlakyChat(['{"questions": ["ok"]}'])
    assert llm.complete("s", "u", Objections, "fiscal", client=_client(chat), settings=settings).questions == ["ok"]
