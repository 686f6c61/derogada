"""Tests de los clientes BOE y CELLAR (con cassettes VCR: offline tras grabar)."""

from __future__ import annotations

import pytest

from derogada.sources import BoeClient, CellarClient


@pytest.fixture(scope="module")
def boe():
    with BoeClient() as c:
        yield c


@pytest.fixture(scope="module")
def cellar():
    with CellarClient() as c:
        yield c


@pytest.mark.vcr
def test_metadatos_derogada(boe):
    meta = boe.metadatos("BOE-A-1992-26318")
    assert meta is not None
    assert meta["estatus_derogacion"] == "S"
    assert meta["numero_oficial"] == "30/1992"
    assert meta["fecha_derogacion"] == "20210402"


@pytest.mark.vcr
def test_metadatos_vigente(boe):
    meta = boe.metadatos("BOE-A-2015-10565")
    assert meta is not None
    assert meta["estatus_derogacion"] == "N"
    assert meta["vigencia_agotada"] == "N"


@pytest.mark.vcr
def test_referencias_posteriores(boe):
    posts = boe.referencias_posteriores("BOE-A-1992-26318")
    derogas = [p for p in posts if "DEROGA" in p.get("relacion", {}).get("texto", "")]
    assert any(p["id_norma"] == "BOE-A-2015-10565" for p in derogas)


@pytest.mark.vcr
def test_indice(boe):
    assert len(boe.indice("BOE-A-1992-26318")) > 100


@pytest.mark.vcr
def test_buscar(boe):
    resultados = boe.buscar("Ley 30/1992", limite=5)
    assert any(r.get("numero_oficial") == "30/1992" for r in resultados)


@pytest.mark.vcr
def test_cellar_rgpd_vigente(cellar):
    est = cellar.estado("32016R0679")
    assert est.encontrado
    assert est.en_vigor is True


@pytest.mark.vcr
def test_cellar_directiva_derogada(cellar):
    est = cellar.estado("31995L0046")
    assert est.encontrado
    assert est.en_vigor is False
    assert "32016R0679" in est.derogada_por
