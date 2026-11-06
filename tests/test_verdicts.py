"""Verdikte und Texte der Suche (nav_evaluation) an handgesetzten Werten; jeder Satz hat seine Schwelle im Test (DEMO-PLAYBOOK §5)."""

import nav_evaluation as V
import nav_search as ns


def _t(sicher=True, grund=("dijkstra",)):
    return {"i": 0, "punkte": 1.0, "abdeckung": 1.0, "sicher": sicher, "grund": list(grund)}


def test_status_nichts_teilweise_woerter():
    assert V.status([]) == V.STATUS_NICHTS
    assert V.status([_t(sicher=False)]) == V.STATUS_TEILWEISE
    assert V.status([_t(sicher=False), _t(sicher=True)]) == V.STATUS_WOERTER  # ein sicherer Treffer genügt
    assert V.status([_t(sicher=True)]) == V.STATUS_WOERTER


def test_statussatz_je_status_und_zahlwort():
    art, satz = V.status_text(V.STATUS_NICHTS, 0)
    assert art == "warning" and "nichts Passendes" in satz
    art, satz = V.status_text(V.STATUS_WOERTER, 1)
    assert art == "info" and satz.startswith("1 Treffer:")  # keine grüne Erfolgsmeldung: „Wörter kommen vor“ ist kein Erfolg
    art, satz = V.status_text(V.STATUS_WOERTER, 12)
    assert satz.startswith("12 Treffer:") and "sagt das nicht" in satz  # sagt ausdrücklich, dass das nichts über die Richtigkeit besagt
    art, satz = V.status_text(V.STATUS_TEILWEISE, 3)
    assert art == "info" and "nur zum Teil oder nur als Wortteil" in satz and satz.startswith("3 Treffer,")


def test_getroffene_woerter_in_der_schreibweise_der_eingabe():
    assert V.getroffene_woerter("Dijkstra Wege", ["dijkstra", "weg"]) == ["Dijkstra", "Wege"]
    assert V.getroffene_woerter("Dijkstra Wege", ["dijkstra"]) == ["Dijkstra"]
    assert V.getroffene_woerter("wie viele Tests brauche ich", ["test"]) == ["Tests"]  # Füllwörter zählen nie
    assert V.getroffene_woerter("Pünktlichkeit", [ns.stem("puenktlichkeit")]) == ["Pünktlichkeit"]  # Umlaut wie getippt, Treffer über die Normalform


def test_synonymwoerter_stehen_getrennt_von_direkten_treffern():
    grund = ["test", "≈ vorhersag"]
    assert V.getroffene_woerter("Tests vorhersagen", grund) == ["Tests"]
    assert V.synonym_woerter("Tests vorhersagen", grund) == ["vorhersagen"]
    assert V.synonym_woerter("Tests", ["test"]) == []


def test_warum_nennt_nur_getroffene_woerter():
    assert V.warum("Dijkstra Wege", ["dijkstra"]) == "Getroffen: „Dijkstra“."
    assert V.warum("Zeitreihe vorhersagen", ["zeitreih", "≈ vorhersag"]) == "Getroffen: „Zeitreihe“; über eine gleichbedeutende Wendung: „vorhersagen“."
    assert V.warum("Dijkstraa", ["dijkstra"]) == "Ähnliche Schreibweise oder Wortteil."  # Tippfehler: das Wort der Eingabe hat einen anderen Stamm
    assert V.warum("", []) == "Ähnliche Schreibweise oder Wortteil."


def test_ort_einer_demo_nennt_linie_und_stelle():
    demo = {"k": "Demo", "t": "x", "l": "Kürzeste Wege", "s": "konzepte-kuerzeste-wege", "n": 2, "b": "Graphentheorie"}
    assert V.ort(demo, {"konzepte-kuerzeste-wege": 12}) == "Konzepte-Demo · in der Linie Kürzeste Wege · Stück 2 von 12"
    assert V.ort(demo, {}) == "Konzepte-Demo · in der Linie Kürzeste Wege"  # Zahl unbekannt: ohne „von N“
    assert V.ort({"k": "Fall-Demo", "b": "Hafenlogistik"}, {}) == "Fall-Demo · Hafenlogistik"
    assert V.ort({"k": "Bereich", "b": "Optimierung"}, {}) == "Bereich"


def test_demozahlen_summieren_sich_zu_den_demos(index):
    z = V.demo_zahlen(index)
    assert sum(z.values()) == sum(1 for e in index["knoten"] if e["k"] == "Demo")
    assert all(v > 0 for v in z.values())


def test_statussatz_nennt_die_kappung_und_den_filter():
    _, satz = V.status_text(V.STATUS_WOERTER, 15, gesamt=268)
    assert satz.startswith("Die ersten 15 von 268 Treffern:")
    _, satz = V.status_text(V.STATUS_WOERTER, 15, gesamt=15)
    assert satz.startswith("15 Treffer:")  # nicht gekappt: keine „ersten“
    art, satz = V.status_text(V.STATUS_NICHTS, 0, gesamt=0, ohne_filter=7)
    assert art == "warning" and "Mit den gewählten Filtern" in satz and "7 Treffer" in satz
    _, satz = V.status_text(V.STATUS_NICHTS, 0, gesamt=0, ohne_filter=None)
    assert "nichts Passendes" in satz and "Filter" not in satz


def test_ein_wort_steht_nicht_zugleich_als_treffer_und_als_synonym():
    t, p = ns.stem("touren"), ns.stem("planen")
    grund = [t, f"≈ {t}/{p}"]
    assert V.getroffene_woerter("Touren planen", grund) == ["Touren"]
    assert V.synonym_woerter("Touren planen", grund) == ["planen"]


def test_unterstrich_gehoert_nicht_zum_wort():
    assert V.getroffene_woerter("kuerzester_Weg", [ns.stem("kuerzester")]) == ["kuerzester"]  # nur der Teil vor dem Unterstrich hat getroffen
    assert V.getroffene_woerter("Weg", ["weg"]) == ["Weg"]
