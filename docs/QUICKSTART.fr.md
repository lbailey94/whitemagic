# Guide de démarrage rapide WhiteMagic

**Langues :** [English](QUICKSTART.md) · [Español](QUICKSTART.es.md) · [Português (BR)](QUICKSTART.pt-BR.md) · **Français** · [Deutsch](QUICKSTART.de.md) · [हिन्दी](QUICKSTART.hi.md) · [Indonesia](QUICKSTART.id.md) · [العربية](QUICKSTART.ar.md) · [Kiswahili](QUICKSTART.sw.md) · [नेपाली](QUICKSTART.ne.md)

**Version** : consultez la version actuelle dans le [README](../README.md).
**Plateforme** : Linux x86-64, Linux arm64, macOS arm64 + x86_64 et
Windows x86_64 — chemins d'installation validés (install-gated). Linux
fournit des builds statiques musl sélectionnés automatiquement par
l'installateur (des builds dynamiques restent disponibles pour les hôtes
glibc 2.39+) ; les versions publient aussi des distributions compressées en
gzip pour les liens lents. macOS s'installe via `install.sh` ; Windows via
`install.ps1` — chaque chemin validé est certifié en CI contre la version
publiée.

De zéro à une mémoire d'agent fonctionnelle en moins de cinq minutes.

## Parcours en 30 secondes

```bash
wm grimoire          # première exécution guidée : hôte, couche de mémoire, agents, mémoire, vocabulaire, continuité
wm connect --write   # connecte chaque client MCP détecté (simulation d'abord : wm connect)
wm quickstart        # facultatif : démo de continuité entre deux processus sur un stockage isolé
```

Vous verrez une décision enregistrée dans une session survivre à un arrêt et
redémarrage complets du processus, puis être récupérée par la session
suivante. C'est le produit.

## 1. Installer (sans droits administrateur)

### Depuis une version publiée

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

Sur Windows (PowerShell) :

```powershell
irm https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.ps1 | iex
```

Le script télécharge la dernière version, vérifie son checksum SHA256 et
installe `wm` dans `~/.local/bin` (Windows :
`%LOCALAPPDATA%\WhiteMagic\bin`, ajouté au PATH utilisateur). Si ce dossier
n'est pas dans votre `PATH` :

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Équivalent manuel : téléchargez le binaire de votre plateforme (les builds
statiques `wm-linux-x86_64-musl` / `wm-linux-aarch64-musl`, les builds
glibc 2.39+ `wm-linux-x86_64` / `wm-linux-aarch64`, `wm-macos-aarch64` /
`wm-macos-x86_64`, ou `wm-windows-x86_64.exe` ; avec leur variante `.gz`
quand elle existe et leur fichier `.sha256`) depuis la
[page des versions](https://github.com/lbailey94/whitemagic/releases), puis :

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

Le binaire exige glibc 2.39+ (compilé sur Ubuntu 24.04) ; les builds musl
statiques n'ont aucune dépendance.

### Depuis les sources

Rust 1.85+ requis. Aucun droit administrateur nécessaire :

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. Vérifier et activer

```bash
wm --version   # affiche la version installée
wm grimoire    # vérification guidée ; se termine en nommant l'étape d'activation
```

`wm grimoire` vérifie l'environnement et montre la configuration des clients ;
l'activation elle-même est l'étape `wm connect --write` ci-dessous.

## 3. Connecter votre client MCP

```bash
wm connect           # simulation : liste les clients détectés et la modification exacte
wm connect --write   # modifie chaque client détecté (sauvegardes horodatées d'abord)
```

Ou configurez un client explicitement avec `wm setup <client> [--write]`. La
configuration manuelle équivalente :

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

## 4. Facultatif : lancer la démo de continuité

```bash
wm quickstart
```

La démo utilise un stockage isolé dans `~/.local/share/whitemagic-quickstart`
(vos données réelles ne sont jamais touchées). Elle montre : début de session
→ enregistrement d'une décision → arrêt du processus → nouveau processus → la
continuité récupère la décision → relecture avec budget. Vous pouvez la
supprimer à tout moment avec `rm -rf ~/.local/share/whitemagic-quickstart`.

Si quelque chose ne va pas, `wm doctor` est l'outil de diagnostic (santé du
stockage, de l'index et du registre) — ce n'est pas une étape d'installation.

Le serveur parle JSON-RPC sur stdio et expose un seul méta-outil `wm`. Le
routage explicite est le contrat fiable :

- `wm(route="session.continuity")` — récupérer la session précédente avant de commencer
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — découvrir tout le reste

Voir [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) pour la configuration par
client.

## 5. Sauvegarder

```bash
wm backup          # stockage complet -> ~/whitemagic-backups/<horodatage>
wm restore --backup <dir> [--force]
```

Conservez les sauvegardes hors de la machine active. Détails dans le README.
