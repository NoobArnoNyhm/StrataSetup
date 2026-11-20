# Lokales Vibecoding mit Strata LLM und Pi

Das Setup liegt vollstaendig in diesem Ordner. Es besteht aus zwei
Linux-Containern: Strata als lokalem Modellserver und einem selbst gebauten
.NET-10-/Python-Entwicklungscontainer mit Pi.

**Wichtig fuer den ersten Start:** Docker sieht auf diesem Rechner aktuell
nur rund 31 GiB RAM. Vor dem Modellstart WSL2 mehr RAM zugestehen, beispielsweise
48 GB. Die WSL-Konfiguration wurde nicht veraendert. Auf ausdruecklichen Wunsch
wurde auch der grosse Modelldownload noch nicht gestartet.

## 1. Bereits eingerichtet

- [compose.yaml](compose.yaml): Strata mit NVIDIA-GPU und ausschliesslich
  lokalem Host-Port sowie ein Nicht-Root-Entwicklungscontainer.
- [Dockerfile](docker/pi/Dockerfile): offizielles Microsoft .NET SDK 10
  auf Ubuntu Noble, Python 3 mit pip/venv/Buildwerkzeugen, Git, curl, jq,
  tree, ripgrep, Node.js 24, GitHub CLI und Pi 1.6.0.
- [Initialize.ps1](Initialize.ps1): erstellt fehlende Datenverzeichnisse,
  erzeugt bei leerem Key einen kryptografisch zufaelligen API-Key und
  validiert Compose. Startet keine Container und aendert WSL nicht.
- [configure.py](docker/pi/configure.py): ermittelt die echte Modell-ID
  von Strata und richtet Pi beim Start automatisch ein.
- [.env](.env): lokale Einstellungen, einschliesslich vorbereitetem API-Key.
  Diese Datei ist in [.gitignore](.gitignore) ausgeschlossen.
- [.env.example](.env.example): Vorlage ohne Zugangsdaten.
- [Tests](tests/test_configure.py): Konfiguration, Fehlerfaelle und ein
  echter Pi-Aufruf mit Streaming und Werkzeugausfuehrung gegen eine lokale
  Test-API, ohne externen Modellanbieter.

Die beiden Images sind lokal gebaut beziehungsweise geladen. Keine
dauerhaften Container wurden gestartet; die Modellverzeichnisse sind noch leer.

## 2. Voraussetzungen und WSL-RAM

Verwendete Hardware: RTX 3080 Laptop GPU mit 16 GB VRAM und 64 GB Host-RAM.
Der erkannte NVIDIA-Treiber 596.52 passt zum CUDA-13-Image.

Erforderlich sind Docker Desktop mit WSL2-Backend, Linux-Container und
funktionierender NVIDIA-GPU-Durchreichung.

In PowerShell pruefen:

```powershell
docker version
docker compose version
docker info --format '{{.OSType}}'
docker info --format '{{.MemTotal}}'
nvidia-smi
```

`MemTotal` ist in Bytes. WSL2 belegt RAM zwar dynamisch, hat aber normalerweise
eine Obergrenze von 50 % des Host-RAMs. Fuer die vorausgewaehlte
IQ2_XS-Quantisierung dokumentiert Strata rund 35,5 GB System-RAM nur fuer die
Experten; dazu kommen Laufzeitpuffer, Entwicklung und weitere Prozesse.

Falls noetig, in `%UserProfile%\.wslconfig` folgende Einstellung in die
vorhandene Konfiguration integrieren:

```ini
[wsl2]
memory=48GB
```

Bestehende Einstellungen nicht ueberschreiben. Das ist eine Obergrenze fuer
WSL2 insgesamt, keine sofortige Reservierung und keine Garantie, dass beliebig
grosse Builds parallel zum Modell passen.

Zur Aktivierung ist ein WSL-Neustart erforderlich. **Vorher alle Arbeiten in
WSL und anderen Docker-Containern sichern und laufende Dienste bewusst stoppen.**
`wsl --shutdown` betrifft auch andere Projekte. Anschliessend Docker Desktop
neu starten und `MemTotal` erneut pruefen.

## 3. Einstellungen und Bind-Mounts

Alle Vorgaben stehen in [.env](.env):

| Variable | Vorgabe | Verwendung |
| --- | --- | --- |
| `STRATA_DATA_DIR` | `C:\00KiData\StrataLLM\data` | Strata: `/data`, Konfiguration und weitere persistente Daten |
| `STRATA_MODELS_DIR` | `C:\00KiData\StrataLLM\models` | Strata: `/data/Strata-data/models`, Modellgewichte |
| `PI_STATE_DIR` | `C:\00KiData\StrataLLM\pi-agent` | Pi: `/home/dev/.pi/agent`, Konfiguration und Sitzungen |
| `WORKSPACE_DIR` | `C:\Users\Arno_NyhmM\source\repos` | Entwicklung: `/workspace` |
| `STRATA_HOST_PORT` | `8080` | Ausschliesslich an `127.0.0.1` gebundener Host-Port |
| `STRATA_FAMILY` | `qwen` | Originale ISTA-DASLab-Packs fuer Qwen3.8-Flash-Next |
| `STRATA_MODEL` | `IQ2_XS` | Unterstuetzte Quantisierung, nicht die API-Modell-ID |
| `STRATA_CONTEXT` | `32k` | Server- und Pi-Kontext: 32768 Tokens |
| `STRATA_PARALLEL` | `1` | Eine gleichzeitige Modellanfrage |
| `STRATA_VISION` | `off` | Vision zunaechst ausgeschaltet |

Die Windows-Pfade sind in einfache Anfuehrungszeichen gesetzt, damit Compose
Backslashes unveraendert uebernimmt. Bestehende Prozess-Umgebungsvariablen
haben nach Compose-Regeln Vorrang vor den Werten in der Datei.

Konfiguration, Presets, API-Key, Tuning, Laufzeitdateien und Hilfsmodelle bleiben
im Daten-Bind-Mount erhalten. Die GGUF-Gewichte liegen im separat gebundenen
Modellverzeichnis. Der untergeordnete Model-Mount innerhalb von `/data` ist
beabsichtigt.

**Kein `MODEL_PATH` auf das leere Verzeichnis setzen.** Diese Strata-Variable
ist fuer bereits vorhandene GGUF-Dateien vorgesehen und verhindert bei einem
leeren Verzeichnis den automatischen Download.

Bei weiteren Anpassungen von Pfaden [Initialize.ps1](Initialize.ps1) erneut
ausfuehren. Ein fehlender Workspace wird nicht automatisch angelegt, sondern
als Fehler gemeldet. Die anderen drei Verzeichnisse werden bei Bedarf erstellt.
Compose selbst legt keine fehlenden Bind-Quellen an.

## 4. Starten

Alle PowerShell-Befehle in diesem Projektordner ausfuehren.

### Initialisierung und Build

Diese Schritte sind auf diesem Rechner bereits erfolgt und koennen wiederholt
werden. Ein vorhandener API-Key wird nicht neu erzeugt.

```powershell
.\Initialize.ps1
docker compose config --quiet
docker compose build pi-dev
```

Falls die lokale PowerShell-Ausfuehrungsrichtlinie das Skript blockiert,
die Datei erst pruefen und gegebenenfalls fuer genau diesen Aufruf starten:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Initialize.ps1
```

Das Entwicklungsimage verwendet nur [docker\pi](docker/pi) als Build-Kontext.
Host-Quellcode und [.env](.env) werden nicht ins Image kopiert. Node.js stammt
aus einer offiziellen Node-Image-Buildstage; GitHub CLI aus dem signierten
Paketrepository des Projekts. Pi wird mit festgelegter Version installiert.
Basisimage-Tags, Betriebssystempakete und transitive npm-Abhaengigkeiten sind
jedoch nicht vollstaendig durch eine Lockdatei eingefroren.

### Strata und ersten Modelldownload starten

**Erst nach Pruefung der RAM-Grenze:**

```powershell
docker compose up -d strata
docker compose logs -f strata
```

Der erste Start laedt fehlende Modell- und Hilfsdateien herunter und bereitet
sie vor. Fuer die kleineren Original-Quantisierungen dokumentiert Strata
Downloads von etwa 66 bis 76 GB; dazu kommen Hilfsdateien. Mindestens rund
100 GB freie SSD als Anfangsreserve einplanen, zusaetzlich zu Images und
Entwicklungsdateien. Bei langsamer Leitung kann der Erststart Stunden dauern.

Die Loganzeige mit Strg+C verlassen; der Container laeuft weiter.

```powershell
docker compose ps
docker compose up -d pi-dev
```

Der Entwicklungscontainer startet erst, wenn Strata gesund ist. Der
Strata-Healthcheck hat eine Anlaufzeit von zwei Stunden. Falls der Download
laenger dauert, Logs pruefen und diese Frist gegebenenfalls mit einer lokalen
Compose-Anpassung verlaengern; nicht unnoetig den Download neu starten.

### Pi benutzen

```powershell
docker compose exec pi-dev bash
```

In der Entwicklungs-Shell ins gewuenschte Projekt wechseln:

```bash
cd /workspace/MeinProjekt
pi
```

Oder direkt aus PowerShell:

```powershell
docker compose exec -w /workspace/MeinProjekt pi-dev pi
```

Kein Provider-Login erforderlich. Das Webfrontend ist auf dem Host unter
**http://127.0.0.1:8080** erreichbar; bei geaendertem Host-Port die URL anpassen.
Falls das Frontend den API-Key anfordert, diesen lokal aus [.env](.env)
uebernehmen. Nicht in Screenshots, Logs oder Commits veroeffentlichen.

## 5. Automatische Pi-Konfiguration

Pi spricht innerhalb des Compose-Netzes mit `http://strata:8080/v1`.
`localhost` waere dort der Pi-Container selbst.

Beim Start:

1. API-Key, Kontext und Vision-Einstellung validieren.
2. Authentifiziert `/v1/models` abfragen und genau eine Modell-ID verlangen.
   Verbindungsfehler werden maximal etwa 60 Sekunden wiederholt; falsche
   Zugangsdaten oder ungueltige Antworten brechen sofort ab.
3. Im persistenten Pi-Verzeichnis `models.json` und `settings.json`
   atomar aktualisieren.
4. Provider `strata` und die ermittelte Modell-ID als Standard setzen.
5. Den Entwicklungscontainer fuer interaktive Aufrufe bereit halten.

Die Einstellungen fuer OpenAI-Chat-Completions, Reasoning-Kompatibilitaet,
Ausgabelimit und automatische Komprimierung folgen
[Stratas Pi-Vorlage fuer v0.2.17](https://github.com/Niko1221/Strata/blob/v0.2.17/terminal/strata_cli/launch/harness.py).
Fuer 32k gelten 4096 Ausgabetokens und ein Komprimierungspunkt von rund
15000 Tokens. Die Pi-Konfiguration enthaelt nur die Referenz `$STRATA_API_KEY`,
nicht den eigentlichen Key.

Andere Provider, Sitzungen und nicht verwaltete Benutzereinstellungen bleiben
erhalten. Verwaltet werden der `strata`-Modelleintrag, dessen Verbindung,
die Provider-/Modell-Defaults und die Komprimierungsparameter.
Ein vorhandenes `defaultThinkingLevel` bleibt erhalten. Die Dateien werden
bei jedem Containerstart erneut mit den Servervorgaben abgeglichen.
Ungueltige bestehende JSON-Dateien werden nicht still ueberschrieben.

Es gibt keinen automatischen Cloud-Fallback und keine andere Modellwahl bei
Fehlern. Zugangsdaten, die man selbst spaeter fuer `strata` in Pi's `auth.json`
speichert, koennen gemaess Pi-Prioritaet den Umgebungs-Key uebersteuern.

## 6. Python und .NET

Das Image enthaelt das .NET-10-SDK, die Runtime und ASP.NET Core.
Plattformuebergreifende .NET-/ASP.NET-Projekte sind vorgesehen, nicht das
Ausfuehren von WPF/WinForms oder Windows-.NET-Framework-Anwendungen.

Python-Projekte in einer eigenen virtuellen Umgebung betreiben:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Keine globalen pip-Installationen mit `--break-system-packages`.
Linux- und Windows-venvs, `node_modules` und Build-Ausgaben nicht mischen.
GitHub CLI ist installiert, aber nicht mit einem Benutzerkonto angemeldet.

Caches und weitere Dateien im Container-Home ausserhalb des Pi-Bind-Mounts
sind absichtlich nicht persistent; nach einem Neuerstellen koennen Restore
oder erneute Anmeldung erforderlich sein.

## 7. Stoppen, Aendern und Aktualisieren

```powershell
docker compose down
```

Bind-Mount-Daten und Quellcode bleiben erhalten. Strata bekommt beim Stoppen
zwei Minuten fuer das geordnete Entladen des Modells.

Nach einer Aenderung an [.env](.env):

```powershell
.\Initialize.ps1
docker compose up -d
```

Bei Aenderungen am Entwicklungsimage oder an dessen Versionsvorgaben:

```powershell
docker compose build pi-dev
docker compose up -d pi-dev
```

Bei einem bewusst gewaehlten neuen Strata-Image-Tag:

```powershell
docker compose pull strata
docker compose up -d
```

Danach pruefen, ob der Pi-Container ebenfalls neu erstellt werden muss, falls
sich API-Modell-ID oder Serverkonfiguration geaendert haben. Bei Bedarf:

```powershell
docker compose up -d --force-recreate pi-dev
```

Modelldateien werden aus den Bind-Mounts weiterverwendet. Kein `strata update`
innerhalb des Containers ausfuehren; die Engine gehoert zum Image.

## 8. Sandbox-Grenzen

- Pi laeuft als Nicht-Root-Benutzer `dev`, ohne Linux-Capabilities und ohne
  Privilegienerhoehung. Kein Docker-Socket, Host-Netzwerk oder GPU-Zugriff
  im Entwicklungscontainer.
- **Pi kann alle Repositories im schreibbar eingebundenen Workspace lesen,
  veraendern und loeschen.** Fuer staerkere Isolation `WORKSPACE_DIR` auf ein
  einzelnes Repository oder eine gesonderte Arbeitskopie begrenzen.
- Auch das persistente Pi-Verzeichnis ist beschreibbar. Erweiterungen und
  Projektkonfiguration nur aus vertrauenswuerdigen Quellen laden.
- Der Strata-Container erhaelt keinen Quellcode-Mount. Die GPU-Freigabe
  bekommt ausschliesslich Strata.
- Der Entwicklungscontainer hat keinen veroeffentlichten Host-Port.
  Entwicklungs-Webserver bei Bedarf ausschliesslich an `127.0.0.1` publizieren.
- Docker-Bridge-Netzwerke erlauben standardmaessig ausgehenden Netzwerkzugriff
  fuer Paketmanager und Git. Dies ist **keine Egress-isolierte Sandbox**.
  Lokale Inferenz verhindert nicht, dass andere Programme Daten versenden.
- Keine Host-SSH-Schluessel oder Credential-Stores werden automatisch geteilt.
  Docker-Administratoren koennen Container-Umgebungsvariablen und damit den
  API-Key einsehen. [.env](.env) lokal und privat halten.
- NTFS-Bind-Mounts koennen bei Modell-Mapping und vielen kleinen Quelldateien
  langsamer sein als ein Linux-Dateisystem in WSL. Die gewuenschten
  Windows-Pfade werden trotzdem unveraendert verwendet.

## 9. Tests wiederholen

Die Konfigurations- und Pi-Integrationstests benoetigen kein Modell und
keinen Internetzugriff. Nach einem Image-Neubau in PowerShell:

```powershell
$tests = Join-Path (Get-Location) 'tests'
docker run --rm --network none --cap-drop ALL `
  --security-opt no-new-privileges:true `
  --entrypoint python3 `
  --mount "type=bind,source=$tests,target=/tests,readonly" `
  -e PYTHONPATH=/opt/pi stratasetup-pi:local `
  -m unittest discover -s /tests -v
```

GPU-Komponenten pruefen, ohne ein Modell herunterzuladen oder zu starten:

```powershell
docker compose run --rm --no-deps strata strata components engine
```

## 10. Bekannte Fehlerbilder

| Symptom | Vorgehen |
| --- | --- |
| Compose meldet leeren API-Key | `Initialize.ps1` ausfuehren; gegebenenfalls leere Prozess-Umgebungsvariable entfernen. |
| Bind-Quelle fehlt | Pfade in `.env` kontrollieren und initialisieren. Der Workspace muss schon existieren. |
| Strata beendet sich beim Modellladen/OOM | Docker-sichtbaren RAM pruefen, WSL-Grenze anpassen und andere Speicherverbraucher reduzieren. Kein unbemerkter Wechsel auf ein kleineres Modell. |
| Pi startet nicht | `docker compose logs pi-dev` sowie `docker compose ps` pruefen. Strata muss gesund sein. |
| Pi meldet HTTP 401/403 | Key-Abgleich und gegebenenfalls gespeicherten `strata`-Eintrag in Pi's `auth.json` pruefen. |
| Ungueltige Pi-JSON-Datei | Genannte Datei im Pi-Bind-Verzeichnis korrigieren; vorher sichern. Kein automatisches Loeschen der Sitzungen. |
| Mehrere Modell-IDs | Dieses Setup erwartet einen Einzelmodellserver; keine beliebige ID automatisch auswaehlen. |
| .NET meldet Workload-Verifizierung | Das SDK kann ohne optionale Workloads einen Hinweis zeigen. Der normale `net10.0`-Build wurde erfolgreich getestet. Workloads nur bei konkretem Projektbedarf installieren. |

## 11. Verifikation auf diesem Rechner

Stand: 20.11.2026.

- Compose-Konfiguration, feste IPv4-Loopback-Portbindung und Pflicht-Key
  geprueft; ein leerer Key wird abgewiesen.
- Initialisierung wiederholt: Key und bestehende Einstellungen unveraendert.
- Entwicklungsimage gebaut: .NET SDK 10.0.404, Python 3.12.3, Node.js
  24.22.3 und Pi 1.6.0 sowie alle verlangten CLI-Werkzeuge vorhanden.
- Nicht-Root-Zugriff auf die Windows-Workspace- und Pi-Bind-Mounts geprueft.
- Alle acht Konfigurations- und Integrationstests erfolgreich, einschliesslich
  echtem Pi-CLI-Aufruf, Streaming, Dateischreib-Tool und Startskript.
- Kleine `net10.0`-Konsolenanwendung unter Nicht-Root gebaut und ausgefuehrt.
- Python-venv erstellt und Python sowie pip darin erfolgreich ausgefuehrt.
- Strata-Image geladen; enthaltene Engine 0.1.63 erkennt Linux/CUDA ueber
  NVIDIA-Passthrough.
- Modellinstallation, echter Strata-Inferenzaufruf, Weboberflaeche unter
  Modelllast und Neustart ohne erneuten Modelldownload sind **noch nicht
  getestet**, weil RAM-Anpassung und Modelldownload bewusst spaeter erfolgen.

Die lokalen Tests simulieren nur das API-Protokoll. Sie belegen die Pi-
Konfiguration und Werkzeugschleife, nicht die Modellqualitaet oder eine
vollstaendig getestete Strata-/Pi-Inferenzverbindung.

## Quellen

- [Strata Docker-Dokumentation](https://github.com/Niko1221/Strata/blob/v0.2.17/docs/DOCKER.md)
- [Strata Modelle und Speicherbedarf](https://github.com/Niko1221/Strata/blob/v0.2.17/docs/MODELS.md)
- [Stratas versionsgebundene Pi-Vorlage](https://github.com/Niko1221/Strata/blob/v0.2.17/terminal/strata_cli/launch/harness.py)
- [Pi: eigene Endpunkte und Modelle](https://docs.pi.dev/latest/models)
- [Pi: Konfiguration](https://docs.pi.dev/latest/configuration)
- [Microsoft .NET SDK Images](https://github.com/dotnet/dotnet-docker/blob/main/README.sdk.md)
- [Docker Desktop: GPU unter WSL2](https://docs.docker.com/desktop/features/gpu/)
- [Microsoft: WSL-Konfiguration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)
- [Modellkarte und Modelllizenz](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)
