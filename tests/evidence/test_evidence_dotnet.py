import shutil
from pathlib import Path

import pytest

from ledger.evidence import dotnet
from ledger.evidence._proc import ProcResult
from ledger.evidence.dotnet import LEDGER_TEST_DIR, DotnetTestRunner, run_in_worktree

DATA = Path(__file__).parent / "data"

MUTANT_PATCH = """diff --git a/file.txt b/file.txt
--- a/file.txt
+++ b/file.txt
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
        self.file_txt = (cwd / "file.txt").read_text(encoding="utf-8") if (cwd / "file.txt").exists() else None
        if self.trx is not None and not self.timed_out:
            results = Path(cmd[cmd.index("--results-directory") + 1])
            results.mkdir(parents=True, exist_ok=True)
            shutil.copy(self.trx, results / "ledger.trx")
        return ProcResult(-1 if self.timed_out else 1, self.output, "", 2.0, timed_out=self.timed_out)


@pytest.fixture
def fake_dotnet(monkeypatch):
    fake = FakeDotnet()
    monkeypatch.setattr(dotnet, "run", fake)
    return fake


def test_run_in_worktree_writes_test_and_filters_by_name(tmp_path, fake_dotnet):
    result = run_in_worktree(tmp_path, "public class Issue2283Probe {}", "Issue2283Probe")

    cmd, cwd = fake_dotnet.calls[0]
    assert cwd == tmp_path
    assert cmd[:2] == ["dotnet", "test"]
    assert "FullyQualifiedName~Issue2283Probe" in cmd
    assert any(arg.startswith("trx") for arg in cmd)
    assert (tmp_path / LEDGER_TEST_DIR / "Issue2283Probe.cs").read_text(encoding="utf-8") == "public class Issue2283Probe {}"
    assert result.red_for_real


def test_previous_generated_tests_are_removed(tmp_path, fake_dotnet):
    stale = tmp_path / LEDGER_TEST_DIR / "OldBrokenTest.cs"
    stale.parent.mkdir(parents=True)
    stale.write_text("this does not compile", encoding="utf-8")

    run_in_worktree(tmp_path, "class T {}", "NewTest")

    assert fake_dotnet.seen_files == ["NewTest.cs"]


@pytest.mark.parametrize("bad_name", ["../evil", "a b", "x;rm -rf", "", "1abc", "A|B"])
def test_unsafe_test_names_are_refused_without_running(tmp_path, fake_dotnet, bad_name):
    result = run_in_worktree(tmp_path, "class T {}", bad_name)

    assert not result.build_ok
    assert "test_name" in result.output_tail
    assert fake_dotnet.calls == []


def test_build_failure_when_no_trx(tmp_path, monkeypatch):
    fake = FakeDotnet(trx=None, output="T.cs(1,1): error CS1002: ; expected")
    monkeypatch.setattr(dotnet, "run", fake)

    result = run_in_worktree(tmp_path, "class T {", "T")

    assert not result.build_ok
    assert "CS1002" in result.output_tail


def test_build_errors_do_not_leak_absolute_worktree_path(tmp_path, monkeypatch):
    out = f"{tmp_path.resolve()}\\tests\\Ledger\\T.cs(1,1): error CS1002: ; expected [{tmp_path.resolve()}\\x.csproj]"
    monkeypatch.setattr(dotnet, "run", FakeDotnet(trx=None, output=out))

    result = run_in_worktree(tmp_path, "class T {", "T")

    assert str(tmp_path.resolve()) not in result.output_tail
    assert "tests\\Ledger\\T.cs(1,1): error CS1002" in result.output_tail


def test_failure_stack_traces_do_not_leak_absolute_worktree_path(tmp_path, monkeypatch):
    trx = (DATA / "pass_fail.trx").read_text(encoding="utf-8").replace(
        "Values differ", f"Values differ at {tmp_path.resolve()}\\src\\TypeCollector.cs:line 1075"
    )
    (tmp_path / "leaky.trx").write_text(trx, encoding="utf-8")
    monkeypatch.setattr(dotnet, "run", FakeDotnet(trx=tmp_path / "leaky.trx"))

    result = run_in_worktree(tmp_path, "class T {}", "T")

    assert str(tmp_path.resolve()) not in result.output_tail
    assert "src\\TypeCollector.cs:line 1075" in result.output_tail


def test_timeout_is_reported_as_build_not_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(dotnet, "run", FakeDotnet(timed_out=True))

    result = run_in_worktree(tmp_path, "class T {}", "T", timeout_s=1)

    assert not result.build_ok
    assert "timeout" in result.output_tail.lower()


def test_runner_uses_side_worktree(settings, fake_dotnet):
    DotnetTestRunner(settings, "2283").run_tests("base", "class T {}", "T")

    _, cwd = fake_dotnet.calls[0]
    assert cwd == settings.work_dir / "2283" / "base"


def test_mutant_runs_in_patched_disposable_worktree(settings, fake_dotnet):
    result = DotnetTestRunner(settings, "2283").run_against_mutant("pr", MUTANT_PATCH, "class T {}", "T")

    _, cwd = fake_dotnet.calls[0]
    assert fake_dotnet.file_txt == "mutant\n"
    assert cwd != settings.work_dir / "2283" / "pr"
    assert not cwd.exists()  # el worktree desechable ya se borró
    assert result.red_for_real


def test_mutant_patch_that_does_not_apply_is_not_run(settings, fake_dotnet):
    result = DotnetTestRunner(settings, "2283").run_against_mutant("pr", "garbage patch", "class T {}", "T")

    assert not result.build_ok
    assert "git apply" in result.output_tail
    assert fake_dotnet.calls == []
