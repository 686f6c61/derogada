"""Tests del render del informe (Markdown y JSON)."""

from __future__ import annotations

import json

from derogada.models import (
    Cita,
    EstadoCita,
    Informe,
    Jurisdiccion,
    NormaRef,
    ResultadoCita,
)
from derogada.report import render_json, render_markdown


def _informe() -> Informe:
    return Informe(
        documento="demanda.pdf",
        resultados=[
            ResultadoCita(
                cita=Cita(
                    texto="Ley 30/1992",
                    jurisdiccion=Jurisdiccion.ES,
                    rango="Ley",
                    numero="30/1992",
                ),
                estado=EstadoCita.DEROGADA,
                norma=NormaRef(
                    identificador="BOE-A-1992-26318",
                    fuente="BOE",
                    url="https://www.boe.es/buscar/act.php?id=BOE-A-1992-26318",
                ),
                derogada_por=NormaRef(identificador="BOE-A-2015-10565", fuente="BOE"),
                nota="Derogada el 02/04/2021",
            ),
            ResultadoCita(
                cita=Cita(texto="RGPD", jurisdiccion=Jurisdiccion.UE, alias="RGPD"),
                estado=EstadoCita.VIGENTE,
                norma=NormaRef(identificador="32016R0679", fuente="EUR-Lex"),
            ),
        ],
    )


def test_markdown():
    md = render_markdown(_informe())
    assert "[DEROGADA]" in md
    assert "[VIGENTE]" in md
    assert "BOE-A-2015-10565" in md
    assert "no constituye asesoramiento jurídico" in md
    assert "2 citas" in md


def test_json():
    datos = json.loads(render_json(_informe()))
    assert datos["resumen"]["total"] == 2
    assert datos["resumen"]["derogadas"] == 1
    assert datos["resumen"]["vigentes"] == 1
    assert datos["resultados"][0]["estado"] == "DEROGADA"
