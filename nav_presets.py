"""Schnellstart (Beispielanfragen), Lesen der Adresszeile und Einstellungen des Navigators (Gerüst aus tools/new_demo.py, angepasst).

Die Adresszeile wird nur gelesen (`?q=…`), nie geschrieben: Eingaben können Persönliches enthalten und würden sonst im Browserverlauf und in
Protokollen der Cloud landen. Wer eine Suche teilen will, bekommt den Link auf Wunsch angezeigt (app.py)."""

from dataclasses import dataclass
from urllib.parse import quote

import streamlit as st

import nav_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str | None
    default: object


SETTING_SPECS = {
    "q_input": SettingSpec("q", ""),
    "art_filter": SettingSpec(None, list(C.ALLE_ARTEN)),
    "bereich_filter": SettingSpec(None, C.ALLE_BEREICHE),
}
PRESET_KEYS = {"q": "q_input"}
Q_MAX = 200  # längere Anfragen schneidet die Adresse ab (Schutz vor überlangen Adressen)


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = list(spec.default) if isinstance(spec.default, list) else spec.default


def load_permalink_settings():
    """Einmal je Sitzung: `?q=` ins Suchfeld übernehmen (gekürzt auf Q_MAX Zeichen). Die Adresse wird nicht zurückgeschrieben."""
    if "permalink_loaded" in st.session_state:
        return
    try:
        q = st.query_params.get("q", "")
    except Exception:
        q = ""
    if isinstance(q, str) and q.strip():
        st.session_state["q_input"] = q.strip()[:Q_MAX]
    st.session_state["permalink_loaded"] = True


def sanitize_filters(bereiche: list[str]):
    """Ein gemerkter Bereich, den der Index nicht mehr kennt, wird zu „Alle Bereiche“ (sonst wirft das Auswahlfeld)."""
    if st.session_state.get("bereich_filter") not in [C.ALLE_BEREICHE, *bereiche]:
        st.session_state["bereich_filter"] = C.ALLE_BEREICHE
    gueltig = [a for a in st.session_state.get("art_filter", []) if a in C.ALLE_ARTEN]
    if gueltig != st.session_state.get("art_filter"):
        st.session_state["art_filter"] = gueltig


def apply_preset(name):
    """Beispielanfrage ins Suchfeld; die Filter gehen auf ihren Standard zurück, damit das Beispiel ohne Einschränkung läuft."""
    for key, state_key in PRESET_KEYS.items():
        if key in C.PRESETS[name]:
            st.session_state[state_key] = C.PRESETS[name][key]
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in PRESET_KEYS.values():
            st.session_state[state_key] = list(spec.default) if isinstance(spec.default, list) else spec.default


def aktives_preset():
    """Name des Beispiels, dessen Anfrage GENAU im Suchfeld steht und bei dem alle Filter auf dem Standard stehen, sonst None."""
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        if all(
            st.session_state.get(state_key, spec.default) == preset.get(preset_key_of.get(state_key), spec.default)
            for state_key, spec in SETTING_SPECS.items()
        ):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Beispiel ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Eine Beispielanfrage einsetzen:")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def link_zur_suche(q: str) -> str:
    """Adresse der App mit der Anfrage, zum Teilen. Wird nur auf Wunsch angezeigt."""
    return f"{C.APP_URL}?q={quote(q.strip()[:Q_MAX], safe='')}"
