"""Ingesta de documentos a texto plano."""

from derogada.ingest.loader import (
    DocumentoError,
    FormatoNoSoportadoError,
    PdfEscaneadoError,
    cargar_documento,
)

__all__ = ["DocumentoError", "FormatoNoSoportadoError", "PdfEscaneadoError", "cargar_documento"]
