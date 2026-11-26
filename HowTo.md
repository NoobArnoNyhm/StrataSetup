# Lokales Vibecoding mit Strata LLM und Pi

Das Setup liegt vollstaendig in diesem Ordner. Es besteht aus zwei
Linux-Containern: Strata als lokalem Modellserver und einem selbst gebauten
.NET-10-/Python-Entwicklungscontainer mit Pi.

**Wichtig fuer den ersten Start:** Vor dem Modellstart den fuer Docker
verfuegbaren RAM pruefen und gegebenenfalls die WSL2-Grenze anpassen.

## 1. Bestandteile

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
- [.env](.env): lokale Einstellungen und API-Key. Diese Datei wird bei Bedarf
  aus der Vorlage erstellt und ist in [.gitignore](.gitignore) ausgeschlossen.
- [.env.example](.env.example): Vorlage ohne Zugangsdaten.
- [Tests](tests/test_configure.py): Konfiguration, Fehlerfaelle und ein
  echter Pi-Aufruf mit Streaming und Werkzeugausfuehrung gegen eine lokale
  Test-API, ohne externen Modellanbieter.

## 2. Voraussetzungen und WSL-RAM

Erforderlich sind Docker Desktop mit WSL2-Backend, Linux-Container und
funktionierender NVIDIA-GPU-Durchreichung. Der NVIDIA-Treiber muss mit dem
gewaehlten CUDA-Image kompatibel sein.

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

Falls noch keine [.env](.env) existiert, die Vorlage kopieren:

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

In [.env](.env) die Bind-Mount-Pfade an den eigenen Rechner anpassen.
Insbesondere muss `WORKSPACE_DIR` auf ein bereits vorhandenes Verzeichnis
zeigen; die Pfade in der Vorlage sind keine allgemeingueltigen Vorgaben.

| Variable | Verwendung |
| --- | --- |
| `STRATA_DATA_DIR` | Strata: `/data`, Konfiguration und weitere persistente Daten |
| `STRATA_MODELS_DIR` | Strata: `/data/Strata-data/models`, Modellgewichte |
| `PI_STATE_DIR` | Pi: `/home/dev/.pi/agent`, Konfiguration und Sitzungen |
| `WORKSPACE_DIR` | Entwicklung: `/workspace` |
| `STRATA_HOST_PORT` | Vorgabe `8080`: ausschliesslich an `127.0.0.1` gebundener Host-Port |
| `STRATA_FAMILY` | Vorgabe `qwen`: originale ISTA-DASLab-Packs fuer Qwen3.8-Flash-Next |
| `STRATA_MODEL` | Vorgabe `IQ2_XS`: unterstuetzte Quantisierung, nicht die API-Modell-ID |
| `STRATA_CONTEXT` | Vorgabe `32k`: Server- und Pi-Kontext mit 32768 Tokens |
| `STRATA_PARALLEL` | Vorgabe `1`: eine gleichzeitige Modellanfrage |
| `STRATA_VISION` | Vorgabe `off`: Vision zunaechst ausgeschaltet |

**Kontextgroesse:** Die voreingestellten `32k` sind fuer ernsthafte
Entwicklungsarbeit zu klein. Im Testsetup funktionierten `128k`, wobei auch
dieser Kontext in der Praxis noch sehr begrenzt war. Fuer diesen Wert in
`.env` setzen:

```dotenv
STRATA_CONTEXT=128k
```

Ein groesserer Kontext kann mehr Speicher benoetigen; ob er funktioniert,
haengt unter anderem von Modell und Hardware ab. Nach der Aenderung die
Initialisierung erneut ausfuehren und die Dienste wie unter
[Stoppen, Aendern und Aktualisieren](#7-stoppen-aendern-und-aktualisieren)
beschrieben aktualisieren.

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

### Alles initialisieren und starten

Nach Pruefung der RAM- und Speicheranforderungen kann dieses Skript
Initialisierung und Start beider Compose-Services uebernehmen:

```powershell
.\initialize_and_start.ps1
```

Es startet `strata` und `pi-dev`; `pi-dev` wartet, bis `strata` gesund ist.
Fuer einen schrittweisen Erststart stattdessen die folgenden Abschnitte nutzen.

### Initialisierung und Build

Diese Schritte koennen wiederholt werden. Ein vorhandener API-Key wird nicht
neu erzeugt.

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

### Pi und Strata benutzen

Die folgenden Zugriffe setzen voraus, dass die Container gestartet sind.
Auf dem Windows-Host im Projektordner pruefen:

```powershell
docker compose ps
```

`strata` muss bereit sein, bevor `pi-dev` startet. Beim ersten Start kann
der Modelldownload lange dauern; den Fortschritt zeigt
`docker compose logs -f strata`. Die Loganzeige mit `Strg+C` verlassen.

#### Pi ueber PowerShell und Docker Compose

```powershell
docker compose exec pi-dev bash
```

Der Befehl oeffnet eine Bash-Shell **im Entwicklungscontainer**. Dort ins
gewuenschte Projekt wechseln und Pi starten:

```bash
cd /workspace/MeinProjekt
pi
```

`MeinProjekt` ist ein Beispiel. Es muss ein vorhandenes Verzeichnis unter
dem in `.env` konfigurierten `WORKSPACE_DIR` sein, das im Container als
`/workspace` eingebunden ist. In Pi eine Aufgabe eintippen und mit `Enter`
absenden, zum Beispiel: `Erklaere mir die Struktur dieses Projekts.`

Pi wird fuer den lokalen Strata-Server konfiguriert; ein Cloud-Login ist
nicht erforderlich. Pi und seine Werkzeuge koennen im eingebundenen
Workspace Dateien lesen, aendern und loeschen.

Alternativ Pi direkt aus der PowerShell auf dem Host im Projektverzeichnis
starten:

```powershell
docker compose exec -w /workspace/MeinProjekt pi-dev pi
```

Fuer PowerShell statt Bash im Entwicklungscontainer:

```powershell
docker compose exec pi-dev pwsh -NoLogo
```

#### Pi mit `docker exec` oder Docker Desktop

Statt Compose kann auch `docker exec` verwendet werden. Im Projektordner
zunaechst die ID des laufenden Entwicklungscontainers ermitteln:

```powershell
$piContainer = docker compose ps -q pi-dev
docker exec -it $piContainer bash
```

In der Container-Shell danach wie oben `cd /workspace/MeinProjekt` und
`pi` ausfuehren. `docker ps` zeigt ebenfalls laufende Container mit Namen
und IDs.

In Docker Desktop unter **Containers** das Compose-Projekt `strata-setup`
aufklappen, den laufenden Container `pi-dev` auswaehlen und den Tab
**Exec** oeffnen. Im Terminal `cd /workspace/MeinProjekt` und anschliessend
`pi` ausfuehren. Ist Docker Debug aktiviert, wird statt **Exec** der Tab
**Debug** angezeigt. Die verfuegbaren Ansichten koennen je nach
Docker-Desktop-Version und Einstellung abweichen.

#### Strata-Webfrontend aufrufen

Auf dem Windows-Host einen Browser oeffnen und
[http://127.0.0.1:8080](http://127.0.0.1:8080) aufrufen. Der Port ist
standardmaessig an `127.0.0.1` gebunden: Das Frontend ist damit auf diesem
Rechner, aber nicht ueber die Netzwerkadresse von anderen Geraeten
erreichbar. Bei geaendertem `STRATA_HOST_PORT` den Port in der Browseradresse
entsprechend anpassen.

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

## 6. Python, .NET und PowerShell

Das Image enthaelt das .NET-10-SDK, die Runtime und ASP.NET Core.
Plattformuebergreifende .NET-/ASP.NET-Projekte sind vorgesehen, nicht das
Ausfuehren von WPF/WinForms oder Windows-.NET-Framework-Anwendungen.
Die .NET-Tools `csharp-ls`, `dotnet-ef`, `csharpier` und `dotnet-outdated`
stehen dem Benutzer `dev` ueber den Suchpfad zur Verfuegung. Fuer das
.NET-10-SDK werden `csharp-ls` 0.28.0 und `dotnet-ef` 10.x installiert.

Python-Projekte in einer eigenen virtuellen Umgebung betreiben:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Keine globalen pip-Installationen mit `--break-system-packages`.
Linux- und Windows-venvs, `node_modules` und Build-Ausgaben nicht mischen.
GitHub CLI ist installiert; fuer authentifizierte Aktionen ist eine Anmeldung
erforderlich.

Das .NET-SDK-Basisimage enthaelt PowerShell 7 (`pwsh`). Damit lassen sich
plattformuebergreifende PowerShell-Skripte im Container entwickeln und testen:

```powershell
docker compose exec pi-dev pwsh -NoLogo
```

In PowerShell im Container beispielsweise ein Skript ausfuehren:

```powershell
& /workspace/MeinProjekt/script.ps1
```

Der Container laeuft unter Linux. Windows-spezifische Funktionen wie Registry,
COM und Windows-PowerShell-5.1-Module muessen auf Windows getestet werden.
Pester ist nicht vorinstalliert; bei Bedarf kann es fuer den Benutzer `dev`
installiert werden. Im Container-Home installierte Module ausserhalb des
Pi-Bind-Mounts sind nach einem Neuerstellen nicht dauerhaft vorhanden.
Ein selbst gewaehltes `DOTNET_IMAGE` muss ebenfalls `pwsh` enthalten.

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
keinen Internetzugriff. Sie simulieren nur das API-Protokoll und pruefen
nicht die Modellqualitaet oder die Strata-/Pi-Inferenzverbindung mit einem
echten Modell. Nach einem Image-Neubau in PowerShell:

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
| .NET meldet Workload-Verifizierung | Das SDK kann ohne optionale Workloads einen Hinweis zeigen. Workloads nur bei konkretem Projektbedarf installieren. |

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
