# Derogada

[![PyPI](https://img.shields.io/pypi/v/derogada)](https://pypi.org/project/derogada/)
[![Python](https://img.shields.io/pypi/pyversions/derogada)](https://pypi.org/project/derogada/)
[![CI](https://github.com/686f6c61/derogada/actions/workflows/ci.yml/badge.svg)](https://github.com/686f6c61/derogada/actions/workflows/ci.yml)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-262C40.svg)](https://github.com/astral-sh/ruff)

**¿Tu demanda invoca una norma derogada sin saberlo?**

**Derogada** lee tu escrito jurídico (PDF, Word o texto), extrae cada referencia
normativa y comprueba en las fuentes oficiales (la API de datos abiertos del
**BOE** y **CELLAR / EUR-Lex**) si sigue vigente, fue modificada o está derogada.
Con enlace oficial en cada línea y propuesta de cambio anclada a la norma vigente.

Sirve tanto para revisar lo que redactas como lo que recibes: una norma derogada
en el escrito de la parte contraria es un argumento a tu favor.

[**Demo en vivo**](https://derogada.686f6c61.dev) ·
[**Documentación técnica**](https://derogada.686f6c61.dev/tecnica.html) ·
[**PyPI**](https://pypi.org/project/derogada/) ·
[**GitHub**](https://github.com/686f6c61/derogada)

```
$ derogada check demanda.pdf --format md --out informe.md
```

## Qué hace

- **Extrae las citas** del documento ("Ley 30/1992, art. 42", "Reglamento (UE)
  2016/679", "art. 217 LECrim"...) con doble canal: regex determinista + LLM opcional.
- **Las contrasta con fuentes oficiales**: API de datos abiertos del BOE y endpoint
  SPARQL de CELLAR (EUR-Lex). Sin scrapers, sin inventar.
- **Informa del estado**: VIGENTE · MODIFICADA · DEROGADA · VIGENCIA AGOTADA ·
  NO RESUELTA · NO ENCONTRADA, con la norma que deroga o modifica y su enlace oficial.
- **Verifica a dos niveles**: la norma completa y el artículo citado (que puede
  estar derogado aunque la norma siga viva).
- **Propone el cambio textual** anclado a la norma vigente equivalente, con fuente.
- Si una cita es ambigua, nunca la adivina: la marca `NO RESUELTA` con los candidatos.

## Instalación

```
pip install derogada
```

Requiere Python ≥ 3.10. Para desarrollo:

```
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Uso

```
derogada check demanda.pdf                  # informe Markdown por stdout
derogada check demanda.docx -f json -o informe.json
derogada check demanda.pdf -f tabla         # tabla en terminal
derogada check demanda.pdf --no-llm         # solo regex, sin LLM
derogada norma BOE-A-1992-26318             # estado de una norma suelta
derogada norma 32016R0679                   # también CELEX (EUR-Lex)
derogada cache clear                        # vacía la caché local
```

Como biblioteca:

```python
from derogada import analizar_documento

informe = analizar_documento("demanda.pdf")
for r in informe.resultados:
    print(r.cita.texto, "->", r.estado.value, r.derogada_por)
```

## Configuración de la IA (opcional)

El canal LLM mejora el recall con siglas y nombres comunes ("el Estatuto de los
Trabajadores", "el RGPD"...). Sin configuración, todo funciona en modo solo-regex.

```
# cualquier modelo LiteLLM: gpt-5.6, anthropic/claude-sonnet-5,
# gemini/gemini-3.5-flash, openai/qwen3.6 (endpoint propio), ollama/llama4...
export DEROGADA_MODEL="anthropic/claude-sonnet-5"
export DEROGADA_API_BASE="https://api.ejemplo/v1" # endpoint OpenAI-compatible
export DEROGADA_API_KEY="sk-..."
```

Las respuestas de las APIs oficiales se cachean localmente (SQLite, TTL 7 días,
`DEROGADA_CACHE_DIR`) para no martillear los servicios públicos.

## Cómo funciona

```
ingesta (txt/docx/pdf) → extracción (regex + LLM) → resolución (BOE-A / CELEX)
→ verificación (norma y artículo) → sugerencia anclada → informe (md/json/tabla)
```

Reglas de diseño: nunca inventar identificadores, validar todo contra la API
(`numero_oficial` y `rango`), y no proponer nada sin fuente oficial. Detalles en
la [documentación técnica](https://derogada.686f6c61.dev/tecnica.html).

## Demo web

La landing ([derogada.686f6c61.dev](https://derogada.686f6c61.dev), rama
[`landing`](https://github.com/686f6c61/derogada/tree/landing)) incluye una demo
que se ejecuta 100% en el navegador: verificación en vivo contra el BOE (CORS
abierto) y EUR-Lex (vía proxy CORS; solo viaja el CELEX, dato público).
El servidor opcional para la demo completa con IA (FastAPI, `demo/`) vive en la
misma rama `landing`, que es la que se despliega en producción.

## Desarrollo

```
ruff check src tests
pytest -q          # 51 tests con cassettes VCR grabadas: no necesita red
```

CI: ruff + pytest en Python 3.10–3.13. Publicación en PyPI con Trusted Publishing
al pushear un tag `v*`.

## Aviso

**Derogada** no ofrece asesoramiento jurídico. Los textos consolidados del BOE
tienen carácter meramente informativo: a efectos jurídicos, consulta siempre la
publicación oficial. Los datos de la UE proceden de CELLAR / EUR-Lex.

## Licencia

[CC BY-NC-SA 4.0](LICENSE) © 2026 686f6c61. Uso libre para fines **no comerciales**
con atribución, y las obras derivadas deben compartirse bajo la misma licencia
(*share-alike*). Para uso comercial, contacta con el autor para una licencia aparte.
