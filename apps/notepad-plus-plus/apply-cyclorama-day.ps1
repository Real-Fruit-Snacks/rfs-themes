<#
.SYNOPSIS
    Apply Cyclorama Day (LX 512 LIGHT) to Notepad++ 8.x.
.DESCRIPTION
    Copies all three Cyclorama Dawn XML themes into %APPDATA%\Notepad++\themes\,
    creates a one-time backup of config.xml (config.xml.pre-rfs.bak), and configures
    Notepad++ DarkMode (Light mode + stylerTheme).
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ThemeName = 'Cyclorama Day'
$ThemeFileName = 'Cyclorama Day.xml'
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
    'enable' = 'no'
    'enableWindowsMode' = 'no'
    'lightThemeName' = 'Cyclorama Day.xml'
    'lightTbFluentColor' = '9'
    'lightTbFluentCustomColor' = '671149'
}

foreach ($Key in $DarkModeAttrs.Keys) {
    [void]$DarkModeNode.SetAttribute($Key, $DarkModeAttrs[$Key])
}

$StylerNode = $GuiConfigs.SelectSingleNode("GUIConfig[@name='stylerTheme']")
if ($null -eq $StylerNode) {
    $StylerNode = $Doc.CreateElement('GUIConfig')
    [void]$StylerNode.SetAttribute('name', 'stylerTheme')
    [void]$GuiConfigs.AppendChild($StylerNode)
}
$ActiveThemePath = Join-Path $ThemesDir $ThemeFileName
[void]$StylerNode.SetAttribute('path', $ActiveThemePath)

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
