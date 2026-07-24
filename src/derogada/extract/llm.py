"""Extracción de citas con LLM vía LiteLLM (salida estructurada JSON Schema).

Configuración por variables de entorno:
- DEROGADA_MODEL: modelo LiteLLM ("openai/qwen3.6", "gpt-4o-mini", "ollama/llama3.1"...).
- DEROGADA_API_BASE / DEROGADA_API_KEY: endpoint y clave (proveedores OpenAI-compatibles).

Sin DEROGADA_MODEL el canal LLM se desactiva y devuelve lista vacía (modo solo regex).
"""

from __future__ import annotations

import json
import os
import re

from derogada.extract.gazetteer import buscar_alias
from derogada.extract.patterns import canon_rango, norm_numero
from derogada.models import Cita, Jurisdiccion

MAX_CARACTERES_TROZO = 60_000
_SOLAPE = 1_000

SCHEMA_CITAS = {
    "type": "object",
    "properties": {
        "citas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string"},
                    "jurisdiccion": {"type": "string", "enum": ["ES", "UE"]},
                    "rango": {"type": ["string", "null"]},
                    "numero": {"type": ["string", "null"]},
                    "articulo": {"type": ["string", "null"]},
                    "alias": {"type": ["string", "null"]},
                },
                "required": ["texto", "jurisdiccion", "rango", "numero", "articulo", "alias"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["citas"],
    "additionalProperties": False,
}

_PROMPT_SISTEMA = (
    "Eres un extractor de referencias normativas de documentos jurídicos españoles. "
    "Respondes exclusivamente con JSON válido conforme al esquema indicado."
)

_PROMPT_USUARIO = """Extrae TODAS las referencias normativas del documento jurídico siguiente.

Incluye leyes, leyes orgánicas, reales decretos, reales decretos-ley, decretos, órdenes,
reglamentos y directivas de la UE, y menciones por siglas o nombre común (LEC, LECrim, LRJCA,
LPAC, ET, CE, RGPD, LOPDGDD, Código Civil, Código Penal, Estatuto de los Trabajadores...).

Reglas:
- "texto": la cita literal tal como aparece (máximo 80 caracteres).
- "jurisdiccion": "ES" (normativa española) o "UE" (Derecho de la Unión Europea).
- "numero": formato "30/1992" o "2016/679" si consta; si no, null.
- "articulo": solo si se cita un artículo concreto ligado a esa norma ("42", "6.1").
- "alias": la sigla o nombre común si la cita no usa número oficial.
- NO inventes referencias que no estén escritas. NO incluyas jurisprudencia ni sentencias.

Documento:
---
{texto}
---"""


def configurado() -> bool:
    """True si hay modelo LLM configurado por entorno."""
    return bool(os.environ.get("DEROGADA_MODEL"))


def _trozos(texto: str) -> list[str]:
    """Trocea por párrafos con solape para no cortar citas por la mitad."""
    if len(texto) <= MAX_CARACTERES_TROZO:
        return [texto]
    trozos: list[str] = []
    inicio = 0
    while inicio < len(texto):
        fin = min(len(texto), inicio + MAX_CARACTERES_TROZO)
        corte = texto.rfind("\n\n", inicio, fin)
        if corte > inicio + MAX_CARACTERES_TROZO // 2:
            fin = corte
        trozos.append(texto[inicio:fin])
        inicio = max(inicio + 1, fin - _SOLAPE)
    return trozos


def _contexto(cita_texto: str, documento: str) -> str | None:
    idx = documento.find(cita_texto)
    if idx < 0:
        return None
    izq = max(0, idx - 120)
    der = min(len(documento), idx + len(cita_texto) + 120)
    return re.sub(r"\s+", " ", documento[izq:der]).strip()


def _parsear(contenido: str) -> list[dict]:
    """JSON estricto; tolera fences ```json de modelos que lo envuelven."""
    contenido = contenido.strip()
    if contenido.startswith("```"):
        contenido = re.sub(r"^```(?:json)?\s*|\s*```$", "", contenido, flags=re.MULTILINE).strip()
    datos = json.loads(contenido)
    if isinstance(datos, list):
        return datos
    return datos.get("citas", [])


def extraer_citas_llm(texto: str, modelo: str | None = None) -> list[Cita]:
    """Citas detectadas por el LLM. Lista vacía si no hay modelo configurado."""
    modelo = modelo or os.environ.get("DEROGADA_MODEL")
    if not modelo:
        return []

    import litellm

    extra: dict = {}
    if base := os.environ.get("DEROGADA_API_BASE"):
        extra["api_base"] = base
    if key := os.environ.get("DEROGADA_API_KEY"):
        extra["api_key"] = key

    citas: list[Cita] = []
    for trozo in _trozos(texto):
        mensajes = [
            {"role": "system", "content": _PROMPT_SISTEMA},
            {"role": "user", "content": _PROMPT_USUARIO.format(texto=trozo)},
        ]
        try:
            resp = litellm.completion(
                model=modelo,
                messages=mensajes,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "citas", "strict": True, "schema": SCHEMA_CITAS},
                },
                temperature=0,
                **extra,
            )
        except litellm.BadRequestError:
            # Proveedores sin json_schema: degradar a json_object
            resp = litellm.completion(
                model=modelo,
                messages=mensajes,
                response_format={"type": "json_object"},
                temperature=0,
                **extra,
            )
        contenido = resp.choices[0].message.content or ""
        for item in _parsear(contenido):
            try:
                citas.append(_a_cita(item, texto))
            except (KeyError, ValueError):
                continue  # descarta entradas mal formadas del modelo
    return citas


def _a_cita(item: dict, documento: str) -> Cita:
    """Normaliza la cita del LLM a las mismas convenciones del canal regex.

    Si el alias casa con el gazetteer, este manda sobre el número y el rango:
    el modelo puede recordar una versión histórica (p. ej. ET = Ley 8/1980)
    cuando la remisión vigente es otra (RDL 2/2015).
    """
    rango = item.get("rango")
    numero = item.get("numero")
    alias = item.get("alias")
    if alias:
        entrada = buscar_alias(str(alias))
        if entrada is not None:
            alias = entrada.alias
            if entrada.numero:
                numero = entrada.numero
            if entrada.rango:
                rango = entrada.rango
    texto = str(item["texto"])[:80]
    return Cita(
        texto=texto,
        jurisdiccion=Jurisdiccion(item.get("jurisdiccion", "ES")),
        rango=canon_rango(str(rango)) if rango else None,
        numero=norm_numero(numero),
        articulo=item.get("articulo"),
        alias=alias,
        contexto=_contexto(texto, documento),
    )
