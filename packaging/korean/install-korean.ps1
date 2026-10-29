[CmdletBinding()]
param(
    [string]$OpenMWPath = "",
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$payloadRoot = Join-Path $scriptDir "payload"
$modFolderName = "Morrowind_Korean_ReTranslation"
$legacyModFolderName = "Morrowind_Korean_ReTranslation_v01"
$payloadMod = Join-Path $payloadRoot "mods\$modFolderName"
$configUpdater = Join-Path $scriptDir "install-korean-config.ps1"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

$requiredRuntimeFiles = @(
    "openmw.exe",
    "settings-default.cfg",
    "resources\vfs\mygui\openmw_hud.layout",
    "resources\vfs\mygui\openmw_hud_box.skin.xml",
    "resources\vfs\textures\omw_mouse_emulation_cursor.dds",
    "resources\vfs\fonts\Galmuri11.ttf",
    "resources\vfs\fonts\Galmuri11-OFL-1.1.md",
    "resources\vfs\fonts\MysticCards.omwfont",
    "resources\vfs\fonts\DejaVuLGCSansMono.omwfont"
)
$requiredModFiles = @(
    "Morrowind_Korean_ReTranslation.esp",
    "Morrowind_Korean_ReTranslation.cel",
    "Morrowind_Korean_ReTranslation.mrk",
    "Morrowind_Korean_ReTranslation.top",
    "Morrowind_Korean_ReTranslation.jrn"
)
$requiredSubtitleFiles = @(
    "mw_intro.srt",
    "mw_cavern.srt",
    "mw_end.srt",
    "bm_bearhunt1.srt",
    "bm_bearhunt2.srt",
    "bm_ceremony1.srt",
    "bm_ceremony2.srt",
    "bm_endgame.srt",
    "bm_frostgiant1.srt",
    "bm_frostgiant2.srt"
)

foreach ($relative in $requiredRuntimeFiles) {
    $requiredPath = Join-Path $payloadRoot $relative
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required Korean OpenMW payload file not found: $requiredPath"
    }
}
foreach ($requiredModFile in $requiredModFiles) {
    $requiredPath = Join-Path $payloadMod $requiredModFile
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Korean translation payload file not found: $requiredPath"
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $payloadMod "l10n") -PathType Container)) {
    throw "Korean translation l10n payload not found: $payloadMod\l10n"
}
foreach ($requiredSubtitleFile in $requiredSubtitleFiles) {
    $requiredPath = Join-Path $payloadMod "video\$requiredSubtitleFile"
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Korean video subtitle payload file not found: $requiredPath"
    }
}
if (-not (Test-Path -LiteralPath $configUpdater -PathType Leaf)) {
    throw "Config updater not found: $configUpdater"
}

function Test-OpenMWInstall([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    try {
        $full = [System.IO.Path]::GetFullPath($Path)
        return (Test-Path -LiteralPath (Join-Path $full "openmw.exe") -PathType Leaf)
    } catch {
        return $false
    }
}

if ([string]::IsNullOrWhiteSpace($OpenMWPath)) {
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    [void]$candidates.Add($scriptDir)
    [void]$candidates.Add((Split-Path -Parent $scriptDir))

    $uninstallRoots = @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($root in $uninstallRoots) {
        Get-ItemProperty $root -ErrorAction SilentlyContinue | Where-Object {
            $_.DisplayName -like 'OpenMW*' -and -not [string]::IsNullOrWhiteSpace($_.InstallLocation)
        } | ForEach-Object {
            [void]$candidates.Add($_.InstallLocation)
        }
    }

    if ($env:ProgramFiles) {
        Get-ChildItem -LiteralPath $env:ProgramFiles -Directory -Filter 'OpenMW*' -ErrorAction SilentlyContinue | ForEach-Object {
            [void]$candidates.Add($_.FullName)
        }
    }
    if (${env:ProgramFiles(x86)}) {
        Get-ChildItem -LiteralPath ${env:ProgramFiles(x86)} -Directory -Filter 'OpenMW*' -ErrorAction SilentlyContinue | ForEach-Object {
            [void]$candidates.Add($_.FullName)
        }
    }

    $OpenMWPath = $candidates | Where-Object { Test-OpenMWInstall $_ } | Select-Object -First 1
}

if ([string]::IsNullOrWhiteSpace($OpenMWPath)) {
    $OpenMWPath = Read-Host "OpenMW installation folder (the folder containing openmw.exe)"
}

$OpenMWPath = [System.IO.Path]::GetFullPath($OpenMWPath)
if (-not (Test-OpenMWInstall $OpenMWPath)) {
    throw "OpenMW installation not found at: $OpenMWPath"
}

$backupDir = Join-Path $OpenMWPath "korean-kr12-2-backup-$timestamp"
$runtimeBackup = Join-Path $backupDir "runtime"
$modBackup = Join-Path $backupDir "mod"
$legacyModBackup = Join-Path $backupDir "legacy-mod"
New-Item -ItemType Directory -Path $runtimeBackup -Force | Out-Null

$newRuntimeFiles = New-Object 'System.Collections.Generic.List[string]'
$overwrittenRuntimeFiles = New-Object 'System.Collections.Generic.List[string]'

Write-Host "Backing up and installing the Korean OpenMW executable and Galmuri11 font payload..."
foreach ($relative in $requiredRuntimeFiles) {
    $source = Join-Path $payloadRoot $relative
    $destination = Join-Path $OpenMWPath $relative

    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        $backup = Join-Path $runtimeBackup $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
        Copy-Item -LiteralPath $destination -Destination $backup -Force
        [void]$overwrittenRuntimeFiles.Add($relative)
    } else {
        [void]$newRuntimeFiles.Add($relative)
    }

    $destinationParent = Split-Path -Parent $destination
    if (-not [string]::IsNullOrWhiteSpace($destinationParent)) {
        New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    }
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

$newRuntimeFiles | Set-Content -LiteralPath (Join-Path $backupDir 'new-runtime-files.txt') -Encoding UTF8
$overwrittenRuntimeFiles | Set-Content -LiteralPath (Join-Path $backupDir 'overwritten-runtime-files.txt') -Encoding UTF8

$targetModsRoot = Join-Path $OpenMWPath "mods"
$targetMod = Join-Path $targetModsRoot $modFolderName
$legacyTargetMod = Join-Path $targetModsRoot $legacyModFolderName
New-Item -ItemType Directory -Path $targetModsRoot -Force | Out-Null

if (Test-Path -LiteralPath $targetMod -PathType Container) {
    Write-Host "Backing up existing Korean mod folder..."
    Copy-Item -LiteralPath $targetMod -Destination $modBackup -Recurse -Force
    Remove-Item -LiteralPath $targetMod -Recurse -Force
}

if (Test-Path -LiteralPath $legacyTargetMod -PathType Container) {
    Write-Host "Backing up retired Korean mod folder..."
    Copy-Item -LiteralPath $legacyTargetMod -Destination $legacyModBackup -Recurse -Force
    Remove-Item -LiteralPath $legacyTargetMod -Recurse -Force
}

Write-Host "Installing Korean translation data and video subtitles..."
Copy-Item -LiteralPath $payloadMod -Destination $targetMod -Recurse -Force

Write-Host "Updating OpenMW user configuration..."
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    & $configUpdater -OpenMWPath $OpenMWPath
} else {
    & $configUpdater -OpenMWPath $OpenMWPath -ConfigPath $ConfigPath
}

$marker = @"
OpenMW 0.51.0 Korean Support KR12.2
Installed: $timestamp
Font: Galmuri11
Backup: $backupDir
"@
Set-Content -LiteralPath (Join-Path $OpenMWPath "OPENMW-KOREAN-KR12.2.txt") -Value $marker -Encoding UTF8

Write-Host ""
Write-Host "Korean OpenMW KR12.2 installation completed."
Write-Host "OpenMW         : $OpenMWPath"
Write-Host "Korean mod     : $targetMod"
Write-Host "Font           : Galmuri11"
Write-Host "Video subtitles: $targetMod\video"
Write-Host "Backup         : $backupDir"
