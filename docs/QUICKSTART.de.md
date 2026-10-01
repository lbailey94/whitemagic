# WhiteMagic Schnellstart

**Sprachen:** [English](QUICKSTART.md) · [Español](QUICKSTART.es.md) · [Português (BR)](QUICKSTART.pt-BR.md) · [Français](QUICKSTART.fr.md) · **Deutsch** · [हिन्दी](QUICKSTART.hi.md) · [Indonesia](QUICKSTART.id.md) · [العربية](QUICKSTART.ar.md) · [Kiswahili](QUICKSTART.sw.md) · [नेपाली](QUICKSTART.ne.md)

**Version**: Die aktuelle Version steht im [README](../README.md).
**Plattform**: Linux x86-64, Linux arm64, macOS arm64 + x86_64 und
Windows x86_64 — Installationspfade sind zertifiziert (install-gated). Linux
liefert vollständig statische musl-Builds, die der Installer automatisch
auswählt (ein dynamisch gelinkter Build bleibt für Hosts mit glibc 2.39+);
Releases veröffentlichen außerdem gzip-komprimierte Distributionen für
langsame Verbindungen. macOS installiert über `install.sh`; Windows über
`install.ps1` — jeder zertifizierte Pfad wird in CI gegen das veröffentlichte
Release geprüft.

Von null zu funktionierender Agenten-Erinnerung in unter fünf Minuten.

## Der 30-Sekunden-Pfad

```bash
wm grimoire          # geführter Erstlauf: Host, Speicherschicht, Agenten, Speicher, Vokabular, Kontinuität
wm connect --write   # verbindet jeden erkannten MCP-Client (vorher testen: wm connect)
wm quickstart        # optional: Kontinuitäts-Demo über zwei Prozesse mit isoliertem Store
```

Du siehst, wie eine im ersten Prozess aufgezeichnete Projektentscheidung
einen vollständigen Prozess-Neustart übersteht und von der nächsten Sitzung
wiederhergestellt wird. Das ist das Produkt.

## 1. Installation (keine Administratorrechte nötig)

### Aus einem Release

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

Unter Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.ps1 | iex
```

Das lädt das neueste Release herunter, prüft dessen SHA256-Checksum und
installiert `wm` nach `~/.local/bin` (Windows:
`%LOCALAPPDATA%\WhiteMagic\bin`, wird dem Benutzer-PATH hinzugefügt). Wenn
dieses Verzeichnis nicht im `PATH` liegt:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Manuell: Lade das Binärpaket deiner Plattform herunter (die statischen
`wm-linux-x86_64-musl` / `wm-linux-aarch64-musl`-Builds, die glibc-2.39+-
Builds `wm-linux-x86_64` / `wm-linux-aarch64`, `wm-macos-aarch64` /
`wm-macos-x86_64` oder `wm-windows-x86_64.exe`; jeweils mit `.gz`-Variante,
falls vorhanden, und `.sha256`-Datei) von der
[Releases-Seite](https://github.com/lbailey94/whitemagic/releases), dann:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

Die dynamisch gelinkten Builds benötigen glibc 2.39+ (gebaut auf Ubuntu
24.04); die statischen musl-Builds haben keine glibc-Anforderung.

### Aus dem Quellcode

Erfordert Rust 1.85+. Keine Administratorrechte nötig:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. Prüfen und aktivieren

```bash
wm --version   # aktuelle Version
wm grimoire    # geführter Erstlauf; nennt am Ende den Aktivierungsschritt
```

`wm grimoire` prüft die Umgebung und zeigt die Client-Verkabelung als
Vorschau; die Aktivierung selbst ist der Schritt `wm connect --write` unten.

## 3. MCP-Client verbinden

```bash
wm connect           # Probelauf: erkannte Clients und die genaue Änderung
wm connect --write   # jeden erkannten Client patchen (vorher zeitgestempelte Backups)
```

Oder einen Client explizit konfigurieren mit `wm setup <client> [--write]`.
Die entsprechende manuelle Konfiguration:

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "wm",
      "args": ["serve", "--profile", "curated"]
    }
  }
}
```

## 4. Optional: Kontinuitäts-Demo ausführen

```bash
wm quickstart
```

Die Demo nutzt einen isolierten Store unter
`~/.local/share/whitemagic-quickstart` (deine echten Daten bleiben
unberührt). Sie zeigt: Sitzungsstart → Entscheidung aufzeichnen →
Prozessstopp → neuer Prozess → Kontinuität stellt die Entscheidung wieder
her → budgetiertes Replay. Jederzeit entfernbar mit
`rm -rf ~/.local/share/whitemagic-quickstart`.

Falls etwas nicht stimmt: `wm doctor` ist das Diagnosewerkzeug (Store-,
Index- und Registry-Zustand) — es ist kein Einrichtungsschritt.

Der Server spricht JSON-RPC über stdio und stellt ein `wm`-Meta-Tool bereit.
Explizites Routing ist der verlässliche Vertrag:

- `wm(route="session.continuity")` — vor Arbeitsbeginn die vorherige Sitzung abrufen
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — alles Weitere entdecken

Siehe [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) für die clientspezifische
Einrichtung.

## 5. Backup

```bash
wm backup          # vollständiger Store -> ~/whitemagic-backups/<timestamp>
wm restore --backup <dir> [--force]
```

Bewahre Backups außerhalb der aktiven Maschine auf. Details im README.
