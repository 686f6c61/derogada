"""Render del informe a Markdown."""

from __future__ import annotations

from derogada import __version__
from derogada.models import Informe


def render_markdown(informe: Informe) -> str:
    """Informe en Markdown: cabecera con aviso legal, ficha por cita y resumen."""
    r = informe.resumen
    lineas = [
        f"# Informe de vigencia normativa: {informe.documento}",
        "",
        f"_Generado: {informe.generado:%d/%m/%Y %H:%M} · derogada {__version__}_",
        "",
        f"> ⚠️ {informe.aviso}",
        "",
        (
            f"**Resumen:** {r.total} citas · {r.derogadas} derogadas · "
            f"{r.modificadas} modificadas · {r.vigentes} vigentes · "
            f"{r.vigencia_agotada} vigencia agotada · {r.no_resueltas} no resueltas · "
            f"{r.no_encontradas} no encontradas"
        ),
        "",
        "---",
        "",
    ]
    for i, res in enumerate(informe.resultados, 1):
        lineas.append(f"## {i}. [{res.estado.value}] {res.cita.texto}")
        lineas.append("")
        if res.cita.articulo:
            lineas.append(f"- **Artículo citado:** {res.cita.articulo}")
        if res.norma:
            lineas.append(f"- **Norma:** `{res.norma.identificador}` ({res.norma.fuente})")
            if res.norma.titulo:
                lineas.append(f"- **Título:** {res.norma.titulo}")
            if res.norma.url:
                lineas.append(f"- **Fuente:** {res.norma.url}")
        if res.derogada_por:
            lineas.append(
                f"- **Derogada por:** `{res.derogada_por.identificador}` · {res.derogada_por.url}"
            )
        for m in res.modificada_por:
            lineas.append(f"- **Modificada por:** `{m.identificador}` · {m.url}")
        if res.nota:
            lineas.append(f"- **Nota:** {res.nota}")
        if res.candidatos:
            lineas.append("- **Candidatos:**")
            for c in res.candidatos:
                lineas.append(f"  - `{c.identificador}` {c.titulo or ''} · {c.url or ''}")
        if res.sugerencia:
            lineas.append(f"- ✏️ **Propuesta:** {res.sugerencia}")
        if res.cita.contexto:
            lineas.append(f"- **Contexto:** “{res.cita.contexto}”")
        lineas.append("")
    return "\n".join(lineas)
