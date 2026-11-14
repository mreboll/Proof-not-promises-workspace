"""Informe HTML (B): estático, imprimible y autocontenido (sin CDN ni JS: se abre sin red en la demo).

Orden pensado para quien firma: primero la decisión y SOLO lo que tiene que leer (amarillo y rojo);
después la evidencia que respalda lo verde, el interrogatorio y el bloque de firma (ARQUITECTURA §3).
Junto al HTML se escribe el JSON del `Report`, para procesarlo a máquina.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ledger.models import ChangeTestEvidence, ChangeType, FragmentVerdict, Report, Risk, Scope, TestRunResult, Verdict

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


def base_view(ct: ChangeTestEvidence | None) -> tuple[str, str, str]:
    """(etiqueta, clase CSS, nota) del resultado en la BASE, que se lee distinto en bug fix y en feature.

    Bug fix: el test tiene que fallar en la base (reproduce el bug). Feature: el resultado en la base es
    evidencia extra (A lo ejecuta desde 6211a32); rojo allí es bueno: el test mide algo que antes no existía.
    """
    if ct is None or ct.base is None:
        return "no ejecutado", "muted", ""
    base = ct.base
    if ct.change_type is ChangeType.FEATURE:
        if base.red_for_real:
            return "rojo en base: el test mide algo nuevo", "none", ""
        if base.green:
            return "verde en base", "muted", "El test pasa también sin la feature: no demuestra que mida algo nuevo (el veredicto solo depende del PR)."
        return run_label(base), "muted", ""
    if base.green:
        return run_label(base), "yellow", "El test pasa también en la base: no reproduce el bug, así que no cuenta como evidencia."
    if not base.build_ok:
        return run_label(base), "muted", "No compila en la base: un fallo de compilación no cuenta como reproducir el bug."
    return run_label(base), run_class(base), ""


def _normalizations(report: Report) -> list[tuple[str, int]]:
    if not report.invariance:
        return []
    return sorted(Counter(c.normalization for c in report.invariance.cases if c.normalization).items())


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


def funnel(report: Report) -> list[dict[str, str]]:
    """Una línea por etapa del embudo (T3 → T1 → T2) para la tira de la cabecera."""
    triage = report.triage
    out = sum(t.scope is Scope.OUT for t in triage)
    high = sum(t.risk is Risk.HIGH for t in triage)
    stage1 = {"id": "T3", "name": "Triaje", "status": "done",
              "lines": [_plural(len(triage), "fichero"), f"{out} fuera de alcance", f"{high} de riesgo alto"]}

    ct, inv = report.change_test, report.invariance
    ev_lines = [
        "sin test del cambio" if ct is None else ("test del cambio superado" if ct.ok else "test del cambio no superado"),
        "sin invarianza" if inv is None else ("invarianza superada" if inv.ok else "invarianza no superada"),
    ]
    ev_ok = bool(ct and ct.ok and inv and inv.ok)
    stage2 = {"id": "T1", "name": "Evidencia", "status": "pass" if ev_ok else "fail", "lines": ev_lines}

    objections = [o for v in report.verdicts for o in v.objections]
    valid = sum(o.valid for o in objections)
    defects = sum((not o.valid) and o.pr_result is not None and o.pr_result.red_for_real for o in objections)
    if objections:
        x_lines = [_plural(len(objections), "objeción", "objeciones"), _plural(valid, "cerrada", "cerradas") + " con test válido"]
        if defects:
            x_lines.append(_plural(defects, "posible defecto", "posibles defectos") + " en el PR")
        status = "pass" if valid == len(objections) else "fail"
    else:
        refused = sum(v.reasons[0].startswith("M7") for v in report.verdicts if v.reasons)
        x_lines = ["sin objeciones" if not refused else "no ejecutado"]
        status = "idle" if not refused else "fail"
    stage3 = {"id": "T2", "name": "Interrogatorio", "status": status, "lines": x_lines}
    return [stage1, stage2, stage3]


def render_html(report: Report, *, models: dict[str, str], issue_title: str) -> str:
    verdict_by_path = {v.path: v for v in report.verdicts}
    rows = [(t, verdict_by_path.get(t.path)) for t in report.triage]
    green_rows = [(t, v) for t, v in rows if v is not None and v.verdict is Verdict.GREEN]
    attention_rows = [(t, v) for t, v in rows if v is None or v.verdict is not Verdict.GREEN]
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
        attention_rows=attention_rows,
        green_rows=green_rows,
        funnel=funnel(report),
        crossexam=[v for v in report.verdicts if v.objections],
        models=[(role, models.get(role, "?"), task) for role, task in ROLES.items()],
        models_by_role={role: models.get(role, "?") for role in ROLES},
        same_family=models.get("pro") == models.get("fiscal"),
        Verdict=Verdict,
        VERDICT_LABEL=VERDICT_LABEL,
        run_label=run_label,
        run_class=run_class,
        base_view=base_view(report.change_test),
        normalizations=_normalizations(report),
    )


def write_report(report: Report, out_dir: Path, *, models: dict[str, str], issue_title: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"report-{report.issue_id}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    target = out_dir / f"report-{report.issue_id}.html"
    target.write_text(render_html(report, models=models, issue_title=issue_title), encoding="utf-8")
    return target


def _context(issue_id: str) -> tuple[dict[str, str], str]:
    """Modelos de cada rol según la configuración ACTUAL (.env) y título real del issue."""
    from ledger import llm
    from ledger.config import load_settings

    settings = load_settings()
    models = {role: llm.model_for(role, settings) for role in ROLES}  # type: ignore[arg-type]
    issue_file = settings.issues_dir / f"{issue_id}.md"
    first_line = issue_file.read_text(encoding="utf-8").splitlines()[0] if issue_file.exists() else ""
    issue_title = first_line.removeprefix("# ").strip() or f"#{issue_id}"  # "# #2283: ..." → "#2283: ..."
    return models, issue_title


def render_report(report: Report, out_dir: Path) -> Path:
    """Punto de entrada del pipeline: resuelve los modelos de cada rol y el título real del issue."""
    models, issue_title = _context(report.issue_id)
    return write_report(report, out_dir, models=models, issue_title=issue_title)


def main(argv: list[str]) -> Path:
    """Re-renderiza el HTML desde el JSON de un informe (p. ej. el de una ejecución con dotnet real):

        python -m ledger.report.render out/report-2283.json

    Ojo: los modelos se toman del .env actual. Si la ejecución usó otros (p. ej. LEDGER_NVIDIA_FOR_ALL=1),
    ejecútalo con la misma configuración para que la tabla de modelos diga la verdad.
    """
    source = Path(argv[0])
    report = Report.model_validate_json(source.read_text(encoding="utf-8"))
    models, issue_title = _context(report.issue_id)
    target = write_report(report, source.parent, models=models, issue_title=issue_title)
    print(target)
    return target


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
