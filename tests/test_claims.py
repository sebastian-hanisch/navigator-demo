"""Jede Zahl und jede überprüfbare Aussage der README steht hier (DEMO-PLAYBOOK §4)."""

import re
from pathlib import Path

import nav_constants as C
import nav_search as ns

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
ZAHLWORT = {1: "eine", 2: "zwei", 3: "drei", 4: "vier", 5: "fünf", 6: "sechs", 7: "sieben"}


def test_sechs_beispiele_und_vier_verworfene():
    assert len(C.PRESETS) == 6 and "Sechs im Schnellstart" in README
    assert len(C.VERWORFENE_BEISPIELE) == 4 and "Vier weitere Kandidaten" in README
    assert not set(C.VERWORFENE_BEISPIELE) & set(C.PRESETS)


def test_zeitlimit_und_zwischenspeicher_stehen_wie_in_der_readme():
    assert C.INDEX_TIMEOUT_S == 4 and "vier Sekunden Zeitlimit je Netzwerkschritt" in README
    assert C.INDEX_GESAMT_S == 10 and "höchstens zehn Sekunden insgesamt" in README
    assert C.CACHE_TTL_S == 6 * 3600 and "sechs Stunden im Speicher" in README
    assert C.RETRY_EINGEBAUT_S == 600 and "nach zehn Minuten versucht die App die Website erneut" in README
    assert C.MAX_TREFFER == 15 and "Die ersten 15 von N Treffern" in README and C.SUCHE_POOL == 400 and "höchstens 400" in README


def test_gewichte_wie_in_der_readme():
    assert (ns.GEWICHT_TITEL, ns.GEWICHT_TEXT, ns.GEWICHT_META) == (3.0, 1.0, 1.5)
    assert "Titel 3, Text 1, Bereichs- und Liniennamen 1,5" in README


def test_ein_titeltreffer_wirkt_weniger_als_dreimal_so_stark_wie_ein_texttreffer():
    """Die README sagt „weniger als dreimal so stark“: die BM25-Sättigung dämpft das Gewicht 3."""
    docs = [{"k": "Demo", "t": "zorvek " + "fuellung " * 4, "d": "", "m": ""}, {"k": "Demo", "t": "fuellung " * 4, "d": "zorvek", "m": ""}]
    m = ns.Maschine(docs)
    a, b = m.beitrag("zorvek")[0], m.beitrag("zorvek")[1]
    assert a > b and a < 3 * b
    assert "weniger als dreimal so stark" in README


def test_schwellen_wie_in_der_readme():
    assert ns.MIN_ANTEIL == 0.3 and "weniger als 30 % der Anfragewörter" in README
    assert ns.MIN_ABDECKUNG == 0.5 and "weniger als die Hälfte" in README
    assert ns.SICHER_ANTEIL == 0.5 and "mindestens die Hälfte der Anfragewörter" in README


def test_tippfehler_erst_ab_fuenf_buchstaben_und_einzelbuchstaben_zaehlen_nicht():
    docs = [{"k": "Demo", "t": "tour", "d": "", "m": ""}, {"k": "Demo", "t": "dijkstra", "d": "", "m": ""}]
    m = ns.Maschine(docs)
    assert m.suche("Toru") == []                   # vier Buchstaben: kein Tippfehler-Abgleich
    assert [t["i"] for t in m.suche("Dijkstraa")] == [1]
    assert m.suche("a") == [] and m.suche("7") == []
    assert "erst bei Wörtern ab fünf Buchstaben" in README and "Einzelne Buchstaben und Ziffern zählen nicht als Suchwörter" in README


def test_wortanfaenge_ab_vier_und_wortteile_ab_fuenf_buchstaben():
    docs = [{"k": "Demo", "t": "tourenplanung", "d": "", "m": ""}, {"k": "Demo", "t": "elektrolieferwagen", "d": "", "m": ""}]
    m = ns.Maschine(docs)
    assert [w for w, _ in m.aehnlich("tour")] == [ns.stem("tourenplanung")]          # Anfang mit vier Buchstaben
    assert m.aehnlich("tou") == []                                                   # drei Buchstaben: kein Wortanfang
    assert [w for w, _ in m.aehnlich("liefer")] == [ns.stem("elektrolieferwagen")]   # Wortteil mit sechs Buchstaben
    assert m.aehnlich("wage") == []                                                  # vier Buchstaben mitten im Wort: zu kurz für einen Wortteil
    assert ns.stem("planen") == ns.stem("planung")                                   # Endungen
    assert "Wortanfänge ab vier Buchstaben" in README and "Wortteile ab fünf" in README


def test_das_orakel_prueft_200_anfragen():
    quelle = (Path(__file__).resolve().parent / "test_oracle_search.py").read_text(encoding="utf-8")
    assert "assert pruefungen == 200" in quelle and "200 Anfragen" in README


def test_zwischenspeicher_merkt_keine_fremden_woerter():
    m = ns.Maschine([{"k": "Demo", "t": "dijkstra", "d": "", "m": ""}])
    m.suche("geheimwort dijkstra")
    assert "geheimwort" not in m._cache and "dijkstra" in m._cache
    assert "nie Ihre Wortlaute" in README


def test_adresse_wird_nur_gelesen():
    quelle = (Path(__file__).resolve().parent.parent / "nav_presets.py").read_text(encoding="utf-8")
    assert "st.query_params[" not in quelle and "query_params.update" not in quelle  # nie schreiben
    assert "wird gelesen, nie geschrieben" in README


def test_requirements_begrenzen_streamlit_wie_in_der_readme():
    req = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text(encoding="utf-8")
    assert re.search(r"streamlit>=1\.51,<1\.55", req) and "1.51 bis unter 1.55" in README
    assert [z.strip() for z in req.splitlines() if z.strip()] == ["streamlit>=1.51,<1.55"]  # nur Streamlit, wie die README sagt


def test_die_testzahl_der_readme_stimmt():
    import subprocess
    import sys

    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", str(Path(__file__).resolve().parent)],
                         capture_output=True, text=True, timeout=300).stdout
    n = int(re.search(r"(\d+) tests? collected", out).group(1))
    assert f"Tests: {n}," in README, f"README nennt eine andere Zahl als die Suite ({n})"
