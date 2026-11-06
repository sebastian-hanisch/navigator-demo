"""Index laden, prüfen, Rückfall; Adressen und Texte absichern (kein Netzzugriff)."""

import io
import json

import pytest

import nav_constants as C
import nav_data as D


def _minimal(**over):
    d = {"v": 1, "stand": "2026-01-01", "knoten": [{"i": 0, "k": "Linie", "t": "Linie", "u": "konzepte-x.html"}], "kanten": [], "baeume": [],
         "pfade": {}, "themen": [], "synonyme": []}
    d.update(over)
    return d


class _Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(data: bytes):
    return lambda url, timeout=None: _Antwort(data)


# ----------------------------------------------------------------------------------------------------------------------- Prüfung
def test_eingebaute_kopie_ist_gueltig_und_hat_die_schluessel(index):
    for k in D.REQUIRED_KEYS:
        assert k in index
    assert index["v"] == C.SCHEMA_VERSION


@pytest.mark.parametrize("raw", [b"", b"nicht json", b"[]", b"null", json.dumps(_minimal(v=2)).encode(), json.dumps(_minimal(v="1")).encode()])
def test_kaputte_oder_fremde_antworten_werden_abgelehnt(raw):
    with pytest.raises(D.DatenFehler):
        D.parse_index(raw)


@pytest.mark.parametrize("fehlt", D.REQUIRED_KEYS)
def test_fehlender_schluessel_wird_abgelehnt(fehlt):
    d = _minimal()
    del d[fehlt]
    with pytest.raises(D.DatenFehler):
        D.parse_index(json.dumps(d))


def test_knoten_muessen_nummeriert_und_beschriftet_sein():
    with pytest.raises(D.DatenFehler):
        D.parse_index(json.dumps(_minimal(knoten=[{"i": 5, "k": "Linie", "t": "x", "u": "y"}])))
    with pytest.raises(D.DatenFehler):
        D.parse_index(json.dumps(_minimal(knoten=[{"i": 0, "k": "Linie", "t": 3, "u": "y"}])))
    with pytest.raises(D.DatenFehler):
        D.parse_index(json.dumps(_minimal(knoten=[])))
    assert D.parse_index(json.dumps(_minimal()))["v"] == 1


# ----------------------------------------------------------------------------------------------------------------------- Abruf
def test_abruf_mit_gueltiger_antwort():
    assert D.hole_index(opener=_opener(json.dumps(_minimal()).encode()))["stand"] == "2026-01-01"


def test_abruf_scheitert_bei_netzfehler_zeitueberschreitung_und_zu_grosser_antwort():
    def kaputt(url, timeout=None):
        raise TimeoutError

    with pytest.raises(D.DatenFehler):
        D.hole_index(opener=kaputt)
    with pytest.raises(D.DatenFehler):
        D.hole_index(opener=_opener(b"x" * 100), max_bytes=50)
    with pytest.raises(D.DatenFehler):
        D.hole_index(opener=_opener(b"<html>404</html>"))


def test_abruf_gibt_dem_opener_das_zeitlimit():
    gesehen = {}

    def opener(url, timeout=None):
        gesehen.update(url=url, timeout=timeout)
        return _Antwort(json.dumps(_minimal()).encode())

    D.hole_index(opener=opener)
    assert gesehen == {"url": C.INDEX_URL, "timeout": C.INDEX_TIMEOUT_S}


def test_rueckfall_auf_die_eingebaute_kopie():
    def nie():
        raise D.DatenFehler("weg")

    index, quelle = D.load_index(fetch=nie)
    assert quelle == D.QUELLE_EINGEBAUT and index["knoten"]
    index, quelle = D.load_index(fetch=lambda: _minimal())
    assert quelle == D.QUELLE_WEBSITE and index["stand"] == "2026-01-01"


# ----------------------------------------------------------------------------------------------------------------------- Adressen
@pytest.mark.parametrize("u, soll", [
    ("konzepte-ranking.html", "https://sebastianhanisch.net/konzepte-ranking.html"),
    ("grundlagen.html#zufall", "https://sebastianhanisch.net/grundlagen.html#zufall"),
    ("https://sebastianhanisch-elo-demo.streamlit.app/", "https://sebastianhanisch-elo-demo.streamlit.app/"),
    ("https://sebastianhanisch.net/demos.html", "https://sebastianhanisch.net/demos.html"),
])
def test_erlaubte_adressen(u, soll):
    assert D.sichere_adresse(u) == soll


@pytest.mark.parametrize("u", [
    "", None, 5, "javascript:alert(1)", "http://sebastianhanisch.net/x.html", "https://example.com/", "https://sebastianhanisch.net.evil.com/",
    "https://evil.streamlit.app/", "https://sebastianhanisch-x.streamlit.app.evil.com/", "https://user:pw@sebastianhanisch.net/",
    "https://sebastianhanisch.net:8443/", "https://sebastianhanisch.net:abc/", "https://sebastianhanisch.net:0/", "https://sebastianhanisch.net:/", "//evil.com/x", "/etc/passwd", "../x.html", "data:text/html,x", "a b.html", "x.html)[evil](https://evil.com",
    "https://sebastianhanisch-Ä.streamlit.app/", "mailto:a@b.de",
])
def test_unsichere_adressen_werden_abgelehnt(u):
    assert D.sichere_adresse(u) is None


def test_alle_adressen_der_eingebauten_kopie_sind_erlaubt(index):
    schlecht = [e["u"] for e in index["knoten"] if D.sichere_adresse(e["u"]) is None]
    assert schlecht == []
    schlecht = [n["url"] for b in index["baeume"] for n in b["knoten"].values() if n["art"] == "ergebnis" and D.sichere_adresse(n["url"]) is None]
    assert schlecht == []


# ----------------------------------------------------------------------------------------------------------------------- Texte
def test_markdown_wird_entschaerft_und_gekuerzt():
    assert D.md_text("A* [Suche] (x) `y` $z$") == r"A\* \[Suche\] \(x\) \`y\` \$z\$"
    assert D.md_text("a\n\n  b") == "a b"
    lang = D.md_text("wort " * 100, 30)
    assert len(lang) <= 31 + 20 and lang.endswith("…")
    assert D.md_text("") == ""


# ----------------------------------------------------------------------------------------------------------------------- Strengere Prüfung
def _mit(index, **felder):
    d = json.loads(json.dumps(index))
    d.update(felder)
    return d


def test_formal_gueltige_aber_unbrauchbare_indizes_werden_abgelehnt(index):
    k0 = dict(index["knoten"][0])
    boese = [
        _mit(index, knoten=[dict(k0, d=None)] + index["knoten"][1:]),
        _mit(index, knoten=[dict(k0, n="3")] + index["knoten"][1:]),
        _mit(index, synonyme=[["a"], [1]]),
        _mit(index, synonyme="x"),
        _mit(index, baeume=[{}]),
        _mit(index, baeume="x"),
        _mit(index, stand="gestern"),
        _mit(index, stand=20261105),
        _mit(index, kanten="x"),
        _mit(index, pfade=[]),
        _mit(index, themen={}),
    ]
    for d in boese:
        with pytest.raises(D.DatenFehler):
            D.parse_index(json.dumps(d))


def test_baeume_mit_toten_verweisen_werden_abgelehnt(index):
    b = json.loads(json.dumps(index["baeume"][0]))
    b["knoten"][b["wurzel"]]["kinder"][0][1] = "gibt-es-nicht"
    with pytest.raises(D.DatenFehler):
        D.parse_index(json.dumps(_mit(index, baeume=[b])))
    b2 = json.loads(json.dumps(index["baeume"][0]))
    b2["wurzel"] = "fehlt"
    with pytest.raises(D.DatenFehler):
        D.parse_index(json.dumps(_mit(index, baeume=[b2])))


def test_tief_verschachteltes_json_wird_zum_datenfehler():
    with pytest.raises(D.DatenFehler):
        D.parse_index("[" * 100000)


def test_der_ganze_abruf_hat_eine_hoechstdauer():
    class Tropft(_Antwort):
        def read(self, n=-1):
            return b"x" * 10  # nie zu Ende

    with pytest.raises(D.DatenFehler, match="zu lange"):
        D.hole_index(opener=lambda url, timeout=None: Tropft(), gesamt_s=0.0)


def test_weiterleitung_auf_fremde_adresse_wird_abgelehnt():
    class Umgeleitet(_Antwort):
        def geturl(self):
            return "https://evil.example/navigator-index.json"

    with pytest.raises(D.DatenFehler, match="Weiterleitung"):
        D.hole_index(opener=lambda url, timeout=None: Umgeleitet(json.dumps(_minimal()).encode()))

    class Unverschluesselt(_Antwort):
        def geturl(self):
            return "http://sebastianhanisch.net/navigator-index.json"

    with pytest.raises(D.DatenFehler, match="Weiterleitung"):
        D.hole_index(opener=lambda url, timeout=None: Unverschluesselt(json.dumps(_minimal()).encode()))


def test_markdown_zeilenanfaenge_und_kaufmannsund_werden_entschaerft():
    assert D.md_text("- Punkt") == "\\- Punkt"
    assert D.md_text("1. Erstens") == "1\\. Erstens"
    assert D.md_text("--- Linie") == "\\--- Linie"
    assert D.md_text("a &amp; b") == "a \\&amp; b"
    assert D.md_text("# Titel") == "\\# Titel"


def test_gueltige_kopie_besteht_die_strenge_pruefung(index):
    assert D.parse_index(json.dumps(index))["stand"] == index["stand"]
