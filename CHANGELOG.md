# Changelog

Todos los cambios notables de Derogada se documentan en este fichero.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [0.1.0] - 2026-07-25

Primera versión pública.

### Añadido

- Pipeline completo: ingesta (`.txt`, `.md`, `.docx`, `.pdf` con detección de
  PDF escaneado) → extracción → resolución → verificación → sugerencia → informe.
- Extracción de citas a doble canal: regex determinista (patrones ES/UE, gazetteer
  de siglas, regla del conector para artículos) + LLM opcional vía LiteLLM con
  salida estructurada (JSON Schema estricto y degradación a `json_object`).
- Clientes de fuentes oficiales con caché SQLite (TTL 7 días) y reintentos:
  API de datos abiertos del BOE (metadatos, análisis, índice y bloques de texto,
  búsqueda con DSL `query_string`) y endpoint SPARQL de CELLAR/EUR-Lex
  (`resource_legal_id_celex`, `in-force`, fechas de validez, derogaciones inversas).
- Resolución de citas a identificadores oficiales (BOE-A… / CELEX) con validación
  contra `numero_oficial` y `rango`; ambigüedad → `NO RESUELTA` con candidatos.
- Verificación a dos niveles (norma y artículo citado) con estados: VIGENTE,
  MODIFICADA, DEROGADA, VIGENCIA AGOTADA, NO RESUELTA, NO ENCONTRADA.
- Sugerencias de cambio textual ancladas a la norma vigente devuelta por la API
  (sin fuente oficial, no hay sugerencia).
- CLI `derogada`: `check` (formatos md/json/tabla, `--no-llm`, `--model`),
  `norma` y `cache clear`.
- Informe en Markdown y JSON con aviso legal permanente y enlaces oficiales.
- 51 tests con cassettes VCR grabadas (offline, deterministas) + e2e opcional
  con LLM configurado. CI con ruff + pytest en Python 3.10–3.13.
- Publicación automatizada en PyPI con Trusted Publishing (OIDC) al pushear tags `v*`.

### Notas

- La landing y la demo web viven en la rama `landing` y se despliegan en
  [derogada.686f6c61.dev](https://derogada.686f6c61.dev).
- Licencia: CC BY-NC-SA 4.0 (uso no comercial con share-alike).

[0.1.0]: https://github.com/686f6c61/derogada/releases/tag/v0.1.0
