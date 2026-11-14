"""Fixtures de la Línea A: un repo git diminuto que imita las ramas del reto."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from ledger.config import Settings, load_settings


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


@pytest.fixture
def fake_repo(tmp_path: Path) -> dict[str, str | Path]:
    """Repo con `origin/ju26-issue-2283` = base + 1 commit, como en el reto."""
    repo = tmp_path / "msgpack"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "ledger@example.invalid")
    _git(repo, "config", "user.name", "ledger")
    (repo / "file.txt").write_text("base\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "Mutable.cs").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "file.txt").write_text("pr\n", encoding="utf-8")
    (repo / "src" / "Mutable.cs").write_text("pr\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "fix")
    pr = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/ju26-issue-2283", pr)
    return {"repo": repo, "base": base, "pr": pr}


@pytest.fixture
def settings(tmp_path: Path, fake_repo: dict[str, str | Path]) -> Settings:
    return replace(load_settings(), msgpack_repo=Path(fake_repo["repo"]), work_dir=tmp_path / "work")


def head_of(path: Path) -> str:
    return _git(path, "rev-parse", "HEAD")
