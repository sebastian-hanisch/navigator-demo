"""End-to-end über Streamlits AppTest: Standardansicht, Suche, Filter, Rückfall, Adresse und der Fragen-Tab bis zum Ergebnis.

Kein Test geht ins Netz (conftest.py ersetzt den Abruf); die App läuft mit der eingebauten Kopie des Index."""

import os
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import nav_constants as C
import nav_data as D
import nav_guide as G

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _karten(at) -> list[tuple[str, str]]:
    """(Titel, Adresse) der Trefferkarten und Ergebniskarten, in der Reihenfolge auf dem Schirm."""
    out = []
    for m in at.markdown:
        g = re.match(r"^\*\*\[(.+?)\]\((https://[^)]+)\)\*\*$", m.value)
        if g:
            out.append((g.group(1), g.group(2)))
    return out


def _suche(at, q):
    at.text_input(key="q_input").set_value(q).run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


# ----------------------------------------------------------------------------------------------------------------------- Standard
def test_standardansicht_ohne_anfrage_zeigt_die_bereiche_und_keine_treffer():
    at = _app()
    assert not _karten(at)
    assert any("Die Bereiche der Website" in m.value for m in at.markdown)
    assert not at.warning
    assert at.tabs and [t.label for t in at.tabs][:2] == ["🔎 Suchen", "🧭 Fragen"]


def test_ohne_netz_steht_die_eingebaute_kopie_in_der_seitenleiste():
    at = _app()
    assert any(c.value.startswith("Eingebaute Kopie, Stand") for c in at.sidebar.caption)


def test_mit_erreichbarer_website_steht_deren_stand_dort(monkeypatch, index):
    neu = dict(index, stand="2099-12-31")
    monkeypatch.setattr(D, "fetch_remote", lambda: neu)
    at = _app()
    assert any(c.value == "Von der Website geladen, Stand 2099-12-31." for c in at.sidebar.caption)


def test_kaputter_index_von_der_website_faellt_auf_die_kopie_zurueck(monkeypatch):
    def kaputt():
        raise D.DatenFehler("Schemaversion 9")

    monkeypatch.setattr(D, "fetch_remote", kaputt)
    at = _app()
    assert any(c.value.startswith("Eingebaute Kopie") for c in at.sidebar.caption)


# ----------------------------------------------------------------------------------------------------------------------- Suche
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_jedes_beispiel_zeigt_sein_ziel_unter_den_ersten_fuenf_karten(name):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    adr = [u for _, u in _karten(at)][:5]
    assert any(z in u for u in adr for z in C.PRESET_ZIELE[name]), (name, adr)


def test_hoechstens_so_viele_karten_wie_erlaubt_und_jede_hat_einen_warum_satz():
    at = _suche(_app(), "Verfahren")
    assert 0 < len(_karten(at)) <= C.MAX_TREFFER
    warum = [c.value for c in at.caption if c.value.startswith("🔎 ")]
    assert len(warum) == len(_karten(at))


def test_nichts_gefunden_zeigt_warnung_bereiche_und_den_kontaktlink():
    at = _suche(_app(), "xqzvbnwk")
    assert not _karten(at)
    assert any("nichts Passendes" in w.value for w in at.warning)
    assert any("Die Bereiche der Website" in m.value for m in at.markdown)
    assert any("kontakt.html" in m.value for m in at.caption)


def test_der_link_zur_suche_wird_angezeigt_aber_nicht_in_die_adresse_geschrieben():
    at = _suche(_app(), "kürzester Weg")
    codes = [c.value for c in at.code]
    assert codes and codes[0] == f"{C.APP_URL}?q=k%C3%BCrzester%20Weg"
    assert "q" not in at.query_params


def test_die_adresse_wird_nur_gelesen():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.query_params["q"] = "Dijkstra"
    at.run()
    assert not at.exception
    assert at.text_input(key="q_input").value == "Dijkstra"
    assert any("dijkstra-demo" in u for _, u in _karten(at))


def test_zu_lange_adresseneingabe_wird_gekuerzt():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.query_params["q"] = "a" * 5000
    at.run()
    assert not at.exception
    assert len(at.text_input(key="q_input").value) <= 200


def test_art_filter_und_leerer_filter():
    at = _suche(_app(), "Warteschlange")
    at.multiselect(key="art_filter").set_value([C.ARTEN["Fall-Demo"]]).run()
    assert not at.exception
    assert all("Fall-Demo" in c.value for c in at.caption if c.value.startswith(("Fall-Demo", "Konzepte-Demo", "Linie", "Erklärseite")))
    at.multiselect(key="art_filter").set_value([]).run()
    assert not _karten(at)
    assert any("Mit den gewählten Filtern gibt es dazu nichts" in w.value and "Treffer: lockern Sie die Filter" in w.value for w in at.warning)


def test_bereichsfilter_zeigt_nur_treffer_dieses_bereichs(index):
    at = _suche(_app(), "Verfahren")
    bereich = at.selectbox(key="bereich_filter").options[1]
    at.selectbox(key="bereich_filter").set_value(bereich).run()
    assert not at.exception
    kn = {e["u"]: e for e in index["knoten"]}
    adr = [u for _, u in _karten(at)]
    adr_rel = [u.removeprefix(C.BASE_URL) for u in adr]
    assert adr_rel and all(kn[u]["b"] == bereich for u in adr_rel if u in kn)


def test_bedienung_ohne_ausnahme_fuer_jeden_knopf_im_standard():
    labels = [b.label for b in _app().button]
    assert labels
    for i in range(len(labels)):
        at = _app()
        at.button[i].click().run()
        assert not at.exception, (labels[i], [str(e) for e in at.exception])


# ----------------------------------------------------------------------------------------------------------------------- Fragen
def _baum_waehlen(at, bi):
    at.selectbox(key="guide_select").set_value(bi).run()
    assert not at.exception, [str(e) for e in at.exception]


def test_fragen_tab_ohne_auswahl_zeigt_einen_hinweis():
    at = _app()
    assert any("Wählen Sie eine Linie" in i.value for i in at.info)


def test_fragen_tab_fuehrt_jeden_baum_mit_der_ersten_antwort_bis_zum_ende(index):
    for bi in (0, len(index["baeume"]) // 2, len(index["baeume"]) - 1):
        at = _app()
        _baum_waehlen(at, bi)
        baum = index["baeume"][bi]
        pfad = ()
        for _ in range(12):
            if not G.antworten(baum, pfad):
                break
            at.button(key=f"antwort_{len(pfad)}_0").click().run()
            assert not at.exception, [str(e) for e in at.exception]
            pfad += (0,)
        assert not G.antworten(baum, pfad)
        assert at.session_state["guide_pfad"] == pfad
        # am Ende steht ein Ergebnis, ein Sprung oder ein Hinweis
        _, n = G.knoten_am_pfad(baum, pfad)
        if n["art"] == "ergebnis":
            assert any("Das passt zu Ihren Antworten" in s.value for s in at.success)
            assert _karten(at)
        elif n["art"] == "hinweis":
            assert any(n["text"] in w.value for w in at.warning)


def test_zurueck_und_neu_beginnen():
    at = _app()
    _baum_waehlen(at, 0)
    at.button(key="antwort_0_0").click().run()
    assert at.session_state["guide_pfad"] == (0,)
    at.button(key="zurueck").click().run()
    assert at.session_state["guide_pfad"] == ()
    at.button(key="antwort_0_0").click().run()
    at.button(key="neu_beginnen").click().run()
    assert at.session_state["guide_pfad"] == ()
    assert at.button(key="zurueck").disabled


def test_ein_sprung_fuehrt_in_den_anderen_baum_derselben_linie(index):
    ziele = [(bi, nid) for bi, b in enumerate(index["baeume"]) for nid, n in b["knoten"].items() if n["art"] == "sprung"]
    assert ziele
    bi, nid = ziele[0]
    at = _app()
    _baum_waehlen(at, bi)
    pfad = G.pfad_zu_knoten(index["baeume"][bi], nid)
    for k, i in enumerate(pfad):
        at.button(key=f"antwort_{k}_{i}").click().run()
    at.button(key="sprung").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    neu = at.session_state["guide_bi"]
    assert neu != bi and index["baeume"][neu]["linie"] == index["baeume"][bi]["linie"]
    assert at.session_state["guide_pfad"] == ()


def test_eine_beschriebene_frage_schlaegt_fragen_vor_und_steigt_dort_ein(index):
    baum = index["baeume"][0]
    q = baum["knoten"][baum["wurzel"]]["text"]
    at = _app()
    at.text_input(key="frage_input").set_value(q).run()
    assert not at.exception
    knoepfe = [b for b in at.button if b.key and b.key.startswith("vorschlag_")]
    assert 0 < len(knoepfe) <= C.MAX_VORSCHLAEGE
    knoepfe[0].click().run()
    assert not at.exception
    assert at.session_state["guide_bi"] is not None
    assert at.selectbox(key="guide_select").value == at.session_state["guide_bi"]


def test_wechsel_des_filters_loescht_den_pfad_im_fragen_tab_nicht():
    at = _app()
    _baum_waehlen(at, 0)
    at.button(key="antwort_0_0").click().run()
    at.multiselect(key="art_filter").set_value([C.ALLE_ARTEN[0]]).run()
    assert at.session_state["guide_pfad"] == (0,)


# ----------------------------------------------------------------------------------------------------------------------- Weitere Fälle
def test_gekappte_trefferzahl_wird_genannt():
    at = _suche(_app(), "Verfahren")
    satz = [i.value for i in at.info if "Treffer" in i.value]
    assert satz and re.match(rf"^Die ersten {C.MAX_TREFFER} von \d+ Treffern:", satz[0])


def test_der_link_zur_suche_steht_auch_ohne_treffer():
    at = _suche(_app(), "xqzvbnwk")
    assert [c.value for c in at.code][:1] == [f"{C.APP_URL}?q=xqzvbnwk"]


def test_eine_frage_ohne_vorschlag_sagt_das():
    at = _app()
    at.text_input(key="frage_input").set_value("xqzvbnwk").run()
    assert any("keine Frage vor" in c.value for c in at.caption)
    assert not [b for b in at.button if b.key and b.key.startswith("vorschlag_")]


def test_nach_einem_rueckfall_versucht_die_app_die_website_erneut(monkeypatch, index):
    import time

    import nav_engine as E

    at = _app()  # ohne Netz: eingebaute Kopie
    assert any(c.value.startswith("Eingebaute Kopie") for c in at.sidebar.caption)
    neu = dict(index, stand="2099-01-01")
    monkeypatch.setattr(D, "fetch_remote", lambda: neu)
    jetzt = time.time() + C.RETRY_EINGEBAUT_S + 5
    monkeypatch.setattr(E.time, "time", lambda: jetzt)  # zehn Minuten später
    at.run()
    assert any(c.value == "Von der Website geladen, Stand 2099-01-01." for c in at.sidebar.caption)


def _feindlich(index, boese):
    """Kopie des Index, in der jedes Textfeld, das die App anzeigt, ein Markdown-Link auf eine fremde Adresse ist."""
    import copy

    h = copy.deepcopy(index)
    for e in h["knoten"]:
        if e["k"] in ("Demo", "Fall-Demo"):
            e["l"], e["b"], e["d"] = boese, boese, boese + " Verfahren"
    for b in h["baeume"]:
        b["titel"] = boese
        for n in b["knoten"].values():
            n["text"] = boese
            if n["art"] == "frage":
                n["kinder"] = [[boese, c] for _, c in n["kinder"]]
    for e in h["knoten"]:
        if e["k"] == "Linie":
            e["t"] = boese
    return h


def _alle_texte(at):
    werte = [m.value for m in at.markdown] + [c.value for c in at.caption] + [b.label for b in at.button]
    werte += [i.value for i in at.info] + [w.value for w in at.warning] + [s.value for s in at.success] + [t.value for t in at.subheader]
    werte += [o for sb in at.selectbox for o in sb.options]
    return werte


def test_feindliche_texte_im_index_werden_nirgends_als_link_gerendert(monkeypatch, index):
    boese = "[KLICK](https://evil.example/x) ![bild](https://evil.example/i.png) <b>x</b>"
    monkeypatch.setattr(D, "fetch_remote", lambda: _feindlich(index, boese))
    at = _suche(_app(), "Verfahren")
    assert _karten(at)
    for wert in _alle_texte(at):
        assert "](https://evil" not in wert and "<b>" not in wert, wert
    # Fragen-Tab: Baum wählen und eine Antwort gehen
    at.selectbox(key="guide_select").set_value(0).run()
    assert not at.exception, [str(e) for e in at.exception]
    at.button(key="antwort_0_0").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    for wert in _alle_texte(at):
        assert "](https://evil" not in wert and "<b>" not in wert, wert


def test_ein_unbrauchbarer_index_der_website_wirft_nicht_sondern_faellt_zurueck(monkeypatch, index):
    kaputt = dict(index, knoten=[dict(index["knoten"][0], t=None)] + index["knoten"][1:])  # besteht keine Prüfung
    monkeypatch.setattr(D, "fetch_remote", lambda: kaputt)
    at = _app()
    assert any(c.value.startswith("Eingebaute Kopie") for c in at.sidebar.caption)
