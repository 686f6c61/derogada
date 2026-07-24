"""Tests del cálculo de CELEX."""

from __future__ import annotations

from derogada.resolve.resolver import celex_desde_referencia


def test_reglamento():
    assert celex_desde_referencia("Reglamento", "2016/679") == "32016R0679"


def test_directiva_ano_corto():
    assert celex_desde_referencia("Directiva", "95/46") == "31995L0046"


def test_decision():
    assert celex_desde_referencia("Decisión", "2015/1520") == "32015D1520"


def test_rango_no_ue():
    assert celex_desde_referencia("Ley", "30/1992") is None


def test_sin_datos():
    assert celex_desde_referencia(None, "2016/679") is None
    assert celex_desde_referencia("Reglamento", None) is None
    assert celex_desde_referencia("Reglamento", "sinbarra") is None
