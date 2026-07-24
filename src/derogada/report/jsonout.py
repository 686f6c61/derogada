"""Render del informe a JSON (máquina-legible)."""

from __future__ import annotations

import json

from derogada.models import Informe


def render_json(informe: Informe) -> str:
    datos = informe.model_dump(mode="json")
    datos["resumen"] = informe.resumen.model_dump(mode="json")
    return json.dumps(datos, ensure_ascii=False, indent=2, default=str)
