# WhiteMagic installer for Windows — PREVIEW (not install-gated yet).
#
# Parity with scripts/install.sh: download a release binary, verify its
# SHA256 checksum, install it per-user (no admin rights), and record the
# arrival channel locally. Windows assets are published in every release;
# this installer is new and stays documented as "published, not
# install-gated" until a tagged-release certification passes in CI.
#
# Usage (PowerShell):
#   irm https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.ps1 | iex
#   ./scripts/install.ps1 -Version v9.2.2
#   ./scripts/install.ps1 -File .\target\release\wm.exe -ChecksumFile .\wm.exe.sha256
#   ./scripts/install.ps1 -Ref hero
#
# Checksum verification is not optional: -File requires -ChecksumFile.

[CmdletBinding()]
param(
    # Release tag to install (default: the most recent release, prereleases included).
    [string]$Version = "",
    # Install directory (default: %LOCALAPPDATA%\WhiteMagic\bin).
    [string]$Dir = "",
    # Local binary to install instead of downloading (CI/testing).
    [string]$File = "",
    # SHA256 file for -File mode (required with -File).
    [string]$ChecksumFile = "",
    # Install-attribution marker (sanitized locally, never transmitted).
    [string]$Ref = ""
)

$ErrorActionPreference = "Stop"
$Repo = "lbailey94/whitemagic"
$Artifact = "wm-windows-x86_64.exe"

if (-not $Dir) {
    $Dir = Join-Path $env:LOCALAPPDATA "WhiteMagic\bin"
}

# TLS 1.2 for Windows PowerShell 5.1.
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch { }

function Sanitize-Ref([string]$value) {
    if (-not $value) { return "" }
    $clean = ($value.ToLower() -replace '[^a-z0-9_-]', '')
    if ($clean.Length -gt 24) { $clean = $clean.Substring(0, 24) }
    return $clean
}

$Ref = Sanitize-Ref $Ref

if (-not $File) {
    if (-not $Version) {
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases?per_page=1" -Headers @{ "User-Agent" = "whitemagic-installer" }
        if (-not $release -or -not $release[0].tag_name) {
            Write-Error "Could not determine the latest release version. Pass -Version explicitly."
            exit 1
        }
        $Version = $release[0].tag_name
    }
    Write-Host "Installing WhiteMagic $Version for Windows (x86_64)..."
} else {
    if (-not $ChecksumFile) {
        Write-Error "-File requires -ChecksumFile: checksum verification is not optional."
        exit 1
    }
    if (-not (Test-Path -LiteralPath $File)) {
        Write-Error "Binary not found: $File"
        exit 1
    }
    Write-Host "Installing WhiteMagic from local file: $File"
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("wm-install-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    if ($File) {
        $binary = Join-Path $tmp $Artifact
        Copy-Item -LiteralPath $File -Destination $binary
        $checksumText = Get-Content -LiteralPath $ChecksumFile -Raw
    } else {
        $baseUrl = "https://github.com/$Repo/releases/download/$Version"
        $binary = Join-Path $tmp $Artifact
        $checksumFile = Join-Path $tmp "$Artifact.sha256"
        Write-Host "Downloading binary..."
        Invoke-WebRequest -Uri "$baseUrl/$Artifact" -OutFile $binary -UseBasicParsing
        Invoke-WebRequest -Uri "$baseUrl/$Artifact.sha256" -OutFile $checksumFile -UseBasicParsing
        $checksumText = Get-Content -LiteralPath $checksumFile -Raw
    }

    Write-Host "Verifying checksum..."
    $expected = ($checksumText -split '\s+')[0].Trim().ToLower()
    if ($expected -notmatch '^[0-9a-f]{64}$') {
        Write-Error "Checksum file does not contain a SHA256 digest."
        exit 1
    }
    $actual = (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $expected) {
        Write-Error "Checksum mismatch: expected $expected, got $actual. Refusing to install."
        exit 1
    }

    Write-Host "Installing to $Dir..."
    New-Item -ItemType Directory -Force -Path $Dir | Out-Null
    Copy-Item -LiteralPath $binary -Destination (Join-Path $Dir "wm.exe") -Force

    # Arrival marker (best effort, mirrors install.sh; never fails the install).
    $storeRoot = $null
    if ($env:XDG_DATA_HOME) {
        $storeRoot = Join-Path $env:XDG_DATA_HOME "whitemagic"
    } elseif ($env:HOME) {
        $storeRoot = Join-Path $env:HOME ".local\share\whitemagic"
    }
    if ($storeRoot) {
        try {
            New-Item -ItemType Directory -Force -Path $storeRoot | Out-Null
            $value = if ($Ref) { "install_ps1:$Ref" } else { "install_ps1" }
            Set-Content -LiteralPath (Join-Path $storeRoot "install_channel") -Value $value
        } catch { }
    }

    # Per-user PATH (no admin rights). Report when the session PATH must be
    # refreshed before `wm` resolves without the full path.
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { $userPath = "" }
    $parts = $userPath -split ';' | Where-Object { $_ }
    if ($parts -notcontains $Dir) {
        $newPath = (($parts + $Dir) -join ';')
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "Added $Dir to the user PATH (open a new terminal to pick it up)."
    }

    Write-Host ""
    Write-Host "WhiteMagic installed: $(Join-Path $Dir 'wm.exe')"
    Write-Host "Verify with: & '$(Join-Path $Dir 'wm.exe')' --version"
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
