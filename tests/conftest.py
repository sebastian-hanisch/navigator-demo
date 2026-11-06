"""Gemeinsame Fixtures. Kein Test geht ins Netz: der Abruf des Index ist ersetzt, die eingebaute Kopie dient als Daten."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import nav_data as D  # noqa: E402
import nav_engine as E  # noqa: E402


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Der Abruf der Website scheitert in jedem Test; die App fällt auf die eingebaute Kopie zurück. Der Zwischenspeicher von Streamlit
    wird geleert, damit kein Test die Suchumgebung eines anderen erbt."""
    import streamlit as st

    def kein_netz(*_a, **_k):
        raise D.DatenFehler("Test: kein Netz")

    monkeypatch.setattr(D, "fetch_remote", kein_netz)
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture(scope="session")
def index():
    return D.load_bundled()


@pytest.fixture(scope="session")
def eng(index):
    return E.build_engine(index, D.QUELLE_EINGEBAUT)
