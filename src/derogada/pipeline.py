"""Pipeline completo: documento -> informe de vigencia."""

from __future__ import annotations

from pathlib import Path

from derogada.check.status import verificar_cita
from derogada.extract import extraer_citas
from derogada.ingest import cargar_documento
from derogada.models import Informe
from derogada.resolve.resolver import resolver_cita
from derogada.sources import BoeClient, Cache, CellarClient


def analizar_documento(
    ruta: str | Path,
    *,
    usar_llm: bool = True,
    modelo: str | None = None,
    con_sugerencias: bool = True,
    cache: Cache | None = None,
) -> Informe:
    """Analiza un documento (.txt/.md/.docx/.pdf) y devuelve el informe de vigencia."""
    texto = cargar_documento(ruta)
    return analizar_texto(
        texto,
        documento=str(ruta),
        usar_llm=usar_llm,
        modelo=modelo,
        con_sugerencias=con_sugerencias,
        cache=cache,
    )


def analizar_texto(
    texto: str,
    *,
    documento: str = "<texto>",
    usar_llm: bool = True,
    modelo: str | None = None,
    con_sugerencias: bool = True,
    cache: Cache | None = None,
) -> Informe:
    """Pipeline: extraer -> resolver -> verificar -> sugerir."""
    cache = cache or Cache()
    citas = extraer_citas(texto, usar_llm=usar_llm, modelo=modelo)
    informe = Informe(documento=documento)
    with BoeClient(cache=cache) as boe, CellarClient(cache=cache) as cellar:
        for cita in citas:
            resolucion = resolver_cita(cita, boe, cellar)
            informe.resultados.append(verificar_cita(cita, resolucion, boe, cellar))
    if con_sugerencias:
        from derogada.suggest.rewrite import proponer_sugerencias

        proponer_sugerencias(informe, modelo=modelo)
    return informe
