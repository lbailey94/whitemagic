# Hosted recall deploy kit — one sitting from a fresh Hetzner box

**Target:** CCX23 (€17/mo, per `docs/hetzner/SETUP.md`), Ubuntu 24.04.
**Result:** `https://mcp.whitemagic.dev/mcp` serving read-only WhiteMagic
recall behind API-key auth, with the Smithery static server card live and
the x402 metered lane designed in (sidecar flag).

## Files

| File | Role |
|---|---|
| `Caddyfile` | TLS + reverse proxy: `/mcp` → auth sidecar → wm SSE; `/health`; server card |
| `whitemagic-hosted.service` | systemd: `wm serve --transport sse --readonly --rate-limit` on 127.0.0.1:18789 |
| `whitemagic-gateway.service` | systemd: the auth/meter sidecar on 127.0.0.1:18790 |
| `authd.py` | ~120-line stdio-only sidecar: Bearer-key check, daily caps, JSON accounting |
| `issue-free-key.sh` | issues an eval key (50 recalls/day default) |
| `server-card.json` | Smithery static card at `/.well-known/mcp/server-card.json` |
| `X402_DESIGN.md` | the metered-lane spec (phase 2 — middleware spec, not yet code) |

## One-sitting order

1. Provision the box (runbook: site repo `docs/hetzner/SETUP.md` steps 1–2,
   but firewall = SSH + 80/443 only, no Ollama port).
2. Install the shipped binary (pin the release, checksum-verified):
   ```bash
   curl -fsSL https://www.whitemagic.dev/install.sh | sh
   wm --version   # record it in /etc/whitemagic-hosted/VERSION
   ```
3. DNS: A record `mcp.whitemagic.dev` → box IPv4.
4. Stage the kit:
   ```bash
   install -d -m 755 /etc/whitemagic-hosted /var/lib/whitemagic-hosted
   install -m 600 authd.py /etc/whitemagic-hosted/
   install -m 600 keys.json.example /var/lib/whitemagic-hosted/keys.json
   install -m 644 server-card.json /var/www/mcp-card/server-card.json
   systemctl enable --now whitemagic-hosted whitemagic-gateway
   apt install -y caddy && install -m 644 Caddyfile /etc/caddy/Caddyfile && systemctl reload caddy
   ```
5. First key: `sudo -u whitemagic /etc/whitemagic-hosted/issue-free-key.sh beta-001`
6. Verify end-to-end:
   ```bash
   KEY=$(jq -r '.keys[0].token' /var/lib/whitemagic-hosted/keys.json)
   curl -s https://mcp.whitemagic.dev/health
   curl -s -H "Authorization: Bearer $KEY" https://mcp.whitemagic.dev/mcp \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
   curl -s https://mcp.whitemagic.dev/.well-known/mcp/server-card.json | jq .serverInfo
   ```

## Non-negotiables (from the economy plan)

- **Read-only**: the store is curated *public* content only; `--readonly` is
  not optional. Personal memory never leaves local.
- **No commerce on Vercel**; this box is the only money rail.
- **Every call auditable**: the sidecar writes one JSON line per request;
  these mirror into the Karma ledger story (measured, not claimed).
- Secrets (wallet key, keys.json) live in `/var/lib/whitemagic-hosted/`,
  mode 600, never in any repo.
