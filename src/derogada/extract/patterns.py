"""Extracción determinista de referencias normativas mediante expresiones regulares.

Cubre los patrones habituales de cita en documentos jurídicos españoles:
- España: "Ley 30/1992", "Real Decreto-ley 6/2022, de 29 de marzo", "Ley Orgánica 3/2018"...
- UE: "Reglamento (UE) 2016/679", "Directiva 95/46/CE", "Decisión (UE) 2015/1520"...
- Siglas del gazetteer: LECrim, LRJCA, LPAC, ET, RGPD...
- Artículo asociado por proximidad: "artículo 42 de la Ley 30/1992" / "Ley 30/1992, art. 42".
"""

from __future__ import annotations

import re

from derogada.extract.gazetteer import ALIASES_RE, buscar_alias
from derogada.models import Cita, Jurisdiccion

_VENTANA_ARTICULO = 160
_VENTANA_CONTEXTO = 120

_RE_NORMA_ES = re.compile(
    r"\b(?P<rango>Ley Orgánica|Ley|Real Decreto-ley|Real Decreto Legislativo|Real Decreto"
    r"|Decreto|Orden|Resolución)"
    r"\s+(?:n[úu]m(?:ero)?\.?\s*)?"
    r"(?P<numero>\d{1,4}\s*/\s*\d{4})",
    re.IGNORECASE,
)

_RE_NORMA_UE = re.compile(
    r"\b(?P<rango>Reglamento|Directiva|Decisión)"
    r"(?:\s*\((?:UE|CE|CEE)\))?"
    r"(?:\s+(?:n[.ºo]+|número)\s*)?"
    r"\s+(?P<numero>\d{2,4}\s*/\s*\d+)(?:\s*/\s*(?:CE|UE))?",
    re.IGNORECASE,
)

_RE_ARTICULO = re.compile(r"\bart(?:ículos?|s)?\.?\s+(?P<articulo>\d+(?:\.\d+)?)", re.IGNORECASE)

_RANGOS_CANONICOS = {
    "ley orgánica": "Ley Orgánica",
    "ley": "Ley",
    "real decreto-ley": "Real Decreto-ley",
    "real decreto legislativo": "Real Decreto Legislativo",
    "real decreto": "Real Decreto",
    "decreto": "Decreto",
    "orden": "Orden",
    "resolución": "Resolución",
    "reglamento": "Reglamento",
    "directiva": "Directiva",
    "decisión": "Decisión",
}


def canon_rango(rango: str) -> str:
    return _RANGOS_CANONICOS.get(rango.lower(), rango.strip().title())


def norm_numero(numero: str | None) -> str | None:
    """Normaliza un número oficial: sin espacios ni sufijo "/CE", "/UE", "/CEE"."""
    if not numero:
        return None
    n = re.sub(r"\s+", "", numero)
    n = re.sub(r"/(CE|CEE|UE)$", "", n, flags=re.IGNORECASE)
    return n or None


def _contexto(texto: str, inicio: int, fin: int) -> str:
    izq = max(0, inicio - _VENTANA_CONTEXTO)
    der = min(len(texto), fin + _VENTANA_CONTEXTO)
    return re.sub(r"\s+", " ", texto[izq:der]).strip()


def _articulo_cercano(texto: str, inicio: int, fin: int) -> str | None:
    """Artículo ligado a la norma: el más próximo en la ventana anterior o posterior.

    Regla del conector: si entre el artículo anterior y la norma solo hay el nombre
    de la propia norma ("del Estatuto de los Trabajadores", "de la Ley"), ese
    artículo es el ligado, aunque haya otro más cerca después.
    """
    mejor: tuple[int, str] | None = None
    izq = max(0, inicio - _VENTANA_ARTICULO)
    previa: str | None = None
    for m in _RE_ARTICULO.finditer(texto[izq:inicio]):
        previa = m.group("articulo")
        mejor = (inicio - (izq + m.end()), previa)
        segmento = texto[izq + m.end() : inicio]
    if previa is not None and re.fullmatch(
        r"\s*(?:del|de la|de los|de las|de)\s+[\wáéíóúüÁÉÍÓÚÜñÑ ()]{0,60}",
        segmento,
        re.IGNORECASE,
    ):
        return previa
    for m in _RE_ARTICULO.finditer(texto[fin : fin + _VENTANA_ARTICULO]):
        distancia = m.start()
        if mejor is None or distancia < mejor[0]:
            mejor = (distancia, m.group("articulo"))
        break  # solo el primero de la ventana posterior
    return mejor[1] if mejor else None


def extraer_citas_regex(texto: str) -> list[Cita]:
    """Devuelve las citas detectadas por patrones, sin duplicados ni solapes."""
    citas: list[Cita] = []
    ocupados: list[tuple[int, int]] = []  # spans ya consumidos por norma ES/UE

    for m in _RE_NORMA_ES.finditer(texto):
        ocupados.append(m.span())
        citas.append(
            Cita(
                texto=m.group(0),
                jurisdiccion=Jurisdiccion.ES,
                rango=canon_rango(m.group("rango")),
                numero=norm_numero(m.group("numero")),
                articulo=_articulo_cercano(texto, m.start(), m.end()),
                contexto=_contexto(texto, m.start(), m.end()),
            )
        )

    for m in _RE_NORMA_UE.finditer(texto):
        ocupados.append(m.span())
        citas.append(
            Cita(
                texto=m.group(0),
                jurisdiccion=Jurisdiccion.UE,
                rango=canon_rango(m.group("rango")),
                numero=norm_numero(m.group("numero")),
                articulo=_articulo_cercano(texto, m.start(), m.end()),
                contexto=_contexto(texto, m.start(), m.end()),
            )
        )

    for m in ALIASES_RE.finditer(texto):
        # Evita falsos positivos: sigla dentro de una cita ya detectada (p. ej. "95/46/CE")
        if any(ini <= m.start() < fin for ini, fin in ocupados):
            continue
        entrada = buscar_alias(m.group("alias"))
        if entrada is None:
            continue
        ocupados.append(m.span())
        citas.append(
            Cita(
                texto=m.group(0),
                jurisdiccion=entrada.jurisdiccion,
                rango=entrada.rango,
                numero=entrada.numero,
                alias=entrada.alias,
                articulo=_articulo_cercano(texto, m.start(), m.end()),
                contexto=_contexto(texto, m.start(), m.end()),
            )
        )

    return deduplicar(citas)


def clave_cita(cita: Cita) -> tuple[str, str, str, str]:
    """Clave de deduplicación: norma normalizada + artículo."""
    norma = (cita.numero or cita.alias or cita.texto).lower()
    return (cita.jurisdiccion.value, norma, (cita.rango or "").lower(), cita.articulo or "")


def deduplicar(citas: list[Cita]) -> list[Cita]:
    """Fusiona duplicados conservando el primero; rellena el artículo si falta."""
    vistos: dict[tuple[str, str, str, str], Cita] = {}
    orden: list[tuple[str, str, str, str]] = []
    for cita in citas:
        clave = clave_cita(cita)
        if clave in vistos:
            existente = vistos[clave]
            if existente.articulo is None and cita.articulo is not None:
                existente.articulo = cita.articulo
        else:
            vistos[clave] = cita
            orden.append(clave)
    return [vistos[k] for k in orden]
