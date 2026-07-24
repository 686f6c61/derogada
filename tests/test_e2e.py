"""Test de extremo a extremo del pipeline.

- test_pipeline_regex_offline: determinista, con cassettes VCR (sin LLM).
- test_pipeline_con_llm: solo si hay DEROGADA_MODEL + DEROGADA_API_KEY (p. ej. .env
  con el endpoint OpenAI-compatible de nan.builders). Se salta en CI.
"""

from __future__ import annotations

import os

import pytest

from derogada.models import EstadoCita
from derogada.pipeline import analizar_texto

TEXTO_DEMANDA = """
DEMANDA DE DESPIDO

PRIMERO.- El despido se produjo sin observar lo dispuesto en el artículo 55 del
Estatuto de los Trabajadores (ET), en relación con el artículo 42 de la Ley 30/1992,
de 26 de noviembre, de Régimen Jurídico de las Administraciones Públicas.

SEGUNDO.- La notificación se practicó conforme a la Ley 39/2015, art. 21.1, del
Procedimiento Administrativo Común.

TERCERO.- El tratamiento de datos personales se ampara en el artículo 6 del
Reglamento (UE) 2016/679 (RGPD), que vino a sustituir a la Directiva 95/46/CE.
"""


@pytest.mark.vcr
def test_pipeline_regex_offline():
    informe = analizar_texto(TEXTO_DEMANDA, usar_llm=False, con_sugerencias=False)
    estados = {(r.cita.alias or r.cita.numero): r.estado for r in informe.resultados}
    assert estados["30/1992"] == EstadoCita.DEROGADA
    assert estados["39/2015"] == EstadoCita.MODIFICADA
    assert estados["2016/679"] == EstadoCita.VIGENTE
    assert estados["95/46"] == EstadoCita.DEROGADA
    assert estados["ET"] == EstadoCita.MODIFICADA
    r30 = next(r for r in informe.resultados if r.cita.numero == "30/1992")
    assert r30.derogada_por is not None
    assert r30.derogada_por.identificador == "BOE-A-2015-10565"
    assert r30.cita.articulo == "42"
    assert informe.resumen.total == 5


def _hay_llm() -> bool:
    return bool(os.environ.get("DEROGADA_API_KEY") and os.environ.get("DEROGADA_MODEL"))


@pytest.mark.skipif(not _hay_llm(), reason="sin DEROGADA_MODEL/DEROGADA_API_KEY configurados")
def test_pipeline_con_llm():
    informe = analizar_texto(TEXTO_DEMANDA, usar_llm=True, con_sugerencias=True)
    r30 = next(r for r in informe.resultados if r.cita.numero == "30/1992")
    assert r30.estado == EstadoCita.DEROGADA
    assert r30.sugerencia
