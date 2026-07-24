"""Tests del cargador de documentos (txt/md/docx/pdf)."""

from __future__ import annotations

import pymupdf
import pytest
from docx import Document

from derogada.ingest import (
    DocumentoError,
    FormatoNoSoportadoError,
    PdfEscaneadoError,
    cargar_documento,
)

TEXTO = "Se cita el artículo 42 de la Ley 30/1992."


def test_txt(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_text(TEXTO, encoding="utf-8")
    assert cargar_documento(p) == TEXTO


def test_md(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text(f"# Título\n\n{TEXTO}", encoding="utf-8")
    assert TEXTO in cargar_documento(p)


def test_docx(tmp_path):
    doc = Document()
    doc.add_paragraph(TEXTO)
    p = tmp_path / "doc.docx"
    doc.save(p)
    assert TEXTO in cargar_documento(p)


def test_pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), TEXTO)
    p = tmp_path / "doc.pdf"
    doc.save(p)
    doc.close()
    assert "Ley 30/1992" in cargar_documento(p)


def test_pdf_escaneado(tmp_path):
    doc = pymupdf.open()
    doc.new_page()  # página en blanco: sin capa de texto
    p = tmp_path / "scan.pdf"
    doc.save(p)
    doc.close()
    with pytest.raises(PdfEscaneadoError):
        cargar_documento(p)


def test_formato_no_soportado(tmp_path):
    p = tmp_path / "doc.xyz"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(FormatoNoSoportadoError):
        cargar_documento(p)


def test_no_existe():
    with pytest.raises(DocumentoError):
        cargar_documento("/no/existe/en/absoluto.txt")
