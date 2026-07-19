# Creates a GitHub Release from version.py and attaches the installer.
# Requires: gh (logged in), installer\ChatList-Setup-<ver>.exe
#
# Examples:
#   .\scripts\publish-release.ps1
#   .\scripts\publish-release.ps1 -Draft
#   .\scripts\publish-release.ps1 -NotesFile .\my-notes.md
#   .\scripts\publish-release.ps1 -AlsoAttachExe

[CmdletBinding()]
param(
    [switch]$Draft,
    [switch]$AlsoAttachExe,
    [string]$NotesFile = "",
    [switch]$SkipBuildCheck
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (Test-Path ".\.venv\Scripts\python.exe") {
    $python = ".\.venv\Scripts\python.exe"
} else {
    $python = "python"
}

$version = & $python -c "from version import __version__; print(__version__)"
if (-not $version) {
    throw "Failed to read __version__ from version.py"
}
$version = "$version".Trim()

$tag = "v$version"
$title = "ChatList $version"
$installer = Join-Path (Get-Location) "installer\ChatList-Setup-$version.exe"
$portable = Join-Path (Get-Location) "dist\ChatList.exe"

if (-not $NotesFile) {
    $NotesFile = Join-Path (Get-Location) ".github\RELEASE_TEMPLATE.md"
}

Write-Host "Version: $version"
Write-Host "Tag:     $tag"
Write-Host "Notes:   $NotesFile"

if (-not (Test-Path -LiteralPath $NotesFile)) {
    throw "Notes file not found: $NotesFile"
}

if (-not $SkipBuildCheck) {
    if (-not (Test-Path -LiteralPath $installer)) {
        throw "Installer not found: $installer. Run .\build.ps1 first."
    }
}

$existing = $null
try {
    $existing = gh release view $tag 2>$null
} catch {
    $existing = $null
}

if ($existing) {
    throw "Release $tag already exists. Bump version.py or delete the release."
}

$assets = @($installer)
if ($AlsoAttachExe) {
    if (-not (Test-Path -LiteralPath $portable)) {
        throw "Portable exe not found: $portable"
    }
    $assets += $portable
}

$ghArgs = @("release", "create", $tag) + $assets + @("--title", $title, "--notes-file", $NotesFile)

if ($Draft) {
    $ghArgs += "--draft"
}

Write-Host "Creating release..."
& gh @ghArgs
if ($LASTEXITCODE -ne 0) {
    throw "gh release create failed with exit code $LASTEXITCODE"
}

$url = "https://github.com/svethina/ChatList/releases/tag/$tag"
Write-Host ""
Write-Host "Done: $url"
if ($Draft) {
    Write-Host "Draft created. Publish it on GitHub when ready."
}
