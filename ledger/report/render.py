"""Informe HTML (B): estático, imprimible y autocontenido (sin CDN ni JS: se abre sin red en la demo).

Orden pensado para quien firma: primero la decisión y SOLO lo que tiene que leer (amarillo y rojo);
después la evidencia que respalda lo verde, el interrogatorio y el bloque de firma (ARQUITECTURA §3).
Junto al HTML se escribe el JSON del `Report`, para procesarlo a máquina.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ledger.models import FragmentVerdict, Report, TestRunResult, Verdict

TEMPLATES = Path(__file__).parent / "templates"
ROLES = {
    "flash": "Triaje de alcance IN/OUT por fichero",
    "pro": "Test independiente del cambio, Defensor y mutantes",
    "fiscal": "Fiscal: objeciones del interrogatorio",
}
VERDICT_LABEL = {Verdict.GREEN: "Verde", Verdict.YELLOW: "Amarillo", Verdict.RED: "Rojo"}

_env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)


def overall_decision(verdicts: tuple[FragmentVerdict, ...]) -> tuple[str, str, str]:
    """(título, explicación, clase CSS) según el peor veredicto."""
    kinds = {v.verdict for v in verdicts}
    if not kinds:
        return "Sin veredictos", "La Etapa 3 no se ha ejecutado: el informe solo muestra el triaje y la evidencia.", "none"
    if Verdict.RED in kinds:
        return "Auditoría manual obligatoria", "Hay fragmentos en rojo: revisa a mano esas líneas antes de aprobar.", "red"
    if Verdict.YELLOW in kinds:
        return "Revisión focalizada", "La evidencia cubre el comportamiento; solo hay que revisar los fragmentos en amarillo.", "yellow"
    return "Aprobable con evidencia", "Todos los fragmentos están respaldados por pruebas ejecutables. No hace falta leer el código.", "green"


def run_label(result: TestRunResult | None) -> str:
    if result is None:
        return "no ejecutado"
    if not result.build_ok:
        return "no compila"
    if result.green:
        return f"verde · {result.passed} ok"
    if result.red_for_real:
        return f"rojo · {result.failed} fallan"
    return "sin tests"


def run_class(result: TestRunResult | None) -> str:
    if result is None or not result.build_ok:
        return "muted"
    return "green" if result.green else "red" if result.red_for_real else "muted"


def render_html(report: Report, *, models: dict[str, str], issue_title: str) -> str:
    verdict_by_path = {v.path: v for v in report.verdicts}
    counts = {k: sum(v.verdict is k for v in report.verdicts) for k in Verdict}
    total = len(report.verdicts)
    title, explanation, css = overall_decision(report.verdicts)
    return _env.get_template("report.html.j2").render(
        r=report,
        issue_title=issue_title,
        decision=title,
        decision_text=explanation,
        decision_class=css,
        counts=counts,
        total=total,
        must_read=[v for v in report.verdicts if v.verdict is not Verdict.GREEN],
        rows=[(t, verdict_by_path.get(t.path)) for t in report.triage],
        crossexam=[v for v in report.verdicts if v.objections],
        models=[(role, models.get(role, "?"), task) for role, task in ROLES.items()],
        same_family=models.get("pro") == models.get("fiscal"),
        Verdict=Verdict,
        VERDICT_LABEL=VERDICT_LABEL,
        run_label=run_label,
        run_class=run_class,
    )


def write_report(report: Report, out_dir: Path, *, models: dict[str, str], issue_title: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"report-{report.issue_id}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    target = out_dir / f"report-{report.issue_id}.html"
    target.write_text(render_html(report, models=models, issue_title=issue_title), encoding="utf-8")
    return target


def render_report(report: Report, out_dir: Path) -> Path:
    """Punto de entrada del pipeline: resuelve los modelos de cada rol y el título real del issue."""
    from ledger import llm
    from ledger.config import load_settings

    settings = load_settings()
    models = {role: llm.model_for(role, settings) for role in ROLES}  # type: ignore[arg-type]
    issue_file = settings.issues_dir / f"{report.issue_id}.md"
    first_line = issue_file.read_text(encoding="utf-8").splitlines()[0] if issue_file.exists() else ""
    issue_title = first_line.removeprefix("# ").strip() or f"#{report.issue_id}"  # "# #2283: ..." → "#2283: ..."
    return write_report(report, out_dir, models=models, issue_title=issue_title)
