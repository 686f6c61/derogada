"""Tests del gazetteer de alias."""

from __future__ import annotations

from derogada.extract.gazetteer import ALIASES_RE, buscar_alias
from derogada.models import Jurisdiccion


def test_alias_exacto():
    entrada = buscar_alias("LECrim")
    assert entrada is not None
    assert entrada.identificador == "BOE-A-1882-6036"


def test_alias_case_insensitive():
    entrada = buscar_alias("rgpd")
    assert entrada is not None
    assert entrada.jurisdiccion == Jurisdiccion.UE
    assert entrada.identificador == "32016R0679"


def test_alias_nombre_largo():
    entrada = buscar_alias("Código Civil")
    assert entrada is not None
    assert entrada.identificador == "BOE-A-1889-4763"


def test_alias_desconocido():
    assert buscar_alias("XYZQW") is None


def test_regex_respeta_limites_de_palabra():
    # "ET" dentro de otra palabra no es alias
    assert ALIASES_RE.search("el PROYECTO actual") is None
    m = ALIASES_RE.search("según el ET vigente")
    assert m is not None and m.group("alias") == "ET"


def test_regex_prefiere_sigla_larga():
    m = ALIASES_RE.search("la LECrim regula")
    assert m is not None and m.group("alias") == "LECrim"
