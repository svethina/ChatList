# Создаёт GitHub Release из version.py и прикрепляет установщик.
# Требования: gh (авторизован), собранный installer\ChatList-Setup-<ver>.exe
#
# Примеры:
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

$python = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

$version = & $python -c "from version import __version__; print(__version__)"
if (-not $version) {
    throw "Не удалось прочитать __version__ из version.py"
}

$tag = "v$version"
$title = "ChatList $version"
$installer = Join-Path $PWD "installer\ChatList-Setup-$version.exe"
$portable = Join-Path $PWD "dist\ChatList.exe"

if (-not $NotesFile) {
    $NotesFile = Join-Path $PWD ".github\RELEASE_TEMPLATE.md"
}

Write-Host "Version: $version"
Write-Host "Tag:     $tag"
Write-Host "Notes:   $NotesFile"

if (-not (Test-Path $NotesFile)) {
    throw "Файл заметок не найден: $NotesFile"
}

if (-not $SkipBuildCheck) {
    if (-not (Test-Path $installer)) {
        throw @"
Установщик не найден: $installer

Сначала соберите проект:
  .\build.ps1
"@
    }
}

$existing = gh release view $tag 2>$null
if ($LASTEXITCODE -eq 0 -and $existing) {
    throw "Релиз $tag уже существует. Поднимите версию в version.py или удалите релиз вручную."
}

$assets = @($installer)
if ($AlsoAttachExe) {
    if (-not (Test-Path $portable)) {
        throw "Не найден portable exe: $portable"
    }
    $assets += $portable
}

$ghArgs = @(
    "release", "create", $tag
) + $assets + @(
    "--title", $title
    "--notes-file", $NotesFile
)

if ($Draft) {
    $ghArgs += "--draft"
}

Write-Host "Создание релиза..."
& gh @ghArgs
if ($LASTEXITCODE -ne 0) {
    throw "gh release create завершился с кодом $LASTEXITCODE"
}

$url = "https://github.com/svethina/ChatList/releases/tag/$tag"
Write-Host ""
Write-Host "Готово: $url"
if ($Draft) {
    Write-Host "Это черновик — опубликуйте его на GitHub, когда будете готовы."
}
