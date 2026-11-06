"""Der Index der Website: holen, prüfen, Rückfall auf die eingebaute Kopie, Adressen und Texte absichern (nur Standardbibliothek).

Quelle ist `navigator-index.json` auf der Website (erzeugt von tools/build_navigator_index.py im Website-Repo). Die App versucht zuerst die
Website; schlägt das fehl (nicht erreichbar, Zeitüberschreitung, zu groß, Weiterleitung auf eine fremde Adresse, kein gültiger Index, andere
Schemaversion), gilt die eingebaute Kopie in data/navigator-index.json. `parse_index`, `hole_index` und `sichere_adresse` werfen nach außen nur
DatenFehler beziehungsweise nie; `nav_engine.load_engine` fängt zusätzlich alles, was beim Bau der Suchumgebung aus einem Index der Website
schiefgeht, und fällt dann ebenfalls auf die Kopie zurück. Ohne gültige eingebaute Kopie ist die App ohnehin nicht lauffähig."""

import json
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import nav_constants as C

BUNDLED = Path(__file__).resolve().parent / "data" / "navigator-index.json"
REQUIRED_KEYS = ("v", "stand", "knoten", "kanten", "baeume", "pfade", "themen", "synonyme")
ARTEN_KNOTEN = ("frage", "ergebnis", "sprung", "hinweis")
QUELLE_WEBSITE = "Website"
QUELLE_EINGEBAUT = "eingebaute Kopie"


class DatenFehler(Exception):
    """Der Index ist nicht brauchbar (kein JSON, falsche Schemaversion, Schlüssel fehlen, Feld vom falschen Typ, zu groß)."""


def _str(x) -> bool:
    return isinstance(x, str)


def _pruefe_knoten(knoten) -> None:
    if not isinstance(knoten, list) or not knoten:
        raise DatenFehler("keine Knoten")
    for i, e in enumerate(knoten):
        if not isinstance(e, dict) or e.get("i") != i or not all(_str(e.get(k)) for k in ("k", "t", "u")):
            raise DatenFehler(f"Knoten {i} ist kaputt")
        if any(k in e and not _str(e[k]) for k in ("d", "b", "l", "s", "f")) or ("n" in e and (not isinstance(e["n"], int) or isinstance(e["n"], bool))):
            raise DatenFehler(f"Knoten {i} hat ein Feld vom falschen Typ")


def _pruefe_baeume(baeume) -> None:
    if not isinstance(baeume, list):
        raise DatenFehler("baeume ist keine Liste")
    for bi, b in enumerate(baeume):
        if not isinstance(b, dict) or not all(_str(b.get(k)) for k in ("linie", "id", "titel", "wurzel")) or not isinstance(b.get("knoten"), dict):
            raise DatenFehler(f"Baum {bi} ist kaputt")
        kn = b["knoten"]
        if b["wurzel"] not in kn:
            raise DatenFehler(f"Baum {bi}: Wurzel fehlt")
        for nid, n in kn.items():
            if not isinstance(n, dict) or n.get("art") not in ARTEN_KNOTEN or not _str(n.get("text")):
                raise DatenFehler(f"Baum {bi}: Knoten {nid} ist kaputt")
            if n["art"] == "ergebnis" and not _str(n.get("url")):
                raise DatenFehler(f"Baum {bi}: Ergebnis {nid} ohne Adresse")
            if n["art"] == "sprung" and not _str(n.get("baum")):
                raise DatenFehler(f"Baum {bi}: Sprung {nid} ohne Ziel")
            if n["art"] == "frage":
                kinder = n.get("kinder")
                if not isinstance(kinder, list) or not kinder:
                    raise DatenFehler(f"Baum {bi}: Frage {nid} ohne Antworten")
                for k in kinder:
                    if not isinstance(k, list) or len(k) != 2 or not _str(k[0]) or k[1] not in kn:
                        raise DatenFehler(f"Baum {bi}: Antwort bei {nid} ist kaputt")


def parse_index(raw: bytes | str) -> dict:
    """Prüft einen Index (Schemaversion, Schlüssel, Typen der Felder, Verweise in den Bäumen) und gibt ihn zurück. Wirft DatenFehler, sonst nie."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError, RecursionError) as e:
        raise DatenFehler(f"kein JSON: {type(e).__name__}") from e
    if not isinstance(data, dict):
        raise DatenFehler("kein Objekt")
    if data.get("v") != C.SCHEMA_VERSION or isinstance(data.get("v"), bool):
        raise DatenFehler(f"Schemaversion {data.get('v')!r} statt {C.SCHEMA_VERSION}")
    fehlt = [k for k in REQUIRED_KEYS if k not in data]
    if fehlt:
        raise DatenFehler(f"Schlüssel fehlen: {', '.join(fehlt)}")
    if not _str(data["stand"]) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["stand"]):
        raise DatenFehler("stand ist kein Datum")
    _pruefe_knoten(data["knoten"])
    _pruefe_baeume(data["baeume"])
    syn = data["synonyme"]
    if not isinstance(syn, list) or not all(isinstance(g, list) and all(_str(p) for p in g) for g in syn):
        raise DatenFehler("synonyme sind keine Gruppen von Texten")
    if not isinstance(data["kanten"], list) or not isinstance(data["pfade"], dict) or not isinstance(data["themen"], list):
        raise DatenFehler("kanten, pfade oder themen haben den falschen Typ")
    return data


def hole_index(url: str = C.INDEX_URL, timeout: float = C.INDEX_TIMEOUT_S, max_bytes: int = C.INDEX_MAX_BYTES, gesamt_s: float = C.INDEX_GESAMT_S,
               opener=urllib.request.urlopen) -> dict:
    """Index von der Website holen und prüfen. `timeout` gilt je Netzwerkschritt, `gesamt_s` für den ganzen Abruf; eine Weiterleitung auf eine
    Adresse außerhalb der Website zählt als Fehler. `opener` ist ersetzbar (Tests gehen nie ins Netz)."""
    ende = time.monotonic() + gesamt_s
    try:
        with opener(url, timeout=timeout) as resp:
            final = getattr(resp, "geturl", lambda: url)()
            if sichere_adresse(final) is None or not str(final).startswith("https://"):
                raise DatenFehler("Weiterleitung auf eine fremde Adresse")
            teile, n = [], 0
            while True:
                stueck = resp.read(65536)
                if not stueck:
                    break
                teile.append(stueck)
                n += len(stueck)
                if n > max_bytes:
                    raise DatenFehler("Antwort zu groß")
                if time.monotonic() > ende:
                    raise DatenFehler("Abruf dauert zu lange")
    except DatenFehler:
        raise
    except Exception as e:  # Netz, Zeitüberschreitung, HTTP-Fehler, alles dasselbe: Rückfall
        raise DatenFehler(f"nicht erreichbar: {type(e).__name__}") from e
    return parse_index(b"".join(teile))


def fetch_remote() -> dict:
    """Der Abruf, den die App benutzt. Eigene Funktion, damit Tests ihn ersetzen können, ohne `hole_index` zu verlieren."""
    return hole_index()


def load_bundled(path: Path = BUNDLED) -> dict:
    return parse_index(path.read_bytes())


def load_index(fetch=None, bundled=None) -> tuple[dict, str]:
    """(Index, Quelle). Quelle ist QUELLE_WEBSITE oder QUELLE_EINGEBAUT. Die Funktionen werden erst beim Aufruf aufgelöst, damit Tests
    sie im Modul ersetzen können (der Abruf geht in Tests nie ins Netz)."""
    try:
        return (fetch or fetch_remote)(), QUELLE_WEBSITE
    except DatenFehler:
        return (bundled or load_bundled)(), QUELLE_EINGEBAUT


# ---------------------------------------------------------------------------------------------------------------- Adressen und Texte
def sichere_adresse(u: str) -> str | None:
    """Absolute https-Adresse auf die Website oder eine ihrer Streamlit-Demos, sonst None. Wirft nie.

    Seitenadressen im Index sind relativ („konzepte-ranking.html“, „grundlagen.html#wort“) und werden auf die Website bezogen. Alles andere
    (andere Hosts, andere Schemata, `javascript:`, ein Port, Zugangsdaten) gilt als unsicher: der Index kommt über das Netz."""
    if not isinstance(u, str) or not u or any(c in u for c in " \t\r\n\"'<>()[]"):
        return None
    try:
        parts = urlsplit(u)
        port = parts.port  # wirft ValueError bei einem Port, der keine Zahl ist
    except ValueError:
        return None
    if not parts.scheme and not parts.netloc:
        if u.startswith(("/", ".", "\\")) or ":" in parts.path:
            return None
        return C.BASE_URL + u
    if parts.scheme != "https" or parts.username is not None or parts.password is not None or port is not None or ":" in parts.netloc:
        return None
    host = (parts.hostname or "").lower()
    if host in C.ERLAUBTE_HOSTS or (host.startswith(C.DEMO_HOST_ANFANG) and host.endswith(C.DEMO_HOST_ENDE) and re.fullmatch(r"[a-z0-9-]+", host[: -len(C.DEMO_HOST_ENDE)])):
        return u
    return None


_MD_SONDER = re.compile(r"([\\`*_{}\[\]()#+!|<>~$&])")
_MD_ANFANG_ZEICHEN = re.compile(r"^(\s*)([-=:])")
_MD_ANFANG_ZAHL = re.compile(r"^(\s*\d+)([.)])")


def md_text(text: str, maxlen: int = C.TITEL_MAX) -> str:
    """Text für Markdown: gekürzt, auf eine Zeile gebracht, Sonderzeichen entschärft (der Index kommt über das Netz). Ein Zeilenanfang, der
    als Liste, Linie oder Überschrift gelesen würde, wird ebenfalls entschärft."""
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) > maxlen:
        text = text[: maxlen - 1].rstrip() + "…"
    text = _MD_SONDER.sub(r"\\\1", text)
    text = _MD_ANFANG_ZEICHEN.sub(lambda m: m.group(1) + "\\" + m.group(2), text)
    return _MD_ANFANG_ZAHL.sub(lambda m: m.group(1) + "\\" + m.group(2), text)
