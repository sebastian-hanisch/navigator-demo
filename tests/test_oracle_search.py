"""Orakel: eine absichtlich naive zweite Bewertung gegen den Suchkern (DEMO-PLAYBOOK §12).

Der Kern baut Indizes, cacht und kennt Wortähnlichkeit. Das Orakel rechnet dasselbe Verfahren (BM25 mit Feldgewichten, Abdeckung, Titelzuschläge)
für jede Anfrage gegen jedes Dokument von vorn, ohne Index und ohne Zwischenspeicher. Damit die Ähnlichkeit (Wortteile, Tippfehler) keine Rolle
spielt, läuft es auf einem Korpus aus erfundenen Wörtern, die einander nicht ähneln: dann zählt nur die Wortgleichheit, und die Rangfolge muss
übereinstimmen."""

import random
from math import log

import nav_search as ns

# keine Silbe endet auf e, n, r nach e oder s: sonst schneidet die Endungsregel des Kerns das Wort ab
SILBEN = ["zor", "vek", "plim", "dra", "muf", "tol", "bux", "yal", "gil", "nox", "sab", "wid", "qui", "hak", "ruv", "fod"]


def _woerter(rng, n=40):
    """n Wörter aus je drei Silben, paarweise ohne Enthaltensein und mit Dice-Ähnlichkeit unter 0,5 (der Kern ist bei 0,6 ähnlich)."""
    out = []
    while len(out) < n:
        w = "".join(rng.sample(SILBEN, 3))
        if all(w not in o and o not in w and ns.dice(ns.trigrams(w), ns.trigrams(o)) < 0.5 for o in out):
            out.append(w)
    return out


def _korpus(rng):
    vokabular = _woerter(rng)
    arten = ["Demo", "Linie", "Fall-Demo", "Frage"]
    docs = []
    for _ in range(60):
        docs.append({"k": rng.choice(arten), "t": " ".join(rng.sample(vokabular, rng.randint(1, 3))), "d": " ".join(rng.choices(vokabular, k=rng.randint(0, 12))),
                     "m": " ".join(rng.sample(vokabular, rng.randint(0, 2)))})
    return vokabular, docs


def _naiv(docs, anfrage):
    """Dieselbe Bewertung wie der Kern, aber ohne Index: alles aus den Rohtexten, Dokument für Dokument."""
    qs = ns.stems(anfrage, drop_stop=True)
    if not qs:
        return []
    tfs, laengen = [], []
    for d in docs:
        tf = {}
        for gewicht, feld in ((3.0, "t"), (1.0, "d"), (1.5, "m")):
            for w in ns.stems(d[feld]):
                tf[w] = tf.get(w, 0.0) + gewicht
        tfs.append(tf)
        laengen.append(sum(tf.values()) or 1.0)
    n = len(docs)
    avg = sum(laengen) / n
    idf = {}
    for w in {w for tf in tfs for w in tf}:
        df = sum(1 for tf in tfs if w in tf)
        idf[w] = log(1 + (n - df + 0.5) / (df + 0.5))
    gewicht = [idf.get(q, 0.0) for q in qs]
    if not any(gewicht):
        return []
    total = sum(gewicht)
    faktor = {"Linie": 1.15, "Demo": 1.0, "Fall-Demo": 1.0, "Frage": 0.8}
    res = []
    for i, d in enumerate(docs):
        punkte, gedeckt = 0.0, set()
        for pos, q in enumerate(qs):
            f = tfs[i].get(q, 0.0)
            if f:
                punkte += idf[q] * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * laengen[i] / avg))
                gedeckt.add(pos)
        if not gedeckt:
            continue
        abd = sum(gewicht[p] for p in gedeckt) / total
        if len(gedeckt) / len(qs) < 0.3 or abd < 0.5:
            continue
        s = punkte * (0.4 + 0.6 * abd) * faktor[d["k"]]
        tt = set(ns.tokens(d["t"]))
        toks = ns.tokens(anfrage, True)
        if toks and all(t in tt for t in toks):
            s *= 1.3
        if ns.norm(d["t"]).strip() == ns.norm(anfrage).strip():
            s *= 1.5
        res.append((s, i))
    res.sort(key=lambda x: (-x[0], x[1]))
    return res


def test_der_korpus_hat_wirklich_unaehnliche_woerter():
    vokabular, docs = _korpus(random.Random(1))
    for w in vokabular:
        assert ns.stem(w) == w  # keine Endung wird abgeschnitten, sonst stimmten Wort und Wortstamm nicht überein
    m = ns.Maschine(docs)
    for w in vokabular[:10]:
        assert [x for x, _ in m.aehnlich(w)] == [w]  # nur das Wort selbst gilt als gleich


def test_rangfolge_und_punkte_stimmen_mit_der_naiven_bewertung_ueberein():
    rng = random.Random(20261105)
    pruefungen = 0
    for _ in range(4):
        vokabular, docs = _korpus(rng)
        maschine = ns.Maschine(docs)
        for _ in range(50):
            anfrage = " ".join(rng.sample(vokabular, rng.randint(1, 3)))
            soll = _naiv(docs, anfrage)
            ist = maschine.suche(anfrage, limit=1000)
            assert [t["i"] for t in ist] == [i for _, i in soll], anfrage
            for t, (s, _) in zip(ist, soll):
                assert abs(t["punkte"] - s) <= 1e-9 * max(1.0, abs(s)), (anfrage, t["punkte"], s)
            pruefungen += 1
    assert pruefungen == 200


def test_ein_titeltreffer_schlaegt_einen_texttreffer():
    docs = [{"k": "Demo", "t": "anderes", "d": "zorvekplim " * 1, "m": ""}, {"k": "Demo", "t": "zorvekplim", "d": "", "m": ""}]
    # beide enthalten das Wort genau einmal, im Titel zählt es dreifach
    treffer = ns.Maschine(docs).suche("zorvekplim")
    assert [t["i"] for t in treffer] == [1, 0]
