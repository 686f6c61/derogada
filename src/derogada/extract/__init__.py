"""Extracción de referencias normativas: canal regex + canal LLM."""

from derogada.extract.extractor import extraer_citas
from derogada.extract.llm import configurado

__all__ = ["configurado", "extraer_citas"]
