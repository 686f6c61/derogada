"""Fusión de los canales de extracción (regex + LLM) con deduplicación."""

from __future__ import annotations

from derogada.extract.gazetteer import buscar_alias
from derogada.extract.llm import extraer_citas_llm
from derogada.extract.patterns import deduplicar, extraer_citas_regex
from derogada.models import Cita


def _identificador_via_alias(cita: Cita) -> str | None:
    if not cita.alias:
        return None
    entrada = buscar_alias(cita.alias)
    return entrada.identificador if entrada else None


def _misma_norma(a: Cita, b: Cita) -> bool:
    """Dos citas refieren a la misma norma aunque difiera el literal o el rango.

    Con número oficial: basta número + (artículo compatible). Sin número: el
    identificador del gazetteer para el alias (así "ET" y "Estatuto de los
    Trabajadores" fusionan), o alias/literal normalizado como último recurso.
    """
    if a.jurisdiccion != b.jurisdiccion:
        return False
    na, nb = (a.numero or "").lower(), (b.numero or "").lower()
    if na and nb:
        if na != nb:
            return False
        if a.articulo and b.articulo:
            return a.articulo == b.articulo
        return True
    ia, ib = _identificador_via_alias(a), _identificador_via_alias(b)
    if ia and ib:
        return ia == ib
    aa, ab = (a.alias or "").lower(), (b.alias or "").lower()
    if aa and ab:
        return aa == ab
    ta, tb = (a.alias or a.texto).strip().lower(), (b.alias or b.texto).strip().lower()
    return ta == tb


def extraer_citas(texto: str, usar_llm: bool = True, modelo: str | None = None) -> list[Cita]:
    """Citas del documento: canal regex siempre; canal LLM si está configurado.

    El canal regex manda: una cita del LLM que duplica una regex se descarta
    (rellenando el artículo si faltara); las genuinamente nuevas se añaden.
    """
    citas = extraer_citas_regex(texto)
    if usar_llm:
        for cita_llm in extraer_citas_llm(texto, modelo=modelo):
            existente = next((c for c in citas if _misma_norma(c, cita_llm)), None)
            if existente is None:
                citas.append(cita_llm)
            elif existente.articulo is None and cita_llm.articulo is not None:
                existente.articulo = cita_llm.articulo
    return deduplicar(citas)
