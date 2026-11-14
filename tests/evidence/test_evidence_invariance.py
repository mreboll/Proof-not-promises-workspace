import hashlib

import pytest

from ledger.evidence.invariance import (
    EXCLUDE_FROM_COVERAGE,
    CorpusCase,
    InvarianceError,
    build_evidence,
    canonical_hash,
    load_corpus,
    normalization_for,
)

G1 = CorpusCase("int-keys", "general")
G2 = CorpusCase("string-keys", "general")
ISSUE = CorpusCase("metadata-generic", "issue-2283")

GENERATED_2297 = (
    "partial class F\r\n"
    "{\r\n"
    "    [global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]\r\n"
    "    public void Serialize() {}\r\n"
    "}\r\n"
)
GENERATED_BASE = "partial class F\n{\n    public void Serialize() {}\n}\n"


def test_load_corpus_reads_tag_header_and_sorts(tmp_path):
    (tmp_path / "b-case.cs").write_text("//@tag: issue-2283\nclass B {}", encoding="utf-8")
    (tmp_path / "a-case.cs").write_text("//@tag: general\nclass A {}", encoding="utf-8")
    (tmp_path / "notes.md").write_text("ignored", encoding="utf-8")

    assert load_corpus(tmp_path) == (CorpusCase("a-case", "general"), CorpusCase("b-case", "issue-2283"))


def test_load_corpus_rejects_case_without_tag(tmp_path):
    (tmp_path / "x.cs").write_text("class X {}", encoding="utf-8")
    with pytest.raises(InvarianceError, match="x.cs"):
        load_corpus(tmp_path)


def test_canonical_hash_is_sha256_and_ignores_line_endings():
    assert canonical_hash("a\r\nb\r\n") == canonical_hash("a\nb\n")
    assert canonical_hash("a\nb\n") == hashlib.sha256(b"a\nb\n").hexdigest()


def test_2297_normalization_removes_only_exclude_from_coverage_lines():
    norm = normalization_for("2297")
    assert norm is not None
    assert EXCLUDE_FROM_COVERAGE in norm.description
    assert canonical_hash(GENERATED_2297, norm) == canonical_hash(GENERATED_BASE)
    assert canonical_hash("public void Other() {}", norm) == canonical_hash("public void Other() {}")


GENERATED_2297_REAL = (
    "namespace Formatters\n"
    "{\n"
    "#if !NETSTANDARD2_0 && !NETFRAMEWORK\n"
    "\t[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]\n"
    "#endif\n"
    "\tinternal sealed class F {}\n"
    "}\n"
    "#if !NETSTANDARD2_0 && !NETFRAMEWORK\n"
    "[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]\n"
    "#endif\n"
    "partial class R {}\n"
)
GENERATED_BASE_REAL = "namespace Formatters\n{\n\tinternal sealed class F {}\n}\npartial class R {}\n"


def test_2297_normalization_removes_the_real_conditional_block():
    """El PR emite el atributo dentro de `#if !NETSTANDARD2_0 && !NETFRAMEWORK ... #endif` (3 líneas)."""
    norm = normalization_for("2297")
    assert canonical_hash(GENERATED_2297_REAL, norm) == canonical_hash(GENERATED_BASE_REAL)


def test_2297_normalization_keeps_unrelated_conditionals():
    norm = normalization_for("2297")
    text = "#if !NETSTANDARD2_0 && !NETFRAMEWORK\n\tusing System.Buffers;\n#endif\nclass X {}\n"
    assert canonical_hash(text, norm) == canonical_hash(text)


def test_2297_normalization_does_not_hide_other_changes():
    norm = normalization_for("2297")
    pr_with_extra_change = GENERATED_2297_REAL.replace("class F {}", "class F {\n}")
    assert canonical_hash(pr_with_extra_change, norm) != canonical_hash(GENERATED_BASE_REAL)


def test_other_issues_have_no_normalization():
    assert normalization_for("2283") is None


def test_identical_outputs_are_ok():
    outputs = {"int-keys": "x", "string-keys": "y", "metadata-generic": "z"}
    ev = build_evidence((G1, G2, ISSUE), outputs, dict(outputs), dict(outputs))

    assert ev.ok and ev.deterministic and ev.unexpected_diffs == ()
    assert all(c.normalization == "" for c in ev.cases)


def test_issue_case_may_differ_but_general_may_not():
    base = {"int-keys": "x", "string-keys": "y", "metadata-generic": "AD0001"}
    pr = {"int-keys": "x", "string-keys": "CHANGED", "metadata-generic": "clean"}

    ev = build_evidence((G1, G2, ISSUE), base, dict(base), pr)

    assert ev.unexpected_diffs == ("string-keys",)
    assert not ev.ok


def test_nondeterministic_base_is_detected():
    base = {"int-keys": "x"}
    ev = build_evidence((G1,), base, {"int-keys": "x-but-reordered"}, base)
    assert not ev.deterministic and not ev.ok


def test_normalization_applies_to_general_pr_only_and_is_declared():
    norm = normalization_for("2297")
    base = {"int-keys": GENERATED_BASE, "metadata-generic": GENERATED_BASE}
    pr = {"int-keys": GENERATED_2297, "metadata-generic": GENERATED_2297}
    issue_case = CorpusCase("metadata-generic", "issue-2297")

    ev = build_evidence((G1, issue_case), base, dict(base), pr, norm)

    general, issue = ev.cases
    assert general.pr_hash == general.base_hash
    assert EXCLUDE_FROM_COVERAGE in general.normalization
    assert issue.pr_hash != issue.base_hash  # el caso del issue se compara en bruto: ahí se ve la feature
    assert issue.normalization == ""
    assert ev.ok


def test_normalization_also_applies_to_other_issues_cases():
    """Bajo el PR de #2297, un caso de #2129 solo debe diferir por la transformación declarada."""
    norm = normalization_for("2297")
    base = {"own": GENERATED_BASE_REAL, "foreign": GENERATED_BASE_REAL}
    pr = {"own": GENERATED_2297_REAL, "foreign": GENERATED_2297_REAL}
    own, foreign = CorpusCase("own", "issue-2297"), CorpusCase("foreign", "issue-2129")

    ev = build_evidence((own, foreign), base, dict(base), pr, norm, issue_id="2297")

    own_case, foreign_case = ev.cases
    assert own_case.pr_hash != own_case.base_hash and own_case.normalization == ""
    assert foreign_case.pr_hash == foreign_case.base_hash and foreign_case.normalization != ""


def test_evidence_records_issue_so_other_issues_cases_must_not_change():
    """Con issue_id relleno, un caso de OTRO issue que cambia es una diferencia inesperada (contrato de models.py)."""
    base = {"own": "a", "foreign": "b", "g": "c"}
    pr = {"own": "A", "foreign": "B", "g": "c"}
    cases = (CorpusCase("own", "issue-2283"), CorpusCase("foreign", "issue-2129"), CorpusCase("g", "general"))

    ev = build_evidence(cases, base, dict(base), pr, issue_id="2283")

    assert ev.issue_id == "2283"
    assert ev.unexpected_diffs == ("foreign",)
    assert not ev.ok


def test_missing_probe_output_raises():
    with pytest.raises(InvarianceError, match="int-keys"):
        build_evidence((G1,), {}, {}, {})
