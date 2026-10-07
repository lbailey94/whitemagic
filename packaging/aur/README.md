# AUR — whitemagic-bin

`whitemagic-bin` installs the checksum-verified release binary to
`/usr/bin/wm`. There is no `whitemagic` package on the AUR as of 2026-10-04
(RPC search: 0 results), so no conflict renames apply.

## First-time account setup (browser-gated, one time)

1. Create an account at <https://aur.archlinux.org/register/>.
2. Add your SSH public key at <https://aur.archlinux.org/account/> —
   `~/.ssh/id_ed25519.pub` on this device is already registered with GitHub and
   can be reused.
3. Verify: `ssh aur@aur.archlinux.org help` (lists commands; the account is
   active when it answers).

## Publish

```bash
git clone ssh://aur@aur.archlinux.org/whitemagic-bin.git /tmp/whitemagic-bin
cp PKGBUILD .SRCINFO /tmp/whitemagic-bin/
cd /tmp/whitemagic-bin
# On an Arch host (or archlinux container): makepkg --printsrcinfo > .SRCINFO
# — regenerate whenever PKGBUILD changes so the two never drift.
git add PKGBUILD .SRCINFO
git commit -m "whitemagic-bin 10.2.0_alpha.4-1"
git push origin master
```

The AUR runs `makepkg --printsrcinfo` server-side and rejects a mismatched
`.SRCINFO`, so regenerate it after any PKGBUILD edit.

## Bump on a release

1. `pkgver=<new version>` (underscore form for prereleases:
   `v10.2.0-alpha.4` → `10.2.0_alpha.4`), `pkgrel=1`.
2. Replace both `sha256sums_*` from the tag's `.gz` release assets
   (`wm-linux-x86_64.gz.sha256`, `wm-linux-aarch64.gz.sha256`).
3. Regenerate `.SRCINFO` (`makepkg --printsrcinfo > .SRCINFO`), commit, push.

The `wm` binary self-reports the version; smoke it with
`makepkg -f && pacman -U whitemagic-bin-*.pkg.tar.zst && wm --version`.
