"""Entscheidungsbäume bedienen: reine Funktionen ohne Streamlit (Plan: Stück 2 des Navigators, Abschnitt 3 „Tab Fragen“).

Ein Baum steht im Index als {linie, id, titel, wurzel, knoten: {id: {art, text, kinder | url | baum}}}. Der Weg durch den Baum ist ein
Tupel von Antwortnummern ab der Wurzel (`pfad`); die Funktionen ändern nie ein Argument. Knotenarten: `frage` (hat Antworten), `ergebnis`
(Demo mit Adresse), `sprung` (weiter in einem anderen Baum derselben Linie), `hinweis` (Randbemerkung, kein Ziel)."""

from collections import deque


def baum_liste(index: dict) -> list[dict]:
    """Alle Bäume für die Auswahl: [{bi, linie, linie_titel, bereich, titel, mehrere}], nach Bereich, dann Linie, dann Reihenfolge im Index."""
    linien = {e["s"]: e for e in index["knoten"] if e["k"] == "Linie"}
    je_linie: dict[str, int] = {}
    for b in index["baeume"]:
        je_linie[b["linie"]] = je_linie.get(b["linie"], 0) + 1
    out = []
    for bi, b in enumerate(index["baeume"]):
        lin = linien.get(b["linie"])
        out.append({"bi": bi, "linie": b["linie"], "linie_titel": lin["t"] if lin else b["linie"], "bereich": lin["b"] if lin else "",
                    "titel": b["titel"], "mehrere": je_linie[b["linie"]] > 1})
    return sorted(out, key=lambda x: (x["bereich"], x["linie_titel"], x["bi"]))


def auswahl_text(eintrag: dict) -> str:
    """Beschriftung einer Baumauswahl: „Bereich: Linie“, bei mehreren Bäumen einer Linie mit dem Titel des Baums."""
    text = f"{eintrag['bereich']}: {eintrag['linie_titel']}" if eintrag["bereich"] else eintrag["linie_titel"]
    return f"{text} – {eintrag['titel']}" if eintrag["mehrere"] else text


def knoten_am_pfad(baum: dict, pfad: tuple) -> tuple[str, dict]:
    """(Knoten-Id, Knoten), an dem `pfad` endet. Ein Pfad, der nicht zum Baum passt, endet an dem Knoten, bis zu dem er gültig war."""
    nid = baum["wurzel"]
    for i in pfad:
        n = baum["knoten"][nid]
        if n["art"] != "frage" or not (0 <= i < len(n["kinder"])):
            break
        nid = n["kinder"][i][1]
    return nid, baum["knoten"][nid]


def antworten(baum: dict, pfad: tuple) -> list[tuple[str, str]]:
    """Die Antworten am Ende des Pfades als [(Beschriftung, Ziel-Id)]; leer, wenn dort keine Frage steht."""
    _, n = knoten_am_pfad(baum, pfad)
    return [(a, c) for a, c in n["kinder"]] if n["art"] == "frage" else []


def waehle(baum: dict, pfad: tuple, i: int) -> tuple:
    """Pfad nach der Antwort Nummer `i`; eine ungültige Nummer ändert nichts."""
    return pfad + (i,) if 0 <= i < len(antworten(baum, pfad)) else pfad


def zurueck(pfad: tuple) -> tuple:
    return pfad[:-1]


def verlauf(baum: dict, pfad: tuple) -> list[tuple[str, str]]:
    """Die bisherigen Schritte als [(Frage, gewählte Antwort)]."""
    out, nid = [], baum["wurzel"]
    for i in pfad:
        n = baum["knoten"][nid]
        if n["art"] != "frage" or not (0 <= i < len(n["kinder"])):
            break
        out.append((n["text"], n["kinder"][i][0]))
        nid = n["kinder"][i][1]
    return out


def pfad_zu_knoten(baum: dict, ziel: str) -> tuple | None:
    """Kürzester Pfad von der Wurzel zum Knoten `ziel` (Breitensuche), None, wenn es ihn nicht gibt oder er nicht erreichbar ist."""
    if ziel not in baum["knoten"]:
        return None
    seen = {baum["wurzel"]}
    todo = deque([(baum["wurzel"], ())])
    while todo:
        nid, pfad = todo.popleft()
        if nid == ziel:
            return pfad
        n = baum["knoten"][nid]
        if n["art"] != "frage":
            continue
        for i, (_, c) in enumerate(n["kinder"]):
            if c in baum["knoten"] and c not in seen:
                seen.add(c)
                todo.append((c, pfad + (i,)))
    return None


def sprung_ziel(index: dict, bi: int, nid: str) -> int | None:
    """Nummer des Baums, auf den der Sprungknoten `nid` im Baum `bi` zeigt (dieselbe Linie), sonst None."""
    b = index["baeume"][bi]
    n = b["knoten"].get(nid)
    if not n or n["art"] != "sprung":
        return None
    for j, other in enumerate(index["baeume"]):
        if other["linie"] == b["linie"] and other["id"] == n["baum"]:
            return j
    return None


def knoten_nach_adresse(index: dict) -> dict[str, dict]:
    """Adresse → Knoten des Index (Demo oder Fall-Demo), damit ein Ergebnis Titel und Kurztext der Demo zeigen kann."""
    out: dict[str, dict] = {}
    for e in index["knoten"]:
        if e["k"] in ("Demo", "Fall-Demo"):
            out.setdefault(e["u"], e)
    return out


def alle_enden(baum: dict) -> list[tuple]:
    """Alle Pfade von der Wurzel bis zu einem Knoten, an dem es nicht weitergeht (für Tests)."""
    out, todo = [], [()]
    while todo:
        pfad = todo.pop()
        a = antworten(baum, pfad)
        if not a:
            out.append(pfad)
        else:
            todo.extend(pfad + (i,) for i in range(len(a)))
    return sorted(out)
