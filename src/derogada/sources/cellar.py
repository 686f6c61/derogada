"""Cliente SPARQL para CELLAR (EUR-Lex / Oficina de Publicaciones de la UE).

Verificado contra el endpoint real (spikes de Fase 0):
- CELEX limpio: `cdm:resource_legal_id_celex`.
  (`cdm:work_id_document` usa valores prefijados tipo "celex:32016R0679").
- El endpoint NO casa literales simples con xsd:string: hay que usar
  FILTER(STR(?o) = "...").
- Vigencia: `cdm:resource_legal_in-force` codificado "1"/"0".
- Quién deroga: inversa de `cdm:resource_legal_repeals_resource_legal`.
- Fechas: `cdm:resource_legal_date_entry-into-force` / `..._date_end-of-validity`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from derogada.sources.cache import Cache

ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
_PREFIX = "PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>\n"

_QUERY_ESTADO = (
    _PREFIX
    + """
SELECT ?inforce ?eif ?endval WHERE {
  ?work cdm:resource_legal_id_celex ?celex .
  FILTER(STR(?celex) = "__CELEX__")
  OPTIONAL { ?work cdm:resource_legal_in-force ?inforce }
  OPTIONAL { ?work cdm:resource_legal_date_entry-into-force ?eif }
  OPTIONAL { ?work cdm:resource_legal_date_end-of-validity ?endval }
}
"""
)

_QUERY_DEROGADA_POR = (
    _PREFIX
    + """
SELECT DISTINCT ?derogante WHERE {
  ?work cdm:resource_legal_id_celex ?c .
  FILTER(STR(?c) = "__CELEX__")
  ?otro cdm:resource_legal_repeals_resource_legal ?work .
  ?otro cdm:resource_legal_id_celex ?derogante .
}
"""
)



@dataclass
class EstadoCellar:
    """Estado de un acto de la UE según CELLAR."""

    celex: str
    encontrado: bool
    en_vigor: bool | None = None
    entrada_vigor: str | None = None
    fin_validez: str | None = None
    derogada_por: list[str] = field(default_factory=list)


class CellarClient:
    """Cliente síncrono del endpoint SPARQL de CELLAR, con caché y reintentos."""

    def __init__(self, cache: Cache | None = None, timeout: float = 60.0) -> None:
        self._cache = cache if cache is not None else Cache()
        self._client = httpx.Client(
            headers={"Accept": "application/sparql-results+json", "User-Agent": "derogada/0.1"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CellarClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        reraise=True,
    )
    def _sparql(self, query: str) -> list[dict[str, str]]:
        guardado = self._cache.get(query)
        if guardado is not None:
            return guardado
        resp = self._client.get(
            ENDPOINT,
            params={"query": query, "format": "application/sparql-results+json"},
        )
        resp.raise_for_status()
        bindings = resp.json()["results"]["bindings"]
        filas = [{var: val["value"] for var, val in fila.items()} for fila in bindings]
        self._cache.set(query, filas)
        return filas

    def estado(self, celex: str) -> EstadoCellar:
        """Vigencia del acto: encontrado, en_vigor y fechas de validez."""
        self._valida_celex(celex)
        filas = self._sparql(_QUERY_ESTADO.replace("__CELEX__", celex))
        if not filas:
            return EstadoCellar(celex=celex, encontrado=False)
        valores = {f["inforce"] for f in filas if "inforce" in f}
        en_vigor = bool(valores & {"1", "true"}) if valores else None
        return EstadoCellar(
            celex=celex,
            encontrado=True,
            en_vigor=en_vigor,
            entrada_vigor=filas[0].get("eif"),
            fin_validez=filas[0].get("endval"),
            derogada_por=self.derogada_por(celex),
        )

    def derogada_por(self, celex: str) -> list[str]:
        """CELEX de los actos que derogan este acto (lista vacía si ninguno)."""
        self._valida_celex(celex)
        filas = self._sparql(_QUERY_DEROGADA_POR.replace("__CELEX__", celex))
        return [f["derogante"] for f in filas if "derogante" in f]

    @staticmethod
    def _valida_celex(celex: str) -> None:
        # Blanqueo estricto: el CELEX se interpola en la query SPARQL
        if not re.match(r"^[0-9A-Za-z()]+$", celex):
            raise ValueError(f"CELEX no válido: {celex!r}")
