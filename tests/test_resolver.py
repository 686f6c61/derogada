"""Tests del resolver (con cassettes VCR)."""

from __future__ import annotations

import pytest

from derogada.models import Cita, Jurisdiccion
from derogada.resolve.resolver import resolver_cita
from derogada.sources import BoeClient, CellarClient


@pytest.fixture(scope="module")
def clientes():
    with BoeClient() as boe, CellarClient() as cellar:
        yield boe, cellar


@pytest.mark.vcr
def test_resolver_ley_30_1992(clientes):
    boe, cellar = clientes
    cita = Cita(texto="Ley 30/1992", jurisdiccion=Jurisdiccion.ES, rango="Ley", numero="30/1992")
    r = resolver_cita(cita, boe, cellar)
    assert r.resuelta
    assert r.identificador == "BOE-A-1992-26318"
    assert r.fuente == "BOE"


@pytest.mark.vcr
def test_resolver_reglamento_ue(clientes):
    boe, cellar = clientes
    cita = Cita(
        texto="Reglamento (UE) 2016/679",
        jurisdiccion=Jurisdiccion.UE,
        rango="Reglamento",
        numero="2016/679",
    )
    r = resolver_cita(cita, boe, cellar)
    assert r.resuelta
    assert r.identificador == "32016R0679"
    assert r.fuente == "EUR-Lex"


@pytest.mark.vcr
def test_resolver_alias_rgpd(clientes):
    boe, cellar = clientes
    cita = Cita(texto="RGPD", jurisdiccion=Jurisdiccion.ES, alias="RGPD")
    r = resolver_cita(cita, boe, cellar)
    assert r.resuelta
    assert r.identificador == "32016R0679"


@pytest.mark.vcr
def test_resolver_alias_lec_valida_gazetteer(clientes):
    boe, cellar = clientes
    cita = Cita(texto="LEC", jurisdiccion=Jurisdiccion.ES, alias="LEC")
    r = resolver_cita(cita, boe, cellar)
    assert r.resuelta
    assert r.identificador == "BOE-A-2000-323"


@pytest.mark.vcr
def test_resolver_alias_lrjap_valida_gazetteer(clientes):
    boe, cellar = clientes
    cita = Cita(texto="LRJAP", jurisdiccion=Jurisdiccion.ES, alias="LRJAP")
    r = resolver_cita(cita, boe, cellar)
    assert r.resuelta
    assert r.identificador == "BOE-A-2015-10566"


@pytest.mark.vcr
def test_resolver_no_encontrada(clientes):
    boe, cellar = clientes
    cita = Cita(texto="Ley 999/2099", jurisdiccion=Jurisdiccion.ES, rango="Ley", numero="999/2099")
    r = resolver_cita(cita, boe, cellar)
    assert not r.resuelta
