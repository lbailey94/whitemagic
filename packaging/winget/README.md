# winget — lbailey94.WhiteMagic

Portable-package manifests for the Windows CLI (`wm` → `wm-windows-x86_64.exe`
from the checksum-verified GitHub release). No `lbailey94.WhiteMagic` package
exists in `microsoft/winget-pkgs` as of 2026-10-04.

## First-time submission (one PR)

```bash
gh repo fork microsoft/winget-pkgs --clone --remote
cd winget-pkgs
mkdir -p manifests/l/lbailey94/WhiteMagic/9.3.4
cp /home/lucas/Desktop/WHITEMAGIC/WMv10/packaging/winget/*.yaml \
   manifests/l/lbailey94/WhiteMagic/9.3.4/
git checkout -b lbailey94.WhiteMagic-9.3.4
git add manifests/l/lbailey94/WhiteMagic
git commit -m "New package: lbailey94.WhiteMagic version 9.3.4"
git push -u origin lbailey94.WhiteMagic-9.3.4
gh pr create --repo microsoft/winget-pkgs --fill
```

**CLA gate:** a first-time contributor to `microsoft/winget-pkgs` must sign the
Microsoft CLA via the bot comment on the PR (browser, one time). Validation
runs automatically; expected local checks on a Windows host:

```powershell
winget validate --manifest packaging/winget
winget install --manifest packaging/winget
```

`wingetcreate` is the alternative path once the package id exists:
`wingetcreate update lbailey94.WhiteMagic --version <v> --urls <exe url> --submit`.

## Bump on a stable release

1. Update `PackageVersion` in all three manifests.
2. Replace `InstallerUrl` + `InstallerSha256` (uppercase hex, from the tag's
   `wm-windows-x86_64.exe.sha256`); update `ReleaseDate`/`ReleaseNotesUrl`.
3. Open a PR to `microsoft/winget-pkgs` — version bumps by existing
   contributors skip the CLA step.
