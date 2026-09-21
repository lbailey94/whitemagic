# Guide de démarrage rapide WhiteMagic

**Langues :** [English](QUICKSTART.md) · [Español](QUICKSTART.es.md) ·
[Português (BR)](QUICKSTART.pt-BR.md) · **Français**

**Version** : consultez la version actuelle dans le [README](../README.md).
**Plateforme** : Linux x86-64 (musl statique, sans dépendance de
distribution) ; les builds Linux arm64 (aarch64) rejoignent la matrice de
publication avec des tests natifs en CI et l'installateur les sélectionne
automatiquement lorsqu'une version les fournit. Les binaires macOS et
Windows sont publiés à chaque version, mais leurs chemins d'installation ne
sont pas encore validés.

De zéro à une mémoire d'agent fonctionnelle en moins de cinq minutes.

## Parcours en 30 secondes

```bash
wm grimoire     # première exécution guidée : hôte, couche de mémoire, agents, mémoire, vocabulaire, continuité
wm quickstart   # démo de continuité entre deux processus sur un stockage isolé
wm selftest     # vérification des invariants de bout en bout (~1 seconde, stockage temporaire)
```

Vous verrez une décision enregistrée dans une session survivre à un arrêt et
redémarrage complets du processus, puis être récupérée par la session
suivante. C'est le produit.

## 1. Installer (sans droits administrateur)

### Depuis une version publiée

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

Le script télécharge la dernière version, vérifie son checksum SHA256 et
installe `wm` dans `~/.local/bin`. Si ce dossier n'est pas dans votre `PATH` :

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Équivalent manuel : téléchargez le binaire de votre plateforme
(`wm-linux-x86_64` ou `wm-linux-aarch64`) et son fichier `.sha256` depuis la
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

## 2. Vérifier

```bash
wm --version   # affiche la version installée
wm doctor      # santé du stockage, de l'index et du registre d'outils
```

## 3. Lancer la démo

```bash
wm quickstart
```

La démo utilise un stockage isolé dans `~/.local/share/whitemagic-quickstart`
(vos données réelles ne sont jamais touchées). Elle montre : début de session
→ enregistrement d'une décision → arrêt du processus → nouveau processus → la
continuité récupère la décision → relecture avec budget. Vous pouvez la
supprimer à tout moment avec `rm -rf ~/.local/share/whitemagic-quickstart`.

## 4. Connecter votre client MCP

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
