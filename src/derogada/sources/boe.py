"""Cliente de la API de datos abiertos del BOE (legislación consolidada).

Verificado contra la API real (spikes de Fase 0):
- `data` puede venir envuelto en una lista de un único elemento (p. ej. /metadatos).
- El análisis jurídico anida las relaciones así:
  {"posteriores": [{"posterior": [{id_norma, relacion, texto}, ...]}]}
- Los metadatos traen: estatus_derogacion, vigencia_agotada, fecha_derogacion,
  estado_consolidacion, numero_oficial, rango, url_html_consolidada, url_eli.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from derogada.sources.cache import Cache

BASE_URL = "https://www.boe.es/datosabiertos/api"
ID_BOE_RE = re.compile(r"^BOE-[A-Z]-\d{4}-\d{1,6}$")


class BoeClient:
    """Cliente síncrono con caché, reintentos y normalización de la respuesta."""

    def __init__(self, cache: Cache | None = None, timeout: float = 30.0) -> None:
        self._cache = cache if cache is not None else Cache()
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"Accept": "application/json", "User-Agent": "derogada/0.1"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BoeClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---------------- HTTP ----------------

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any | None:
        clave = path + "|" + json.dumps(params or {}, sort_keys=True)
        guardado = self._cache.get(clave)
        if guardado is not None:
            return guardado
        resp = self._client.get(path, params=params)
        if resp.status_code in (400, 404):
            return None  # identificador no válido o sin datos
        resp.raise_for_status()
        data = resp.json().get("data")
        if isinstance(data, list) and len(data) == 1:
            data = data[0]
        if data is not None:
            self._cache.set(clave, data)
        return data

    # ---------------- API ----------------

    def metadatos(self, boe_id: str) -> dict[str, Any] | None:
        """Metadatos de la norma: vigencia, derogación, rango, número oficial, URLs."""
        self._valida_id(boe_id)
        return self._request(f"/legislacion-consolidada/id/{boe_id}/metadatos")

    def analisis(self, boe_id: str) -> dict[str, Any] | None:
        """Análisis jurídico: materias, notas y referencias a otras normas."""
        self._valida_id(boe_id)
        return self._request(f"/legislacion-consolidada/id/{boe_id}/analisis")

    def referencias_posteriores(self, boe_id: str) -> list[dict[str, Any]]:
        """Relaciones posteriores aplanadas: quién deroga/modifica/añade esta norma.

        Cada item: {"id_norma": str, "relacion": {"codigo", "texto"}, "texto": str}.
        """
        analisis = self.analisis(boe_id) or {}
        referencias = analisis.get("referencias", {}) or {}
        salida: list[dict[str, Any]] = []
        for grupo in referencias.get("posteriores", []) or []:
            if isinstance(grupo, dict):
                salida.extend(grupo.get("posterior", []) or [])
        return salida

    def indice(self, boe_id: str) -> list[dict[str, Any]]:
        """Índice del texto consolidado (bloques: artículos, disposiciones...)."""
        self._valida_id(boe_id)
        data = self._request(f"/legislacion-consolidada/id/{boe_id}/texto/indice") or {}
        if isinstance(data, dict):
            bloques = data.get("bloque", []) or []
            return bloques if isinstance(bloques, list) else [bloques]
        return []

    def bloque(self, boe_id: str, bloque_id: str) -> dict[str, Any] | None:
        """Contenido y versiones de un bloque concreto (p. ej. artículo 'a42')."""
        self._valida_id(boe_id)
        return self._request(f"/legislacion-consolidada/id/{boe_id}/texto/bloque/{bloque_id}")

    def buscar(self, consulta: str, limite: int = 5) -> list[dict[str, Any]]:
        """Búsqueda en la legislación consolidada por texto del título.

        La API usa un DSL tipo Elasticsearch en el parámetro `query` (JSON):
        {"query": {"query_string": {"query": "titulo:(...)"}}}.
        Los resultados traen `numero_oficial` y `rango`, útiles para desambiguar.
        """
        consulta = consulta.replace('"', " ").strip()
        query_json = json.dumps(
            {"query": {"query_string": {"query": f"titulo:({consulta})"}}},
            ensure_ascii=False,
        )
        data = self._request(
            "/legislacion-consolidada",
            params={"query": query_json, "limit": limite, "offset": 0},
        )
        if not data:
            return []
        resultados = data if isinstance(data, list) else [data]
        return resultados[:limite]

    @staticmethod
    def _valida_id(boe_id: str) -> None:
        if not ID_BOE_RE.match(boe_id):
            raise ValueError(f"Identificador BOE no válido: {boe_id!r} (esperado BOE-A-AAAA-NNNNN)")
