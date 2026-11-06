"""Eigenschaften des Suchkerns an der eingebauten Kopie des Index (dieselben wie im Website-Repo, tests/test_navigator.py)."""

import pytest

import nav_constants as C
import nav_engine as E
import nav_search as ns


def _adressen(eng, treffer):
    return [eng.index["knoten"][t["i"]]["u"] for t in treffer]


def test_leer_und_unsinn_geben_keine_antwort(eng):
    for q in ("", "   ", "xqzvbnwk", "wie wer was"):
        assert eng.maschine.suche(q) == [], q


def test_jede_linie_steht_bei_ihrem_titel_unter_den_ersten_drei(eng):
    for e in eng.index["knoten"]:
        if e["k"] == "Linie":
            assert e["u"] in _adressen(eng, eng.maschine.suche(e["t"], limit=3)), e["t"]


def test_jede_fall_demo_steht_bei_ihrem_titel_unter_den_ersten_fuenf(eng):
    fehl = [e["t"] for e in eng.index["knoten"] if e["k"] == "Fall-Demo" and e["u"] not in _adressen(eng, eng.maschine.suche(e["t"], limit=5))]
    assert fehl == []


def test_gross_klein_und_umlaut_schreibweise_aendern_nichts(eng):
    a = [t["i"] for t in eng.maschine.suche("Kürzester Weg")]
    b = [t["i"] for t in eng.maschine.suche("kuerzester WEG")]
    assert a == b and a


def test_stoppwoerter_aendern_die_rangfolge_nicht(eng):
    assert [t["i"] for t in eng.maschine.suche("Zeitreihe vorhersagen")] == [t["i"] for t in eng.maschine.suche("wie kann ich eine Zeitreihe vorhersagen")]


def test_deterministisch(eng, index):
    zweite = ns.Maschine(ns.knoten_dokumente(index), ns.synonym_groups(index["synonyme"]))
    assert eng.maschine.suche("Gruppen finden in Daten") == zweite.suche("Gruppen finden in Daten")


def test_ein_tippfehler_findet_das_fachwort(eng):
    assert any("dijkstra-demo" in u for u in _adressen(eng, eng.maschine.suche("Dijkstraa", limit=3)))


def test_treffer_nennen_ihren_grund(eng):
    t = eng.maschine.suche("Dijkstra", limit=1)[0]
    assert "dijkstra" in t["grund"] and t["sicher"]


def test_art_und_bereichsfilter(eng):
    nur_demo = E.suchen(eng, "Warteschlange", [C.ARTEN["Fall-Demo"]], C.ALLE_BEREICHE)
    assert nur_demo and all(eng.index["knoten"][t["i"]]["k"] == "Fall-Demo" for t in nur_demo)
    assert E.suchen(eng, "Warteschlange", [], C.ALLE_BEREICHE) == []
    bereich = eng.bereiche[0]
    gefiltert = E.suchen(eng, "Verfahren", list(C.ALLE_ARTEN), bereich)
    assert all(eng.index["knoten"][t["i"]]["b"] == bereich for t in gefiltert)
    assert len(E.suchen(eng, "Verfahren", list(C.ALLE_ARTEN), C.ALLE_BEREICHE)) <= C.MAX_TREFFER


def test_leere_anfrage_gibt_nichts(eng):
    assert E.suchen(eng, "  ", list(C.ALLE_ARTEN), C.ALLE_BEREICHE) == []
    assert E.vorschlaege(eng, "") == []


def test_vorschlaege_nennen_eine_frage_der_baeume(eng):
    q = eng.index["baeume"][0]["knoten"][eng.index["baeume"][0]["wurzel"]]["text"]
    v = E.vorschlaege(eng, q)
    assert 0 < len(v) <= C.MAX_VORSCHLAEGE
    assert any(baum["knoten"][nid]["text"] == q for _, nid, baum in v)
    assert all(baum["knoten"][nid]["art"] == "frage" for _, nid, baum in v)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_jedes_beispiel_findet_sein_ziel_unter_den_ersten_fuenf(eng, name):
    adr = _adressen(eng, eng.maschine.suche(C.PRESETS[name]["q"], limit=5))
    assert any(z in u for u in adr for z in C.PRESET_ZIELE[name]), (name, adr)


def test_alle_beispiele_haben_ein_ziel_und_keines_steht_im_auswertungsset_des_website_repos():
    assert set(C.PRESETS) == set(C.PRESET_ZIELE)
    # die zehn Anfragen des Website-Repos, die als Auswertungsset gelten, dürfen hier nicht als Beispiel auftauchen
    verboten = {"Touren für Lieferwagen planen", "kürzester Weg", "wer gewinnt eine Wahl", "Zeitreihe vorhersagen", "wie viele Tests brauche ich",
                "Gruppen finden in Daten", "Ausreißer erkennen", "Schichtplan erstellen", "Wartezeit am Gate", "Rangliste aus Spielergebnissen"}
    assert not verboten & {v["q"] for v in C.PRESETS.values()}


def test_unbekannte_woerter_bleiben_nicht_im_speicher(eng):
    eng.maschine.suche("geheimwort krankenhuas dijkstra")
    assert "geheimwort" not in eng.maschine._cache and "krankenhuas" not in eng.maschine._cache
    assert "dijkstra" in eng.maschine._cache  # ein Wort des Index darf gemerkt werden


def test_einzelne_buchstaben_sind_keine_suchwoerter(eng):
    assert eng.maschine.suche("a") == [] and eng.maschine.suche("1") == []
    assert [t["i"] for t in eng.maschine.suche("a Dijkstra")] == [t["i"] for t in eng.maschine.suche("Dijkstra")]


def test_load_engine_faellt_auch_bei_einem_baufehler_auf_die_kopie_zurueck(index):
    kaputt = dict(index, knoten=[{"i": 0}])  # kein Titel: build_engine wirft einen KeyError
    e = E.load_engine(fetch=lambda: kaputt)
    assert e.quelle == "eingebaute Kopie" and e.index["knoten"] == index["knoten"]


def test_erneuter_versuch_nur_bei_der_eingebauten_kopie_und_nach_zehn_minuten(eng):
    import dataclasses

    kopie = dataclasses.replace(eng, quelle="eingebaute Kopie", geladen_um=1000.0)
    assert not E.erneut_versuchen(kopie, jetzt=1000.0 + C.RETRY_EINGEBAUT_S - 1)
    assert E.erneut_versuchen(kopie, jetzt=1000.0 + C.RETRY_EINGEBAUT_S)
    web = dataclasses.replace(eng, quelle="Website", geladen_um=0.0)
    assert not E.erneut_versuchen(web, jetzt=10 ** 9)


def test_trefferzahl_ist_die_gesamtzahl_nach_den_filtern(eng):
    treffer, gesamt = E.suchen_mit_zahl(eng, "Verfahren", list(C.ALLE_ARTEN), C.ALLE_BEREICHE)
    assert len(treffer) == C.MAX_TREFFER and gesamt > len(treffer)
    assert E.suchen_mit_zahl(eng, "", list(C.ALLE_ARTEN), C.ALLE_BEREICHE) == ([], 0)
    assert E.suchen(eng, "Verfahren", list(C.ALLE_ARTEN), C.ALLE_BEREICHE) == treffer
