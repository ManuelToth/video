# Renderer v2 – neu aufgebaut am 03.10.2026

Diese Version ist eine neue Implementierung, keine Wiederherstellung des früher erwähnten v2-Pakets. Basis ist der in Render bereitgestellte Commit `8722e150e79fb7fe692b119ccf2504d0641fb564` von `ManuelToth/video`.

## Verhalten

- Der bestehende Textmodus bleibt erhalten: fünf Szenen, 2–12 ganze Sekunden pro Szene, zusammen höchstens 45 Sekunden; alte Textanfragen höchstens 32768 Bytes.
- Bildmodus: fünf statische PNG/JPEG-Bilder als reines Base64 in `image_b64`; jede Szene enthält `text`, `dauer_s`, optional `motion`. Werte: `still`, `zoom_in`, `zoom_out`, `pan_left`, `pan_right`.
- Alle fünf Szenen enthalten Bilder oder alle sind Textszenen. Mischungen werden abgelehnt.
- Ausgabe: H.264/yuv420p, 360 × 640, 12 fps, ohne Audio. Ein Bild wird formatfüllend beschnitten. Der Bildmodus ist ausdrücklich als Hypothesen-Testvideo beschriftet.
- Maximal 1572864 Bytes je Bild, 10551296 Bytes je Anfrage. Die größere Grenze berücksichtigt die Base64-Vergrößerung von fünf maximal großen Bildern plus 65536 Bytes JSON-Overhead.
- Seitenlänge 64–4096 Pixel, maximal 12 Millionen Pixel; Animationen/SVG/URLs/Dateipfade und freie FFmpeg-Kommandos werden nicht akzeptiert. Bildheader und PNG-Prüfsummen werden vor Annahme geprüft; ungültige komprimierte Pixel führen zu einem fehlgeschlagenen Job, ohne Download.
- Der n8n-Payload-Node begrenzt seine eigenen Anfragen aktuell weiterhin auf 8 MiB. Diese zusätzliche Grenze wird mit diesem Serverpaket nicht verändert.
- Ein Renderjob und höchstens eine gleichzeitig eingelesene Renderanfrage; HTTP 429 bei Belegung. Authentifizierung weiterhin über vorhandenes `RENDER_API_KEY`/Header `X-API-Key`.
- Status liefert nach Fertigstellung zusätzlich gemessene `duration_s`, `file_size_bytes`, `width`, `height`.
- Health liefert `version: 2.0.0-rebuilt` und `image_mode: true` zusätzlich zu den bestehenden Feldern.
- Status-/Downloadpfade bleiben erhalten. Dateien/Jobs sind temporär und laufen nach einer Stunde ab; Neustart/Deployment verliert die temporären Jobs.

## Prüfung und Reproduktion

`python3 -m unittest discover -s tests -p test_renderer.py -v`

Die Tests verwenden nur lokale HTTP-Aufrufe, lokale FFmpeg-Prozesse und technische Testbilder. Kein Gemini, kein Render-Cloud-Auftrag. `tests/baseline_server.py` dient als unveränderte Vergleichsbasis aus dem genannten Commit. Die JPEG/PNG-Testbilder und der 38-Sekunden-Payload sind im Paket enthalten. Ergebnisse und Beispielvideo stehen in `evidence/`.

Die Dockerfile bleibt unverändert. Der tatsächliche Docker-Build/Start und der spätere Live-n8n-Bildtest sind eigenständige Prüfungen, nicht durch die lokalen Ergebnisse ersetzt.

## Vorgeschlagene Bereitstellung nach Freigabe

1. Den zuletzt bereitgestellten Basis-Commit und den unveränderten `main`-Stand erneut prüfen.
2. Änderungen in `ManuelToth/video` auf einem separaten Branch erfassen. Nur `server.py` ist eine Produktionscodeänderung; keine Secrets in Dateien oder Commits.
3. Für die Übernahme nach `main` prüfen, ob Auto-Deploy aktiv ist: der Merge/Upload kann bereits die Produktion ändern. Erst nach ausdrücklicher Deployment-Freigabe ausführen.
4. In Render den erfolgreichen Build und den neuen Commit prüfen. Anschließend `GET /health`: Version `2.0.0-rebuilt`, `image_mode=true`, `render_enabled=true`.
5. Nach gesonderter bzw. explizit kombinierter Testfreigabe genau einen isolierten Bildrender starten und bis `done` oder `failed` begrenzt abfragen. Kein Gemini-Aufruf erforderlich. Dauer/Abmessungen/Größe und abspielbare MP4 prüfen.
6. Video Factory erst nach erfolgreichem Live-Test anbinden. Audio, echte Bildgenerierung und Veröffentlichung bleiben weitere Arbeitsschritte.

## Rückkehr zur Basis

Bei Problemen in Render den früheren erfolgreichen Basis-Deploymentstand/Commit wieder bereitstellen. Damit gelten erneut die 32-KB-Grenze und der reine Textmodus. Temporäre Jobs überleben diesen Wechsel nicht. Die n8n-Video-Factory wurde in dieser Arbeitseinheit nicht geändert.
