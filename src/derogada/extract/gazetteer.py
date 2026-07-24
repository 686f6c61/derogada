"""Alias y siglas habituales de normas -> identificación oficial.

Dos usos:
- Canal regex: solo las siglas cortas (`en_regex=True`), con coincidencia sensible
  a mayúsculas y límites de palabra.
- Resolución: cualquier alias normalizado (incluidos nombres largos como
  "Código Civil") mapea a su identificador, que SIEMPRE se valida contra la API.

Los identificadores marcados aquí se verifican con metadatos de la API antes de
usarse; si no casan (número oficial distinto), el resolver degrada a búsqueda.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from derogada.models import Jurisdiccion


@dataclass(frozen=True)
class EntradaAlias:
    alias: str
    jurisdiccion: Jurisdiccion
    identificador: str  # "BOE-A-..." o CELEX
    nombre: str
    rango: str | None = None
    numero: str | None = None
    en_regex: bool = False


_ENTRADAS = [
    EntradaAlias("CE", Jurisdiccion.ES, "BOE-A-1978-31229", "Constitución Española",
                 rango="Constitución", en_regex=True),
    EntradaAlias("LEC", Jurisdiccion.ES, "BOE-A-2000-323", "Ley de Enjuiciamiento Civil",
                 rango="Ley", numero="1/2000", en_regex=True),
    EntradaAlias("LECrim", Jurisdiccion.ES, "BOE-A-1882-6036", "Ley de Enjuiciamiento Criminal",
                 en_regex=True),
    EntradaAlias("LRJCA", Jurisdiccion.ES, "BOE-A-1992-26318",
                 "Ley de Régimen Jurídico de las Administraciones Públicas y del PAC",
                 rango="Ley", numero="30/1992", en_regex=True),
    EntradaAlias("LPAC", Jurisdiccion.ES, "BOE-A-2015-10565",
                 "Ley del Procedimiento Administrativo Común",
                 rango="Ley", numero="39/2015", en_regex=True),
    EntradaAlias("LRJAP", Jurisdiccion.ES, "BOE-A-2015-10566",
                 "Ley de Régimen Jurídico del Sector Público",
                 rango="Ley", numero="40/2015", en_regex=True),
    EntradaAlias("ET", Jurisdiccion.ES, "BOE-A-2015-11430", "Estatuto de los Trabajadores",
                 rango="Real Decreto Legislativo", numero="2/2015", en_regex=True),
    EntradaAlias("LGT", Jurisdiccion.ES, "BOE-A-2003-23186", "Ley General Tributaria",
                 rango="Ley", numero="58/2003", en_regex=True),
    EntradaAlias("RGPD", Jurisdiccion.UE, "32016R0679", "Reglamento General de Protección de Datos",
                 rango="Reglamento", numero="2016/679", en_regex=True),
    EntradaAlias("LOPDGDD", Jurisdiccion.ES, "BOE-A-2018-16673",
                 "Ley Orgánica de Protección de Datos y Garantía de los Derechos Digitales",
                 rango="Ley Orgánica", numero="3/2018", en_regex=True),
    # Nombres largos: solo para resolución (los detecta sobre todo el canal LLM)
    EntradaAlias("Código Civil", Jurisdiccion.ES, "BOE-A-1889-4763", "Código Civil"),
    EntradaAlias("Codigo Civil", Jurisdiccion.ES, "BOE-A-1889-4763", "Código Civil"),
    EntradaAlias("Código Penal", Jurisdiccion.ES, "BOE-A-1995-25444", "Código Penal",
                 rango="Ley Orgánica", numero="10/1995"),
    EntradaAlias("Codigo Penal", Jurisdiccion.ES, "BOE-A-1995-25444", "Código Penal",
                 rango="Ley Orgánica", numero="10/1995"),
    EntradaAlias("Constitución Española", Jurisdiccion.ES, "BOE-A-1978-31229",
                 "Constitución Española", rango="Constitución"),
    EntradaAlias("Estatuto de los Trabajadores", Jurisdiccion.ES, "BOE-A-2015-11430",
                 "Estatuto de los Trabajadores", rango="Real Decreto Legislativo", numero="2/2015"),
    EntradaAlias("Ley de Enjuiciamiento Civil", Jurisdiccion.ES, "BOE-A-2000-323",
                 "Ley de Enjuiciamiento Civil", rango="Ley", numero="1/2000"),
    EntradaAlias("Ley de Enjuiciamiento Criminal", Jurisdiccion.ES, "BOE-A-1882-6036",
                 "Ley de Enjuiciamiento Criminal"),
    EntradaAlias("Reglamento General de Protección de Datos", Jurisdiccion.UE, "32016R0679",
                 "Reglamento General de Protección de Datos",
                 rango="Reglamento", numero="2016/679"),
]

ALIASES: dict[str, EntradaAlias] = {e.alias: e for e in _ENTRADAS}

# Regex de siglas cortas: sensibles a mayúsculas, con límites de palabra,
# primero las más largas (LECrim antes que LEC).
_SIGLAS = sorted((a for a, e in ALIASES.items() if e.en_regex), key=len, reverse=True)
ALIASES_RE = re.compile(r"\b(?P<alias>" + "|".join(re.escape(a) for a in _SIGLAS) + r")\b")


def buscar_alias(texto: str) -> EntradaAlias | None:
    """Entrada del gazetteer para un alias (exacto, case-insensitive, sin paréntesis)."""
    if not texto:
        return None
    if texto in ALIASES:
        return ALIASES[texto]
    bajo = texto.lower()
    for alias, entrada in ALIASES.items():
        if alias.lower() == bajo:
            return entrada
    # "Estatuto de los Trabajadores (ET)" -> "Estatuto de los Trabajadores"
    limpio = re.sub(r"\s*\([^)]*\)\s*$", "", texto).strip()
    if limpio and limpio != texto:
        return buscar_alias(limpio)
    # "Estatuto de los Trabajadores, ET" -> prueba cada parte (la larga primero)
    if "," in texto:
        for parte in sorted((p.strip() for p in texto.split(",")), key=len, reverse=True):
            if parte and parte != texto and (entrada := buscar_alias(parte)):
                return entrada
    return None
