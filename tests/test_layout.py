"""Layout (DEMO-PLAYBOOK §2): fester Kopf, Schnellstart oben in der Seitenleiste, aktives Beispiel hervorgehoben.

Die Hervorhebung ist zustandslos (`aktives_preset` vergleicht jede Einstellung aus SETTING_SPECS mit dem Beispiel). Der Test unten stellt
sicher, dass wirklich JEDE Einstellung dort steht: sonst bliebe das Beispiel trotz Änderung markiert."""

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import nav_constants as C
import nav_presets as P

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))
REGLER_ARTEN = ("slider", "number_input", "select_slider", "selectbox", "radio", "toggle", "checkbox", "text_input", "multiselect")


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _typen(at) -> dict:
    """Button-Typ je Beispiel-Name (die Schnellstart-Buttons der Seitenleiste)."""
    return {b.label: b.proto.type for b in at.sidebar.button if b.label in C.PRESETS}


def _regler(at, key):
    for container in (at.sidebar, at.main):
        for art in REGLER_ARTEN:
            try:
                return getattr(container, art)(key=key)
            except KeyError:
                continue
    raise AssertionError(f"Einstellung {key} steht weder in der Seitenleiste noch im Hauptbereich")


def test_beispiele_stehen_in_der_seitenleiste_und_nicht_im_hauptbereich():
    at = _app()
    assert [b.label for b in at.sidebar.button][: len(C.PRESETS)] == list(C.PRESETS)
    assert not [b for b in at.main.button if b.label in C.PRESETS]


def test_titel_steht_im_festen_kopf():
    at = _app()
    assert "st-key-kopf" in " ".join(h.proto.body for h in at.get("html"))
    assert at.title[0].value


def test_beim_start_ist_kein_beispiel_hervorgehoben():
    assert "primary" not in _typen(_app()).values()  # das Suchfeld ist leer


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_angeklicktes_beispiel_ist_hervorgehoben_und_bleibt_es_im_naechsten_lauf(name):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert at.text_input(key="q_input").value == C.PRESETS[name]["q"]
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]
    at.run()
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]


def test_jede_einstellung_der_seitenleiste_steht_in_setting_specs():
    at = _app()
    schluessel = {w.key for art in REGLER_ARTEN for w in getattr(at.sidebar, art) if w.key}
    assert schluessel, "keine Einstellungen in der Seitenleiste gefunden"
    fehlt = schluessel - set(P.SETTING_SPECS)
    assert not fehlt, f"{sorted(fehlt)} fehlen in SETTING_SPECS: ihre Änderung hebt das aktive Beispiel nicht auf"


@pytest.mark.parametrize("state_key", list(P.SETTING_SPECS))
def test_jede_aenderung_einer_einstellung_hebt_die_hervorhebung_auf(state_key):
    at = _app()
    name = next(iter(C.PRESETS))
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert _typen(at)[name] == "primary"
    regler = _regler(at, state_key)
    if state_key == "q_input":
        regler.set_value(C.PRESETS[name]["q"] + " zusätzlich").run()
    elif state_key == "art_filter":
        regler.set_value([C.ALLE_ARTEN[0]]).run()
    else:
        regler.set_value(at.selectbox(key="bereich_filter").options[1]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert "primary" not in _typen(at).values()
    at.sidebar.button(key=f"preset_{name}").click().run()  # erneutes Anklicken markiert wieder und setzt die Filter zurück
    assert _typen(at)[name] == "primary"
