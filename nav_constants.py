"""Konstanten: Adressen, Grenzen, Texte der Arten und die Beispielanfragen des Schnellstarts (Gerüst aus tools/new_demo.py)."""

BASE_URL = "https://sebastianhanisch.net/"
INDEX_URL = BASE_URL + "navigator-index.json"
APP_URL = "https://sebastianhanisch-navigator-demo.streamlit.app/"
SCHEMA_VERSION = 1                 # eine andere Version des Index nimmt die App nicht, bis sie angepasst ist
INDEX_TIMEOUT_S = 4                # Wartezeit auf die Website, danach gilt die eingebaute Kopie
INDEX_GESAMT_S = 10                # Höchstdauer des ganzen Abrufs (INDEX_TIMEOUT_S gilt je Netzwerkschritt)
INDEX_MAX_BYTES = 3_000_000        # reichlich mehr als der heutige Index (unter 1 MB): darüber stimmt etwas nicht
RETRY_EINGEBAUT_S = 600            # hat die App auf die eingebaute Kopie zurückgegriffen, versucht sie die Website nach so vielen Sekunden erneut
CACHE_TTL_S = 6 * 3600             # so lange gilt der geladene Index im Speicher der App

MAX_TREFFER = 15                   # Trefferkarten je Suche
SUCHE_POOL = 400                   # so viele Treffer holt der Kern, bevor der Bereichsfilter angewendet wird
MAX_VORSCHLAEGE = 3                # „Meinen Sie: …“ im Fragen-Tab
TITEL_MAX = 140                    # Länge von Titeln und Kurztexten auf dem Schirm (Schutz vor überlangen Einträgen)

ALLE_BEREICHE = "Alle Bereiche"

# Art im Index → Beschriftung für den Filter und auf den Karten
ARTEN = {
    "Bereich": "Bereich",
    "Linie": "Linie",
    "Demo": "Konzepte-Demo",
    "Fall-Demo": "Fall-Demo",
    "Erklärseite": "Erklärseite",
    "Thema": "Themenseite",
    "Wort": "Grundlagen: Wort",
    "Frage": "Grundlagen: Frage",
}
ALLE_ARTEN = tuple(ARTEN.values())
ART_VON_LABEL = {label: art for art, label in ARTEN.items()}

# Adressen, auf die die App verlinkt: die Website und ihre Streamlit-Demos, sonst nichts
ERLAUBTE_HOSTS = ("sebastianhanisch.net", "www.sebastianhanisch.net")
DEMO_HOST_ENDE = ".streamlit.app"
DEMO_HOST_ANFANG = "sebastianhanisch-"

# Beispielanfragen (Schnellstart). Keine stammt aus dem Auswertungsset des Website-Repos. Jede hat ein erwartetes Ziel, das ein Test unter
# den ersten fünf Treffern verlangt. Vier Kandidaten stehen nicht hier: „Zwei Messreihen vergleichen“, „Lieferungen bündeln“ und „Stau vermeiden“ fanden
# beim Probelauf am 2026-11-05 nichts Passendes, „Pünktlichkeit im Busverkehr“ hat sein Ziel nach den Änderungen vom 2026-11-06 nicht mehr unter den ersten
# fünf. Sie sind Lücken der Suche, keine Beispiele. „Wie viele Mitarbeiter pro Schicht“ fand am 2026-11-05 nichts und ist seit den Synonymen vom 2026-11-06 ein Beispiel.
PRESETS = {
    "Welche Maschine zuerst": {"q": "Welche Maschine zuerst"},
    "Sitzplätze fair verteilen": {"q": "Sitzplätze fair verteilen"},
    "Wie viele Mitarbeiter pro Schicht": {"q": "Wie viele Mitarbeiter pro Schicht"},
    "Daten sinnvoll in Gruppen teilen": {"q": "Daten sinnvoll in Gruppen teilen"},
    "Ausfälle vorhersagen": {"q": "Ausfälle vorhersagen"},
    "Welche Mannschaft ist wirklich stärker": {"q": "Welche Mannschaft ist wirklich stärker"},
}
VERWORFENE_BEISPIELE = ("Pünktlichkeit im Busverkehr", "Zwei Messreihen vergleichen", "Lieferungen bündeln", "Stau vermeiden")
PRESET_HELP = {name: "Diese Anfrage ins Suchfeld setzen und suchen." for name in PRESETS}
# erwartetes Ziel je Beispiel: ein Teilstring der Adresse; der Test verlangt ihn unter den ersten fünf Treffern
PRESET_ZIELE = {
    "Welche Maschine zuerst": ("scheduling-demo", "shifting-bottleneck-demo", "konzepte-klassische-scheduling-theorie"),
    "Sitzplätze fair verteilen": ("konzepte-abstimmen-fair-teilen", "sitzverteilung-demo"),
    "Wie viele Mitarbeiter pro Schicht": ("shift-demo", "schichtplanung"),
    "Daten sinnvoll in Gruppen teilen": ("clusteranalyse", "konzepte-clustering"),
    "Ausfälle vorhersagen": ("konzepte-zeitreihen-prognose", "naive-forecast-demo", "forecast"),
    "Welche Mannschaft ist wirklich stärker": ("team-einzel-demo", "konzepte-ranking", "bradley-terry-demo", "elo-demo"),
}
