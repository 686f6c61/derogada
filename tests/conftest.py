"""Configuración de pytest: caché aislada por test y cassettes VCR."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _cache_aislada(tmp_path, monkeypatch):
    monkeypatch.setenv("DEROGADA_CACHE_DIR", str(tmp_path / "cache"))


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "cassette_library_dir": "tests/cassettes",
        "record_mode": "once",
        "filter_headers": ["authorization"],
    }
