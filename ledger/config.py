"""Configuración compartida: ramas, tipo de cambio por issue y rutas. CONJUNTO."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from ledger.models import ChangeType

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class IssueSpec:
    issue_id: str
    branch: str
    change_type: ChangeType
    summary: str


# La base de cada rama es su commit padre (`<rama>~1`, hoy 32258fdb en las cuatro).
ISSUES: dict[str, IssueSpec] = {
    spec.issue_id: spec
    for spec in (
        IssueSpec("2283", "ju26-issue-2283", ChangeType.BUGFIX, "Generator and analyzer crash with IndexOutOfRangeException on a closed generic struct from a referenced assembly"),
        IssueSpec("2234", "ju26-issue-2234", ChangeType.BUGFIX, "Analyzer does not work if SuppressSourceGeneration = true"),
        IssueSpec("2129", "ju26-issue-2129", ChangeType.FEATURE, "Generate formatters for types in referenced assemblies"),
        IssueSpec("2297", "ju26-issue-2297", ChangeType.FEATURE, "Add ExcludeFromCodeCoverage to generated code"),
    )
}


@dataclass(frozen=True)
class Settings:
    msgpack_repo: Path
    work_dir: Path
    cache_dir: Path
    out_dir: Path
    issues_dir: Path
    gemini_api_key: str
    model_pro: str
    model_flash: str
    nvidia_api_key: str
    nvidia_model: str
    nvidia_base_url: str
    nvidia_model_fast: str
    # Mientras no haya créditos de Gemini: los roles "pro" y "flash" también van a Nemotron.
    nvidia_for_all: bool
    runner: str  # "local" (dotnet en esta máquina) | "modal" (Modal Sandboxes)

    def ref(self, issue_id: str, side: str) -> str:
        branch = f"origin/{get_issue(issue_id).branch}"
        return branch if side == "pr" else f"{branch}~1"


def get_issue(issue_id: str) -> IssueSpec:
    try:
        return ISSUES[issue_id]
    except KeyError as exc:
        known = ", ".join(sorted(ISSUES))
        raise ValueError(f"Issue desconocido '{issue_id}'. Conocidos: {known}") from exc


def _resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def load_settings() -> Settings:
    return Settings(
        msgpack_repo=_resolve(os.environ.get("MSGPACK_REPO", "../junction26-messagepack-csharp")),
        work_dir=PROJECT_ROOT / ".work",
        cache_dir=PROJECT_ROOT / ".cache",
        out_dir=PROJECT_ROOT / "out",
        issues_dir=PROJECT_ROOT / "issues",
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        # gemini-2.5-* ya no está disponible para claves nuevas (404); estos son los modelos con los que se ejecutó.
        model_pro=os.environ.get("GEMINI_MODEL_PRO", "gemini-4-hydrogen"),
        model_flash=os.environ.get("GEMINI_MODEL_FLASH", "gemini-3.8-flash"),
        nvidia_api_key=os.environ.get("NVIDIA_API_KEY", ""),
        nvidia_model=os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"),
        nvidia_base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        nvidia_model_fast=os.environ.get("NVIDIA_MODEL_FAST", "nvidia/nemotron-3.5-lightning-30b-a3b"),
        nvidia_for_all=os.environ.get("LEDGER_NVIDIA_FOR_ALL", "0").strip().lower() in {"1", "true", "yes"},
        runner=os.environ.get("LEDGER_RUNNER", "local"),
    )
