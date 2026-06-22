#!/usr/bin/env bash

set -euo pipefail
# =============================================================================
# Phase B — Hetzner VPS hardening + core packages for whitemagic.dev
#
# Scope:
#   - System update + required packages
#   - hostname + timezone
#   - `whitemagic` deploy user with SSH key copied from root
#   - Scoped passwordless sudo for the deploy user
#   - UFW firewall (22, 80, 443)
#   - fail2ban + unattended-upgrades
#   - Node.js 20 (LTS)
#   - Caddy (installed, NOT started — we'll configure in Phase D)
#   - /srv/whitemagic-site directory owned by deploy user
#
# Out of scope (intentionally deferred):
#   - Disabling root SSH login + password auth  → run phase-b-lock-ssh.sh
#     AFTER verifying `ssh whitemagic@<host>` works from your laptop.
#
# Safety:
#   - `set -euo pipefail` aborts on the first error
#   - All destructive ops are idempotent (safe to re-run)
#   - No SSH config changes happen here (see lock script)
#
# Usage (on the VPS, as root):
#   bash phase-b-harden.sh
# =============================================================================
set -euo pipefail

log() { echo -e "\n\033[1;36m[phase-b]\033[0m $*"; }
die() { echo -e "\n\033[1;31m[phase-b] FATAL:\033[0m $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Must run as root."

# -----------------------------------------------------------------------------
log "Step 1/9 — Core packages (NO apt upgrade — box may have running services)"
# -----------------------------------------------------------------------------
# Intentionally NOT running `apt upgrade` because this box may be hosting
# other services (Docker containers, etc.). Package upgrades can restart
# daemons and disrupt running workloads. If you want a full upgrade, run
# it yourself in a maintenance window.
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  openssh-server \
  ufw fail2ban unattended-upgrades \
  curl ca-certificates gnupg lsb-release \
  debian-keyring debian-archive-keyring apt-transport-https \
  git
systemctl enable --now ssh

# -----------------------------------------------------------------------------
log "Step 2/9 — Hostname + timezone"
# -----------------------------------------------------------------------------
hostnamectl set-hostname whitemagic-site
timedatectl set-timezone UTC
echo "  hostname: $(hostname)"
echo "  timezone: $(timedatectl | grep 'Time zone' | awk '{print $3}')"

# -----------------------------------------------------------------------------
log "Step 3/9 — Deploy user 'whitemagic' + SSH keys"
# -----------------------------------------------------------------------------
if id -u whitemagic >/dev/null 2>&1; then
  echo "  user 'whitemagic' already exists; skipping useradd"
else
  useradd -m -s /bin/bash whitemagic
  usermod -aG sudo whitemagic
fi

install -d -m 700 -o whitemagic -g whitemagic /home/whitemagic/.ssh

if [[ -f /root/.ssh/authorized_keys ]]; then
  install -m 600 -o whitemagic -g whitemagic \
    /root/.ssh/authorized_keys /home/whitemagic/.ssh/authorized_keys
  echo "  copied /root/.ssh/authorized_keys → /home/whitemagic/.ssh/authorized_keys"
else
  die "No /root/.ssh/authorized_keys found. Fix this before re-running."
fi

ls -la /home/whitemagic/.ssh/

# -----------------------------------------------------------------------------
log "Step 4/9 — Scoped passwordless sudo for deploy user"
# -----------------------------------------------------------------------------
cat > /etc/sudoers.d/whitemagic-deploy <<'EOF'
whitemagic ALL=(root) NOPASSWD: /usr/bin/systemctl restart whitemagic-site
whitemagic ALL=(root) NOPASSWD: /usr/bin/systemctl status whitemagic-site
whitemagic ALL=(root) NOPASSWD: /usr/bin/systemctl reload caddy
EOF
chmod 440 /etc/sudoers.d/whitemagic-deploy
visudo -c

# -----------------------------------------------------------------------------
log "Step 5/9 — UFW firewall"
# -----------------------------------------------------------------------------
ufw --force reset >/dev/null 2>&1 || true
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose

# -----------------------------------------------------------------------------
log "Step 6/9 — fail2ban + unattended-upgrades"
# -----------------------------------------------------------------------------
systemctl enable --now fail2ban

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
systemctl enable --now unattended-upgrades

echo "  fail2ban:             $(systemctl is-active fail2ban)"
echo "  unattended-upgrades:  $(systemctl is-active unattended-upgrades)"

# -----------------------------------------------------------------------------
log "Step 7/9 — Node.js 20 (LTS)"
# -----------------------------------------------------------------------------
if ! command -v node >/dev/null || [[ "$(node --version)" != v20.* ]]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
echo "  node: $(node --version)"
echo "  npm:  $(npm --version)"

# -----------------------------------------------------------------------------
log "Step 8/9 — Caddy (installed, not started)"
# -----------------------------------------------------------------------------
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update
  apt-get install -y caddy
  # Stop auto-start; we'll start after Caddyfile is configured (Phase D)
  systemctl stop caddy || true
fi
echo "  caddy: $(caddy version)"

# -----------------------------------------------------------------------------
log "Step 9/9 — Deploy directory"
# -----------------------------------------------------------------------------
mkdir -p /srv/whitemagic-site
chown whitemagic:whitemagic /srv/whitemagic-site
ls -ld /srv/whitemagic-site

# -----------------------------------------------------------------------------
log "DONE — Phase B core complete."
# -----------------------------------------------------------------------------
cat <<'BANNER'

==============================================================================
  READY FOR SSH VERIFICATION

  From your LAPTOP (not this VPS), run:
      ssh whitemagic@204.168.162.7 'whoami && id && hostname'

  Expected:
      whitemagic
      uid=1001(whitemagic) gid=1001(whitemagic) groups=1001(whitemagic),27(sudo)
      whitemagic-site

  If that succeeds, THEN (and only then) run:
      bash phase-b-lock-ssh.sh

  to disable root SSH login and password authentication.

  If it fails, DO NOT run the lock script. Debug first.
==============================================================================

BANNER
