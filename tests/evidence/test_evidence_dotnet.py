import shutil
from pathlib import Path

import pytest

from ledger.evidence import dotnet
from ledger.evidence._proc import ProcResult
from ledger.evidence.dotnet import LEDGER_TEST_DIR, DotnetTestRunner, mutant_patch_problem, run_in_worktree

DATA = Path(__file__).parent / "data"

MUTANT_PATCH = """diff --git a/src/Mutable.cs b/src/Mutable.cs
--- a/src/Mutable.cs
+++ b/src/Mutable.cs
@@ -1 +1 @@
-pr
+mutant
"""


class FakeDotnet:
    """Sustituye a `_proc.run`: registra la llamada y deja (o no) un .trx en --results-directory."""

    def __init__(self, trx: Path | None = DATA / "pass_fail.trx", output: str = "", timed_out: bool = False):
        self.trx, self.output, self.timed_out = trx, output, timed_out
        self.calls: list[tuple[list[str], Path]] = []
        self.seen_files: list[str] = []

    def __call__(self, cmd, cwd, *, timeout_s, check=False):
        self.calls.append((cmd, cwd))
        self.seen_files = sorted(p.name for p in (cwd / LEDGER_TEST_DIR).glob("*"))
        mutable = cwd / "src" / "Mutable.cs"
        self.mutable = mutable.read_text(encoding="utf-8") if mutable.exists() else None
        results = Path(cmd[cmd.index("--results-directory") + 1])
        results.mkdir(parents=True, exist_ok=True)
        if self.trx is not None and not self.timed_out:
            shutil.copy(self.trx, results / "ledger.trx")
        return ProcResult(-1 if self.timed_out else 1, self.output, "", 2.0, timed_out=self.timed_out)


@pytest.fixture
def fake_dotnet(monkeypatch):
    fake = FakeDotnet()
    monkeypatch.setattr(dotnet, "run", fake)
    return fake


def test_run_in_worktree_writes_test_and_filters_by_exact_class(tmp_path, fake_dotnet):
    result = run_in_worktree(tmp_path, "public class LedgerIssue2283Probe {}", "LedgerIssue2283Probe")

    cmd, cwd = fake_dotnet.calls[0]
    assert cwd == tmp_path
    assert cmd[:2] == ["dotnet", "test"]
    # Con punto final: solo esa clase, no cualquier test cuyo nombre CONTENGA el texto.
    assert "FullyQualifiedName~LedgerIssue2283Probe." in cmd
    assert any(arg.startswith("trx") for arg in cmd)
    assert (tmp_path / LEDGER_TEST_DIR / "LedgerIssue2283Probe.cs").read_text(encoding="utf-8") == "public class LedgerIssue2283Probe {}"
    assert result.red_for_real


def test_previous_generated_tests_are_removed(tmp_path, fake_dotnet):
    stale = tmp_path / LEDGER_TEST_DIR / "OldBrokenTest.cs"
    stale.parent.mkdir(parents=True)
    stale.write_text("this does not compile", encoding="utf-8")

    run_in_worktree(tmp_path, "class LedgerNew {}", "LedgerNew")

    assert fake_dotnet.seen_files == ["LedgerNew.cs"]


@pytest.mark.parametrize(
    "bad_name",
    ["../evil", "a b", "x;rm -rf", "", "1abc", "A|B", "Generics", "MessagePack", "ledgerLowercase"],
)
def test_unsafe_or_unprefixed_test_names_are_refused_without_running(tmp_path, fake_dotnet, bad_name):
    """Sin prefijo `Ledger`, el filtro podría ejecutar tests existentes del repo (que pasan) y dar un verde falso."""
    result = run_in_worktree(tmp_path, "class T {}", bad_name)

    assert not result.build_ok
    assert "test_name" in result.output_tail
    assert fake_dotnet.calls == []


def test_build_failure_when_no_trx(tmp_path, monkeypatch):
    fake = FakeDotnet(trx=None, output="T.cs(1,1): error CS1002: ; expected")
    monkeypatch.setattr(dotnet, "run", fake)

    result = run_in_worktree(tmp_path, "class LedgerT {", "LedgerT")

    assert not result.build_ok
    assert "CS1002" in result.output_tail


def test_build_errors_do_not_leak_absolute_worktree_path(tmp_path, monkeypatch):
    out = f"{tmp_path.resolve()}\\tests\\Ledger\\T.cs(1,1): error CS1002: ; expected [{tmp_path.resolve()}\\x.csproj]"
    monkeypatch.setattr(dotnet, "run", FakeDotnet(trx=None, output=out))

    result = run_in_worktree(tmp_path, "class LedgerT {", "LedgerT")

    assert str(tmp_path.resolve()) not in result.output_tail
    assert "tests\\Ledger\\T.cs(1,1): error CS1002" in result.output_tail


def test_failure_stack_traces_do_not_leak_absolute_worktree_path(tmp_path, monkeypatch):
    trx = (DATA / "pass_fail.trx").read_text(encoding="utf-8").replace(
        "Values differ", f"Values differ at {tmp_path.resolve()}\\src\\TypeCollector.cs:line 1075"
    )
    (tmp_path / "leaky.trx").write_text(trx, encoding="utf-8")
    monkeypatch.setattr(dotnet, "run", FakeDotnet(trx=tmp_path / "leaky.trx"))

    result = run_in_worktree(tmp_path, "class LedgerT {}", "LedgerT")

    assert str(tmp_path.resolve()) not in result.output_tail
    assert "src\\TypeCollector.cs:line 1075" in result.output_tail


def test_timeout_is_reported_as_build_not_ok_and_cleans_results(tmp_path, monkeypatch):
    monkeypatch.setattr(dotnet, "run", FakeDotnet(timed_out=True))

    result = run_in_worktree(tmp_path, "class LedgerT {}", "LedgerT", timeout_s=1)

    assert not result.build_ok
    assert "timeout" in result.output_tail.lower()
    assert not any((tmp_path / dotnet.RESULTS_DIR).iterdir())


def test_runner_uses_side_worktree(settings, fake_dotnet):
    DotnetTestRunner(settings, "2283").run_tests("base", "class LedgerT {}", "LedgerT")

    _, cwd = fake_dotnet.calls[0]
    assert cwd == settings.work_dir / "2283" / "base"


def test_mutant_runs_in_patched_disposable_worktree(settings, fake_dotnet):
    result = DotnetTestRunner(settings, "2283").run_against_mutant("pr", MUTANT_PATCH, "class LedgerT {}", "LedgerT")

    _, cwd = fake_dotnet.calls[0]
    assert fake_dotnet.mutable == "mutant\n"
    assert cwd != settings.work_dir / "2283" / "pr"
    assert not cwd.exists()  # el worktree desechable ya se borró
    assert result.red_for_real


CODE_PATCH = "--- a/src/Code.cs\n+++ b/src/Code.cs\n@@ -1,5 +1,5 @@\n class C\n {\n-    int a = 1;\n+    int a = 0;\n     int b = 2;\n }\n"


def _commit_code_file(repo: Path, eol: str) -> None:
    import subprocess

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()

    (repo / ".gitattributes").write_text(f"*.cs text eol={eol}\n", encoding="utf-8")
    (repo / "src" / "Code.cs").write_bytes(b"class C\n{\n    int a = 1;\n    int b = 2;\n}\n")
    git("add", ".")
    git("commit", "-q", "-m", f"code {eol}")
    git("update-ref", "refs/remotes/origin/ju26-issue-2283", git("rev-parse", "HEAD"))


def _run_mutant_capturing_code(settings, monkeypatch, patch: str) -> tuple[object, list[bytes]]:
    seen: list[bytes] = []
    inner = FakeDotnet()

    def capture(cmd, cwd, **kw):
        seen.append((cwd / "src" / "Code.cs").read_bytes())
        return inner(cmd, cwd, **kw)

    monkeypatch.setattr(dotnet, "run", capture)
    return DotnetTestRunner(settings, "2283").run_against_mutant("pr", patch, "class LedgerT {}", "LedgerT"), seen


@pytest.mark.parametrize(
    ("checkout_eol", "patch"),
    [
        ("crlf", CODE_PATCH),
        ("lf", CODE_PATCH.replace("\n", "\r\n")),
        ("crlf", CODE_PATCH.replace("     int b = 2;", "         int b = 2;")),
    ],
    ids=["lf-patch-on-crlf-checkout", "crlf-patch-on-lf-checkout", "llm-context-indent-drift"],
)
def test_mutant_patch_applies_regardless_of_line_endings(settings, fake_repo, monkeypatch, checkout_eol, patch):
    _commit_code_file(fake_repo["repo"], checkout_eol)

    result, seen = _run_mutant_capturing_code(settings, monkeypatch, patch)

    assert result.build_ok, result.output_tail
    assert (b"\r\n" in seen[0]) is (checkout_eol == "crlf")  # el checkout tenía de verdad ese final de línea
    assert b"int a = 0;" in seen[0]


def test_mutant_patch_that_does_not_apply_is_not_run(settings, fake_dotnet):
    wrong_context = MUTANT_PATCH.replace("-pr", "-something else")
    result = DotnetTestRunner(settings, "2283").run_against_mutant("pr", wrong_context, "class LedgerT {}", "LedgerT")

    assert not result.build_ok
    assert "git apply" in result.output_tail
    assert fake_dotnet.calls == []


# --------------------------------------------------------------------------- integridad de los mutantes


def _patch_for(path: str, old: str = "a/") -> str:
    return f"--- {old}{path}\n+++ b/{path}\n@@ -1 +1 @@\n-x\n+y\n"


@pytest.mark.parametrize(
    "patch",
    [
        _patch_for("src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs"),
        "diff --git a/src/A.cs b/src/A.cs\n" + _patch_for("src/A.cs"),
    ],
)
def test_product_code_mutants_are_accepted(patch):
    assert mutant_patch_problem(patch) is None


@pytest.mark.parametrize(
    ("patch", "why"),
    [
        (_patch_for("tests/MessagePack.SourceGenerator.Tests/Ledger/LedgerT.cs"), "tests"),
        (_patch_for("src/MessagePack.SourceGenerator/MessagePack.SourceGenerator.csproj"), "csproj"),
        (_patch_for("Directory.Build.targets"), "build"),
        (_patch_for("src/Directory.Build.props"), "props"),
        (_patch_for("src/New.cs", old="/dev/null").replace("--- /dev/nullsrc/New.cs", "--- /dev/null"), "new file"),
        ("garbage patch", "no files"),
    ],
)
def test_mutants_outside_product_source_are_rejected(patch, why):
    """Un mutante solo puede romper código del producto: ni el test (trampa a la antitrampa) ni la build
    (que en local ejecutaría código fuera de cualquier sandbox)."""
    assert mutant_patch_problem(patch) is not None, why


def test_rejected_mutant_is_never_applied_nor_run(settings, fake_dotnet):
    evil = _patch_for("tests/MessagePack.SourceGenerator.Tests/Ledger/LedgerT.cs")

    result = DotnetTestRunner(settings, "2283").run_against_mutant("pr", evil, "class LedgerT {}", "LedgerT")

    assert not result.build_ok
    assert "mutant" in result.output_tail.lower()
    assert fake_dotnet.calls == []
