#!/usr/bin/env bash
# =============================================================================
# Phase B — Lock down SSH (disable root login + password authentication)
#
# PRE-REQUISITES — if any of these are not true, STOP:
#   1. phase-b-harden.sh has run successfully
#   2. You have verified from your LAPTOP that:
#        ssh whitemagic@<host> 'whoami'
#      succeeds and returns 'whitemagic'
#   3. You have a second open SSH session as root (safety net) so that if
#      this script breaks SSH, you can recover without the Hetzner web
#      console.
#
# What this does:
#   - Sets `PermitRootLogin no` in sshd_config
#   - Sets `PasswordAuthentication no` in sshd_config
#   - Validates the config with `sshd -t` BEFORE restarting sshd
#   - Restarts sshd only if config is valid
#
# Usage (on the VPS, as root):
#   bash phase-b-lock-ssh.sh
# =============================================================================
set -euo pipefail

log() { echo -e "\n\033[1;36m[lock-ssh]\033[0m $*"; }
die() { echo -e "\n\033[1;31m[lock-ssh] FATAL:\033[0m $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Must run as root."

# -----------------------------------------------------------------------------
log "Confirming the whitemagic user exists and has SSH keys"
# -----------------------------------------------------------------------------
id -u whitemagic >/dev/null 2>&1 \
  || die "User 'whitemagic' does not exist. Run phase-b-harden.sh first."
[[ -s /home/whitemagic/.ssh/authorized_keys ]] \
  || die "No authorized_keys for whitemagic. Cannot lock down SSH safely."

# -----------------------------------------------------------------------------
log "Backing up current sshd_config"
# -----------------------------------------------------------------------------
cp /etc/ssh/sshd_config "/etc/ssh/sshd_config.bak.$(date +%Y%m%d-%H%M%S)"

# -----------------------------------------------------------------------------
log "Applying hardening directives"
# -----------------------------------------------------------------------------
# Use idempotent sed: handle commented-out, uncommented, and missing cases.
apply_directive() {
  local key="$1" value="$2" file="/etc/ssh/sshd_config"
  if grep -qE "^[[:space:]]*#?[[:space:]]*${key}[[:space:]]" "$file"; then
    sed -i -E "s|^[[:space:]]*#?[[:space:]]*${key}[[:space:]]+.*|${key} ${value}|" "$file"
  else
    echo "${key} ${value}" >> "$file"
  fi
}

apply_directive PermitRootLogin no
apply_directive PasswordAuthentication no
apply_directive ChallengeResponseAuthentication no
apply_directive UsePAM yes
apply_directive PubkeyAuthentication yes

# -----------------------------------------------------------------------------
log "Validating sshd config before restart"
# -----------------------------------------------------------------------------
if ! sshd -t; then
  die "sshd -t reported a config error. NOT restarting sshd. Review /etc/ssh/sshd_config."
fi

# -----------------------------------------------------------------------------
log "Restarting ssh"
# -----------------------------------------------------------------------------
systemctl restart ssh

# -----------------------------------------------------------------------------
log "Current effective config"
# -----------------------------------------------------------------------------
grep -E '^(PermitRootLogin|PasswordAuthentication|PubkeyAuthentication)' /etc/ssh/sshd_config

cat <<'BANNER'

==============================================================================
  SSH LOCK APPLIED

  From your laptop, verify:
      ssh root@204.168.162.7           # EXPECTED: "Permission denied (publickey)"
      ssh whitemagic@204.168.162.7     # EXPECTED: success
  
  If root SSH still succeeds, something is wrong — check the output above.
==============================================================================

BANNER
