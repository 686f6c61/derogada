"""Tests del canal regex de extracción de citas."""

from __future__ import annotations

from derogada.extract.patterns import extraer_citas_regex
from derogada.models import Jurisdiccion


def test_ley_con_articulo_posterior():
    citas = extraer_citas_regex("conforme a la Ley 30/1992, artículo 42, se exige")
    ley = next(c for c in citas if c.numero == "30/1992")
    assert ley.rango == "Ley"
    assert ley.articulo == "42"


def test_articulo_anterior_con_conector():
    citas = extraer_citas_regex("el artículo 21.1 de la Ley 39/2015 establece")
    ley = next(c for c in citas if c.numero == "39/2015")
    assert ley.articulo == "21.1"


def test_articulo_de_nombre_largo():
    citas = extraer_citas_regex(
        "el artículo 55 del Estatuto de los Trabajadores (ET) "
        "y el artículo 42 de la Ley 30/1992"
    )
    et = next(c for c in citas if c.alias == "ET")
    assert et.articulo == "55"
    ley = next(c for c in citas if c.numero == "30/1992")
    assert ley.articulo == "42"


def test_real_decreto_ley():
    citas = extraer_citas_regex("según el Real Decreto-ley 6/2022, de 29 de marzo")
    assert citas[0].rango == "Real Decreto-ley"
    assert citas[0].numero == "6/2022"


def test_ley_organica():
    citas = extraer_citas_regex("la Ley Orgánica 3/2018, de 5 de diciembre")
    assert citas[0].rango == "Ley Orgánica"
    assert citas[0].numero == "3/2018"


def test_reglamento_ue():
    citas = extraer_citas_regex("el Reglamento (UE) 2016/679 impone obligaciones")
    rgpd = next(c for c in citas if c.jurisdiccion == Jurisdiccion.UE)
    assert rgpd.rango == "Reglamento"
    assert rgpd.numero == "2016/679"


def test_directiva_ce_sin_falso_positivo_constitucion():
    citas = extraer_citas_regex("la Directiva 95/46/CE fue derogada")
    assert any(c.numero == "95/46" for c in citas)
    # "CE" de la Directiva no debe confundirse con la Constitución Española
    assert not any(c.alias == "CE" for c in citas)


def test_alias_sigla():
    citas = extraer_citas_regex("el art. 217 LECrim regula las pruebas")
    lecrim = next(c for c in citas if c.alias == "LECrim")
    assert lecrim.articulo == "217"


def test_deduplicacion():
    citas = extraer_citas_regex("la Ley 30/1992 y, más adelante, la Ley 30/1992 otra vez")
    assert sum(1 for c in citas if c.numero == "30/1992") == 1


def test_sin_citas():
    assert extraer_citas_regex("texto sin ninguna referencia normativa") == []
