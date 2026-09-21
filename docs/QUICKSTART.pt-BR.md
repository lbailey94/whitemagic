# Guia rápido do WhiteMagic

**Idiomas:** [English](QUICKSTART.md) · [Español](QUICKSTART.es.md) · **Português (BR)** · [Français](QUICKSTART.fr.md)

**Versão**: consulte a versão atual no [README](../README.md).
**Plataforma**: Linux x86-64 e Linux arm64 (aarch64) — rotas de instalação
verificadas, builds estáticos musl selecionados automaticamente pelo
instalador (também há builds dinâmicos para hosts com glibc 2.39+); as
versões também publicam distribuições comprimidas em gzip para links lentos.
Os binários de macOS e Windows são publicados em toda versão, mas suas rotas
de instalação ainda não são verificadas.

De zero a memória de agente funcionando em menos de cinco minutos.

## Caminho de 30 segundos

```bash
wm grimoire     # primeira execução guiada: host, camada de memória, agentes, memória, vocabulário, continuidade
wm quickstart   # demo de continuidade entre dois processos em um armazenamento isolado
wm selftest     # verificação de invariantes ponta a ponta (~1 segundo, armazenamento temporário)
```

Você verá uma decisão registrada em uma sessão sobreviver a um encerramento e
reinício completos do processo e ser recuperada pela sessão seguinte. Esse é
o produto.

## 1. Instalar (sem permissões de administrador)

### A partir de um release

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

Baixa a versão mais recente, verifica o checksum SHA256 e instala o `wm` em
`~/.local/bin`. Se esse diretório não estiver no seu `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Equivalente manual: baixe o binário da sua plataforma (os builds estáticos
`wm-linux-x86_64-musl` / `wm-linux-aarch64-musl`, ou os builds glibc 2.39+
`wm-linux-x86_64` / `wm-linux-aarch64`, com sua variante `.gz`) e o arquivo
`.sha256` na
[página de releases](https://github.com/lbailey94/whitemagic/releases) e
depois:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

Os builds com link dinâmico exigem glibc 2.39+ (compilados no Ubuntu 24.04);
os builds estáticos musl não exigem glibc.

### A partir do código-fonte

Requer Rust 1.85+. Sem permissões de administrador:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. Verificar

```bash
wm --version   # imprime a versão instalada
wm doctor      # saúde do armazenamento, do índice e do registro de ferramentas
```

## 3. Executar a demo

```bash
wm quickstart
```

A demo usa um armazenamento isolado em `~/.local/share/whitemagic-quickstart`
(seus dados reais nunca são tocados). Ela mostra: início de sessão → registro
de uma decisão → parada do processo → processo novo → a continuidade recupera
a decisão → replay com orçamento. Você pode apagá-la a qualquer momento com
`rm -rf ~/.local/share/whitemagic-quickstart`.

## 4. Conectar seu cliente MCP

```bash
wm connect           # simulação: lista os clientes detectados e a mudança exata
wm connect --write   # altera cada cliente detectado (com backup antes)
```

Ou configure um cliente explicitamente com `wm setup <client> [--write]`. A
configuração manual equivalente:

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

O servidor fala JSON-RPC via stdio e expõe uma única meta-ferramenta `wm`. O
roteamento explícito é o contrato confiável:

- `wm(route="session.continuity")` — recupera a sessão anterior antes de começar a trabalhar
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — descobre todo o resto

Veja [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) para a configuração por
cliente.

## 5. Fazer backup

```bash
wm backup          # armazenamento completo -> ~/whitemagic-backups/<timestamp>
wm restore --backup <dir> [--force]
```

Mantenha os backups fora da máquina em uso. Detalhes no README.
