"""Derogada: verifica la vigencia de las normas citadas en documentos jurídicos."""

__version__ = "0.1.0"


def __getattr__(nombre: str):
    # Importación perezosa: evita cargar httpx/litellm con `import derogada`
    if nombre in {"analizar_documento", "analizar_texto"}:
        from derogada import pipeline

        return getattr(pipeline, nombre)
    if nombre in {"Informe", "Cita", "ResultadoCita", "EstadoCita", "Jurisdiccion"}:
        from derogada import models

        return getattr(models, nombre)
    raise AttributeError(f"module 'derogada' has no attribute {nombre!r}")


__all__ = [
    "Cita",
    "EstadoCita",
    "Informe",
    "Jurisdiccion",
    "ResultadoCita",
    "analizar_documento",
    "analizar_texto",
]
