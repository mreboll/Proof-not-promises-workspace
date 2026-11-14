"""Etapa 1 (B), eje A: alcance IN/OUT con el LLM (rol "flash"). El LLM se sustituye por un doble."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ledger.config import load_settings
from ledger.models import Scope
from ledger.triage.diff import FileDiff, Hunk
from ledger.triage.scope import MAX_DIFF_CHARS, IssueNotFound, ScopeAnswer, classify_scope, load_issue_text

ISSUE = "# #2283: Generator and analyzer crash with IndexOutOfRangeException\n\nThe generated resolver is missing."
CODE = FileDiff(
    path="src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs",
    status="modified",
    hunks=(Hunk(header="@@ -1 +1 @@", text="@@ -1 +1 @@\n-a\n+DeclaringSyntaxReferences.FirstOrDefault()\n"),),
    added=("DeclaringSyntaxReferences.FirstOrDefault()",),
    removed=("a",),
)
SNAPSHOT = FileDiff(path="tests/MessagePack.SourceGenerator.Tests/Resources/X/Formatters.Y.g.cs", status="modified")


class FakeComplete:
    def __init__(self, answer: ScopeAnswer | None = None):
        self.answer = answer or ScopeAnswer(scope=Scope.IN, justification="Arregla el crash del issue.")
        self.calls: list[dict] = []

    def __call__(self, system, user, schema, role, **kwargs):
        self.calls.append({"system": system, "user": user, "schema": schema, "role": role})
        return self.answer


def test_asks_the_flash_role_with_schema_and_returns_its_answer():
    fake = FakeComplete()
    assert classify_scope(ISSUE, CODE, complete=fake) == (Scope.IN, "Arregla el crash del issue.")
    call = fake.calls[0]
    assert call["role"] == "flash" and call["schema"] is ScopeAnswer


def test_prompt_contains_literal_issue_path_and_diff():
    fake = FakeComplete()
    classify_scope(ISSUE, CODE, complete=fake)
    user = fake.calls[0]["user"]
    assert ISSUE in user and CODE.path in user and "FirstOrDefault" in user


def test_issue_and_diff_are_framed_as_data_not_instructions():
    fake = FakeComplete()
    classify_scope(ISSUE, CODE, complete=fake)
    assert "data" in fake.calls[0]["system"].lower() and "instruction" in fake.calls[0]["system"].lower()


def test_out_answer_is_passed_through():
    fake = FakeComplete(ScopeAnswer(scope=Scope.OUT, justification="El issue no pide documentación."))
    assert classify_scope(ISSUE, FileDiff(path="README.md", status="modified"), complete=fake)[0] is Scope.OUT


def test_long_diff_is_truncated_and_says_so():
    big = CODE.model_copy(update={"hunks": (Hunk(header="@@", text="+x\n" * MAX_DIFF_CHARS),)})
    fake = FakeComplete()
    classify_scope(ISSUE, big, complete=fake)
    user = fake.calls[0]["user"]
    assert len(user) < MAX_DIFF_CHARS + len(ISSUE) + 2000
    assert "truncated" in user


def test_snapshot_skips_llm_and_is_in_when_issue_mentions_generated_code():
    fake = FakeComplete()
    scope, why = classify_scope(ISSUE, SNAPSHOT, complete=fake)
    assert scope is Scope.IN and fake.calls == []
    assert "no LLM" in why


def test_snapshot_is_out_when_issue_does_not_mention_generated_code():
    fake = FakeComplete()
    scope, _ = classify_scope("# #1: Typo in README", SNAPSHOT, complete=fake)
    assert scope is Scope.OUT and fake.calls == []


def test_binary_file_is_still_classified_by_path():
    fake = FakeComplete()
    classify_scope(ISSUE, FileDiff(path="img/logo.png", status="modified", binary=True), complete=fake)
    assert "binary" in fake.calls[0]["user"].lower()


class FlakyComplete(FakeComplete):
    """Falla con LLMError en los roles de `fail_roles` (p. ej. el modelo devuelve el esquema en vez de la respuesta)."""

    def __init__(self, fail_roles):
        super().__init__()
        self.fail_roles = fail_roles

    def __call__(self, system, user, schema, role, **kwargs):
        self.calls.append({"system": system, "user": user, "schema": schema, "role": role})
        if role in self.fail_roles:
            from ledger.llm import LLMError

            raise LLMError("JSON inválido tras reparar")
        return self.answer


def test_falls_back_to_pro_role_when_flash_gives_invalid_json():
    fake = FlakyComplete({"flash"})
    assert classify_scope(ISSUE, CODE, complete=fake) == (Scope.IN, "Arregla el crash del issue.")
    assert [c["role"] for c in fake.calls] == ["flash", "pro"]


def test_unclassifiable_file_goes_to_human_review_instead_of_crashing():
    fake = FlakyComplete({"flash", "pro"})
    scope, why = classify_scope(ISSUE, CODE, complete=fake)
    assert scope is Scope.OUT and "human review" in why and "JSON inválido" in why


def test_load_issue_text_reads_the_literal_markdown():
    text = load_issue_text(load_settings(), "2283")
    assert text.startswith("# #2283:") and "IndexOutOfRangeException" in text


def test_missing_issue_file_gives_clear_error(tmp_path):
    with pytest.raises(IssueNotFound, match="issues"):
        load_issue_text(replace(load_settings(), issues_dir=tmp_path), "2283")
