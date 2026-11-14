from pathlib import Path

from conftest import head_of

from ledger.evidence.workspace import disposable_worktree, ensure_worktree


def test_ensure_worktree_checks_out_base_and_pr(settings, fake_repo):
    base = ensure_worktree(settings, "2283", "base")
    pr = ensure_worktree(settings, "2283", "pr")

    assert base == settings.work_dir / "2283" / "base"
    assert head_of(base) == fake_repo["base"]
    assert head_of(pr) == fake_repo["pr"]
    assert (pr / "file.txt").read_text(encoding="utf-8") == "pr\n"


def test_ensure_worktree_is_idempotent_and_keeps_build_outputs(settings):
    first = ensure_worktree(settings, "2283", "pr")
    (first / "obj").mkdir()
    (first / "obj" / "cache.bin").write_text("x", encoding="utf-8")

    second = ensure_worktree(settings, "2283", "pr")

    assert second == first
    assert (second / "obj" / "cache.bin").exists()


def test_ensure_worktree_resets_tracked_changes(settings):
    path = ensure_worktree(settings, "2283", "pr")
    (path / "file.txt").write_text("dirty\n", encoding="utf-8")

    ensure_worktree(settings, "2283", "pr")

    assert (path / "file.txt").read_text(encoding="utf-8") == "pr\n"


def test_ensure_worktree_recovers_when_directory_was_deleted(settings, fake_repo):
    import shutil

    path = ensure_worktree(settings, "2283", "base")
    shutil.rmtree(path)

    again = ensure_worktree(settings, "2283", "base")

    assert head_of(again) == fake_repo["base"]


def test_disposable_worktree_is_removed_on_exit(settings, fake_repo):
    with disposable_worktree(settings, "2283", "pr") as path:
        assert head_of(path) == fake_repo["pr"]
        captured: Path = path

    assert not captured.exists()


def test_disposable_worktree_is_removed_even_on_error(settings):
    captured: list[Path] = []
    try:
        with disposable_worktree(settings, "2283", "base") as path:
            captured.append(path)
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert not captured[0].exists()


def test_two_disposable_worktrees_do_not_collide(settings):
    with disposable_worktree(settings, "2283", "pr") as a, disposable_worktree(settings, "2283", "pr") as b:
        assert a != b
