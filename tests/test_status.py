"""Tests de verificación de estado (con cassettes VCR)."""

from __future__ import annotations

import pytest

from derogada.check.status import verificar_cita
from derogada.models import Cita, EstadoCita, Jurisdiccion
from derogada.resolve.resolver import Resolucion
from derogada.sources import BoeClient, CellarClient


@pytest.fixture(scope="module")
def clientes():
    with BoeClient() as boe, CellarClient() as cellar:
        yield boe, cellar


def _res_boe(boe_id: str) -> Resolucion:
    return Resolucion(identificador=boe_id, fuente="BOE")


@pytest.mark.vcr
def test_ley_30_1992_derogada(clientes):
    boe, cellar = clientes
    cita = Cita(texto="Ley 30/1992", jurisdiccion=Jurisdiccion.ES, rango="Ley", numero="30/1992")
    r = verificar_cita(cita, _res_boe("BOE-A-1992-26318"), boe, cellar)
    assert r.estado == EstadoCita.DEROGADA
    assert r.derogada_por is not None
    assert r.derogada_por.identificador == "BOE-A-2015-10565"


@pytest.mark.vcr
def test_ley_39_2015_modificada(clientes):
    boe, cellar = clientes
    cita = Cita(texto="Ley 39/2015", jurisdiccion=Jurisdiccion.ES, rango="Ley", numero="39/2015")
    r = verificar_cita(cita, _res_boe("BOE-A-2015-10565"), boe, cellar)
    assert r.estado == EstadoCita.MODIFICADA
    assert len(r.modificada_por) > 0


@pytest.mark.vcr
def test_rgpd_vigente(clientes):
    boe, cellar = clientes
    cita = Cita(texto="Reglamento (UE) 2016/679", jurisdiccion=Jurisdiccion.UE)
    r = verificar_cita(cita, Resolucion(identificador="32016R0679", fuente="EUR-Lex"), boe, cellar)
    assert r.estado == EstadoCita.VIGENTE


@pytest.mark.vcr
def test_directiva_derogada(clientes):
    boe, cellar = clientes
    cita = Cita(texto="Directiva 95/46/CE", jurisdiccion=Jurisdiccion.UE)
    r = verificar_cita(cita, Resolucion(identificador="31995L0046", fuente="EUR-Lex"), boe, cellar)
    assert r.estado == EstadoCita.DEROGADA
    assert r.derogada_por is not None
    assert r.derogada_por.identificador == "32016R0679"


def test_no_resuelta_con_candidatos():
    from derogada.models import NormaRef

    cita = Cita(texto="Real Decreto 429/1993", jurisdiccion=Jurisdiccion.ES)
    resolucion = Resolucion(
        candidatos=[NormaRef(identificador="BOE-A-1993-1", fuente="BOE")]
    )
    r = verificar_cita(cita, resolucion, BoeClient(), CellarClient())
    assert r.estado == EstadoCita.NO_RESUELTA
    assert len(r.candidatos) == 1


def test_no_encontrada():
    cita = Cita(texto="Ley inventada 1/1800", jurisdiccion=Jurisdiccion.ES)
    r = verificar_cita(cita, Resolucion(), BoeClient(), CellarClient())
    assert r.estado == EstadoCita.NO_ENCONTRADA
