"""Etapa 1 (B): reglas estáticas de riesgo. Un test por regla, más combinación, exclusiones y casos reales."""

from __future__ import annotations

import pytest

from ledger.config import load_settings
from ledger.models import Risk
from ledger.triage.diff import FileDiff, load_diff
from ledger.triage.rules import RULES, assess_risk

GEN = "src/MessagePack.SourceGenerator"


def fd(path: str, added: tuple[str, ...] = (), removed: tuple[str, ...] = (), binary: bool = False) -> FileDiff:
    return FileDiff(path=path, status="modified", added=added, removed=removed, binary=binary)


def ids(path: str, added: tuple[str, ...] = (), removed: tuple[str, ...] = ()) -> set[str]:
    return {hit.split(":")[0] for hit in assess_risk(fd(path, added, removed)).rule_hits}


# --------------------------------------------------------------------------- una regla, un test


def test_r_low_01_tests_folder():
    a = assess_risk(fd("tests/MessagePack.Tests/FooTests.cs", added=("    public async Task Foo() { }",)))
    assert a.risk is Risk.LOW and not a.touches_public_api
    assert ids("tests/MessagePack.Tests/FooTests.cs") == {"R-LOW-01"}


def test_r_low_02_markdown():
    assert assess_risk(fd("doc/analyzers/MsgPack004.md", added=("public member",))).risk is Risk.LOW
    assert ids("README.md") == {"R-LOW-02"}


def test_r_low_03_csproj():
    assert ids("tests/X/X.csproj") >= {"R-LOW-03"}
    assert assess_risk(fd("src/MessagePack/MessagePack.csproj")).risk is Risk.LOW


def test_r_low_04_editorconfig():
    assert ids(".editorconfig") == {"R-LOW-04"}
    assert ids("src/.editorconfig") == {"R-LOW-04"}


def test_r_low_05_generated_snapshot():
    path = "tests/MessagePack.SourceGenerator.Tests/Resources/Foo/Formatters.MyType.g.cs"
    assert ids(path) == {"R-LOW-01", "R-LOW-05"}
    assert assess_risk(fd(path)).risk is Risk.LOW


def test_r_med_01_production_code_in_src():
    a = assess_risk(fd(f"{GEN}/Analyzers/MsgPack00xMessagePackAnalyzer.cs", added=("    private static void X() { }",)))
    assert a.risk is Risk.MED and not a.touches_public_api
    assert {h.split(":")[0] for h in a.rule_hits} == {"R-MED-01"}


def test_r_high_01_public_signature_added_or_removed():
    added = assess_risk(fd("src/MessagePack.Annotations/Attributes.cs", added=("    public class GeneratedMessagePackFormatterAttribute : Attribute",)))
    removed = assess_risk(fd("src/MessagePack/Foo.cs", removed=("    public void Gone() { }",)))
    for a in (added, removed):
        assert a.risk is Risk.HIGH and a.touches_public_api
        assert any(h.startswith("R-HIGH-01") for h in a.rule_hits)


def test_r_high_01_public_after_attribute_on_same_line():
    assert "R-HIGH-01" in ids("src/MessagePack/Foo.cs", added=("    [Obsolete] public int X { get; }",))


@pytest.mark.parametrize("line", ["    Span<byte> buf = stackalloc byte[8];", "    unsafe void P() { }", "    ReadOnlySpan<char> s = x;"])
def test_r_high_02_memory(line):
    a = assess_risk(fd("src/MessagePack/Internal/Buf.cs", added=(line,)))
    assert a.risk is Risk.HIGH and not a.touches_public_api
    assert "R-HIGH-02" in {h.split(":")[0] for h in a.rule_hits}


@pytest.mark.parametrize("folder", ["CodeAnalysis", "Transforms", "Transforms/StringKey"])
def test_r_high_03_core_generator_namespace(folder):
    a = assess_risk(fd(f"{GEN}/{folder}/X.cs", added=("    var a = 1;",)))
    assert a.risk is Risk.HIGH
    assert "R-HIGH-03" in {h.split(":")[0] for h in a.rule_hits}


def test_r_default_unknown_file_is_med():
    a = assess_risk(fd("src/MessagePack.SourceGenerator/version.json"))
    assert a.risk is Risk.MED
    assert [h.split(":")[0] for h in a.rule_hits] == ["R-DEFAULT"]


# --------------------------------------------------------------------------- combinación y exclusiones


def test_final_risk_is_the_max_and_every_hit_is_listed():
    a = assess_risk(fd(f"{GEN}/CodeAnalysis/TypeCollector.cs", added=("    public Span<byte> X;",)))
    assert a.risk is Risk.HIGH and a.touches_public_api
    assert {h.split(":")[0] for h in a.rule_hits} == {"R-MED-01", "R-HIGH-01", "R-HIGH-02", "R-HIGH-03"}


@pytest.mark.parametrize("line", ["    // public void Commented()", "    /// <summary>Uses Span<T> in public API</summary>", "    * public in block comment"])
def test_comments_do_not_fire_line_rules(line):
    assert assess_risk(fd("src/MessagePack/Foo.cs", added=(line,))).risk is Risk.MED


def test_public_inside_string_literal_does_not_fire():
    assert assess_risk(fd(f"{GEN}/Emit.cs", added=('    this.Write("public sealed class ");',))).risk is Risk.MED


def test_t4_template_text_is_not_a_public_signature():
    a = assess_risk(fd(f"{GEN}/Transforms/FormatterTemplate.tt", added=("public sealed class <#= Name #>Formatter",)))
    assert not a.touches_public_api  # es texto emitido, no la API del generador (sigue HIGH por R-HIGH-03)


def test_binary_file_only_uses_path_rules():
    assert assess_risk(fd("src/MessagePack/logo.png", binary=True)).risk is Risk.MED


def test_hit_cites_the_offending_line():
    a = assess_risk(fd("src/MessagePack/Foo.cs", added=("    public void Bar() { }",)))
    assert any("public void Bar()" in h for h in a.rule_hits if h.startswith("R-HIGH-01"))


def test_rule_ids_are_unique_and_deterministic():
    assert len({r.id for r in RULES}) == len(RULES)
    f = fd(f"{GEN}/CodeAnalysis/X.cs", added=("    public int A;",))
    assert assess_risk(f) == assess_risk(f)


# --------------------------------------------------------------------------- contra el repo real

_settings = load_settings()
needs_repo = pytest.mark.skipif(not (_settings.msgpack_repo / ".git").exists(), reason="repo del reto no clonado")


@needs_repo
def test_real_2283_risks():
    got = {f.path: assess_risk(f) for f in load_diff(_settings, "2283")}
    assert got[f"{GEN}/CodeAnalysis/TypeCollector.cs"].risk is Risk.HIGH
    assert not got[f"{GEN}/CodeAnalysis/TypeCollector.cs"].touches_public_api
    assert got["tests/MessagePack.SourceGenerator.Tests/GenericsFormatterTests.cs"].risk is Risk.LOW
    assert got["README.md"].risk is Risk.LOW
    assert got["doc/analyzers/MsgPack004.md"].risk is Risk.LOW


@needs_repo
def test_real_2129_touches_public_api_in_annotations():
    got = {f.path: assess_risk(f) for f in load_diff(_settings, "2129")}
    attrs = got["src/MessagePack.Annotations/Attributes.cs"]
    assert attrs.risk is Risk.HIGH and attrs.touches_public_api


# --------------------------------------------------------------------------- seguridad (D18)


@pytest.mark.parametrize("line", [
    "    var t = Type.GetType(typeName, throwOnError: true);",
    "    var asm = Assembly.Load(bytes);",
    "    return Activator.CreateInstance(t);",
    "    options = options.WithSecurity(MessagePackSecurity.UntrustedData);",
    "    var f = new BinaryFormatter();",
    "    Process.Start(\"sh\");",
    "    using var aes = System.Security.Cryptography.Aes.Create();",
    "    Marshal.Copy(src, dst, 0, n);",
])
def test_r_high_04_security_sensitive_api(line):
    a = assess_risk(fd("src/MessagePack/Formatters/X.cs", added=(line,)))
    assert a.risk is Risk.HIGH
    assert "R-HIGH-04" in {h.split(":")[0] for h in a.rule_hits}


def test_r_high_04_ignores_comments_strings_and_tests():
    assert "R-HIGH-04" not in ids("src/MessagePack/X.cs", added=("    // Type.GetType is dangerous",))
    assert "R-HIGH-04" not in ids("src/MessagePack/X.cs", added=('    var s = "Process.Start";',))
    assert "R-HIGH-04" not in ids("tests/MessagePack.Tests/X.cs", added=("    Type.GetType(n);",))


@pytest.mark.parametrize("path", ["src/MessagePack/MessagePackSecurity.cs", "src/MessagePack/Formatters/TypelessFormatter.cs"])
def test_r_high_05_security_paths(path):
    a = assess_risk(fd(path, added=("    var a = 1;",)))
    assert a.risk is Risk.HIGH and "R-HIGH-05" in {h.split(":")[0] for h in a.rule_hits}


@pytest.mark.parametrize("path", ["src/MessagePack/Typeless/Foo.cs", "src/MessagePack/Security/Y.cs"])
def test_r_high_05_matches_security_directories_too(path):
    assert "R-HIGH-05" in ids(path, added=("    var a = 1;",))


@pytest.mark.parametrize("line", ["    Process.Start (\"sh\");", "    Assembly.Load (bytes);", "    Type.GetType (n);"])
def test_r_high_04_tolerates_a_space_before_the_parenthesis(line):
    assert "R-HIGH-04" in ids("src/MessagePack/X.cs", added=(line,))
