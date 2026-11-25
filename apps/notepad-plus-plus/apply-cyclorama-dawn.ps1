<#
.SYNOPSIS
    Apply Cyclorama Dawn (LX 263 DARK) to Notepad++ 8.x.
.DESCRIPTION
    Copies all three Cyclorama Dawn XML themes into %APPDATA%\Notepad++\themes\,
    creates a one-time backup of config.xml (config.xml.pre-rfs.bak), and configures
    Notepad++ DarkMode Custom Tone (colorTone="32").
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ThemeName = 'Cyclorama Dawn'
$ThemeFileName = 'Cyclorama Dawn.xml'
$AllThemes = @('Cyclorama Dawn.xml', 'Cyclorama Steel.xml', 'Cyclorama Day.xml')

$NppDir = Join-Path $env:APPDATA 'Notepad++'
$ThemesDir = Join-Path $NppDir 'themes'
$ConfigPath = Join-Path $NppDir 'config.xml'
$BackupPath = Join-Path $NppDir 'config.xml.pre-rfs.bak'

$Running = Get-Process -Name 'notepad++' -ErrorAction SilentlyContinue
if ($null -ne $Running) {
    Write-Warning '[!] Notepad++ is currently running. Close Notepad++ before applying so it does not overwrite config.xml on exit, or re-run this script after closing Notepad++.'
}

if (-not (Test-Path -LiteralPath $ThemesDir)) {
    New-Item -ItemType Directory -Path $ThemesDir -Force | Out-Null
}

$Copied = 0
foreach ($File in $AllThemes) {
    $Src = Join-Path $PSScriptRoot $File
    if (Test-Path -LiteralPath $Src) {
        Copy-Item -LiteralPath $Src -Destination (Join-Path $ThemesDir $File) -Force
        $Copied++
    }
}
Write-Host "[ok] Copied $Copied Cyclorama XML theme(s) into $ThemesDir"

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Write-Warning "[!] $ConfigPath not found. Launch Notepad++ once to initialize config.xml, then select '$ThemeName' in Settings -> Style Configurator."
    return
}

if (-not (Test-Path -LiteralPath $BackupPath)) {
    Copy-Item -LiteralPath $ConfigPath -Destination $BackupPath -Force
    Write-Host "[ok] Created one-time backup: $BackupPath"
} else {
    Write-Host "[i]  Preserving existing backup: $BackupPath"
}

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$RawXml = [System.IO.File]::ReadAllText($ConfigPath, $Utf8NoBom)
$Doc = New-Object System.Xml.XmlDocument
$Doc.PreserveWhitespace = $true
$Doc.LoadXml($RawXml)

$GuiConfigs = $Doc.SelectSingleNode('/NotepadPlus/GUIConfigs')
if ($null -eq $GuiConfigs) {
    throw "Could not find <GUIConfigs> in $ConfigPath"
}

$DarkModeNode = $GuiConfigs.SelectSingleNode("GUIConfig[@name='DarkMode']")
if ($null -eq $DarkModeNode) {
    $DarkModeNode = $Doc.CreateElement('GUIConfig')
    [void]$DarkModeNode.SetAttribute('name', 'DarkMode')
    [void]$GuiConfigs.AppendChild($DarkModeNode)
}

$DarkModeAttrs = [ordered]@{
    'enable' = 'yes'
    'enableWindowsMode' = 'no'
    'colorTone' = '32'
    'customColorTop' = '591623'
    'customColorMenuHotTrack' = '1709076'
    'customColorActive' = '1051660'
    'customColorMain' = '460037'
    'customColorError' = '3679433'
    'customColorText' = '16315892'
    'customColorDarkText' = '12629427'
    'customColorDisabledText' = '10325900'
    'customColorLinkText' = '5542655'
    'customColorEdge' = '3484714'
    'customColorHotEdge' = '5542655'
    'customColorDisabledEdge' = '3024679'
    'darkThemeName' = 'Cyclorama Dawn.xml'
    'darkTbFluentColor' = '9'
    'darkTbFluentCustomColor' = '5542655'
}

foreach ($Key in $DarkModeAttrs.Keys) {
    [void]$DarkModeNode.SetAttribute($Key, $DarkModeAttrs[$Key])
}

$Settings = New-Object System.Xml.XmlWriterSettings
$Settings.Encoding = $Utf8NoBom
$Settings.Indent = $true
$Settings.OmitXmlDeclaration = $false

$Writer = [System.Xml.XmlWriter]::Create($ConfigPath, $Settings)
try {
    $Doc.Save($Writer)
} finally {
    $Writer.Dispose()
}

Write-Host "[ok] Applied '$ThemeName' to $ConfigPath"
Write-Host "[i]  Launch (or restart) Notepad++ to see $ThemeName in full effect."
