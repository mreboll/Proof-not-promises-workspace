from dataclasses import dataclass, field
from pathlib import Path

import pytest

from ledger.evidence.modal_runner import REMOTE_RESULTS, ModalTestRunner, worktree_dir

DATA = Path(__file__).parent / "data"
TRX = (DATA / "pass_fail.trx").read_text(encoding="utf-8")
SRC_PATCH = "--- a/src/A.cs\n+++ b/src/A.cs\n@@ -1 +1 @@\n-x\n+y\n"


@dataclass
class FakeProcess:
    returncode: int
    out: str = ""
    err: str = ""

    def wait(self) -> int:
        return self.returncode

    @property
    def stdout(self):
        return _Reader(self.out)

    @property
    def stderr(self):
        return _Reader(self.err)


@dataclass
class _Reader:
    text: str

    def read(self) -> str:
        return self.text


@dataclass
class FakeFilesystem:
    files: dict[str, str] = field(default_factory=dict)

    def write_text(self, data: str, remote_path: str) -> None:
        self.files[remote_path] = data

    def read_text(self, remote_path: str) -> str:
        if remote_path not in self.files:
            raise FileNotFoundError(remote_path)
        return self.files[remote_path]


@dataclass
class FakeSandbox:
    """Simula un Sandbox de Modal: registra los comandos y, si `trx`, deja el .trx al ejecutar dotnet test."""

    trx: str | None = TRX
    apply_ok: bool = True
    build_output: str = ""
    commands: list[str] = field(default_factory=list)
    filesystem: FakeFilesystem = field(default_factory=FakeFilesystem)
    terminated: bool = False

    def exec(self, *args: str, timeout: int | None = None, **_kw) -> FakeProcess:
        script = args[-1]
        self.commands.append(script)
        if "git apply" in script and not self.apply_ok:
            return FakeProcess(1, err="error: patch failed: Code.cs:1")
        if "dotnet test" in script:
            if self.trx is not None:
                self.filesystem.files[f"{REMOTE_RESULTS}/ledger.trx"] = self.trx
            return FakeProcess(1, out=self.build_output)
        return FakeProcess(0)

    def terminate(self) -> None:
        self.terminated = True


@dataclass
class FakeFactory:
    sandbox: FakeSandbox
    created: list[dict] = field(default_factory=list)

    def __call__(self, **kwargs) -> FakeSandbox:
        self.created.append(kwargs)
        return self.sandbox


def make_runner(settings, sandbox: FakeSandbox) -> tuple[ModalTestRunner, FakeFactory]:
    factory = FakeFactory(sandbox)
    return ModalTestRunner(settings, "2283", sandbox_factory=factory), factory


def test_runs_test_in_side_worktree_without_network(settings):
    sandbox = FakeSandbox()
    runner, factory = make_runner(settings, sandbox)

    result = runner.run_tests("base", "public class LedgerT {}", "LedgerT")

    assert factory.created[0]["block_network"] is True
    wt = worktree_dir("2283", "base")
    assert sandbox.filesystem.files[f"{wt}/tests/MessagePack.SourceGenerator.Tests/Ledger/LedgerT.cs"] == "public class LedgerT {}"
    test_cmd = next(c for c in sandbox.commands if "dotnet test" in c)
    assert f"cd {wt}" in test_cmd and "--no-restore" in test_cmd and "FullyQualifiedName~LedgerT." in test_cmd
    assert result.red_for_real
    assert sandbox.terminated


def test_previous_ledger_tests_are_removed_before_writing(settings):
    sandbox = FakeSandbox()
    runner, _ = make_runner(settings, sandbox)

    runner.run_tests("pr", "class LedgerT {}", "LedgerT")

    clean = sandbox.commands[0]
    assert "rm -rf" in clean and "Ledger" in clean


def test_build_failure_when_no_trx(settings):
    sandbox = FakeSandbox(trx=None, build_output="/w/2283/pr/tests/Ledger/T.cs(1,1): error CS1002: ; expected")
    runner, _ = make_runner(settings, sandbox)

    result = runner.run_tests("pr", "class LedgerT {", "LedgerT")

    assert not result.build_ok
    assert "CS1002" in result.output_tail
    assert "/w/2283/pr/" not in result.output_tail  # rutas relativas, igual que en local


@pytest.mark.parametrize("bad_name", ["../evil", "a;b", ""])
def test_unsafe_names_never_reach_a_sandbox(settings, bad_name):
    sandbox = FakeSandbox()
    runner, factory = make_runner(settings, sandbox)

    result = runner.run_tests("pr", "class LedgerT {}", bad_name)

    assert not result.build_ok and factory.created == []


def test_mutant_is_applied_in_the_sandbox_before_testing(settings):
    sandbox = FakeSandbox()
    runner, _ = make_runner(settings, sandbox)

    result = runner.run_against_mutant("pr", SRC_PATCH.replace("\n", "\r\n"), "class LedgerT {}", "LedgerT")

    patch_path = next(p for p in sandbox.filesystem.files if p.endswith("mutant.patch"))
    assert "\r" not in sandbox.filesystem.files[patch_path]  # normalizado a LF, como en local
    apply_idx = next(i for i, c in enumerate(sandbox.commands) if "git apply" in c)
    test_idx = next(i for i, c in enumerate(sandbox.commands) if "dotnet test" in c)
    assert apply_idx < test_idx
    assert "--ignore-whitespace" in sandbox.commands[apply_idx]  # reintento tolerante incluido
    assert result.red_for_real


def test_lenient_apply_only_runs_if_strict_fails(settings):
    """`cd X && A || cd X && B` ejecuta B siempre (y falla: el parche ya está aplicado). Hay que agrupar."""
    sandbox = FakeSandbox()
    runner, _ = make_runner(settings, sandbox)

    runner.run_against_mutant("pr", SRC_PATCH, "class LedgerT {}", "LedgerT")

    apply_cmd = next(c for c in sandbox.commands if "git apply" in c)
    strict, lenient = apply_cmd.split("||")
    assert strict.count("&&") == 1 and strict.strip().endswith(".patch")
    assert "&&" not in lenient  # el tolerante solo depende del fallo del estricto
    assert "{" in strict and lenient.strip().endswith("}")


def test_mutant_that_does_not_apply_is_not_tested(settings):
    sandbox = FakeSandbox(apply_ok=False)
    runner, _ = make_runner(settings, sandbox)

    result = runner.run_against_mutant("pr", SRC_PATCH, "class LedgerT {}", "LedgerT")

    assert not result.build_ok and "git apply" in result.output_tail
    assert not any("dotnet test" in c for c in sandbox.commands)
    assert sandbox.terminated


def test_sandbox_is_terminated_even_if_exec_raises(settings):
    class Exploding(FakeSandbox):
        def exec(self, *args, **kw):
            raise RuntimeError("modal down")

    sandbox = Exploding()
    runner, _ = make_runner(settings, sandbox)

    result = runner.run_tests("pr", "class LedgerT {}", "LedgerT")

    assert not result.build_ok and "modal down" in result.output_tail
    assert sandbox.terminated


def test_mutant_outside_product_source_never_reaches_a_sandbox(settings):
    sandbox = FakeSandbox()
    runner, factory = make_runner(settings, sandbox)

    evil = SRC_PATCH.replace("src/A.cs", "tests/X/LedgerT.cs")
    result = runner.run_against_mutant("pr", evil, "class LedgerT {}", "LedgerT")

    assert not result.build_ok and "mutant" in result.output_tail.lower()
    assert factory.created == []


def test_unknown_issue_never_reaches_a_sandbox(settings):
    sandbox = FakeSandbox()
    factory = FakeFactory(sandbox)
    runner = ModalTestRunner(settings, "2283; rm -rf /", sandbox_factory=factory)

    result = runner.run_tests("pr", "class LedgerT {}", "LedgerT")

    assert not result.build_ok and "issue" in result.output_tail.lower()
    assert factory.created == []
