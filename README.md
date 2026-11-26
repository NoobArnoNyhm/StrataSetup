# StrataSetup

StrataSetup richtet eine lokale KI-gestuetzte Entwicklungsumgebung unter
Windows ein. Sie kombiniert den Modellserver
[Strata](https://github.com/Niko1221/Strata) mit dem Coding-Agenten
[Pi](https://github.com/badlogic/pi-mono) und einer Linux-Entwicklungsumgebung
in Docker-Containern.

Das Projekt eignet sich beispielsweise, um mit einem lokalen Sprachmodell
Quellcode zu erklaeren, Aenderungen vorzubereiten und Projekte mit Pi zu
bearbeiten. Das Modell laeuft ueber Strata auf der eigenen Hardware; fuer die
Modellabfragen ist kein Cloud-Provider-Login erforderlich.

**Lokal bedeutet nicht automatisch offline:** Fuer Images, Pakete und den
ersten Modelldownload wird Internetzugriff benoetigt. Auch die laufenden
Container koennen standardmaessig ausgehende Netzwerkverbindungen aufbauen.
Pi kann Dateien im eingebundenen Workspace lesen, aendern und loeschen.

> **Erststart und Speicherbedarf:** Beim ersten Start werden grosse Modelle,
> Hilfsdateien, Docker-Images und weitere Pakete heruntergeladen und
> eingerichtet. Je nach Internetverbindung und Rechner kann das etliche
> Stunden dauern. Die Dateien belegen dauerhaft viel Speicherplatz: Fuer Modell
> und Hilfsdateien mindestens rund 100 GB freien SSD-Speicher einplanen,
> zusaetzlich zum Platz fuer Images und Projektdaten. Modell- und andere
> Bind-Mount-Daten bleiben auch nach `docker compose down` erhalten.

## Getestete Hardware

Das Setup wurde bisher nur auf einem Rechner mit folgender Ausstattung
getestet:

- NVIDIA RTX 3080 mit 16 GB VRAM
- 64 GB Arbeitsspeicher
- Windows mit WSL2 und Docker Desktop

Auf diesem Rechner musste der fuer WSL2 und damit Docker verfuegbare RAM auf
**48 GB** hochgesetzt werden. Das ist eine Obergrenze fuer die gesamte
WSL2-Umgebung, keine feste Reservierung ausschliesslich fuer dieses Projekt.
Andere Hardware- und Softwarekombinationen wurden bisher nicht getestet; die
genannten Werte sind daher keine allgemeine Mindestanforderung oder Garantie.

## Funktionsweise

Docker Compose startet zwei Dienste:

1. **`strata`** stellt das lokale Sprachmodell ueber eine API und ein
   Webfrontend bereit. Dieser Container erhaelt Zugriff auf die NVIDIA-GPU.
   Modellgewichte und Strata-Daten werden in Host-Verzeichnissen gespeichert.
2. **`pi-dev`** ist der Entwicklungscontainer. Er enthaelt Pi und
   Entwicklungswerkzeuge, bindet den gewaehlten Workspace ein und verbindet
   sich ueber das interne Compose-Netz mit Strata.

Beim Start ermittelt `pi-dev` die Modell-ID ueber die Strata-API und
konfiguriert Pi automatisch. Der Dienst wartet darauf, dass Strata gesund
ist. Ein API-Key schuetzt die Verbindung; der Host-Port des Modellservers
ist standardmaessig nur an `127.0.0.1` gebunden.

Die Vorlage verwendet die Strata-Modellfamilie `qwen` mit der Quantisierung
`IQ2_XS`, einem Kontext von `32k` und einer parallelen Anfrage. Modell,
Kontext und weitere Einstellungen koennen in der lokalen `.env` angepasst
werden. Ein anderes Modell kann andere Anforderungen und Downloads mit sich
bringen; es wird bei Fehlern nicht automatisch auf ein kleineres Modell
gewechselt.

### Entwicklungsumgebung

Das Entwicklungsimage enthaelt unter anderem:

- .NET 10 SDK und ASP.NET Core sowie `csharp-ls`, `dotnet-ef`, `csharpier`
  und `dotnet-outdated`
- PowerShell 7 (`pwsh`) zum Entwickeln und Testen plattformuebergreifender
  PowerShell-Skripte
- Python 3 mit `pip`, `venv` und Buildwerkzeugen
- Node.js, npm und den Coding-Agenten Pi
- Git, GitHub CLI, OpenSSH-Client, curl, jq, ripgrep, tree und Midnight Commander

Die Werkzeuge laufen im Linux-Container. Plattformuebergreifende .NET- und
ASP.NET-Projekte sind vorgesehen; WPF, WinForms und Anwendungen fuer das
Windows-.NET-Framework laufen dort nicht.
Ebenso muessen Windows-spezifische PowerShell-Funktionen auf Windows getestet
werden. Pester ist nicht vorinstalliert.

## Voraussetzungen

### Hardware und Speicher

- Eine NVIDIA-GPU mit unterstuetztem Treiber und funktionierender
  GPU-Durchreichung an Docker unter WSL2.
- Ausreichend System-RAM und VRAM fuer das gewaehlte Modell. Fuer die
  vorbelegte `IQ2_XS`-Quantisierung dokumentiert Strata rund 35,5 GB
  System-RAM allein fuer die Experten; Betriebssystem, Laufzeitpuffer und
  Entwicklungswerkzeuge benoetigen zusaetzlichen Speicher.
- Fuer die kleineren Original-Quantisierungen dokumentiert Strata Downloads
  von etwa 66 bis 76 GB. Dazu kommen Hilfsdateien, Images und Projektdaten.
  Als Anfangsreserve mindestens rund 100 GB freien SSD-Speicher fuer Modell
  und Hilfsdateien einplanen.
- Eine Internetverbindung fuer Image-Build und -Download, Paketinstallation
  und den ersten Modelldownload. Der erste Start kann lange dauern.

Der tatsaechliche Bedarf haengt von Modell, Quantisierung, Kontext und
Arbeitslast ab. Details stehen in der
[Strata-Modelluebersicht](https://github.com/Niko1221/Strata/blob/v0.2.17/docs/MODELS.md).

### Software auf dem Windows-Host

- Windows mit aktiviertem und eingerichtetem **WSL2** sowie
  Virtualisierungsunterstuetzung.
- **Docker Desktop** mit WSL2-Backend, Linux-Containern und Docker Compose.
  Docker Desktop muss gestartet sein.
- Ein zur verwendeten GPU und zum CUDA-Image passender NVIDIA-Treiber fuer
  Windows und funktionierender GPU-Zugriff aus WSL2/Docker.
- **PowerShell** zum Ausfuehren der Einrichtungsskripte.
- **Git**, falls das Repository geklont werden soll; alternativ kann es
  anderweitig heruntergeladen werden.

Python, Node.js und das .NET SDK muessen fuer die Entwicklungsumgebung nicht
zusaetzlich auf dem Host installiert werden; sie sind im Image enthalten.
Installation und Voraussetzungen der Einzelkomponenten:
[WSL](https://learn.microsoft.com/en-us/windows/wsl/install),
[Docker Desktop fuer Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
und [GPU-Unterstuetzung in Docker Desktop](https://docs.docker.com/desktop/features/gpu/).

### Voraussetzungen pruefen

In PowerShell:

```powershell
wsl --status
docker version
docker compose version
docker info --format '{{.OSType}}'
docker info --format '{{.MemTotal}}'
nvidia-smi
```

`docker info` sollte als Betriebssystemtyp `linux` ausgeben. `MemTotal` zeigt
den fuer Docker sichtbaren Arbeitsspeicher in Bytes. `nvidia-smi` prueft den
Treiber auf dem Host; die GPU-Durchreichung in den Strata-Container kann
zusaetzlich wie in [HowTo.md](HowTo.md) beschrieben geprueft werden.

## WSL2-Speicher konfigurieren

Falls Docker fuer das gewaehlte Modell zu wenig RAM sieht, die Datei
`%UserProfile%\.wslconfig` pruefen. Fuer die oben genannte getestete
Konfiguration wurde folgende Einstellung verwendet:

```ini
[wsl2]
memory=48GB
```

Die Einstellung bei Bedarf in die **bestehende** Datei integrieren, statt
andere WSL-Einstellungen zu ueberschreiben. Die Grenze gilt fuer WSL2
insgesamt; Windows und andere Programme benoetigen ebenfalls RAM. Die
Initialisierungsskripte aendern `.wslconfig` nicht automatisch.

Damit eine Aenderung wirksam wird, muessen WSL und Docker Desktop neu
gestartet werden. **Vorher alle Arbeiten in WSL und anderen Containern
sichern und laufende Dienste bewusst stoppen.** Der folgende Befehl beendet
alle laufenden WSL-Distributionen und kann auch andere Projekte betreffen:

```powershell
wsl --shutdown
```

Danach Docker Desktop wieder starten und den verfuegbaren Speicher mit
`docker info --format '{{.MemTotal}}'` erneut pruefen.

## Einrichtung und erster Start

Alle folgenden PowerShell-Befehle werden im Projektordner ausgefuehrt.
Die ausfuehrliche Anleitung mit weiteren Pruefungen und Fehlerbildern steht
in [HowTo.md](HowTo.md).

### 1. Repository und Konfiguration vorbereiten

Repository klonen und in den Projektordner wechseln:

```powershell
git clone https://github.com/NoobArnoNyhm/StrataSetup.git
Set-Location StrataSetup
```

Falls das Repository bereits vorliegt, stattdessen den vorhandenen Ordner
verwenden. Eine vorhandene `.env` nicht ueberschreiben:

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
notepad .env
```

In `.env` insbesondere diese absoluten Windows-Pfade an die eigene Umgebung
anpassen:

| Variable | Zweck |
| --- | --- |
| `STRATA_DATA_DIR` | Persistente Strata-Daten und Konfiguration |
| `STRATA_MODELS_DIR` | Persistente Modellgewichte |
| `PI_STATE_DIR` | Pi-Konfiguration und Sitzungen |
| `WORKSPACE_DIR` | Entwicklungsverzeichnis, das unter `/workspace` eingebunden wird |

`WORKSPACE_DIR` muss bereits existieren; die anderen Verzeichnisse legt das
Initialisierungsskript bei Bedarf an. Die Pfade in der Vorlage sind an die
eigene Umgebung anzupassen. Windows-Pfade in der `.env` in einfache
Anfuehrungszeichen setzen, damit Compose die Backslashes unveraendert
uebernimmt.

`STRATA_API_KEY` kann fuer die Initialisierung leer bleiben: Das Skript
erzeugt dann einen zufaelligen Key und speichert ihn in `.env`, ohne ihn
auszugeben. Ein selbst gesetzter Key muss mindestens 16 Zeichen lang sein.
Die Datei `.env` ist von Git ausgeschlossen und sollte privat bleiben.
Prozess-Umgebungsvariablen koennen die Werte aus `.env` bei Compose
ueberschreiben.

### 2. Initialisieren und starten

Nach Pruefung von RAM, freiem Speicher und den Pfaden:

```powershell
.\initialize_and_start.ps1
```

Das Skript fuehrt zuerst [Initialize.ps1](Initialize.ps1) aus und startet
anschliessend beide Compose-Dienste im Hintergrund. Die Initialisierung
prueft unter anderem die Konfiguration, den API-Key und die Bind-Mounts.
Sie warnt bei weniger als 46 GiB Docker-sichtbarem RAM, stoppt deshalb aber
nicht automatisch.

Alternativ laesst sich die Initialisierung getrennt ausfuehren:

```powershell
.\Initialize.ps1
docker compose up -d strata
docker compose logs -f strata
```

Beim ersten Start laedt Strata fehlende Modell- und Hilfsdateien herunter.
Die Loganzeige mit `Strg+C` verlassen; der Container laeuft weiter. Sobald
Strata gesund ist, den Entwicklungscontainer starten:

```powershell
docker compose up -d pi-dev
```

Wenn eine PowerShell-Ausfuehrungsrichtlinie das Skript blockiert, das Skript
zuerst pruefen und gegebenenfalls fuer den einzelnen Aufruf starten:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\initialize_and_start.ps1
```

### 3. Pi verwenden

Status pruefen und eine Shell im Entwicklungscontainer oeffnen:

```powershell
docker compose ps
docker compose exec pi-dev bash
```

Fuer PowerShell statt Bash:

```powershell
docker compose exec pi-dev pwsh -NoLogo
```

In der Shell ein Projekt im eingebundenen Workspace auswaehlen und Pi starten:

```bash
cd /workspace/MeinProjekt
pi
```

`MeinProjekt` ist ein Beispiel und muss durch ein vorhandenes Verzeichnis
ersetzt werden. Das Strata-Webfrontend ist standardmaessig auf dem Host
unter `http://127.0.0.1:8080` erreichbar. Bei geaendertem
`STRATA_HOST_PORT` den Port entsprechend anpassen. Falls das Frontend den
API-Key verlangt, den Wert lokal aus `.env` entnehmen.

## Betrieb und Daten

```powershell
docker compose ps
docker compose logs -f strata
docker compose logs -f pi-dev
docker compose down
```

`docker compose down` stoppt und entfernt die Compose-Container und das
Compose-Netzwerk. Die eingebundenen Host-Verzeichnisse mit Quellcode,
Modellen, Strata-Daten und Pi-Sitzungen bleiben erhalten.

Nach einer Aenderung an `.env` erneut initialisieren und die Dienste
aktualisieren:

```powershell
.\Initialize.ps1
docker compose up -d
```

Nach Aenderungen am Entwicklungsimage dieses neu bauen und den
Entwicklungscontainer neu erstellen:

```powershell
docker compose build pi-dev
docker compose up -d pi-dev
```

## Sicherheit und Grenzen

- Pi laeuft als Benutzer `dev` ohne Root-Rechte, zusaetzliche
  Linux-Capabilities oder Docker-Socket. Es ist aber keine vollstaendige
  Sicherheitsgrenze fuer den eingebundenen Workspace.
- **Der Workspace ist beschreibbar.** Pi und im Container ausgefuehrte
  Programme koennen dort Dateien lesen, aendern und loeschen. Fuer staerkere
  Isolation ein einzelnes Repository oder eine gesonderte Arbeitskopie
  einbinden.
- Die Container sind nicht vom Internet isoliert. Lokale Modellinferenz
  verhindert nicht, dass andere Programme Daten ueber das Netzwerk senden.
- `.env` und API-Key nicht veroeffentlichen oder committen. Docker-
  Administratoren koennen Container-Umgebungsvariablen einsehen.
- Strata ist standardmaessig nur ueber den lokalen Host-Port erreichbar;
  der Entwicklungscontainer veroeffentlicht keinen eigenen Host-Port.
- Projekt- und Pi-Konfiguration sowie Erweiterungen nur aus
  vertrauenswuerdigen Quellen verwenden.

## Projektdateien und Tests

| Datei | Aufgabe |
| --- | --- |
| [compose.yaml](compose.yaml) | Dienste, Netzwerk, GPU und Bind-Mounts |
| [.env.example](.env.example) | Vorlage fuer die lokale Konfiguration |
| [Initialize.ps1](Initialize.ps1) | Konfiguration und Verzeichnisse vorbereiten, ohne Container zu starten |
| [initialize_and_start.ps1](initialize_and_start.ps1) | Initialisieren und beide Dienste starten |
| [docker/pi/Dockerfile](docker/pi/Dockerfile) | Entwicklungsimage mit Pi und Werkzeugen |
| [docker/pi/configure.py](docker/pi/configure.py) | Automatische Verbindung und Pi-Konfiguration |
| [tests/test_configure.py](tests/test_configure.py) | Konfigurations- und Pi-Integrationstests |
| [HowTo.md](HowTo.md) | Ausfuehrliche Einrichtung, Betrieb, Tests und Fehlerbehebung |

Die Tests in [HowTo.md](HowTo.md) simulieren das API-Protokoll und benoetigen
kein Modell. Sie pruefen nicht die Modellqualitaet oder eine vollstaendige
Inferenzverbindung mit einem echten Modell.
