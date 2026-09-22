# Entry point of the UIA-TL-BASE scheduled task (registered by create-uia-base.ps1).
# Pulls the latest code, links config.yaml to the copy CI deploys into config-center, then starts base.
# All paths derive from this file: <parent>\true-love-n\.github\systemd\ sits next to <parent>\config-center\.

$Host.UI.RawUI.WindowTitle = "UIA-TL-BASE"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$WorkDir = Join-Path $RepoRoot "true-love-base"
$ConfigRepo = Join-Path (Split-Path $RepoRoot -Parent) "config-center"
$ConfigFile = Join-Path $ConfigRepo "true-love-n\true-love-base\config.yaml"
$ConfigLink = Join-Path $WorkDir "config.yaml"

Set-Location $WorkDir
Write-Host "Starting true-love-base at $(Get-Date)" -ForegroundColor Cyan
Write-Host "WorkDir: $WorkDir" -ForegroundColor Gray
Write-Host "Config : $ConfigFile" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Gray

# A failed pull (e.g. network down) should not keep base from starting with what is on disk
git pull

if (-not (Test-Path $ConfigFile)) {
    Write-Host "Config not found: $ConfigFile (run the true-love-base deploy workflow to upload it)" -ForegroundColor Red
    exit 1
}

# Keep a pre-existing regular config.yaml as config.bak.yaml (still gitignored) the first time we switch to the link
$existing = Get-Item $ConfigLink -Force -ErrorAction SilentlyContinue
if ($existing -and -not $existing.LinkType) {
    Move-Item $ConfigLink (Join-Path $WorkDir "config.bak.yaml") -Force
}
# Removes an old link, even a dangling one; does nothing when there is none
[System.IO.File]::Delete($ConfigLink)
# The task runs with highest privileges, which creating a symlink on Windows requires
New-Item -ItemType SymbolicLink -Path $ConfigLink -Target $ConfigFile | Out-Null

uv sync
uv run -m true_love_base
