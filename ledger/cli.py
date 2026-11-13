"""CLI: `python -m ledger run --issue 2283` y `python -m ledger llm-ping`."""

from __future__ import annotations

import typer
from pydantic import BaseModel

from ledger import llm, pipeline
from ledger.config import load_settings
from ledger.fakes import FakeTestRunner

app = typer.Typer(no_args_is_help=True, add_completion=False)


class _Pong(BaseModel):
    reply: str


ROLES = ("pro", "flash", "fiscal")


@app.command("llm-ping")
def llm_ping(role: str = typer.Option("all", help="pro | flash | fiscal | all")) -> None:
    """Comprueba claves y modelos (Gemini y Nemotron) con salida estructurada, sin caché."""
    roles = ROLES if role == "all" else (role,)
    failed = False
    for current in roles:
        try:
            pong = llm.complete("Answer in JSON.", "Reply with the word pong.", _Pong, current, use_cache=False)  # type: ignore[arg-type]
            typer.secho(f"OK   {current:<6} {pong.reply}", fg=typer.colors.GREEN)
        except llm.LLMError as exc:
            failed = True
            typer.secho(f"FAIL {current:<6} {exc}", fg=typer.colors.RED)
    if failed:
        raise typer.Exit(code=1)


@app.command()
def run(
    issue: str = typer.Option(..., help="2283 | 2234 | 2129 | 2297"),
    fixtures: bool = typer.Option(False, help="Usa fixtures/ en vez de las etapas reales"),
    fake_runner: bool = typer.Option(False, help="Usa FakeTestRunner en vez de dotnet"),
) -> None:
    """Ejecuta el embudo completo y escribe el informe en out/."""
    settings = load_settings()
    if fake_runner:
        runner = FakeTestRunner()
    elif settings.runner == "modal":
        from ledger.evidence.modal_runner import ModalTestRunner  # entrega de la Línea A (bounty Modal)

        runner = ModalTestRunner(settings, issue)
    else:
        from ledger.evidence.dotnet import DotnetTestRunner  # entrega de la Línea A

        runner = DotnetTestRunner(settings, issue)
    try:
        path = pipeline.run(issue, settings, runner, use_fixtures=fixtures)
    except (NotImplementedError, ValueError) as exc:
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    typer.secho(f"Informe: {path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
