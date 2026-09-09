#!/usr/bin/env bash
# Issue a free eval key: ./issue-free-key.sh <name> [daily_cap]
set -euo pipefail
STATE="${WM_HOSTED_STATE:-/var/lib/whitemagic-hosted}"
NAME="${1:?usage: issue-free-key.sh <name> [daily_cap]}"
CAP="${2:-50}"
TOKEN="wm_$(openssl rand -hex 24)"
python3 - "$STATE" "$TOKEN" "$NAME" "$CAP" <<'EOF'
import json, pathlib, sys
state, token, name, cap = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
p = state / "keys.json"
data = json.loads(p.read_text()) if p.exists() else {"keys": []}
data["keys"].append({"token": token, "name": name, "daily_cap": cap})
p.write_text(json.dumps(data, indent=2) + "\n")
p.chmod(0o600)
print(token)
EOF
echo "key '$NAME' issued (cap $CAP/day) — token printed above"
