"""Spike Fase 0: verificar el endpoint SPARQL de CELLAR (EUR-Lex) con casos de control.

Casos de control:
- 32016R0679 (Reglamento (UE) 2016/679, RGPD): esperado EN VIGOR.
- 31995L0046 (Directiva 95/46/CE): esperada DEROGADA (derogada por el RGPD).

Hallazgos del spike (documentados para Fase 1):
- El CELEX limpio se consulta con `cdm:resource_legal_id_celex`.
  (`cdm:work_id_document` existe pero con valores prefijados tipo "celex:32016R0679").
- El endpoint almacena los literales como xsd:string y NO casa con literales simples
  en la query: hay que filtrar con FILTER(STR(?o) = "...").
- Vigencia: `cdm:resource_legal_in-force` ("true"/"false").
- Quién deroga: inversa de `cdm:resource_legal_repeals_resource_legal`.
- Fechas: `cdm:resource_legal_date_entry-into-force` y `cdm:resource_legal_date_end-of-validity`.

Uso: .venv/bin/python spikes/spike_cellar.py
"""

from __future__ import annotations

import sys

import httpx

ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
PREFIX = "PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>\n"

CASOS = [
    ("32016R0679", "EN VIGOR"),
    ("31995L0046", "DEROGADA"),
]

QUERY_STATUS = (
    PREFIX
    + """
SELECT ?inforce ?eif ?endval WHERE {
  ?work cdm:resource_legal_id_celex ?celex .
  FILTER(STR(?celex) = "%s")
  OPTIONAL { ?work cdm:resource_legal_in-force ?inforce }
  OPTIONAL { ?work cdm:resource_legal_date_entry-into-force ?eif }
  OPTIONAL { ?work cdm:resource_legal_date_end-of-validity ?endval }
}
"""
)

QUERY_REPEALED_BY = (
    PREFIX
    + """
SELECT DISTINCT ?celex WHERE {
  ?work cdm:resource_legal_id_celex ?c .
  FILTER(STR(?c) = "%s")
  ?other cdm:resource_legal_repeals_resource_legal ?work .
  ?other cdm:resource_legal_id_celex ?celex .
}
"""
)


def sparql(client: httpx.Client, query: str) -> list[dict]:
    resp = client.get(
        ENDPOINT,
        params={"query": query, "format": "application/sparql-results+json"},
        headers={"Accept": "application/sparql-results+json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def main() -> int:
    ok = True
    with httpx.Client() as client:
        for celex, esperado in CASOS:
            rows = sparql(client, QUERY_STATUS % celex)
            if not rows:
                print(f"[FALLO] {celex}: sin resultados en CELLAR")
                ok = False
                continue

            valores = {row["inforce"]["value"] for row in rows if "inforce" in row}
            # CELLAR codifica el booleano como "1"/"0"
            en_vigor = bool(valores & {"1", "true"})
            obtenido = "EN VIGOR" if en_vigor else "DEROGADA"
            if obtenido != esperado:
                ok = False
            marca = "OK   " if obtenido == esperado else "FALLO"
            eif = rows[0].get("eif", {}).get("value", "-")
            endval = rows[0].get("endval", {}).get("value", "-")
            print(f"[{marca}] {celex}: in-force={sorted(valores)} -> {obtenido} ({esperado=})")
            print(f"        entrada en vigor={eif} | fin de validez={endval}")

            derogantes = sparql(client, QUERY_REPEALED_BY % celex)
            for row in derogantes:
                print(f"        derogada por: {row['celex']['value']}")

    print("RESULTADO:", "OK" if ok else "FALLO")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
