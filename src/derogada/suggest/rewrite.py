"""Propuestas de cambio textual ancladas a datos de las fuentes oficiales.

Regla de oro: la propuesta solo usa normas reales devueltas por la API
(la que deroga/modifica la citada). Sin fuente oficial, no hay sugerencia.
"""

from __future__ import annotations

import os

from derogada.models import EstadoCita, Informe, ResultadoCita

_PROMPT = """Un escrito jurídico español contiene esta cita normativa:

- Cita literal: «{cita}»
- Estado verificado en la fuente oficial ({fuente}): {estado}
- Norma que la derogó: {derogante} ({url_derogante})
{detalle}

Redacta UNA propuesta de sustitución de la cita para que el escrito sea correcto a día
de hoy, citando la norma vigente indicada. Si la derogación es parcial o el precepto
equivalente no es obvio, dilo explícitamente en la propia propuesta.
Responde SOLO con la frase de sustitución, sin explicaciones ni comillas."""


def _detalle(resultado: ResultadoCita) -> str:
    partes = []
    if resultado.nota:
        partes.append(f"- Detalle oficial: {resultado.nota}")
    if resultado.cita.articulo:
        partes.append(f"- Artículo citado: {resultado.cita.articulo}")
    if resultado.cita.contexto:
        partes.append(f"- Contexto en el escrito: «{resultado.cita.contexto}»")
    return "\n".join(partes)


def proponer_sugerencias(informe: Informe, modelo: str | None = None) -> None:
    """Rellena `sugerencia` en resultados derogados/agotados con sustituta conocida.

    Sin LLM configurado no hace nada (modo silencioso).
    """
    modelo = modelo or os.environ.get("DEROGADA_MODEL")
    if not modelo:
        return

    objetivos = [
        r
        for r in informe.resultados
        if r.estado in (EstadoCita.DEROGADA, EstadoCita.VIGENCIA_AGOTADA) and r.derogada_por
    ]
    if not objetivos:
        return

    import litellm

    extra: dict = {}
    if base := os.environ.get("DEROGADA_API_BASE"):
        extra["api_base"] = base
    if key := os.environ.get("DEROGADA_API_KEY"):
        extra["api_key"] = key

    for resultado in objetivos:
        derogante = resultado.derogada_por
        assert derogante is not None
        prompt = _PROMPT.format(
            cita=resultado.cita.texto,
            fuente=resultado.norma.fuente if resultado.norma else "?",
            estado=resultado.estado.value,
            derogante=derogante.titulo or derogante.identificador,
            url_derogante=derogante.url or "",
            detalle=_detalle(resultado),
        )
        try:
            resp = litellm.completion(
                model=modelo,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                **extra,
            )
            sugerencia = (resp.choices[0].message.content or "").strip()
            if sugerencia:
                resultado.sugerencia = sugerencia
        except Exception:
            continue  # una sugerencia fallida nunca rompe el informe
