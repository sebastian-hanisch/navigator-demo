"""Aus dem Index die fertige Suchumgebung bauen: zwei Suchmaschinen (Knoten, Fragen) und die Nachschlagetabellen (kein Streamlit)."""

import time
from dataclasses import dataclass

import nav_constants as C
import nav_data as D
import nav_evaluation as V
import nav_guide as G
import nav_search as ns


@dataclass
class Engine:
    index: dict
    quelle: str                     # D.QUELLE_WEBSITE oder D.QUELLE_EINGEBAUT
    maschine: ns.Maschine           # über alle Knoten des Index
    nach_adresse: dict              # Adresse → Demo-Knoten
    demo_zahl: dict                 # Linie → Zahl der Demos
    baeume: list                    # Auswahlliste der Bäume (G.baum_liste)
    bereiche: list                  # Namen der Bereiche in der Reihenfolge des Index
    geladen_um: float = 0.0         # time.time() beim Bau; bei der eingebauten Kopie zählt es für den erneuten Versuch (C.RETRY_EINGEBAUT_S)


def build_engine(index: dict, quelle: str) -> Engine:
    return Engine(
        index=index,
        quelle=quelle,
        maschine=ns.Maschine(ns.knoten_dokumente(index), ns.synonym_groups(index["synonyme"])),
        nach_adresse=G.knoten_nach_adresse(index),
        demo_zahl=V.demo_zahlen(index),
        baeume=G.baum_liste(index),
        bereiche=[e["t"] for e in index["knoten"] if e["k"] == "Bereich"],
        geladen_um=time.time(),
    )


def load_engine(fetch=None, bundled=None) -> Engine:
    """Suchumgebung aus dem Index der Website; geht dabei irgendetwas schief (auch beim Bau aus einem formal gültigen, aber unbrauchbaren Index),
    gilt die eingebaute Kopie."""
    try:
        index, quelle = D.load_index(fetch=fetch, bundled=bundled)
        return build_engine(index, quelle)
    except Exception:
        return build_engine((bundled or D.load_bundled)(), D.QUELLE_EINGEBAUT)


def erneut_versuchen(eng: Engine, jetzt: float | None = None) -> bool:
    """Soll die App die Website erneut versuchen? Nur wenn die eingebaute Kopie läuft und der letzte Versuch lange genug her ist."""
    if eng.quelle != D.QUELLE_EINGEBAUT:
        return False
    return (time.time() if jetzt is None else jetzt) - eng.geladen_um >= C.RETRY_EINGEBAUT_S


def suchen_mit_zahl(eng: Engine, anfrage: str, arten: list[str], bereich: str) -> tuple[list[dict], int]:
    """(Treffer, Gesamtzahl). Die Treffer (höchstens C.MAX_TREFFER) kommen nach Art- und Bereichsfilter; `arten` sind die Beschriftungen aus
    C.ARTEN. Die Gesamtzahl zählt alle Treffer des Kerns nach den Filtern (höchstens C.SUCHE_POOL)."""
    kinds = {C.ART_VON_LABEL[a] for a in arten if a in C.ART_VON_LABEL}
    if not kinds or not anfrage.strip():
        return [], 0
    treffer = eng.maschine.suche(anfrage, limit=C.SUCHE_POOL, kinds=kinds)
    if bereich != C.ALLE_BEREICHE:
        treffer = [t for t in treffer if eng.index["knoten"][t["i"]].get("b") == bereich]
    return treffer[: C.MAX_TREFFER], len(treffer)


def suchen(eng: Engine, anfrage: str, arten: list[str], bereich: str) -> list[dict]:
    """Wie `suchen_mit_zahl`, nur die Treffer."""
    return suchen_mit_zahl(eng, anfrage, arten, bereich)[0]


def vorschlaege(eng: Engine, anfrage: str) -> list[tuple[int, str, dict]]:
    """Entscheidungsbäume zur Anfrage: [(Baumnummer, Wurzel-Id, Baum)], höchstens C.MAX_VORSCHLAEGE.

    Sie kommen aus den Linien, zu denen die Suche sichere Treffer liefert (`ns.baum_vorschlaege`), nicht aus einem Vergleich der Fragetexte."""
    if not anfrage.strip():
        return []
    out = []
    for bi, _punkte in ns.baum_vorschlaege(eng.index, eng.maschine, anfrage, n=C.MAX_VORSCHLAEGE):
        baum = eng.index["baeume"][bi]
        out.append((bi, baum["wurzel"], baum))
    return out
