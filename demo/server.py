"""Servidor de demo de Derogada: sirve la landing y expone el pipeline por HTTP.

Instalación:  pip install -e ".[demo]"
Arranque:     .venv/bin/python demo/server.py   ->  http://localhost:8000
Producción:   uvicorn demo.server:app --host 0.0.0.0 --port 8000

Endpoints:
- POST /api/check  {"texto": "...", "usar_llm": true}  -> informe JSON
- GET  /api/norma/{identificador}  (BOE-A-AAAA-NNNNN o CELEX) -> estado JSON
- GET  /api/config -> {"llm": bool, "max_caracteres": int}
- GET  /*          -> landing estática (landing/index.html, tecnica.html)
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from derogada.check.status import verificar_cita
from derogada.ingest import DocumentoError
from derogada.models import Cita, Informe, Jurisdiccion
from derogada.pipeline import analizar_texto
from derogada.resolve.resolver import Resolucion
from derogada.sources import BoeClient, CellarClient

logger = logging.getLogger("derogada.demo")

MSG_FUENTES = "Error consultando las fuentes oficiales. Inténtalo de nuevo."

LANDING_DIR = Path(__file__).resolve().parent.parent / "landing"
MAX_CARACTERES = 50_000
RATE_LIMIT_POR_MINUTO = 30

app = FastAPI(title="Derogada demo", version="0.1.0")
_peticiones: dict[str, list[float]] = defaultdict(list)


class PeticionCheck(BaseModel):
    texto: str = Field(min_length=1, max_length=MAX_CARACTERES)
    usar_llm: bool = True


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "?"
    ahora = time.time()
    _peticiones[ip] = [t for t in _peticiones[ip] if ahora - t < 60]
    if len(_peticiones[ip]) >= RATE_LIMIT_POR_MINUTO:
        raise HTTPException(429, "Demasiadas peticiones; espera un minuto.")
    _peticiones[ip].append(ahora)


def _informe_dict(informe: Informe) -> dict:
    datos = informe.model_dump(mode="json")
    datos["resumen"] = informe.resumen.model_dump(mode="json")
    return datos


@app.get("/api/config")
def config() -> dict:
    return {"llm": bool(os.environ.get("DEROGADA_MODEL")), "max_caracteres": MAX_CARACTERES}


@app.post("/api/check")
def check(peticion: PeticionCheck, request: Request) -> JSONResponse:
    _rate_limit(request)
    try:
        informe = analizar_texto(
            peticion.texto,
            documento="demo web",
            usar_llm=peticion.usar_llm,
            con_sugerencias=peticion.usar_llm,
        )
    except DocumentoError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        logger.exception("fallo consultando fuentes oficiales en /api/check")
        raise HTTPException(502, MSG_FUENTES) from exc
    return JSONResponse(_informe_dict(informe))


@app.get("/api/norma/{identificador}")
def norma(identificador: str, request: Request) -> JSONResponse:
    _rate_limit(request)
    es_boe = identificador.upper().startswith("BOE-")
    cita = Cita(
        texto=identificador,
        jurisdiccion=Jurisdiccion.ES if es_boe else Jurisdiccion.UE,
    )
    resolucion = Resolucion(
        identificador=identificador,
        fuente="BOE" if es_boe else "EUR-Lex",
    )
    try:
        with BoeClient() as boe, CellarClient() as cellar:
            resultado = verificar_cita(cita, resolucion, boe, cellar)
    except Exception as exc:
        logger.exception("fallo consultando fuentes oficiales en /api/norma")
        raise HTTPException(502, MSG_FUENTES) from exc
    return JSONResponse(resultado.model_dump(mode="json"))


# La landing estática al final, para que /api tenga prioridad
app.mount("/", StaticFiles(directory=LANDING_DIR, html=True), name="landing")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
