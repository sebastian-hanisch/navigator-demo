# Navigator – die passende Demo finden – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-navigator-demo.streamlit.app/)** -->

Werkzeug für die Website „Sebastian Hanisch – Operations Research und Machine Learning“: eine Suche über die Beschreibungen der Website (Bereiche, Linien, Konzepte-Demos, Fall-Demos, Erklärseiten, Themenseiten, Grundlagen) und ein Führer durch die Entscheidungsbäume der Linien. Es ist die ausführlichere Schwester des Suchfelds auf der Seite „Algorithmen und Verfahren erklärt“. Kein Sprachmodell, kein Konto, nichts wird gespeichert.

## Warum dieses Werkzeug

Die Website ist groß geworden. Das Suchfeld dort findet nur, wenn jedes Suchwort als Teilstring vorkommt; wer „Touren für Lieferwagen planen“ oder „Zeitreihe vorhersagen“ tippt, findet nichts, weil auf der Website „Tourenplanung“ und „Prognose“ stehen. Der Navigator vergleicht Wörter nach Seltenheit, kennt Endungen, Tippfehler und eine Liste gleichbedeutender Wendungen und führt auf Wunsch Frage für Frage zur Demo.

## Modell

Der Navigator rechnet nichts über die Sache, nur über Wörter. Die Anfrage wird in Wörter zerlegt (ohne Füllwörter), jedes Wort mit den Wörtern der Einträge verglichen und nach BM25 bewertet: seltene Wörter zählen mehr; die Felder eines Eintrags sind gewichtet (Titel 3, Text 1, Bereichs- und Liniennamen 1,5), danach dämpft die BM25-Formel, ein Titeltreffer wirkt also weniger als dreimal so stark wie ein Texttreffer. Dazu kommen Endungen (planen = Planung), Wortanfänge ab vier Buchstaben, Wortteile ab fünf, Tippfehler (Ähnlichkeit der Buchstabengruppen und Editierabstand) und die Synonymliste. Ein Treffer gilt als „Wörter kommen vor“, wenn er mindestens die Hälfte der Anfragewörter erklärt, sonst als „teilweise“; erklärt er weniger als 30 % der Anfragewörter (nach Köpfen) oder weniger als die Hälfte (nach Seltenheit gewichtet), fällt er weg. Der Kern steht in `nav_search.py`, einer byte-genauen Kopie von `tools/navigator_search.py` im Website-Repo.

Der Tab „Fragen“ gibt die Entscheidungsbäume wieder, die auf den Linienseiten stehen (Fragen, Antworten, Demos, Sprünge zwischen Bäumen, Hinweise). Der Navigator erfindet keine eigenen.

## Methodik

- **Daten.** `navigator-index.json` der Website, erzeugt aus denselben Beschreibungen wie die Seiten (`tools/build_navigator_index.py`). Die App holt sie mit vier Sekunden Zeitlimit je Netzwerkschritt und höchstens zehn Sekunden insgesamt; eine Weiterleitung auf eine fremde Adresse zählt als Fehler. Sie hält die Datei sechs Stunden im Speicher. Schlägt der Abruf fehl, ist die Datei nicht gültig (Schemaversion, Felder, Verweise in den Bäumen) oder lässt sich aus ihr keine Suchumgebung bauen, gilt die eingebaute Kopie in `data/`; nach zehn Minuten versucht die App die Website erneut. Die Seitenleiste nennt die Quelle und den Stand.
- **Adressen.** Verlinkt wird nur auf die Website und ihre Streamlit-Demos; jede andere Adresse im Index (auch eine mit Port oder Zugangsdaten) wird nicht verlinkt. Alle Texte aus dem Index werden für Markdown entschärft, weil der Index über das Netz kommt.
- **Adresszeile.** `?q=…` wird gelesen, nie geschrieben: Eingaben können Persönliches enthalten. Wer eine Suche teilen will, bekommt den Link auf Wunsch angezeigt (auch ohne Treffer).
- **Beispielanfragen.** Sechs im Schnellstart, keine aus dem Auswertungsset im Website-Repo. Vier weitere Kandidaten fanden bei meiner Durchsicht am 2026-11-05 nichts Passendes und stehen deshalb nicht dort (`VERWORFENE_BEISPIELE` in `nav_constants.py`); sie sind Lücken der Suche, keine Beispiele.

## Befunde (gemessen, keine Behauptungen)

| Frage | Befund | Beleg |
|---|---|---|
| Geht die Rangfolge auf die Formel zurück? | Ja: auf einem Korpus aus einander unähnlichen erfundenen Wörtern stimmen Rangfolge und Punkte mit einer naiven Neuberechnung überein, 200 Anfragen | `tests/test_oracle_search.py` |
| Steht jede Linie bei ihrem Titel unter den ersten drei, jede Fall-Demo unter den ersten fünf? | Ja | `tests/test_search.py` |
| Führt jeder Entscheidungsbaum bis zu einem Ergebnis, Sprung oder Hinweis, ohne Schleife? | Ja, alle Bäume der eingebauten Kopie | `tests/test_guide.py` |
| Steht für jedes Beispiel mindestens eines der erwarteten Ziele unter den ersten fünf Treffern? | Ja, alle sechs (nicht immer auf Platz 1, siehe Grenzen) | `tests/test_search.py`, `tests/test_app.py` |
| Läuft die App ohne Netz? | Ja: scheitert der Abruf, fällt sie auf die eingebaute Kopie zurück | `tests/test_data.py`, `tests/test_app.py` |

Die Güte der Suche selbst (Treffer unter den ersten fünf bei 52 Anfragen, gegen die heutige Suche der Website) misst das Website-Repo mit `tools/navigator_eval.py`; die Zahlen stehen dort in `docs/planung/navigator-planung/PLAN.md`, nicht hier, weil sie hier nicht nachrechenbar sind.

## Ehrliche Grenzen

- **Wörter, kein Verstehen.** „Wörter kommen vor“ heißt nicht „passt zu Ihrem Problem“. Bei Anfragen in ganz anderen Wörtern als denen der Website findet die Suche nichts oder Falsches. Beim Probelauf der Beispiele fand etwa „Pünktlichkeit im Busverkehr“ als ersten Treffer eine Demo zu Verkehrsumlegung (Wort „Verkehr“) und erst danach die Taktfahrplan-Demo.
- **Die Statuszeile prüft nur Wörter.** Auch bei den vier verworfenen Beispielen meldet sie „Ihre Wörter kommen vor“, obwohl nichts Passendes dabei ist; sie sagt nichts über die Richtigkeit. Bei „Daten sinnvoll in Gruppen teilen“ steht an erster Stelle eine Grundlagen-Frage zu Bestenlisten, die Themenseite zur Clusteranalyse erst auf Platz 2.
- **Tippfehler** verzeiht die Suche erst bei Wörtern ab fünf Buchstaben; „Toru“ statt „Tour“ findet nichts. Einzelne Buchstaben und Ziffern zählen nicht als Suchwörter.
- **Die Fragen-Vorschläge im Tab „Fragen“** vergleichen ebenfalls nur Wörter und sind schwächer als die Suche: „Gruppen in Daten finden“ führt zu einer Frage der Spieltheorie, „Cluster“ zur Clustering-Linie.
- **Trefferzahl.** Die Statuszeile nennt bei mehr als 15 Treffern „Die ersten 15 von N Treffern“; N zählt die Treffer des Kerns nach den Filtern, höchstens 400.
- **Lücken der Synonymliste.** Die Liste ist von Hand geschrieben und wurde nachträglich um die Alltagswörter erweitert, die ein erster Messlauf vermisst hatte; sie ist deshalb für die dort gemessenen Anfragen besser als für neue.
- **Die Reihenfolge ist keine Empfehlung.** Ganz oben steht, was die Wörter am besten trifft.
- **Der Bereichsfilter** zeigt nur Einträge, die zu einem Bereich gehören; Fall-Demos, Themenseiten, Grundlagen und ein Teil der Erklärseiten haben keinen.
- **Der Index veraltet,** wenn die Website wächst und die Datei dort nicht neu hochgeladen wurde; die App nutzt dann die eingebaute Kopie oder eine ältere Datei und sagt es.
- **Browser:** Schnellstart, Eingabe, Tab „Fragen“ mit Sprung in den zweiten Baum und das Telefonformat (375 Pixel) wurden am 2026-11-05 im Browser durchgespielt, nur im dunklen Design. Das helle Design und die Seite im echten Cloud-Betrieb sind nicht angesehen; die Tests laufen mit `AppTest`.

## Tests

Die Suite mit pytest (Zahl und Laufzeit siehe unten) deckt: Kern (Eigenschaften und Orakel), Daten (Prüfung, Abruf, Rückfall, Adressen, Texte), Entscheidungsbäume, Verdikte, Layout und die App mit `AppTest`, dazu Footer, Laufzeit-Importe und die Zahlen dieser README. Kein Test geht ins Netz. Getestet wird mit der Streamlit-Version, die die Cloud installiert (`requirements.txt` begrenzt sie auf unter 1.55).

Tests: 159, Laufzeit rund eine halbe Minute.

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-App: Kopf, Seitenleiste, Tab „Suchen“, Tab „Fragen“, Erklärungen |
| `nav_constants.py` | Adressen, Grenzen, Namen der Arten, Beispielanfragen und ihre Ziele |
| `nav_data.py` | Index holen, prüfen, Rückfall; Adressen und Texte absichern |
| `nav_engine.py` | Suchumgebung aus dem Index; Suche mit Filtern; Fragen-Vorschläge |
| `nav_evaluation.py` | Verdikte und „Warum“-Texte (reine Funktionen) |
| `nav_guide.py` | Entscheidungsbäume bedienen (reine Funktionen) |
| `nav_layout.py` | Fester Kopf (Stylesheet) |
| `nav_presets.py` | Schnellstart, Lesen der Adresszeile, Einstellungen |
| `nav_search.py` | Suchkern, Kopie aus dem Website-Repo (`python tools/sync_navigator_app.py` dort) |
| `data/navigator-index.json` | Eingebaute Kopie des Index, Rückfall |
| `tests/` | Kern, Orakel, Daten, Bäume, Verdikte, Layout, App, Footer, Laufzeit-Importe, Zahlen der README |
| `requirements.txt` | Laufzeit: nur Streamlit, begrenzt auf 1.51 bis unter 1.55 |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |

## Bewusst nicht umgesetzt

- **Kein Sprachmodell.** Es kostet, braucht einen Schlüssel und kann Adressen erfinden; die Suche soll nachvollziehbar bleiben.
- **Kein Speichern von Eingaben,** auch keine Rückmeldungsfunktion. Der Zwischenspeicher der Suche merkt sich nur Wörter, die im Index vorkommen, nie Ihre Wortlaute (Test). Bei „nichts Passendes“ gibt es einen Link zur Kontaktseite.
- **Kein PDF-Export, kein Diagramm.** Der Navigator liefert Verweise, keine Ergebnisse zum Mitnehmen.
- **Kein Lernweg, keine Karte, keine ähnlichen Demos, keine Merkliste.** Das sind spätere Stücke des Navigators; der Lernweg braucht eine Richtung der Verweise zwischen Linien, die es heute nicht gibt (die Verweise sind symmetrisch).

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html).
