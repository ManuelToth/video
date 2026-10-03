# Prüfbericht – Renderer v2, neu aufgebaut am 03.10.2026

## Ergebnis

14/14 Testmethoden erfolgreich unter Ubuntu FFmpeg 6.1.1 / Python 3.12.14 und 14/14 unter Debian FFmpeg 5.1.9 / Python 3.12.15 mit Debian-DejaVu-Schrift. Alle Tests verwenden lokale HTTP-/FFmpeg-Ausführungen. Keine Cloud-Renderjobs, keine Gemini-Aufrufe, keine Änderungen in n8n oder Render und keine GitHub-Schreibzugriffe.

| Kriterium | Frische Evidenz | Status |
|---|---|---|
| Aktuelles n8n-Bildschema | Payload-Node live gelesen; passender Vertragstest | Bestätigt |
| Fünf Bildszenen, Zoom/Schwenk | Echter 38-s-Render; bewegte Bildbereiche je Szene verglichen | Bestätigt |
| PNG und JPEG, statisches Bild | Gemischter echter Render; Stabilität mit Toleranz für verlustbehaftete H.264-Kompression | Bestätigt |
| 1,5 MiB je Bild | exakter Grenzwert akzeptiert, +1 Byte abgelehnt | Bestätigt |
| Gesamtgrenze 10551296 Bytes | fünf maximal große PNGs plus JSON-Padding per HTTP angenommen und gerendert; +1-Header abgelehnt | Bestätigt |
| Alter Textmodus | Unveränderter Basiscode mit identischem Input/FFmpeg/Schrift bytegleich verglichen | Bestätigt |
| API-Auth, Fehler, Belegung, Ablauf | 401/503/400/413/429/409/404 sowie fehlerhafte Pixel geprüft | Bestätigt |
| Reale Dauer/Größe/Format | Status gegen Download/ffprobe verglichen | Bestätigt |
| Docker-Build und Start als UID 10001 | Docker fehlt; chroot-Recht nicht verfügbar | Nicht geprüft |
| Live-Bildrender über n8n/Render | Nicht gestartet | Nicht geprüft |

Das Bookworm-Testsystem nutzt das offizielle Python-Basisimage (Digest in `evidence/runtime-source.json`) und SHA-256-geprüfte Debian-Pakete. Wegen fehlender Docker-/chroot-Möglichkeiten laufen Interpreter und FFmpeg über den extrahierten Debian-Lader mit Debian-Bibliotheken; die Dateisystem-/UID-/Netzwerkisolation eines echten Containers wurde damit nicht getestet. Die erste unprivilegierte Bibliotheksauswahl musste um Debian-Unterverzeichnisse ergänzt werden, damit keine Ubuntu-PulseAudio-Bibliothek geladen wird. Kein Privilegien-Escalation-Versuch.

## Beispielvideo mit technischen Testbildern

- Dauer: 38.000000 Sekunden.
- Dateigröße: 4831813 Bytes.
- 360 × 640, H.264/yuv420p, 12 fps, 456 Frames, kein Audiostream.
- Fünf technische Musterbilder. Es handelt sich nicht um neu generierte KI-Motive oder ein fertiges redaktionelles Video.
- Textdarstellung an allen fünf Szenen visuell geprüft; Kontaktbogen in `evidence/kontaktbogen.png`.
- Wörter/Behauptungen aus dem Testworkflow sind Testtexte; keine neue inhaltliche Faktenfreigabe.

## Legacy-Vergleich

Basis: `8722e150e79fb7fe692b119ccf2504d0641fb564`, unveränderte `tests/baseline_server.py`.

Bookworm-Vergleichsvideo: 52340 Bytes, SHA-256 `e8985cb7d2d2e173d87789cf81db4eb6acf890be67a4ba9f205594a03eeca712`, exakt bytegleich. Das Testmanifest enthält fünf Szenen à zwei Sekunden. Es ist nicht derselbe Input wie der historische Produktionslauf 141; dessen 102170 Bytes werden hier nicht als erneut gemessen behauptet.

## Testbefehle und Ergebnisdateien

- `python3 -m unittest discover -s tests -p test_renderer.py -v`: Exit 0, 14 Tests; `evidence/test-run-ffmpeg6.txt`.
- Derselbe Testbefehl mit extrahiertem Python 3.12.15, Debian-FFmpeg im PATH und `RENDER_TEST_FONT` auf die Debian-Schrift: Exit 0, 14 Tests; `evidence/test-run-bookworm-userspace.txt`.
- `python3 -m py_compile server.py tests/test_renderer.py`: Exit 0.
- `ffprobe -v error -count_frames -show_streams -show_format -of json evidence/bildmodus-test.mp4`: Format/Stream-Evidenz in `evidence/ffprobe-image.json`.

Ein erster JPEG-Stabilitätstest verlangte identische dekodierte H.264-Pixel. Wegen normaler verlustbehafteter Kompression wurde die Prüfung auf eine geringe mittlere Pixelabweichung geändert; der Produktionscode wurde dafür nicht angepasst. Die bitgenaue Legacy-Prüfung bleibt unverändert streng.

## Umfang und offene Schritte

Produktionsänderung nur in `server.py`; Dockerfile unverändert. Neu: Bildvalidierung, feste Bewegungsfilter, Request-Lock, 15-s-Einlese-Timeout, Decoder-Pixelgrenze und additive Messdaten/Versionsanzeige. Authentifizierung, Endpunkte, temporäre Joblogik und die eigentlichen Legacy-FFmpeg-Kommandos bleiben erhalten.

Nicht umgesetzt: Deployment, neue bezahlte Bildgenerierung, Audio, höhere Auflösung, Veröffentlichung, begrenztes n8n-Polling oder Anschluss an Video Factory. Der bestehende KI-Bilder-Testworkfow wurde nur gelesen. Für das Deployment ist eine ausdrückliche Freigabe erforderlich, weil ein GitHub-Update von main einen Auto-Deploy auslösen kann. Die nächste unabhängige Evidenz ist ein erfolgreicher Render-Build und ein isolierter Live-Bildrender nach Freigabe.
