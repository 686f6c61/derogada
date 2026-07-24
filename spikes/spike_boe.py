"""Spike Fase 0: verificar la API de datos abiertos del BOE con casos de control.

Casos de control:
- Ley 30/1992 (BOE-A-1992-26318): esperada DEROGADA (por Leyes 39/2015 y 40/2015).
- Ley 39/2015 (BOE-A-2015-10565): esperada VIGENTE.

Además imprime las referencias posteriores del análisis jurídico (quién deroga/modifica)
y prueba el acceso al índice del texto (bloques de artículos).

Uso: .venv/bin/python spikes/spike_boe.py
"""

from __future__ import annotations

import sys
from typing import Any

import httpx

BASE = "https://www.boe.es/datosabiertos/api"
HEADERS = {"Accept": "application/json"}

CASOS = [
    ("BOE-A-1992-26318", "DEROGADA"),
    ("BOE-A-2015-10565", "VIGENTE"),
]


def get(client: httpx.Client, path: str) -> Any:
    resp = client.get(f"{BASE}{path}", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()["data"]
    # La API envuelve a veces el resultado en una lista de un único elemento (p. ej. /metadatos)
    if isinstance(data, list) and len(data) == 1:
        return data[0]
    return data


def estado(meta: dict) -> str:
    if meta.get("estatus_derogacion") == "S":
        return "DEROGADA"
    if meta.get("vigencia_agotada") == "S":
        return "VIGENCIA AGOTADA"
    return "VIGENTE"


def main() -> int:
    ok = True
    with httpx.Client() as client:
        for boe_id, esperado in CASOS:
            meta = get(client, f"/legislacion-consolidada/id/{boe_id}/metadatos")
            titulo = str(meta.get("titulo", ""))[:70]
            obtenido = estado(meta)
            if obtenido != esperado:
                ok = False
            marca = "OK   " if obtenido == esperado else "FALLO"
            print(f"[{marca}] {boe_id} — {titulo}")
            print(
                f"        estado={obtenido} (esperado={esperado})"
                f" | estatus_derogacion={meta.get('estatus_derogacion')}"
                f" | vigencia_agotada={meta.get('vigencia_agotada')}"
                f" | estado_consolidacion={meta.get('estado_consolidacion')}"
            )
            print(f"        url_html_consolidada={meta.get('url_html_consolidada')}")

            analisis = get(client, f"/legislacion-consolidada/id/{boe_id}/analisis")
            referencias = (analisis or {}).get("referencias", {}) or {}
            # Estructura real: {"posteriores": [{"posterior": [{id_norma, relacion, texto}, ...]}]}
            posteriores: list[dict] = []
            for grupo in referencias.get("posteriores", []) or []:
                if isinstance(grupo, dict):
                    posteriores.extend(grupo.get("posterior", []) or [])
            for ref in posteriores[:5]:
                relacion = ref.get("relacion", "")
                if isinstance(relacion, dict):
                    relacion = relacion.get("texto", "")
                print(
                    f"        ref posterior: {relacion} {str(ref.get('texto', ''))[:60]}"
                    f" [{ref.get('id_norma', '-')}]"
                )

            indice = get(client, f"/legislacion-consolidada/id/{boe_id}/texto/indice")
            bloques = (indice or {}).get("bloque", []) or []
            print(f"        bloques de texto en el índice: {len(bloques)}")
            print()

    print("RESULTADO:", "OK" if ok else "FALLO")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
