# WhiteMagic Mwongozo wa Haraka

**Lugha:** [English](QUICKSTART.md) · [Español](QUICKSTART.es.md) · [Português (BR)](QUICKSTART.pt-BR.md) · [Français](QUICKSTART.fr.md) · [Deutsch](QUICKSTART.de.md) · [हिन्दी](QUICKSTART.hi.md) · [Indonesia](QUICKSTART.id.md) · [العربية](QUICKSTART.ar.md) · **Kiswahili** · [नेपाली](QUICKSTART.ne.md)

**Toleo**: toleo la sasa liko kwenye [README](../README.md).
**Njia ya usakinishaji**: Linux x86-64, Linux arm64, macOS arm64 + x86_64 na
Windows x86_64 — zilizothibitishwa (install-gated). Linux hutoa build tuli za
musl ambazo kisakinishi huchagua kiotomatiki (build inayotegemea glibc 2.39+
inabaki kwa hosts zinazohitaji); matoleo pia hutoa distribusheni zilizobanwa
kwa gzip kwa mitandao ya polepole. macOS husakinishwa kwa `install.sh`;
Windows kwa `install.ps1` — kila njia iliyothibitishwa hupimwa katika CI
dhidi ya toleo lililochapishwa.

Kutoka sifuri hadi kumbukumbu ya wakala inayofanya kazi chini ya dakika tano.

## Njia ya sekunde 30

```bash
wm grimoire          # mbio ya kwanza inayoongozwa: host, safu ya kumbukumbu, mawakala, kumbukumbu, msamiati, mwendelezo
wm connect --write   # unganisha kila mteja wa MCP anayegunduliwa (jaribu kwanza: wm connect)
wm quickstart        # hiari: onyesho la mwendelezo la michakato miwili kwenye hifadhi iliyotengwa
```

Utaona uamuzi wa mradi uliorekodiwa katika kikao kimoja ukivuka kusimamishwa
na kuanzishwa upya kwa mchakato kamili, kisha kurejeshwa na kikao
kinachofuata. Hiyo ndiyo bidhaa.

## 1. Sakinisha (hakuna haki za msimamizi)

### Kutoka kwa toleo

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

Kwenye Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.ps1 | iex
```

Hii hupakua toleo la hivi punde, huthibitisha checksum yake ya SHA256, na
husakinisha `wm` kwenye `~/.local/bin` (Windows:
`%LOCALAPPDATA%\WhiteMagic\bin`, huongezwa kwenye PATH ya mtumiaji). Ikiwa
saraka hiyo haiko kwenye `PATH` yako:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Njia ya mkono: pakua faili yako ya kukimbia ya jukwaa lako (build tuli za
`wm-linux-x86_64-musl` / `wm-linux-aarch64-musl`, build za glibc 2.39+
`wm-linux-x86_64` / `wm-linux-aarch64`, `wm-macos-aarch64` /
`wm-macos-x86_64`, au `wm-windows-x86_64.exe`; kila moja na toleo lake la
`.gz` inapopatikana na faili yake ya `.sha256`) kutoka
[ukurasa wa matoleo](https://github.com/lbailey94/whitemagic/releases), kisha:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

Build zinazotegemea glibc zinahitaji glibc 2.39+ (zilijengwa kwenye Ubuntu
24.04); build tuli za musl hazihitaji glibc.

### Kutoka kwa chanzo

Inahitaji Rust 1.85+. Hakuna haki za msimamizi:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. Thibitisha na uwashe

```bash
wm --version   # toleo la sasa
wm grimoire    # ukaguzi wa kwanza unaoongozwa; huisha kwa kutaja hatua ya uanzishaji
```

`wm grimoire` huthibitisha mazingira na kuonyesha muhtasari wa kuunganisha
wateja; uanzishaji wenyewe ni hatua ya `wm connect --write` hapa chini.

## 3. Unganisha mteja wako wa MCP

```bash
wm connect           # mbio kavu: orodhesha wateja waliogunduliwa na mabadiliko kamili
wm connect --write   # rekebisha kila mteja aliyegunduliwa (nakala za chelezo zenye muhuri wa muda kwanza)
```

Au sanidi mteja mmoja kwa uwazi kwa `wm setup <client> [--write]`. Usanidi wa
mkono unaolingana:

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

## 4. Hiari: endesha onyesho la mwendelezo

```bash
wm quickstart
```

Onyesho hutumia hifadhi iliyotengwa kwenye
`~/.local/share/whitemagic-quickstart` (data yako halisi haigusiwi kamwe).
Huonyesha: kikao kuanza → rekodi uamuzi → mchakato kusimama → mchakato mpya →
mwendelezo hurejesha uamuzi → uchezaji upya wenye bajeti. Ondoa wakati wowote
kwa `rm -rf ~/.local/share/whitemagic-quickstart`.

Kama kitu kionekana vibaya, `wm doctor` ndiyo zana ya utatuzi (afya ya
hifadhi, faharasa, na rejista) — si hatua ya usanidi.

Seva huongea JSON-RPC kupitia stdio na hutoa zana moja ya meta `wm`. Uelekezaji
wa wazi ndio mkataba wa kuaminika:

- `wm(route="session.continuity")` — kumbuka kikao kilichopita kabla ya kuanza kazi
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — gundua kila kitu kingine

Tazama [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) kwa usanidi wa kila
mteja.

## 5. Nakala rudufu

```bash
wm backup          # hifadhi kamili -> ~/whitemagic-backups/<timestamp>
wm restore --backup <dir> [--force]
```

Weka nakala rudufu nje ya mashine inayoendelea. Maelezo yamo kwenye README.
