<#
.SYNOPSIS
    Validate and register Cyclorama Day (LX 512 LIGHT) in Windows PowerShell ISE.
.DESCRIPTION
    Loads Microsoft.PowerShell.GPowerShell, deserializes Cyclorama Day.StorableColorTheme.ps1xml via
    StorableColorTheme::FromFile(), validates all 73 keys (0 errors required),
    and stores the theme in PowerShell ISE via StoreTheme(). If executed inside
    PowerShell ISE ($psISE present), also applies the theme immediately.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSEdition -eq 'Core') {
    throw 'Windows PowerShell ISE requires Windows PowerShell 5.1 (powershell.exe), not PowerShell 7 (pwsh).'
}

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName Microsoft.PowerShell.GPowerShell

if ($null -eq [System.Windows.Application]::Current) {
    $null = New-Object System.Windows.Application
}

$ThemeFileName = 'Cyclorama Day.StorableColorTheme.ps1xml'
$ThemePath = Join-Path $PSScriptRoot $ThemeFileName
if (-not (Test-Path -LiteralPath $ThemePath)) {
    throw "Theme file not found: $ThemePath"
}

$Asm = [System.Reflection.Assembly]::LoadWithPartialName('Microsoft.PowerShell.GPowerShell')
$Flags = [System.Reflection.BindingFlags]'Public,NonPublic,Static,Instance'
$ThemeType = $Asm.GetType('Microsoft.Windows.PowerShell.Gui.Internal.StorableColorTheme')
$PresetType = $Asm.GetType('Microsoft.Windows.PowerShell.Gui.Internal.PresetThemes')

$FromFileMethod = $ThemeType.GetMethod('FromFile', $Flags)
$ValidateMethod = $ThemeType.GetMethod('Validate', $Flags)
$StoreMethod = $ThemeType.GetMethod('StoreTheme', $Flags)
$ApplyMethod = $ThemeType.GetMethod('ApplyToISEOptions', $Flags)

function Invoke-ClrMethod {
    param([System.Reflection.MethodInfo]$Method, $Target, $Arg)
    $Unwrapped = if ($Arg -is [psobject]) { $Arg.BaseObject } else { $Arg }
    $ArgArray = [object[]]::new(1)
    $ArgArray[0] = $Unwrapped
    $TargetObj = if ($Target -is [psobject]) { $Target.BaseObject } else { $Target }
    return $Method.Invoke($TargetObj, $ArgArray)
}

$Theme = Invoke-ClrMethod $FromFileMethod $null ([string]$ThemePath)
if ($null -eq $Theme) {
    throw "StorableColorTheme::FromFile returned null for $ThemePath"
}

$Presets = $PresetType.GetProperty('Themes', $Flags).GetValue($null)
$KnownGood = $Presets['Light Console, Light Editor']
$ValidationErrors = @(Invoke-ClrMethod $ValidateMethod $Theme $KnownGood)
if ($ValidationErrors.Count -ne 0) {
    $Joined = ($ValidationErrors -join '; ')
    throw "Theme validation failed with $($ValidationErrors.Count) error(s): $Joined"
}

[void](Invoke-ClrMethod $StoreMethod $null $Theme)
Write-Host "[ok] Validated (0 errors) and registered '$($Theme.Name)' in Windows PowerShell ISE."

$IseVar = Get-Variable -Name 'psISE' -ErrorAction SilentlyContinue
if ($null -ne $IseVar -and $null -ne $IseVar.Value) {
    [void](Invoke-ClrMethod $ApplyMethod $Theme $IseVar.Value.Options)
    Write-Host "[ok] Applied '$($Theme.Name)' to the active PowerShell ISE session."
} else {
    Write-Host "[i]  Open PowerShell ISE -> Tools -> Options -> Colors and Fonts -> Manage Themes -> select '$($Theme.Name)'."
}
