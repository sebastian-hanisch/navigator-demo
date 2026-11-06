"""Navigator – die passende Demo finden - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Eine Suche über die Beschreibungen der Website und ein Führer durch die Entscheidungsbäume der Linien. Kein Sprachmodell, nichts wird
gespeichert. Aufbau und Regeln: DEMO-PLAYBOOK.md (§2); Plan: docs/planung/navigator-planung/PLAN-02-navigator-app.md im Website-Repo.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import nav_constants as C
import nav_data as D
import nav_engine as E
import nav_evaluation as V
import nav_guide as G
from nav_layout import dunkles_design, kopf_css
from nav_presets import (
    init_session_state_defaults,
    link_zur_suche,
    load_permalink_settings,
    sanitize_filters,
    sidebar_presets,
)

st.set_page_config(page_title="Navigator – Sebastian Hanisch", layout="wide")


@st.cache_resource(ttl=C.CACHE_TTL_S, show_spinner="Index der Website wird geladen …")
def _engine() -> E.Engine:
    return E.load_engine()


# ---------------------------------------------------------------------------------------------------------------- Rückrufe (Fragen-Tab)
def _neuer_baum():
    st.session_state["guide_bi"] = st.session_state.get("guide_select")
    st.session_state["guide_pfad"] = ()


def _antwort(i: int):
    st.session_state["guide_pfad"] = tuple(st.session_state.get("guide_pfad", ())) + (i,)


def _zurueck():
    st.session_state["guide_pfad"] = G.zurueck(tuple(st.session_state.get("guide_pfad", ())))


def _neu_beginnen():
    st.session_state["guide_pfad"] = ()


def _steige(bi: int, pfad: tuple):
    st.session_state["guide_bi"] = bi
    st.session_state["guide_select"] = bi
    st.session_state["guide_pfad"] = pfad


# ---------------------------------------------------------------------------------------------------------------- Darstellung
def _m(text: str, n: int = 400) -> str:
    """Text aus dem Index für Markdown entschärfen (der Index kommt über das Netz)."""
    return D.md_text(text, n)


def _link(titel: str, adresse: str) -> str:
    sicher = D.sichere_adresse(adresse)
    t = D.md_text(titel)
    return f"[{t}]({sicher})" if sicher else t


def _karte(eng: E.Engine, t: dict, anfrage: str):
    e = eng.index["knoten"][t["i"]]
    with st.container(border=True):
        st.markdown(f"**{_link(e['t'], e['u'])}**")
        st.caption(_m(V.ort(e, eng.demo_zahl)))
        if e.get("d"):
            st.markdown(D.md_text(e["d"], 220))
        st.caption("🔎 " + V.warum(anfrage, t["grund"]) + ("" if t["sicher"] else " Passt nur teilweise."))


def _bereiche(eng: E.Engine):
    st.markdown("**Die Bereiche der Website**")
    for e in eng.index["knoten"]:
        if e["k"] == "Bereich":
            st.markdown(f"- **{_link(e['t'], e['u'])}**: {D.md_text(e.get('d', ''), 200)}")


def _ergebnis(eng: E.Engine, n: dict):
    demo = eng.nach_adresse.get(n["url"])
    with st.container(border=True):
        st.markdown(f"**{_link(demo['t'] if demo else n['text'], n['url'])}**")
        if demo:
            st.caption(_m(V.ort(demo, eng.demo_zahl)))
            if demo.get("d"):
                st.markdown(D.md_text(demo["d"], 260))
        st.caption("Der Baum nennt diese Demo als Antwort: " + D.md_text(n["text"], 200))


def _fragen_tab(eng: E.Engine):
    st.markdown("Beantworten Sie ein paar Fragen. Die Fragen stammen aus den Entscheidungsbäumen der Linien auf der Website; der Navigator erfindet keine neuen.")
    optionen = {x["bi"]: x for x in eng.baeume}
    st.selectbox(
        "Eine Linie wählen", list(optionen), index=None, key="guide_select", on_change=_neuer_baum, placeholder="Linie wählen oder tippen …",
        format_func=lambda bi: _m(G.auswahl_text(optionen[bi])),
    )
    frage = st.text_input("Oder beschreiben Sie Ihre Frage", key="frage_input", placeholder="z. B. Cluster oder Prognose", max_chars=200)
    vorschl = E.vorschlaege(eng, frage)
    if frage.strip() and not vorschl:
        st.caption("Dazu schlägt der Navigator keine Frage vor. Wählen Sie oben eine Linie oder probieren Sie andere Wörter.")
    elif vorschl:
        st.caption("Fragen aus den Bäumen, die Ihre Wörter enthalten (nur ein Wortvergleich, die Vorschläge können danebenliegen):")
    for k, (bi, nid, baum) in enumerate(vorschl):
        lin = optionen[bi]
        pfad = G.pfad_zu_knoten(baum, nid) or ()
        st.button(
            _m(f"{baum['knoten'][nid]['text']}  ·  {lin['linie_titel']}"), key=f"vorschlag_{k}", width="stretch",
            on_click=_steige, args=(bi, pfad),
        )
    bi = st.session_state.get("guide_bi")
    if bi is None or bi >= len(eng.index["baeume"]):
        st.info("Wählen Sie eine Linie oder beschreiben Sie Ihre Frage, dann geht es los.")
        return
    baum = eng.index["baeume"][bi]
    pfad = tuple(st.session_state.get("guide_pfad", ()))
    st.divider()
    st.markdown(f"**{D.md_text(optionen[bi]['linie_titel'])}**: {D.md_text(baum['titel'], 200)}")
    for frage_text, antwort in G.verlauf(baum, pfad):
        st.caption(f"✓ {_m(frage_text)}  →  {_m(antwort)}")
    nid, n = G.knoten_am_pfad(baum, pfad)
    if n["art"] == "frage":
        st.subheader(_m(n["text"]))
        for i, (label, _) in enumerate(n["kinder"]):
            st.button(_m(label), key=f"antwort_{len(pfad)}_{i}", width="stretch", on_click=_antwort, args=(i,))
    elif n["art"] == "ergebnis":
        st.success("Das passt zu Ihren Antworten:")
        _ergebnis(eng, n)
    elif n["art"] == "sprung":
        ziel = G.sprung_ziel(eng.index, bi, nid)
        st.info(_m(n["text"]))
        if ziel is not None:
            st.button("Weiter im nächsten Baum dieser Linie", key="sprung", on_click=_steige, args=(ziel, ()))
    else:
        st.warning(_m(n["text"]))
    c1, c2 = st.columns(2)
    c1.button("← Zurück", key="zurueck", on_click=_zurueck, disabled=not pfad, width="stretch")
    c2.button("Neu beginnen", key="neu_beginnen", on_click=_neu_beginnen, disabled=not pfad, width="stretch")


# ---------------------------------------------------------------------------------------------------------------- Seite
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🧭 Navigator – die passende Demo finden")
st.markdown(
    """
Zwei Wege zur passenden Demo: **tippen**, was Sie wissen wollen, oder **Fragen beantworten**. Der Navigator **vergleicht Wörter** mit den
Beschreibungen der Website (Linien, Demos, Erklärseiten, Grundlagen); er versteht Ihre Frage nicht und empfiehlt nichts. Treffer sind Vorschläge.

Weiter unten: **🔧 So sucht der Navigator** und **🚧 Wo die Annahmen enden**.
"""
)

load_permalink_settings()
init_session_state_defaults()
eng = _engine()
if E.erneut_versuchen(eng):  # lief die eingebaute Kopie, ist die Website vielleicht inzwischen wieder da
    _engine.clear()
    eng = _engine()
sanitize_filters(eng.bereiche)

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Beispiel ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Suche eingrenzen**")
    st.multiselect("Art der Treffer", list(C.ALLE_ARTEN), key="art_filter", help="Nur diese Arten von Einträgen zeigen.")
    st.selectbox(
        "Bereich", [C.ALLE_BEREICHE, *eng.bereiche], key="bereich_filter",
        help="Nur Einträge eines Bereichs. Einträge ohne Bereich fehlen dann: Fall-Demos, Themenseiten, Grundlagen und einige Erklärseiten.",
    )
    st.markdown("**Index**")
    if eng.quelle == D.QUELLE_WEBSITE:
        st.caption(f"Von der Website geladen, Stand {_m(eng.index['stand'])}.")
    else:
        st.caption(f"Eingebaute Kopie, Stand {_m(eng.index['stand'])}. Die Website war nicht erreichbar oder ihr Index nicht brauchbar; neuere Einträge fehlen vielleicht. Die App versucht es später noch einmal.")

tab_suche, tab_fragen = st.tabs(["🔎 Suchen", "🧭 Fragen"])

with tab_suche:
    q = st.text_input(
        "Was möchten Sie wissen?", key="q_input", max_chars=200, placeholder="z. B. kürzester Weg, Schichtplan, wer gewinnt eine Wahl",
        help="Eigene Worte genügen. Groß- und Kleinschreibung und Umlaute spielen keine Rolle; bei Wörtern ab fünf Buchstaben verzeihen wir leichte Tippfehler.",
    )
    treffer, gesamt = E.suchen_mit_zahl(eng, q, st.session_state["art_filter"], st.session_state["bereich_filter"])
    if q.strip():
        ohne_filter = None
        if not treffer and (set(st.session_state["art_filter"]) != set(C.ALLE_ARTEN) or st.session_state["bereich_filter"] != C.ALLE_BEREICHE):
            ohne_filter = E.suchen_mit_zahl(eng, q, list(C.ALLE_ARTEN), C.ALLE_BEREICHE)[1] or None
        art, satz = V.status_text(V.status(treffer), len(treffer), gesamt, ohne_filter)
        getattr(st, art)(satz)
        for t in treffer:
            _karte(eng, t, q)
        if not treffer:
            _bereiche(eng)
        with st.expander("🔗 Link zu dieser Suche"):
            st.caption("Die Adresse der App merkt sich Ihre Eingabe nicht von selbst. Wenn Sie diese Suche teilen wollen, kopieren Sie:")
            st.code(link_zur_suche(q), language=None)
        st.caption(
            "Fehlt etwas oder passt nichts? Das ist eine Lücke der Suche, kein Fehler von Ihnen: "
            "[Schreiben Sie mir](https://sebastianhanisch.net/kontakt.html), was Sie gesucht haben. Die App speichert Ihre Eingabe nicht."
        )
    else:
        st.caption(f"Durchsucht werden {len(eng.index['knoten'])} Einträge der Website. Links im Schnellstart stehen Beispielanfragen.")
        _bereiche(eng)

with tab_fragen:
    _fragen_tab(eng)

st.markdown("---")

with st.expander("🔧 So sucht der Navigator"):
    st.markdown(
        """
- **Wörter vergleichen.** Ihre Anfrage wird in Wörter zerlegt (ohne Füllwörter wie „wie“, „eine“). Jedes Wort zählt umso mehr, je seltener es auf
  der Website vorkommt; ein Treffer im Titel wiegt stärker als einer im Text (Gewicht 3 gegen 1, danach dämpft die BM25-Formel).
- **Endungen und Tippfehler.** „planen“ und „Planung“ gelten als dasselbe Wort, ebenso Einzahl und Mehrzahl; „Dijkstraa“ findet Dijkstra.
  Tippfehler verzeiht die Suche erst bei Wörtern ab fünf Buchstaben; „Toru“ statt „Tour“ findet nichts.
  Wortanfänge (ab vier Buchstaben) und Wortteile in Zusammensetzungen (ab fünf) zählen mit, aber weniger als das ganze Wort.
- **Gleichbedeutende Wendungen.** Eine von Hand gepflegte Liste verbindet Alltagswörter mit Fachwörtern („vorhersagen“ mit „Prognose“). Sie
  erweitert die Suche, ersetzt sie nicht; das steht auf der Karte als „über eine gleichbedeutende Wendung“.
- **Fragen.** Der Tab „Fragen“ führt durch die Entscheidungsbäume, die auf den Linienseiten der Website stehen. Der Navigator fügt keine hinzu.
- **Woher die Daten kommen.** Aus der Datei `navigator-index.json` der Website, erzeugt aus denselben Beschreibungen wie die Seiten. Ist die
  Website nicht erreichbar, gilt eine eingebaute Kopie; links steht, welche gerade benutzt wird.
"""
    )

with st.expander("🚧 Wo die Annahmen enden"):
    st.markdown(
        """
- **Wörter, kein Verstehen.** Die Suche findet, was dieselben oder ähnliche Wörter enthält. „Wörter kommen vor“ heißt nicht „passt zu Ihrem
  Problem“. Bei Anfragen in ganz anderen Wörtern als denen der Website findet sie nichts oder Falsches.
- **Lücken der Synonymliste.** Was nicht auf der Liste steht, wird nicht verbunden. Der Navigator sagt dann „nichts Passendes“ oder zeigt
  Treffer, die nur einen Teil der Wörter enthalten.
- **Die Reihenfolge ist keine Empfehlung.** Ganz oben steht, was die Wörter am besten trifft, nicht, was für Sie am nützlichsten ist.
- **Die Fragen gehören den Linien.** Ein Entscheidungsbaum gilt für seine Linie und nennt nur Demos dieser Linie. Die Fragen-Vorschläge im Tab
  „Fragen“ vergleichen ebenfalls nur Wörter und sind schwächer als die Suche: „Gruppen in Daten finden“ führt zu einer Frage der Spieltheorie.
- **Nichts wird gespeichert.** Eingaben bleiben in Ihrer Sitzung; die Adresse der App ändert sich nicht, solange Sie nichts teilen. Der Zwischenspeicher der Suche merkt sich nur Wörter, die im Index vorkommen, nie Ihre Wortlaute.
"""
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html)."
)
