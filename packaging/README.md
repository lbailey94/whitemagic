# Packaging

Third-party package manifests for the stable release line. These track the
latest **stable** release (the alphas are not submitted anywhere users default
to); bump them in the same PR that cuts a stable tag.

| Directory | Channel | Submission |
|---|---|---|
| [`aur/`](aur/) | Arch User Repository (`whitemagic-bin`) | AUR account + SSH key (browser-gated first time) |
| [`winget/`](winget/) | Windows Package Manager (`lbailey94.WhiteMagic`) | PR to `microsoft/winget-pkgs` (CLA for first-time contributors) |

Source of truth for every URL/checksum here: the tag's release assets on
`github.com/lbailey94/whitemagic`. The v10 line is glibc-only (the ONNX
runtime has no musl build), so the Linux AUR package uses the
`wm-linux-<arch>` (gnu) assets, not the pre-v10 musl ones.
