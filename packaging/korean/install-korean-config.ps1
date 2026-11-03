[CmdletBinding()]
param(
    [string]$ConfigPath = "",
    [string]$OpenMWPath = ""
)

$ErrorActionPreference = "Stop"

$fallbackBeginMarker = "# BEGIN OPENMW KOREAN MANAGED FALLBACKS"
$fallbackEndMarker = "# END OPENMW KOREAN MANAGED FALLBACKS"
$dataBeginMarker = "# BEGIN OPENMW KOREAN MANAGED DATA"
$dataEndMarker = "# END OPENMW KOREAN MANAGED DATA"
$contentBeginMarker = "# BEGIN OPENMW KOREAN MANAGED CONTENT"
$contentEndMarker = "# END OPENMW KOREAN MANAGED CONTENT"
$modFolderName = "Morrowind_Korean_ReTranslation"
$pluginFileName = "Morrowind_Korean_ReTranslation.esp"
$compatPluginFileName = "Morrowind_Korean_MasterIndex_Compat.esp"
$legacyModFolderNames = @(
    "Morrowind_Korean_ReTranslation_v01"
)
$retiredPluginFileNames = @(
    "Morrowind_Korean_ReTranslation_v01.esp",
    "Morrowind_Korean_Interior_CellNames_v01.esp"
)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$payloadPath = Join-Path $scriptDir "korean-fallbacks.cfg"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path -LiteralPath $payloadPath -PathType Leaf)) {
    throw "Korean fallback payload not found: $payloadPath"
}

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $documents = [Environment]::GetFolderPath('MyDocuments')
    $ConfigPath = Join-Path $documents "My Games\OpenMW\openmw.cfg"
}

$ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "OpenMW config not found: $ConfigPath`nRun OpenMW once first, or pass -ConfigPath <path>."
}

$manageMod = -not [string]::IsNullOrWhiteSpace($OpenMWPath)
$dataLine = ""
if ($manageMod) {
    $OpenMWPath = [System.IO.Path]::GetFullPath($OpenMWPath)
    if (-not (Test-Path -LiteralPath (Join-Path $OpenMWPath "openmw.exe") -PathType Leaf)) {
        throw "OpenMW installation not found at: $OpenMWPath"
    }

    $modDataPath = Join-Path $OpenMWPath "mods\$modFolderName"
    if (-not (Test-Path -LiteralPath (Join-Path $modDataPath $pluginFileName) -PathType Leaf)) {
        throw "Korean translation ESP not found in OpenMW mods folder: $modDataPath"
    }
    $cfgModDataPath = $modDataPath.Replace('\', '/')
    $dataLine = 'data="' + $cfgModDataPath + '"'
}

$payloadLines = [System.IO.File]::ReadAllLines($payloadPath, $utf8NoBom)
$managedKeys = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($line in $payloadLines) {
    if ($line -match '^\s*fallback=([^,]+),') {
        [void]$managedKeys.Add($Matches[1].Trim())
    }
}
if ($managedKeys.Count -eq 0) {
    throw "No managed fallback keys were found in $payloadPath"
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = "$ConfigPath.korean-backup-$timestamp"
Copy-Item -LiteralPath $ConfigPath -Destination $backupPath -Force

$currentLines = [System.IO.File]::ReadAllLines($ConfigPath, $utf8NoBom)
$outputLines = New-Object 'System.Collections.Generic.List[string]'
$repairedBlocks = New-Object 'System.Collections.Generic.List[string]'

function Test-ManagedDataLine([string]$Line) {
    if ($Line -notmatch '^\s*data\s*=\s*(.*)$') {
        return $false
    }
    $dataValue = $Matches[1].Trim().Trim('"').Replace('\', '/').TrimEnd('/')
    foreach ($folderName in @($modFolderName) + $legacyModFolderNames) {
        $pattern = '(?i)(^|/)mods/' + [regex]::Escape($folderName) + '$'
        if ($dataValue -match $pattern) {
            return $true
        }
    }
    return $false
}

function Test-ManagedContentLine([string]$Line) {
    if ($Line -notmatch '^\s*content\s*=\s*(.+?)\s*$') {
        return $false
    }
    $contentName = $Matches[1].Trim().Trim('"')
    return ($contentName -ieq $pluginFileName -or $contentName -ieq $compatPluginFileName -or $retiredPluginFileNames -icontains $contentName)
}

$i = 0
while ($i -lt $currentLines.Length) {
    $line = $currentLines[$i]
    $trimmed = $line.Trim()
    $blockType = ""
    $blockEndMarker = ""

    if ($trimmed -eq $fallbackBeginMarker) {
        $blockType = "fallback"
        $blockEndMarker = $fallbackEndMarker
    } elseif ($trimmed -eq $dataBeginMarker) {
        $blockType = "data"
        $blockEndMarker = $dataEndMarker
    } elseif ($trimmed -eq $contentBeginMarker) {
        $blockType = "content"
        $blockEndMarker = $contentEndMarker
    }

    if (-not [string]::IsNullOrWhiteSpace($blockEndMarker)) {
        $matchingEnd = -1
        for ($j = $i + 1; $j -lt $currentLines.Length; $j++) {
            if ($currentLines[$j].Trim() -eq $blockEndMarker) {
                $matchingEnd = $j
                break
            }
        }

        if ($matchingEnd -ge 0) {
            $i = $matchingEnd + 1
            continue
        }

        # A previous installer may have been interrupted after writing BEGIN but before END.
        # The config has already been backed up. Remove only lines that are unmistakably
        # ours, then resume at the first unrelated user/OpenMW setting.
        [void]$repairedBlocks.Add($blockType)
        $i++
        while ($i -lt $currentLines.Length) {
            $candidate = $currentLines[$i]
            $candidateTrimmed = $candidate.Trim()

            if ($candidateTrimmed -eq $fallbackBeginMarker -or $candidateTrimmed -eq $dataBeginMarker -or $candidateTrimmed -eq $contentBeginMarker -or $candidateTrimmed -eq $fallbackEndMarker -or $candidateTrimmed -eq $dataEndMarker -or $candidateTrimmed -eq $contentEndMarker) {
                break
            }

            $isManagedPayload = $false
            if ($blockType -eq "fallback") {
                if ($payloadLines -contains $candidate) {
                    $isManagedPayload = $true
                } elseif ($candidate -match '^\s*fallback=([^,]+),' -and $managedKeys.Contains($Matches[1].Trim())) {
                    $isManagedPayload = $true
                }
            } elseif ($blockType -eq "data") {
                $isManagedPayload = Test-ManagedDataLine $candidate
            } elseif ($blockType -eq "content") {
                $isManagedPayload = Test-ManagedContentLine $candidate
            }

            if (-not $isManagedPayload) {
                break
            }
            $i++
        }
        continue
    }

    # Drop orphan END markers left by interrupted or manually edited installs.
    if ($trimmed -eq $fallbackEndMarker -or $trimmed -eq $dataEndMarker -or $trimmed -eq $contentEndMarker) {
        $i++
        continue
    }

    if ($line -match '^\s*fallback=([^,]+),' -and $managedKeys.Contains($Matches[1].Trim())) {
        $i++
        continue
    }

    if ($manageMod) {
        if (Test-ManagedContentLine $line) {
            $i++
            continue
        }
        if (Test-ManagedDataLine $line) {
            $i++
            continue
        }
    }

    [void]$outputLines.Add($line)
    $i++
}

if ($repairedBlocks.Count -gt 0) {
    $types = ($repairedBlocks | Select-Object -Unique) -join ", "
    Write-Warning "Recovered unclosed Korean managed block(s): $types. Backup: $backupPath"
}

function Insert-LinesAt {
    param(
        [System.Collections.Generic.List[string]]$List,
        [int]$Index,
        [string[]]$Lines
    )
    for ($j = $Lines.Count - 1; $j -ge 0; $j--) {
        $List.Insert($Index, $Lines[$j])
    }
}

if ($manageMod) {
    $dataBlock = @(
        $dataBeginMarker,
        $dataLine,
        $dataEndMarker
    )

    $lastDataIndex = -1
    for ($i = 0; $i -lt $outputLines.Count; $i++) {
        if ($outputLines[$i] -match '^\s*data\s*=') {
            $lastDataIndex = $i
        }
    }

    if ($lastDataIndex -ge 0) {
        Insert-LinesAt -List $outputLines -Index ($lastDataIndex + 1) -Lines $dataBlock
    } else {
        $firstContentIndex = -1
        for ($i = 0; $i -lt $outputLines.Count; $i++) {
            if ($outputLines[$i] -match '^\s*content\s*=') {
                $firstContentIndex = $i
                break
            }
        }
        if ($firstContentIndex -ge 0) {
            Insert-LinesAt -List $outputLines -Index $firstContentIndex -Lines $dataBlock
        } else {
            foreach ($line in $dataBlock) {
                [void]$outputLines.Add($line)
            }
        }
    }

    $contentBlock = @(
        $contentBeginMarker,
        "content=$pluginFileName",
        $contentEndMarker
    )

    $lastOfficialMasterIndex = -1
    for ($i = 0; $i -lt $outputLines.Count; $i++) {
        if ($outputLines[$i] -match '^\s*content\s*=\s*(Morrowind\.esm|Tribunal\.esm|Bloodmoon\.esm)\s*$') {
            $lastOfficialMasterIndex = $i
        }
    }

    if ($lastOfficialMasterIndex -ge 0) {
        Insert-LinesAt -List $outputLines -Index ($lastOfficialMasterIndex + 1) -Lines $contentBlock
    } else {
        $firstContentIndex = -1
        for ($i = 0; $i -lt $outputLines.Count; $i++) {
            if ($outputLines[$i] -match '^\s*content\s*=') {
                $firstContentIndex = $i
                break
            }
        }
        if ($firstContentIndex -ge 0) {
            Insert-LinesAt -List $outputLines -Index $firstContentIndex -Lines $contentBlock
        } else {
            foreach ($line in $contentBlock) {
                [void]$outputLines.Add($line)
            }
        }
    }

    # Bethesda's optional Master Index plugin adds/extends dialogue chains that
    # the base Korean ESP can otherwise win by load order. If the official
    # plugin is active, load our narrow dialogue overlay after both files.
    $masterIndexContentIndex = -1
    $koreanContentIndex = -1
    for ($i = 0; $i -lt $outputLines.Count; $i++) {
        if ($outputLines[$i] -match '^\s*content\s*=\s*master_index\.esp\s*$') {
            $masterIndexContentIndex = $i
        }
        if ($outputLines[$i] -match ('^\s*content\s*=\s*' + [regex]::Escape($pluginFileName) + '\s*$')) {
            $koreanContentIndex = $i
        }
    }

    if ($masterIndexContentIndex -ge 0) {
        $compatPluginPath = Join-Path $modDataPath $compatPluginFileName
        if (-not (Test-Path -LiteralPath $compatPluginPath -PathType Leaf)) {
            throw "Master Index compatibility ESP not found: $compatPluginPath"
        }

        $compatContentBlock = @(
            $contentBeginMarker,
            "content=$compatPluginFileName",
            $contentEndMarker
        )
        $compatInsertAfter = [Math]::Max($masterIndexContentIndex, $koreanContentIndex)
        Insert-LinesAt -List $outputLines -Index ($compatInsertAfter + 1) -Lines $compatContentBlock
    }
}

$fallbackBlock = New-Object 'System.Collections.Generic.List[string]'
[void]$fallbackBlock.Add($fallbackBeginMarker)
foreach ($line in $payloadLines) {
    [void]$fallbackBlock.Add($line)
}
[void]$fallbackBlock.Add($fallbackEndMarker)

$encodingIndex = -1
for ($i = $outputLines.Count - 1; $i -ge 0; $i--) {
    if ($outputLines[$i] -match '^\s*encoding\s*=') {
        $encodingIndex = $i
        break
    }
}

if ($encodingIndex -ge 0) {
    Insert-LinesAt -List $outputLines -Index $encodingIndex -Lines $fallbackBlock.ToArray()
} else {
    if ($outputLines.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($outputLines[$outputLines.Count - 1])) {
        [void]$outputLines.Add("")
    }
    foreach ($line in $fallbackBlock) {
        [void]$outputLines.Add($line)
    }
}

[System.IO.File]::WriteAllLines($ConfigPath, $outputLines, $utf8NoBom)

Write-Host "Updated OpenMW Korean configuration."
Write-Host "Config : $ConfigPath"
Write-Host "Backup : $backupPath"
Write-Host "Managed fallback keys: $($managedKeys.Count)"
if ($manageMod) {
    Write-Host "Korean data : $dataLine"
    Write-Host "Korean plugin: content=$pluginFileName"
    if ($masterIndexContentIndex -ge 0) {
        Write-Host "Master Index compat: content=$compatPluginFileName"
    }
}
if ($encodingIndex -ge 0) {
    Write-Host "Managed fallback block inserted immediately before the final encoding= line."
} else {
    Write-Host "Managed fallback block appended at the end because no encoding= line exists."
}
