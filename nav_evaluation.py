"""Verdikte und Texte der Suche: reine Funktionen ohne Streamlit (Gerüst aus tools/new_demo.py, angepasst).

Der Kern (nav_search.py) liefert je Treffer `sicher` (mindestens die Hälfte der Anfragewörter erklärt) und `grund` (getroffene Wortstämme,
„≈ …“ bei Synonymen). Hier wird daraus der Satz über der Trefferliste und der „Warum“-Text je Karte. „Wörter kommen vor“ heißt nur das:
die Wörter kommen vor. Es heißt nicht, dass der Treffer die richtige Antwort ist."""

import re

import nav_constants as C
import nav_search as ns

STATUS_NICHTS = "nichts"
STATUS_TEILWEISE = "teilweise"
STATUS_WOERTER = "woerter"


def status(treffer: list[dict]) -> str:
    """„nichts“ ohne Treffer; „woerter“, wenn mindestens ein Treffer die Hälfte der Anfragewörter erklärt; sonst „teilweise“."""
    if not treffer:
        return STATUS_NICHTS
    return STATUS_WOERTER if any(t["sicher"] for t in treffer) else STATUS_TEILWEISE


def status_text(st_: str, n: int, gesamt: int | None = None, ohne_filter: int | None = None) -> tuple[str, str]:
    """(Streamlit-Art, Satz) für die Zeile über den Treffern. `n` = Zahl der gezeigten Treffer, `gesamt` = alle Treffer (größer als `n`, wenn
    gekappt), `ohne_filter` = Zahl der Treffer ohne Art- und Bereichsfilter (nur beim Status „nichts“ wichtig)."""
    if st_ == STATUS_NICHTS:
        if ohne_filter:
            return "warning", f"Mit den gewählten Filtern gibt es dazu nichts. Ohne Filter gäbe es {ohne_filter} Treffer: lockern Sie die Filter links."
        return "warning", "Dazu habe ich nichts Passendes gefunden. Unten stehen die Bereiche der Website; oder probieren Sie andere Wörter."
    if gesamt and gesamt > n:
        zahl = f"Die ersten {n} von {gesamt} Treffern"
    else:
        zahl = "1 Treffer" if n == 1 else f"{n} Treffer"
    if st_ == STATUS_WOERTER:
        return "info", f"{zahl}: Ihre Wörter kommen vor. Ob es das Gesuchte ist, sagt das nicht; die Beschreibung auf der Karte hilft beim Entscheiden."
    return "info", f"{zahl}, die nur einen Teil Ihrer Wörter enthalten. Prüfen Sie, ob einer passt."


def _woerter(text: str) -> list[tuple[str, str]]:
    """[(Wort wie getippt, Wortstamm)] ohne Stoppwörter."""
    out = []
    for w in re.findall(r"[^\W_]+", text):
        toks = ns.tokens(w, drop_stop=True)
        if toks:
            out.append((w, ns.stem(toks[0])))
    return out


def getroffene_woerter(anfrage: str, grund: list[str]) -> list[str]:
    """Die Wörter der Anfrage (wie getippt), die der Treffer enthält, ohne die über Synonyme erklärten."""
    stems = {g for g in grund if not g.startswith("≈")}
    out: list[str] = []
    for w, st_ in _woerter(anfrage):
        if st_ in stems and w not in out:
            out.append(w)
    return out


def synonym_woerter(anfrage: str, grund: list[str]) -> list[str]:
    """Die Wörter der Anfrage, bei denen eine gleichbedeutende Wendung geholfen hat."""
    stems: set[str] = set()
    for g in grund:
        if g.startswith("≈"):
            stems.update(g.removeprefix("≈").strip().split("/"))
    direkt = set(getroffene_woerter(anfrage, grund))
    out: list[str] = []
    for w, st_ in _woerter(anfrage):
        if st_ in stems and w not in out and w not in direkt:  # ein Wort, das schon direkt getroffen hat, steht nicht noch einmal als Synonym da
            out.append(w)
    return out


def warum(anfrage: str, grund: list[str]) -> str:
    """Ein Satz, welche Wörter getroffen haben; sagt nichts über die Sache."""
    direkt = getroffene_woerter(anfrage, grund)
    syn = synonym_woerter(anfrage, grund)
    teile = []
    if direkt:
        teile.append("Getroffen: " + ", ".join(f"„{w}“" for w in direkt))
    if syn:
        teile.append("über eine gleichbedeutende Wendung: " + ", ".join(f"„{w}“" for w in syn))
    if not teile:
        return "Ähnliche Schreibweise oder Wortteil."
    return "; ".join(teile) + "."


def ort(knoten: dict, demo_zahl: dict[str, int]) -> str:
    """Kurzzeile zur Herkunft: Art, Bereich oder Linie, bei Demos die Stelle in der Linie."""
    teile = [C.ARTEN.get(knoten["k"], knoten["k"])]
    if knoten["k"] == "Demo" and knoten.get("l"):
        teile.append(f"in der Linie {knoten['l']}")
        n_ges = demo_zahl.get(knoten.get("s", ""), 0)
        if knoten.get("n") and n_ges:
            teile.append(f"Stück {knoten['n']} von {n_ges}")
    elif knoten.get("b") and knoten["k"] != "Bereich":
        teile.append(knoten["b"])
    return " · ".join(teile)


def demo_zahlen(index: dict) -> dict[str, int]:
    """Zahl der Demos je Linie (Schlüssel: `s` im Index, der Dateiname der Linie ohne .html)."""
    out: dict[str, int] = {}
    for e in index["knoten"]:
        if e["k"] == "Demo":
            out[e.get("s", "")] = out.get(e.get("s", ""), 0) + 1
    return out
