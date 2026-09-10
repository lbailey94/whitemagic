#!/usr/bin/env python3
"""authd — WhiteMagic hosted-recall gateway sidecar.

Single responsibility: decide, per request, whether it may pass to the
read-only wm SSE upstream, and account for it. One JSON line per request
in state/access.jsonl = the audit trail.

Design constraints (AGENTIC_ECONOMY_PLAN_V1):
- Bearer-key auth; keys.json = {token, name, daily_cap, x402: bool}
- Free eval tier default cap 50/day; metered keys bypass cap via x402 (phase 2)
- Never logs content — only key id, method, status, bytes
- stdlib only, no deps; stdio-only, no telemetry
"""
import argparse
import datetime as dt
import json
import http.server
import pathlib
import urllib.request
import urllib.error

TOKEN_HEADER = "Authorization"


class Gateway(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # silence default logging; we keep our own line
        pass

    # ── accounting ────────────────────────────────────────────────────
    def audit(self, key, method, status, req_bytes, note=""):
        line = json.dumps({
            "ts": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "key": key, "method": method, "status": status,
            "bytes": req_bytes, "note": note,
        })
        with open(self.server.state_dir / "access.jsonl", "a") as f:
            f.write(line + "\n")

    def load_keys(self):
        return json.loads((self.server.state_dir / "keys.json").read_text())

    def today_count(self, key):
        today = dt.date.today().isoformat()
        n = 0
        p = self.server.state_dir / "usage.json"
        if p.exists():
            n = json.loads(p.read_text()).get(f"{key}:{today}", 0)
        return n

    def bump(self, key):
        p = self.server.state_dir / "usage.json"
        data = json.loads(p.read_text()) if p.exists() else {}
        today = dt.date.today().isoformat()
        data[f"{key}:{today}"] = data.get(f"{key}:{today}", 0) + 1
        p.write_text(json.dumps(data))

    # ── request handling ─────────────────────────────────────────────
    def do_GET(self):
        self.relay("GET")

    def do_POST(self):
        self.relay("POST")

    def relay(self, method):
        key_info = self.authorize()
        if key_info is None:
            return
        # forward to upstream, streaming both ways
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(
            self.server.upstream + self.path,
            data=body,
            method=method,
            headers={k: v for k, v in self.headers.items()
                     if k.lower() not in ("host", "authorization")},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as up:
                self.send_response(up.status)
                for k, v in up.headers.items():
                    if k.lower() not in ("transfer-encoding",):
                        self.send_header(k, v)
                self.end_headers()
                n = 0
                while True:
                    chunk = up.read(4096)
                    if not chunk:
                        break
                    n += len(chunk)
                    self.wfile.write(chunk)
                self.audit(key_info["name"], method, up.status, n)
                self.bump(key_info["name"])
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
            self.audit(key_info["name"], method, e.code, 0, "upstream-error")

    def authorize(self):
        keys = self.load_keys()
        auth = self.headers.get(TOKEN_HEADER, "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        match = next((k for k in keys["keys"] if k["token"] == token), None)
        if match is None:
            self.send_response(401)
            # x402 seam (phase 2): this 401 becomes a 402 challenge when the
            # request carries an X-PAYMENT-capable accept and no valid key.
            self.send_header("WWW-Authenticate", 'Bearer realm="whitemagic-hosted"')
            self.end_headers()
            self.audit("unknown", self.command, 401, 0)
            return None
        if self.today_count(match["name"]) >= match.get("daily_cap", 50):
            self.send_response(429)
            self.send_header("Retry-After", "86400")
            self.end_headers()
            self.audit(match["name"], self.command, 429, 0, "cap-reached")
            return None
        return match


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="127.0.0.1:18790")
    ap.add_argument("--upstream", default="http://127.0.0.1:18789")
    ap.add_argument("--state", required=True)
    args = ap.parse_args()
    host, port = args.listen.rsplit(":", 1)

    class S(http.server.ThreadingHTTPServer):
        state_dir = pathlib.Path(args.state)
        upstream = args.upstream

    pathlib.Path(args.state).mkdir(parents=True, exist_ok=True)
    print(f"authd listening on {args.listen} -> {args.upstream}", flush=True)
    S((host, int(port)), Gateway).serve_forever()


if __name__ == "__main__":
    main()
