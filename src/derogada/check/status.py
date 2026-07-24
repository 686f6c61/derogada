"""Verificación de vigencia de una cita ya resuelta, a dos niveles:

1. Norma completa: metadatos (estatus_derogacion, vigencia_agotada) + análisis
   jurídico (qué norma la deroga o modifica) en el BOE; in-force en CELLAR.
2. Artículo citado: existencia del bloque en el texto consolidado del BOE
   (un artículo puede estar derogado aunque la norma siga vigente).
"""

from __future__ import annotations

import json

from derogada.models import Cita, EstadoCita, NormaRef, ResultadoCita
from derogada.resolve.resolver import URL_BOE, URL_EURLEX, Resolucion
from derogada.sources.boe import BoeClient
from derogada.sources.cellar import CellarClient

_MAX_MODIFICACIONES = 5


def verificar_cita(
    cita: Cita, resolucion: Resolucion, boe: BoeClient, cellar: CellarClient
) -> ResultadoCita:
    """Clasifica la cita: VIGENTE / MODIFICADA / DEROGADA / AGOTADA / NO_RESUELTA..."""
    if not resolucion.resuelta:
        if resolucion.candidatos:
            return ResultadoCita(
                cita=cita,
                estado=EstadoCita.NO_RESUELTA,
                candidatos=resolucion.candidatos,
                nota=f"{len(resolucion.candidatos)} candidatos posibles; revise manualmente",
            )
        return ResultadoCita(
            cita=cita,
            estado=EstadoCita.NO_ENCONTRADA,
            nota="No se pudo identificar la norma en las fuentes oficiales",
        )

    norma = NormaRef(
        identificador=resolucion.identificador or "?",
        fuente=resolucion.fuente or "?",
        titulo=resolucion.titulo,
        url=resolucion.url,
    )
    if resolucion.fuente == "BOE":
        return _verificar_boe(cita, resolucion.identificador or "", norma, boe)
    return _verificar_ue(cita, resolucion.identificador or "", norma, cellar)


# ---------------- España (BOE) ----------------


def _relacion(posterior: dict) -> str:
    rel = posterior.get("relacion", "")
    if isinstance(rel, dict):
        return str(rel.get("texto", ""))
    return str(rel)


def _ref_desde_posterior(p: dict) -> NormaRef:
    id_norma = p.get("id_norma", "?")
    return NormaRef(
        identificador=id_norma,
        fuente="BOE",
        titulo=str(p.get("texto", "")).strip() or None,
        url=URL_BOE.format(boe_id=id_norma),
    )


def _fecha_boe(fecha: str | None) -> str | None:
    if fecha and len(fecha) == 8:
        return f"{fecha[6:8]}/{fecha[4:6]}/{fecha[0:4]}"
    return None


def _verificar_boe(cita: Cita, boe_id: str, norma: NormaRef, boe: BoeClient) -> ResultadoCita:
    meta = boe.metadatos(boe_id)
    if meta is None:
        return ResultadoCita(
            cita=cita, estado=EstadoCita.NO_ENCONTRADA, norma=norma,
            nota="Sin ficha en la API del BOE",
        )

    posteriores = boe.referencias_posteriores(boe_id)
    derogaciones = [p for p in posteriores if "DEROGA" in _relacion(p)]
    modificaciones = [
        p for p in posteriores if "MODIFICA" in _relacion(p) or "AÑADE" in _relacion(p)
    ]

    derogada_por = None
    nota = None
    if meta.get("estatus_derogacion") == "S":
        estado = EstadoCita.DEROGADA
        if derogaciones:
            derogada_por = _ref_desde_posterior(derogaciones[0])
        nota = "Derogada"
        if fecha := _fecha_boe(meta.get("fecha_derogacion")):
            nota += f" el {fecha}"
        if derogaciones and derogaciones[0].get("texto"):
            nota += f" ({derogaciones[0]['texto'].strip()})"
    elif meta.get("vigencia_agotada") == "S":
        estado = EstadoCita.VIGENCIA_AGOTADA
        nota = "Vigencia agotada según el BOE"
    elif modificaciones:
        estado = EstadoCita.MODIFICADA
        nota = f"{len(modificaciones)} modificaciones posteriores consolidadas"
    else:
        estado = EstadoCita.VIGENTE

    resultado = ResultadoCita(
        cita=cita,
        estado=estado,
        norma=norma,
        derogada_por=derogada_por,
        modificada_por=[_ref_desde_posterior(p) for p in modificaciones[:_MAX_MODIFICACIONES]],
        nota=nota,
    )
    _comprobar_articulo(resultado, boe)
    return resultado


def _comprobar_articulo(resultado: ResultadoCita, boe: BoeClient) -> None:
    """Nivel artículo: existencia del bloque en el texto consolidado actual."""
    articulo = resultado.cita.articulo
    if not articulo or not resultado.norma:
        return
    boe_id = resultado.norma.identificador
    bloque_id = f"a{articulo.split('.')[0]}"
    try:
        indice = boe.indice(boe_id)
    except Exception:
        return
    ids = {str(b.get("id", "")).lower() for b in indice}
    nota = None
    if bloque_id.lower() not in ids:
        nota = (
            f"el artículo {articulo} no consta en el texto consolidado "
            "(posible derogación puntual o numeración distinta)"
        )
    else:
        try:
            info = boe.bloque(boe_id, bloque_id)
        except Exception:
            info = None
        if info and _bloque_derogado(info):
            nota = (
                f"el texto consolidado contiene una indicación de derogación "
                f"sobre el artículo {articulo}"
            )
    if nota:
        if resultado.nota:
            resultado.nota = f"{resultado.nota}. Además, {nota}"
        else:
            resultado.nota = nota.capitalize()


def _bloque_derogado(info: dict) -> bool:
    bloque = info.get("bloque", info) if isinstance(info, dict) else {}
    return "derogad" in json.dumps(bloque, ensure_ascii=False).lower()


# ---------------- UE (CELLAR) ----------------


def _verificar_ue(cita: Cita, celex: str, norma: NormaRef, cellar: CellarClient) -> ResultadoCita:
    estado = cellar.estado(celex)
    if not estado.encontrado:
        return ResultadoCita(cita=cita, estado=EstadoCita.NO_ENCONTRADA, norma=norma)
    if estado.en_vigor:
        nota = f"En vigor desde {estado.entrada_vigor}" if estado.entrada_vigor else None
        return ResultadoCita(cita=cita, estado=EstadoCita.VIGENTE, norma=norma, nota=nota)
    derogada_por = None
    if estado.derogada_por:
        celex_derogante = estado.derogada_por[0]
        derogada_por = NormaRef(
            identificador=celex_derogante,
            fuente="EUR-Lex",
            url=URL_EURLEX.format(celex=celex_derogante),
        )
    nota = f"Fin de validez: {estado.fin_validez}" if estado.fin_validez else None
    return ResultadoCita(
        cita=cita,
        estado=EstadoCita.DEROGADA,
        norma=norma,
        derogada_por=derogada_por,
        nota=nota,
    )
