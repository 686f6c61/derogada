"""Test de humo del scaffolding: el paquete importa y expone versión."""

import derogada


def test_version() -> None:
    assert derogada.__version__ == "0.1.0"
