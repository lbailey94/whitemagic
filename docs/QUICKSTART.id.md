# WhiteMagic Mulai Cepat

**Bahasa:** [English](QUICKSTART.md) · [Español](QUICKSTART.es.md) · [Português (BR)](QUICKSTART.pt-BR.md) · [Français](QUICKSTART.fr.md) · [Deutsch](QUICKSTART.de.md) · [हिन्दी](QUICKSTART.hi.md) · **Indonesia** · [العربية](QUICKSTART.ar.md) · [Kiswahili](QUICKSTART.sw.md) · [नेपाली](QUICKSTART.ne.md)

**Versi**: lihat versi terbaru di [README](../README.md).
**Jalur instalasi**: Linux x86-64, Linux arm64, macOS arm64 + x86_64, dan
Windows x86_64 — terverifikasi (install-gated). Linux menyediakan build musl
statis penuh yang dipilih otomatis oleh installer (build dinamis tetap
tersedia untuk host dengan glibc 2.39+); rilis juga menyediakan distribusi
terkompresi gzip untuk koneksi lambat. macOS dipasang melalui `install.sh`;
Windows melalui `install.ps1` — setiap jalur terverifikasi diuji di CI
terhadap rilis yang dipublikasikan.

Dari nol ke memori agen yang berfungsi dalam waktu kurang dari lima menit.

## Jalur 30 detik

```bash
wm grimoire          # jalan pertama terpandu: host, lapisan memori, agen, memori, kosakata, kontinuitas
wm connect --write   # hubungkan setiap klien MCP yang terdeteksi (uji dulu: wm connect)
wm quickstart        # opsional: demo kontinuitas dua proses pada penyimpanan terisolasi
```

Anda akan melihat keputusan proyek yang dicatat dalam satu sesi bertahan
melewati penghentian dan permulaan proses penuh, lalu dipulihkan oleh sesi
berikutnya. Itulah produknya.

## 1. Pasang (tanpa hak admin)

### Dari rilis

```bash
curl -fsSL https://www.whitemagic.dev/install.sh?ref=wmv9-quickstart | sh
```

Di Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.ps1 | iex
```

Perintah ini mengunduh rilis terbaru, memverifikasi checksum SHA256-nya, dan
memasang `wm` ke `~/.local/bin` (Windows: `%LOCALAPPDATA%\WhiteMagic\bin`,
ditambahkan ke PATH pengguna). Jika direktori itu tidak ada di `PATH` Anda:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Setara manual: unduh biner platform Anda (build statis
`wm-linux-x86_64-musl` / `wm-linux-aarch64-musl`, build glibc 2.39+
`wm-linux-x86_64` / `wm-linux-aarch64`, `wm-macos-aarch64` /
`wm-macos-x86_64`, atau `wm-windows-x86_64.exe`; masing-masing dengan
varian `.gz` bila tersedia dan berkas `.sha256`) dari
[halaman rilis](https://github.com/lbailey94/whitemagic/releases), lalu:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm-linux-x86_64
mkdir -p ~/.local/bin && mv wm-linux-x86_64 ~/.local/bin/wm
```

Build dinamis memerlukan glibc 2.39+ (dibangun di Ubuntu 24.04); build musl
statis tidak memerlukan glibc.

### Dari sumber

Memerlukan Rust 1.85+. Tanpa hak admin:

```bash
cargo build --release
mkdir -p ~/.local/bin && cp target/release/wm ~/.local/bin/
```

## 2. Verifikasi dan aktivasi

```bash
wm --version   # versi saat ini
wm grimoire    # pemeriksaan pertama terpandu; diakhiri dengan langkah aktivasi
```

`wm grimoire` membuktikan lingkungan dan menampilkan pratinjau koneksi
klien; aktivasi itu sendiri adalah langkah `wm connect --write` di bawah.

## 3. Hubungkan klien MCP Anda

```bash
wm connect           # uji kering: daftar klien terdeteksi dan perubahan persisnya
wm connect --write   # tambal setiap klien terdeteksi (cadangan bertimestamp lebih dulu)
```

Atau konfigurasikan satu klien secara eksplisit dengan
`wm setup <client> [--write]`. Konfigurasi manual yang setara:

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

## 4. Opsional: jalankan demo kontinuitas

```bash
wm quickstart
```

Demo memakai penyimpanan terisolasi di
`~/.local/share/whitemagic-quickstart` (data asli Anda tidak pernah
disentuh). Demo menunjukkan: sesi mulai → catat keputusan → proses berhenti →
proses baru → kontinuitas memulihkan keputusan → replay beranggaran. Hapus
kapan saja dengan `rm -rf ~/.local/share/whitemagic-quickstart`.

Jika ada yang tampak salah, `wm doctor` adalah alat pemecahan masalah
(kesehatan store, indeks, dan registry) — bukan langkah penyiapan.

Server berbicara JSON-RPC melalui stdio dan mengekspos satu meta-tool `wm`.
Perutean eksplisit adalah kontrak yang dapat diandalkan:

- `wm(route="session.continuity")` — panggil sesi sebelumnya sebelum mulai bekerja
- `wm(route="session.start", args={"title": "..."})`
- `wm(route="session.record", args={"content": "...", "turn_type": "decision"})`
- `wm(route="tools.list")` — temukan semua sisanya

Lihat [`MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) untuk penyiapan per klien.

## 5. Cadangan

```bash
wm backup          # store penuh -> ~/whitemagic-backups/<timestamp>
wm restore --backup <dir> [--force]
```

Simpan cadangan di luar mesin aktif. Lihat README untuk detail.
