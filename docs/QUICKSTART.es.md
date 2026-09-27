# Guía rápida de WhiteMagic

**Idiomas:** [English](QUICKSTART.md) · **Español** · [Português (BR)](QUICKSTART.pt-BR.md) · [Français](QUICKSTART.fr.md)

**Versión**: consulta la versión actual en el [README](../README.md).
**Plataforma**: Linux x86-64, Linux arm64 y macOS arm64 — rutas de
instalación verificadas. Linux ofrece builds estáticos musl seleccionados
automáticamente por el instalador (también hay builds dinámicos para hosts con
glibc 2.39+); las versiones publican además distribuciones comprimidas en gzip
para enlaces lentos. Los binarios de macOS x86_64 y Windows x86_64 se publican
en cada versión, pero sus rutas de instalación aún no están verificadas.

De cero a memoria de agente funcionando en menos de cinco minutos.

## Ruta de 30 segundos

```bash
wm grimoire          # primera ejecución guiada: host, capa de memoria, agentes, memoria, vocabulario, continuidad
wm connect --write   # conecta cada cliente MCP detectado (simulación primero: wm connect)
wm quickstart        # opcional: demo de continuidad entre dos procesos sobre un almacén aislado
```

Verás una decisión registrada en una sesión sobrevivir a un cierre y arranque
completo del proceso, y ser recuperada por la sesión siguiente. Ese es el
producto.

## 1. Instalar (sin permisos de administrador)

### Desde un release

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

Descarga la última versión, verifica su checksum SHA256 e instala `wm` en
`~/.local/bin`. Si ese directorio no está en tu `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Equivalente manual: descarga el binario de tu plataforma (los builds
estáticos `wm-linux-x86_64-musl` / `wm-linux-aarch64-musl` / `wm-macos-aarch64`, o los builds
glibc 2.39+ `wm-linux-x86_64` / `wm-linux-aarch64`, con su variante `.gz`)
y su archivo `.sha256` desde la
[página de releases](https://github.com/lbailey94/whitemagic/releases), y
luego:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

Los builds con enlace dinámico requieren glibc 2.39+ (compilados en
Ubuntu 24.04); los builds estáticos musl no requieren glibc.

### Desde el código fuente

Requiere Rust 1.85+. Sin permisos de administrador:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. Verificar y activar

```bash
wm --version   # imprime la versión instalada
wm grimoire    # comprobación guiada; termina nombrando el paso de activación
```

`wm grimoire` comprueba el entorno y muestra la configuración de clientes; la
activación es el paso `wm connect --write` de abajo.

## 3. Conectar tu cliente MCP

```bash
wm connect           # simulación: lista los clientes detectados y el cambio exacto
wm connect --write   # modifica cada cliente detectado (con copias de seguridad previas)
```

O configura un cliente explícitamente con `wm setup <client> [--write]`. La
configuración manual equivalente:

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

## 4. Opcional: ejecutar la demo de continuidad

```bash
wm quickstart
```

La demo usa un almacén aislado en `~/.local/share/whitemagic-quickstart`
(tus datos reales nunca se tocan). Muestra: inicio de sesión → registro de una
decisión → parada del proceso → proceso nuevo → la continuidad recupera la
decisión → replay con presupuesto. Puedes borrarla cuando quieras con
`rm -rf ~/.local/share/whitemagic-quickstart`.

Si algo va mal, `wm doctor` es la herramienta de diagnóstico (salud del
almacén, del índice y del registro) — no es un paso de instalación.

El servidor habla JSON-RPC sobre stdio y expone una sola meta-herramienta
`wm`. El enrutado explícito es el contrato confiable:

- `wm(route="session.continuity")` — recupera la sesión anterior antes de empezar a trabajar
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — descubre todo lo demás

Consulta [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) para la configuración
por cliente.

## 5. Respaldar

```bash
wm backup          # almacén completo -> ~/whitemagic-backups/<timestamp>
wm restore --backup <dir> [--force]
```

Mantén los respaldos fuera de la máquina en uso. Detalles en el README.
