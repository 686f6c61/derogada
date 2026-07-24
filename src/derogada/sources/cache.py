"""Caché SQLite para respuestas de las APIs oficiales (BOE / CELLAR).

Evita martillear las fuentes oficiales: una misma norma citada 20 veces
provoca una única petición real por TTL.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

_TTL_POR_DEFECTO = 7 * 24 * 3600  # 7 días


def ruta_por_defecto() -> Path:
    base = os.environ.get("DEROGADA_CACHE_DIR")
    if base:
        return Path(base) / "cache.sqlite3"
    return Path.home() / ".cache" / "derogada" / "cache.sqlite3"


class Cache:
    """Caché clave-valor con TTL (clave: URL + parámetros; valor: JSON)."""

    def __init__(self, ruta: str | Path | None = None, ttl: int = _TTL_POR_DEFECTO) -> None:
        self.ttl = ttl
        if ruta is not None and str(ruta) == ":memory:":
            self.ruta = None
            self._db = sqlite3.connect(":memory:")
        else:
            self.ruta = Path(ruta) if ruta else ruta_por_defecto()
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(self.ruta)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS cache (clave TEXT PRIMARY KEY, valor TEXT, ts REAL)"
        )

    def get(self, clave: str) -> Any | None:
        fila = self._db.execute(
            "SELECT valor, ts FROM cache WHERE clave = ?", (clave,)
        ).fetchone()
        if not fila:
            return None
        valor, ts = fila
        if time.time() - ts > self.ttl:
            self._db.execute("DELETE FROM cache WHERE clave = ?", (clave,))
            self._db.commit()
            return None
        return json.loads(valor)

    def set(self, clave: str, valor: Any) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO cache (clave, valor, ts) VALUES (?, ?, ?)",
            (clave, json.dumps(valor, ensure_ascii=False), time.time()),
        )
        self._db.commit()

    def clear(self) -> int:
        cur = self._db.execute("DELETE FROM cache")
        self._db.commit()
        return cur.rowcount

    def close(self) -> None:
        self._db.close()
