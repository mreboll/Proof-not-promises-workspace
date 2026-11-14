"""Etapa 1 (B): lectura del diff. `parse_diff` es pura; `load_diff` se prueba contra el repo real si existe."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ledger.config import load_settings
from ledger.triage.diff import DiffError, FileDiff, load_diff, parse_diff

MODIFIED = """\
diff --git a/src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs b/src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs
index e121773d..c4ebe3e1 100644
--- a/src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs
+++ b/src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs
@@ -236,3 +236,3 @@ public class TypeCollector
     {
-        this.reportDiagnostic = reportAnalyzerDiagnostic;
+        this.reportDiagnostic = Wrap(reportAnalyzerDiagnostic);
         this.options = options;
@@ -1426,2 +1426,4 @@ public class TypeCollector
     private static Location? A() => null;
+
+    private void ReportIfLocatedInCompilation() { }
     private static Location? B() => null;
"""

ADDED = """\
diff --git a/doc/new.md b/doc/new.md
new file mode 100644
index 00000000..5ae00d37
--- /dev/null
+++ b/doc/new.md
@@ -0,0 +1,2 @@
+# Title
+Body
"""

REMOVED = """\
diff --git a/old.txt b/old.txt
deleted file mode 100644
index 5ae00d37..00000000
--- a/old.txt
+++ /dev/null
@@ -1 +0,0 @@
-gone
"""

RENAMED = """\
diff --git a/src/A.cs b/src/B.cs
similarity index 90%
rename from src/A.cs
rename to src/B.cs
index 1111111..2222222 100644
--- a/src/A.cs
+++ b/src/B.cs
@@ -1 +1 @@
-internal class A { }
+internal class B { }
"""

BINARY = """\
diff --git a/img/logo.png b/img/logo.png
index 1111111..2222222 100644
Binary files a/img/logo.png and b/img/logo.png differ
"""


def _one(text: str) -> FileDiff:
    files = parse_diff(text)
    assert len(files) == 1
    return files[0]


def test_modified_file_collects_added_and_removed_lines_across_hunks():
    fd = _one(MODIFIED)
    assert fd.path == "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs"
    assert fd.status == "modified"
    assert fd.removed == ("        this.reportDiagnostic = reportAnalyzerDiagnostic;",)
    assert fd.added == (
        "        this.reportDiagnostic = Wrap(reportAnalyzerDiagnostic);",
        "",
        "    private void ReportIfLocatedInCompilation() { }",
    )
    assert len(fd.hunks) == 2
    assert fd.hunks[0].header.startswith("@@ -236,3 +236,3 @@")
    assert "ReportIfLocatedInCompilation" in fd.hunks[1].text


def test_added_file():
    fd = _one(ADDED)
    assert (fd.path, fd.status, fd.added, fd.removed) == ("doc/new.md", "added", ("# Title", "Body"), ())


def test_removed_file_uses_source_path():
    fd = _one(REMOVED)
    assert (fd.path, fd.status, fd.removed) == ("old.txt", "removed", ("gone",))


def test_renamed_file_keeps_old_path():
    fd = _one(RENAMED)
    assert (fd.path, fd.old_path, fd.status) == ("src/B.cs", "src/A.cs", "renamed")


def test_binary_file_has_no_lines():
    fd = _one(BINARY)
    assert fd.path == "img/logo.png"
    assert fd.binary and fd.added == () and fd.hunks == ()


def test_crlf_and_bom_are_stripped_from_lines():
    text = MODIFIED.replace("+        this.reportDiagnostic = Wrap(reportAnalyzerDiagnostic);\n", "+﻿using X;\r\n")
    assert "using X;" in _one(text).added


def test_several_files_keep_diff_order():
    paths = [f.path for f in parse_diff(MODIFIED + ADDED + BINARY)]
    assert paths == ["src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs", "doc/new.md", "img/logo.png"]


def test_file_diff_is_frozen():
    fd = _one(ADDED)
    with pytest.raises(Exception):
        fd.path = "x"  # type: ignore[misc]


def test_empty_diff_gives_no_files():
    assert parse_diff("") == ()


def test_missing_repo_gives_clear_error(tmp_path):
    settings = replace(load_settings(), msgpack_repo=tmp_path / "no-existe")
    with pytest.raises(DiffError, match="MSGPACK_REPO"):
        load_diff(settings, "2283")


# --------------------------------------------------------------------------- contra el repo real (se salta en CI)

_settings = load_settings()
needs_repo = pytest.mark.skipif(not (_settings.msgpack_repo / ".git").exists(), reason="repo del reto no clonado")


@needs_repo
def test_real_diff_2283_has_the_four_expected_files():
    paths = {f.path for f in load_diff(_settings, "2283")}
    assert paths == {
        "README.md",
        "doc/analyzers/MsgPack004.md",
        "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs",
        "tests/MessagePack.SourceGenerator.Tests/GenericsFormatterTests.cs",
    }


@needs_repo
@pytest.mark.parametrize(("issue_id", "count"), [("2234", 4), ("2129", 28), ("2297", 237)])
def test_real_diff_file_counts_match_the_guide(issue_id, count):
    assert len(load_diff(_settings, issue_id)) == count
