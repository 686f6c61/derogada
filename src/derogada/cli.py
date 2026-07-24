"""Interfaz de línea de comandos de derogada."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from derogada import __version__
from derogada.models import EstadoCita, Informe

app = typer.Typer(
    name="derogada",
    help="Detecta normas derogadas o modificadas en documentos jurídicos (BOE + EUR-Lex).",
    no_args_is_help=True,
)
console = Console()

_COLORES = {
    EstadoCita.VIGENTE: "green",
    EstadoCita.MODIFICADA: "yellow",
    EstadoCita.DEROGADA: "red",
    EstadoCita.VIGENCIA_AGOTADA: "red",
    EstadoCita.NO_RESUELTA: "magenta",
    EstadoCita.NO_ENCONTRADA: "cyan",
}


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"derogada {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Muestra la versión y sale.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Punto de entrada de la CLI."""


@app.command()
def check(
    documento: Annotated[
        Path,
        typer.Argument(exists=True, readable=True, help="Documento (.txt/.md/.docx/.pdf)"),
    ],
    formato: Annotated[
        str, typer.Option("--format", "-f", help="Salida: md | json | tabla")
    ] = "md",
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Fichero de salida (por defecto, stdout)")
    ] = None,
    modelo: Annotated[
        str | None, typer.Option("--model", help="Modelo LiteLLM (sobreescribe DEROGADA_MODEL)")
    ] = None,
    sin_llm: Annotated[bool, typer.Option("--no-llm", help="Solo canal regex, sin LLM")] = False,
    sin_sugerencias: Annotated[
        bool, typer.Option("--no-sugerencias", help="No generar propuestas de cambio")
    ] = False,
) -> None:
    """Analiza un documento y verifica la vigencia de cada cita normativa."""
    from derogada.pipeline import analizar_documento
    from derogada.report import render_json, render_markdown

    try:
        informe = analizar_documento(
            documento,
            usar_llm=not sin_llm,
            modelo=modelo,
            con_sugerencias=not sin_sugerencias,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if formato == "tabla":
        _imprimir_tabla(informe)
        return

    salida = render_json(informe) if formato == "json" else render_markdown(informe)
    if out:
        out.write_text(salida, encoding="utf-8")
        console.print(f"[green]Informe escrito en {out}")
    else:
        typer.echo(salida)


def _imprimir_tabla(informe: Informe) -> None:
    tabla = Table(title=f"Informe de vigencia: {informe.documento}")
    tabla.add_column("#", justify="right")
    tabla.add_column("Cita", max_width=42)
    tabla.add_column("Art.")
    tabla.add_column("Estado")
    tabla.add_column("Norma / fuente")
    for i, res in enumerate(informe.resultados, 1):
        color = _COLORES.get(res.estado, "white")
        norma = ""
        if res.derogada_por:
            norma = f"derogada por {res.derogada_por.identificador}"
        elif res.norma:
            norma = res.norma.identificador
        tabla.add_row(
            str(i),
            res.cita.texto,
            res.cita.articulo or "-",
            f"[{color}]{res.estado.value}[/{color}]",
            norma,
        )
    console.print(tabla)
    r = informe.resumen
    console.print(
        f"{r.total} citas · [red]{r.derogadas} derogadas[/red] · "
        f"[yellow]{r.modificadas} modificadas[/yellow] · [green]{r.vigentes} vigentes[/green] · "
        f"{r.vigencia_agotada} agotadas · {r.no_resueltas} no resueltas · "
        f"{r.no_encontradas} no encontradas"
    )


@app.command()
def norma(
    identificador: Annotated[
        str, typer.Argument(help="BOE-A-AAAA-NNNNN (BOE) o CELEX (EUR-Lex)")
    ],
) -> None:
    """Consulta el estado de una norma concreta en la fuente oficial."""
    from derogada.check.status import verificar_cita
    from derogada.models import Cita, Jurisdiccion
    from derogada.resolve.resolver import Resolucion
    from derogada.sources import BoeClient, CellarClient

    es_boe = identificador.upper().startswith("BOE-")
    cita = Cita(
        texto=identificador,
        jurisdiccion=Jurisdiccion.ES if es_boe else Jurisdiccion.UE,
    )
    resolucion = Resolucion(
        identificador=identificador,
        fuente="BOE" if es_boe else "EUR-Lex",
    )
    with BoeClient() as boe, CellarClient() as cellar:
        resultado = verificar_cita(cita, resolucion, boe, cellar)
    color = _COLORES.get(resultado.estado, "white")
    console.print(f"[bold]{identificador}[/bold]: [{color}]{resultado.estado.value}[/{color}]")
    if resultado.norma and resultado.norma.titulo:
        console.print(f"  {resultado.norma.titulo}")
    if resultado.nota:
        console.print(f"  {resultado.nota}")
    if resultado.derogada_por:
        console.print(f"  Derogada por: {resultado.derogada_por.identificador}")
    if resultado.norma and resultado.norma.url:
        console.print(f"  {resultado.norma.url}")


cache_app = typer.Typer(help="Gestión de la caché local de respuestas de las APIs.")
app.add_typer(cache_app, name="cache")


@cache_app.command("clear")
def cache_clear() -> None:
    """Vacía la caché local."""
    from derogada.sources import Cache

    borradas = Cache().clear()
    console.print(f"[green]Caché vaciada ({borradas} entradas).")
