"""Entscheidungsbäume bedienen (nav_guide), geprüft an allen Bäumen der eingebauten Kopie."""

import nav_guide as G


def _zahl_fragen(baum):
    return sum(1 for n in baum["knoten"].values() if n["art"] == "frage")


def test_jeder_baum_ist_von_der_wurzel_aus_begehbar_und_endet(index):
    for bi, baum in enumerate(index["baeume"]):
        assert baum["wurzel"] in baum["knoten"], bi
        enden = G.alle_enden(baum)
        assert enden, bi
        for pfad in enden:
            _, n = G.knoten_am_pfad(baum, pfad)
            assert n["art"] in ("ergebnis", "sprung", "hinweis"), (bi, pfad)
            assert len(pfad) <= _zahl_fragen(baum), f"Schleife im Baum {bi}?"


def test_jeder_knoten_ist_erreichbar_und_der_kuerzeste_pfad_fuehrt_hin(index):
    for bi, baum in enumerate(index["baeume"]):
        erreichbar = set()
        for pfad in G.alle_enden(baum):
            nid = baum["wurzel"]
            erreichbar.add(nid)
            for i in pfad:
                nid = baum["knoten"][nid]["kinder"][i][1]
                erreichbar.add(nid)
        assert erreichbar == set(baum["knoten"]), f"Baum {bi}: unerreichbare Knoten"
        for nid in baum["knoten"]:
            pfad = G.pfad_zu_knoten(baum, nid)
            assert pfad is not None and G.knoten_am_pfad(baum, pfad)[0] == nid, (bi, nid)


def test_zurueck_hebt_jede_antwort_auf(index):
    baum = index["baeume"][0]
    pfad = ()
    for _ in range(10):
        a = G.antworten(baum, pfad)
        if not a:
            break
        neu = G.waehle(baum, pfad, 0)
        assert neu == pfad + (0,)
        assert G.zurueck(neu) == pfad
        pfad = neu
    assert G.zurueck(()) == ()


def test_ungueltige_antwort_aendert_nichts(index):
    baum = index["baeume"][0]
    assert G.waehle(baum, (), 99) == () and G.waehle(baum, (), -1) == ()
    ende = G.alle_enden(baum)[0]
    assert G.waehle(baum, ende, 0) == ende  # am Ende gibt es keine Antworten
    assert G.antworten(baum, ende) == []


def test_verlauf_hat_je_antwort_einen_schritt(index):
    baum = index["baeume"][0]
    ende = max(G.alle_enden(baum), key=len)
    v = G.verlauf(baum, ende)
    assert len(v) == len(ende)
    assert v[0][0] == baum["knoten"][baum["wurzel"]]["text"]


def test_kaputter_pfad_endet_am_letzten_gueltigen_knoten(index):
    baum = index["baeume"][0]
    nid, _ = G.knoten_am_pfad(baum, (0, 99, 0))
    assert nid == G.knoten_am_pfad(baum, (0,))[0]


def test_jeder_sprung_zeigt_auf_einen_baum_derselben_linie(index):
    gesehen = 0
    for bi, baum in enumerate(index["baeume"]):
        for nid, n in baum["knoten"].items():
            if n["art"] == "sprung":
                ziel = G.sprung_ziel(index, bi, nid)
                assert ziel is not None and ziel != bi and index["baeume"][ziel]["linie"] == baum["linie"]
                gesehen += 1
    assert gesehen >= 1


def test_sprung_ziel_fuer_andere_knoten_ist_none(index):
    baum = index["baeume"][0]
    assert G.sprung_ziel(index, 0, baum["wurzel"]) is None
    assert G.sprung_ziel(index, 0, "gibt-es-nicht") is None


def test_jedes_ergebnis_hat_eine_demo_im_index(index):
    nach_adresse = G.knoten_nach_adresse(index)
    fehl = [(b["linie"], n["url"]) for b in index["baeume"] for n in b["knoten"].values() if n["art"] == "ergebnis" and n["url"] not in nach_adresse]
    assert fehl == []


def test_auswahlliste_ist_vollstaendig_und_eindeutig_beschriftet(index):
    liste = G.baum_liste(index)
    assert sorted(x["bi"] for x in liste) == list(range(len(index["baeume"])))
    texte = [G.auswahl_text(x) for x in liste]
    assert len(set(texte)) == len(texte), "zwei Bäume mit derselben Beschriftung"
    assert liste == G.baum_liste(index)  # deterministisch
    assert all(x["linie_titel"] for x in liste)
