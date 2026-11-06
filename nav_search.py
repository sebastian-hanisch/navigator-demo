#!/usr/bin/env python3
"""Suchkern des Navigationsassistenten (nur Standardbibliothek, keine Streamlit-Abhängigkeit).

Liest `navigator-index.json` (tools/build_navigator_index.py) und `tools/content/navigator_synonyme.json` und ordnet die Knoten zu einer
Anfrage. Der Kern ist absichtlich klein und deterministisch (kein Zufall, keine Uhr); die Streamlit-App im Folgestück bündelt eine Kopie.

Verfahren:
  * Normalisierung: klein, ä/ö/ü → ae/oe/ue, ß → ss, übrige Akzente weg. „kürzester“ und „kuerzester“ sind gleich.
  * Wortstamm: grobe Endungen weg (planen/Planung → plan). Zusammensetzungen bleiben ganz; dafür gibt es die nächsten zwei Stufen.
  * Treffer eines Anfragewortes in einem Wort des Index: gleich (1,0); eines beginnt mit dem anderen oder enthält es, ab fünf Buchstaben (0,7);
    Tippfehler über die Dice-Ähnlichkeit der Buchstaben-Dreiergruppen ab 0,6 (bis 0,9).
  * Gewichtung wie BM25 (seltene Wörter zählen mehr, Titel dreifach, Bereich/Linie 1,5-fach); Stoppwörter fallen heraus.
  * Synonyme (Alltagswort ↔ Fachwort) kommen aus einer von Hand gepflegten Datei und zählen zusätzlich, nicht anstelle.
  * Abdeckung: der Anteil der Anfragewörter (nach Seltenheit gewichtet), den ein Treffer erklärt. Erklärt ein Treffer weniger als die Hälfte
    (nach Seltenheit gewichtet) oder weniger als 30 % (nach Köpfen) der Anfragewörter, fällt er weg; bleibt nichts übrig, meldet `suche`
    „nichts Passendes“ (leere Liste), statt einen Treffer zu erzwingen. Ab der Hälfte nach Köpfen gilt ein Treffer als sicher
    (`sicher`), darunter als schwach. Wörter, die im Index nirgends vorkommen, zählen nicht für die Rangfolge, wohl aber für den Anteil.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
SYNONYME = SITE / "tools" / "content" / "navigator_synonyme.json"

STOPPWOERTER = frozenset("""
der die das den dem des ein eine einen einem einer eines und oder aber mit ohne fuer von vom zu zum zur im in am an auf aus bei nach
wie wer was wo wann welche welcher welches welchen wenn ich mein meine meinen meiner mir mich du dein sie wir man es ist sind wird werden
kann koennen soll sollen muss muessen brauche brauchen will wollen habe haben hat gibt viele wie viel wieviele wieviel nur auch noch
nicht kein keine als dass da dort hier so zwischen ueber unter durch gegen um bis ab dabei dann mehr sehr schon immer jede jeder jedes zwei drei
""".split())

SUFFIXE = ("ungen", "ung", "keit", "heit", "isch", "lich", "ern", "en", "er", "es", "e", "n", "s")
KURZE_SUFFIXE = frozenset(("en", "er", "es", "e", "n", "s"))
KIND_FAKTOR = {"Linie": 1.15, "Thema": 1.05, "Bereich": 1.0, "Demo": 1.0, "Fall-Demo": 1.0, "Erklärseite": 1.0, "Frage": 0.8, "Wort": 0.8}
GEWICHT_TITEL, GEWICHT_TEXT, GEWICHT_META = 3.0, 1.0, 1.5
MIN_ABDECKUNG = 0.5  # Anteil der Anfragewörter (nach Seltenheit gewichtet), den ein Treffer erklären muss
MIN_ANTEIL = 0.3  # und Anteil nach Köpfen; ab SICHER_ANTEIL gilt der Treffer als sicher, darunter als schwach
SICHER_ANTEIL = 0.5
K1, B = 1.2, 0.75


def norm(text: str) -> str:
    s = text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii")


def stem(word: str) -> str:
    """Grobe Endungen weg, höchstens zwei Durchgänge (Gates → Gate → Gat), damit Einzahl und Mehrzahl zusammenfallen."""
    for _ in range(2):
        for suf in SUFFIXE:
            kurz = suf in KURZE_SUFFIXE
            if word.endswith(suf) and len(word) >= (4 if kurz else 6) and len(word) - len(suf) >= (3 if kurz else 4):
                word = word[: -len(suf)]
                break
        else:
            break
    return word


def tokens(text: str, drop_stop: bool = False) -> list[str]:
    out = re.findall(r"[a-z0-9]+", norm(text))
    if drop_stop:
        out = [t for t in out if t not in STOPPWOERTER]
    return out


def stems(text: str, drop_stop: bool = False) -> list[str]:
    return [stem(t) for t in tokens(text, drop_stop)]


def trigrams(word: str) -> frozenset[str]:
    w = f"^{word}$"
    return frozenset(w[i : i + 3] for i in range(len(w) - 2))


def osa(a: str, b: str) -> int:
    """Editierabstand mit Vertauschung benachbarter Buchstaben (optimal string alignment)."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            c = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def dice(a: frozenset[str], b: frozenset[str]) -> float:
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


def synonym_groups(raw: list[list[str]]) -> list[list[list[str]]]:
    """Gruppen von Wendungen (Texte) → je Wendung die Wortstämme ohne Stoppwörter. Eine Anfrage, die alle Wörter einer Wendung enthält
    (in beliebiger Reihenfolge), wird um die der Gruppe erweitert."""
    return [[stems(p, drop_stop=True) for p in g] for g in raw]


def load_synonyms(path: Path = SYNONYME) -> list[list[list[str]]]:
    """Synonymgruppen aus der Datei tools/content/navigator_synonyme.json (leer, wenn es sie nicht gibt)."""
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return synonym_groups([g["gleich"] for g in data["gruppen"]])


class Maschine:
    """Gewichteter Wortindex über beliebige Dokumente {t: Titel, d: Text, m: weitere Felder}."""

    def __init__(self, docs: list[dict], synonyme: list[list[list[str]]] | None = None):
        self.docs = docs
        self.synonyme = synonyme or []
        post: dict[str, dict[int, float]] = defaultdict(dict)
        lengths: list[float] = []
        for i, d in enumerate(docs):
            tf: dict[str, float] = defaultdict(float)
            for w in stems(d.get("t", "")):
                tf[w] += GEWICHT_TITEL
            for w in stems(d.get("d", "")):
                tf[w] += GEWICHT_TEXT
            for w in stems(d.get("m", "")):
                tf[w] += GEWICHT_META
            lengths.append(sum(tf.values()) or 1.0)
            for w, f in tf.items():
                post[w][i] = f
        n = len(docs)
        avg = sum(lengths) / n if n else 1.0
        self.postings: dict[str, dict[int, float]] = {}
        self.idf: dict[str, float] = {}
        for w, plist in post.items():
            df = len(plist)
            self.idf[w] = math.log(1 + (n - df + 0.5) / (df + 0.5))
            self.postings[w] = {i: f * (K1 + 1) / (f + K1 * (1 - B + B * lengths[i] / avg)) for i, f in plist.items()}
        self.vocab = sorted(self.postings)
        self.tri: dict[str, frozenset[str]] = {w: trigrams(w) for w in self.vocab if len(w) >= 4}
        self.tri_index: dict[str, list[str]] = defaultdict(list)
        for w, g in self.tri.items():
            for t in g:
                self.tri_index[t].append(w)
        self._cache: dict[str, list[tuple[str, float]]] = {}

    def aehnlich(self, q: str) -> list[tuple[str, float]]:
        """Wörter des Index, die zum Anfragewort passen, mit Ähnlichkeit."""
        if q in self._cache:
            return self._cache[q]
        out: dict[str, float] = {}
        if q in self.postings:
            out[q] = 1.0
        if len(q) >= 4:
            for w in self.vocab:
                if w == q or len(w) < 4:
                    continue
                if (len(q) >= 5 and len(w) >= 5 and (q in w or w in q)) or (len(q) >= 4 and (w.startswith(q) or (len(w) >= 5 and q.startswith(w)))):
                    out[w] = max(out.get(w, 0), 0.7)
            if len(q) >= 5:
                gq = trigrams(q)
                cand = {w for t in gq for w in self.tri_index.get(t, ())}
                for w in cand:
                    if w in out:
                        continue
                    s = dice(gq, self.tri[w])
                    if s >= 0.6:
                        out[w] = 0.9 * s
                    elif len(q) >= 6 and abs(len(q) - len(w)) <= 1 and osa(q, w) <= (1 if len(q) < 9 else 2):
                        out[w] = 0.85
        res = sorted(out.items())
        if q in self.postings:  # nur Wörter des Index merken; was jemand tippt und der Index nicht kennt, bleibt nicht im Speicher
            self._cache[q] = res
        return res

    def beitrag(self, q: str) -> dict[int, float]:
        """Dokument → bester Beitrag eines Anfragewortes (Ähnlichkeit × Seltenheit × Häufigkeit im Dokument)."""
        best: dict[int, float] = {}
        for w, sim in self.aehnlich(q):
            weight = sim * self.idf[w]
            for i, tfw in self.postings[w].items():
                v = weight * tfw
                if v > best.get(i, 0.0):
                    best[i] = v
        return best

    def erweiterungen(self, qs: list[str]) -> list[tuple[list[int], list[str]]]:
        """Synonymgruppen, deren Wendung in der Anfrage vorkommt: (Positionen der Wendung, Wörter der übrigen Wendungen)."""
        out = []
        for gruppe in self.synonyme:
            for ph in gruppe:
                if not ph:
                    continue
                if all(w in qs for w in ph):
                    others = [w for o in gruppe if o is not ph for w in o]
                    out.append((sorted({qs.index(w) for w in ph}), others))
        return out

    def suche(self, anfrage: str, limit: int = 15, kinds: set[str] | None = None) -> list[dict]:
        qs = [q for q in stems(anfrage, drop_stop=True) if len(q) >= 2]  # einzelne Buchstaben und Ziffern sind keine Suchwörter
        if not qs:
            return []
        eigene = [self.beitrag(q) for q in qs]
        # Wörter, die im Index nirgends (auch nicht ähnlich) vorkommen, zählen nicht für die Rangfolge; ob genug Anfragewörter getroffen
        # sind, entscheidet der Anteil unten.
        gewicht = [max((self.idf[w] * sim for w, sim in self.aehnlich(q)), default=0.0) for q in qs]
        if not any(gewicht):
            return []
        punkte: dict[int, float] = defaultdict(float)
        gedeckt: dict[int, set[int]] = defaultdict(set)
        grund: dict[int, set[str]] = defaultdict(set)
        for pos, b in enumerate(eigene):
            for i, v in b.items():
                punkte[i] += v
                gedeckt[i].add(pos)
                grund[i].add(qs[pos])
        for positions, words in self.erweiterungen(qs):
            alt: dict[int, float] = defaultdict(float)
            for w in set(words):
                for i, v in self.beitrag(w).items():
                    alt[i] = max(alt[i], 0.8 * v)
            for i, v in alt.items():
                punkte[i] += v
                gedeckt[i].update(positions)
                grund[i].add("≈ " + "/".join(sorted({qs[p] for p in positions})))
        total = sum(gewicht) or 1.0
        qn = norm(anfrage).strip()
        res = []
        for i, p in punkte.items():
            d = self.docs[i]
            if kinds and d.get("k") not in kinds:
                continue
            abd = sum(gewicht[p2] for p2 in gedeckt[i]) / total
            anteil = len(gedeckt[i]) / len(qs)
            if anteil < MIN_ANTEIL or abd < MIN_ABDECKUNG:
                continue
            s = p * (0.4 + 0.6 * abd) * KIND_FAKTOR.get(d.get("k", ""), 1.0)
            tt = set(tokens(d.get("t", "")))
            if tokens(anfrage, True) and all(t in tt for t in tokens(anfrage, True)):
                s *= 1.3
            if norm(d.get("t", "")).strip() == qn:
                s *= 1.5
            res.append({"i": i, "punkte": s, "abdeckung": abd, "sicher": anteil >= SICHER_ANTEIL, "grund": sorted(grund[i])})
        res.sort(key=lambda r: (-r["punkte"], r["i"]))
        return res[:limit]


def knoten_dokumente(index: dict) -> list[dict]:
    """Dokumente für die Maschine aus den Knoten des Navigator-Index (gleiche Reihenfolge wie `index['knoten']`)."""
    return [{"k": e["k"], "t": e["t"], "d": e.get("d", ""), "m": " ".join([e.get("b", ""), e.get("l", ""), e.get("f", "")])} for e in index["knoten"]]


def frage_dokumente(index: dict) -> tuple[list[dict], list[tuple[int, str]]]:
    """Dokumente für den Problem-Assistenten: je Frage-Knoten der Entscheidungsbäume die Frage, ihre Antworten und die Ergebnisse darunter."""
    docs, refs = [], []
    for bi, baum in enumerate(index["baeume"]):
        for nid, n in baum["knoten"].items():
            if n["art"] != "frage":
                continue
            antworten = " ".join(a for a, _ in n["kinder"])
            ergebnisse = " ".join(baum["knoten"][c]["text"] for _, c in n["kinder"] if baum["knoten"].get(c, {}).get("art") == "ergebnis")
            docs.append({"k": "Frage", "t": n["text"], "d": f"{antworten} {ergebnisse}", "m": baum["titel"]})
            refs.append((bi, nid))
    return docs, refs


def laden(site: Path = SITE) -> tuple[dict, Maschine]:
    """Index und Suchmaschine aus `navigator-index.json`; die Synonyme stehen im Index (eine Datenquelle wie in der App)."""
    index = json.loads((site / "navigator-index.json").read_text(encoding="utf-8"))
    return index, Maschine(knoten_dokumente(index), synonym_groups(index.get("synonyme", [])))
