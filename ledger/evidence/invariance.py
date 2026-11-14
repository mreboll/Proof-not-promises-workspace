"""Invarianza de generación (decision-log D2): el PR no cambia el código generado ni los
diagnósticos fuera del caso del issue.

`harness/GeneratorProbe` se copia y compila DENTRO de cada worktree (cada proceso carga su propia
versión del generador, D3) y escribe `<out>/<case>.txt` por cada snippet de `harness/corpus/`.
Aquí se ejecuta la base dos veces (control de determinismo) y el PR una, y se comparan SHA-256.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ledger.config import PROJECT_ROOT, Settings
from ledger.evidence._proc import DEFAULT_TIMEOUT_S, run
from ledger.evidence.workspace import ensure_worktree
from ledger.models import InvarianceCase, InvarianceEvidence, Side

_PROBE_RUNS: tuple[tuple[Side, tuple[str, ...]], ...] = (("base", ("base", "base-rerun")), ("pr", ("pr",)))

HARNESS_DIR = PROJECT_ROOT / "harness"
PROBE_SRC = HARNESS_DIR / "GeneratorProbe"
CORPUS_DIR = HARNESS_DIR / "corpus"
PROBE_IN_WORKTREE = Path(".ledger-probe")
EXCLUDE_FROM_COVERAGE = "[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]"
_TAG_HEADER = re.compile(r"^//@tag:\s*(general|issue-\d+)\s*$", re.MULTILINE)
_PROBE_COPY_IGNORE = shutil.ignore_patterns("bin", "obj")


class InvarianceError(RuntimeError):
    pass


@dataclass(frozen=True)
class CorpusCase:
    id: str
    tag: str  # "general" o "issue-<id>"


@dataclass(frozen=True)
class Normalization:
    """Transformación DECLARADA que el PR introduce a propósito en todo el código generado."""

    description: str
    apply: Callable[[str], str]


_COVERAGE_GUARD_IF = "#if !NETSTANDARD2_0 && !NETFRAMEWORK"
_COVERAGE_GUARD_END = "#endif"


def _drop_exclude_from_coverage(text: str) -> str:
    """Quita el atributo de #2297 tal y como lo emite el PR: dentro de
    `#if !NETSTANDARD2_0 && !NETFRAMEWORK` / `#endif` (el bloque entero) o como línea suelta.
    Cualquier otro `#if` o cambio queda intacto."""
    lines = text.splitlines(keepends=True)
    kept: list[str] = []
    i = 0
    while i < len(lines):
        window = [line.strip() for line in lines[i : i + 3]]
        if window == [_COVERAGE_GUARD_IF, EXCLUDE_FROM_COVERAGE, _COVERAGE_GUARD_END]:
            i += 3
            continue
        if window[0] != EXCLUDE_FROM_COVERAGE:
            kept.append(lines[i])
        i += 1
    return "".join(kept)


_NORMALIZATIONS: dict[str, Normalization] = {
    "2297": Normalization(
        f"removed {EXCLUDE_FROM_COVERAGE} lines and their `{_COVERAGE_GUARD_IF}`/`{_COVERAGE_GUARD_END}` "
        "guard blocks (feature #2297)",
        _drop_exclude_from_coverage,
    ),
}


def normalization_for(issue_id: str) -> Normalization | None:
    return _NORMALIZATIONS.get(issue_id)


def load_corpus(corpus_dir: Path = CORPUS_DIR) -> tuple[CorpusCase, ...]:
    cases = []
    for path in sorted(corpus_dir.glob("*.cs")):
        match = _TAG_HEADER.search(path.read_text(encoding="utf-8"))
        if not match:
            raise InvarianceError(f"{path.name}: falta la cabecera '//@tag: general|issue-<id>'")
        cases.append(CorpusCase(path.stem, match.group(1)))
    return tuple(cases)


def canonical_hash(text: str, normalization: Normalization | None = None) -> str:
    canonical = text.replace("\r\n", "\n")
    if normalization is not None:
        canonical = normalization.apply(canonical)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_evidence(
    cases: tuple[CorpusCase, ...],
    base: Mapping[str, str],
    base_rerun: Mapping[str, str],
    pr: Mapping[str, str],
    normalization: Normalization | None = None,
) -> InvarianceEvidence:
    """La normalización solo se aplica al PR de los casos `general`: los casos del issue se comparan
    en bruto, porque ahí es donde el cambio tiene que verse."""
    missing = [c.id for c in cases if not all(c.id in side for side in (base, base_rerun, pr))]
    if missing:
        raise InvarianceError(f"el probe no produjo salida para: {', '.join(missing)}")

    def to_case(case: CorpusCase) -> InvarianceCase:
        norm = normalization if case.tag == "general" else None
        return InvarianceCase(
            id=case.id,
            tag=case.tag,
            base_hash=canonical_hash(base[case.id]),
            base_hash_rerun=canonical_hash(base_rerun[case.id]),
            pr_hash=canonical_hash(pr[case.id], norm),
            normalization=norm.description if norm else "",
        )

    return InvarianceEvidence(cases=tuple(to_case(c) for c in cases))


# --------------------------------------------------------------------------- ejecución real (dotnet)


def install_probe(worktree: Path) -> Path:
    """Copia el probe al worktree (sin bin/obj) y devuelve la ruta de su .csproj."""
    target = worktree / PROBE_IN_WORKTREE
    target.mkdir(exist_ok=True)
    # Ficheros MSBuild vacíos: cortan la herencia del repo (StyleCop, CPM, rutas de bin/obj).
    for name in ("Directory.Build.props", "Directory.Build.targets", "Directory.Packages.props"):
        shutil.copy(HARNESS_DIR / "isolation" / name, target / name)
    shutil.copytree(PROBE_SRC, target / "GeneratorProbe", ignore=_PROBE_COPY_IGNORE, dirs_exist_ok=True)
    return target / "GeneratorProbe" / "GeneratorProbe.csproj"


def build_probe(worktree: Path, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> Path:
    project = install_probe(worktree)
    proc = run(["dotnet", "build", str(project), "-c", "Release", "-nologo"], worktree, timeout_s=timeout_s)
    if not proc.ok:
        raise InvarianceError(f"no compila GeneratorProbe en {worktree.name}:\n{proc.combined[-3000:]}")
    return project


def run_probe(worktree: Path, project: Path, corpus_dir: Path, out_dir: Path, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, str]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    cmd = ["dotnet", "run", "--project", str(project), "-c", "Release", "--no-build", "--", str(corpus_dir), str(out_dir)]
    proc = run(cmd, worktree, timeout_s=timeout_s)
    if not proc.ok:
        raise InvarianceError(f"GeneratorProbe falló en {worktree.name}:\n{proc.combined[-3000:]}")
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(out_dir.glob("*.txt"))}


def collect_invariance(settings: Settings, issue_id: str, corpus_dir: Path = CORPUS_DIR) -> InvarianceEvidence:
    cases = load_corpus(corpus_dir)
    out_root = settings.work_dir / issue_id / "probe-out"
    outputs: dict[str, dict[str, str]] = {}
    for side, runs in _PROBE_RUNS:
        worktree = ensure_worktree(settings, issue_id, side)
        project = build_probe(worktree)
        for label in runs:
            outputs[label] = run_probe(worktree, project, corpus_dir, out_root / label)
    return build_evidence(cases, outputs["base"], outputs["base-rerun"], outputs["pr"], normalization_for(issue_id))


__all__ = [
    "CorpusCase",
    "InvarianceError",
    "Normalization",
    "build_evidence",
    "canonical_hash",
    "collect_invariance",
    "load_corpus",
    "normalization_for",
]
