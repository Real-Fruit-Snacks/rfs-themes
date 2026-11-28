#Requires -Version 5.1
<#
.SYNOPSIS
    Installs Cyclorama Dawn (LX 263 Dark · Beacon Orange) on Windows 11.
.DESCRIPTION
    Backup-first installer for Cyclorama Dawn v2.3.2 (Real-Fruit-Snacks).
    Copies Oklab-calibrated 1080p & 4K wallpapers and native .theme files into
    %LOCALAPPDATA%\rfs-themes\windows and %LOCALAPPDATA%\Microsoft\Windows\Themes,
    exports a one-time registry backup (backup-pre-rfs.reg), configures Personalize,
    DWM, Explorer AccentPalette (32 bytes), and applies the wallpaper and accents live.
.PARAMETER Resolution
    Wallpaper resolution: 'auto' (4k when any connected display exceeds 1920x1080 —
    such as 1440p, ultrawide, or 4K — else 1080p), '1080p', or '4k'.
.PARAMETER TintTaskbar
    When specified, enables accent tinting on Start and Taskbar (ColorPrevalence = 1).
    Defaults to off so the taskbar stays matte dark.
.EXAMPLE
    .\install-cyclorama-dawn.ps1
.EXAMPLE
    .\install-cyclorama-dawn.ps1 -Resolution 4k -TintTaskbar
#>
[CmdletBinding()]
param(
    [ValidateSet('auto', '1080p', '4k')]
    [string]$Resolution = 'auto',
    [switch]$TintTaskbar
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$VariantId      = 'cyclorama-dawn'
$ThemeName      = 'Cyclorama Dawn'
$ThemeFileName  = 'Cyclorama Dawn.theme'
$ScriptDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot    = Join-Path $env:LOCALAPPDATA 'rfs-themes\windows'
$WallpaperDest  = Join-Path $InstallRoot 'wallpapers'
$WinThemesDir   = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Themes'
$BackupRegPath  = Join-Path $InstallRoot 'backup-pre-rfs.reg'

if (-not ([System.Management.Automation.PSTypeName]'RfsThemes.NativeWin32').Type) {
    Add-Type -Namespace 'RfsThemes' -Name 'NativeWin32' -MemberDefinition @'
        [System.Runtime.InteropServices.DllImport("user32.dll", SetLastError = true)]
        public static extern bool SetProcessDpiAwarenessContext(System.IntPtr value);

        [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
        public static extern bool SystemParametersInfoW(uint uiAction, uint uiParam, string pvParam, uint fWinIni);

        [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
        public static extern System.IntPtr SendMessageTimeoutW(
            System.IntPtr hWnd,
            uint Msg,
            System.UIntPtr wParam,
            string lParam,
            uint fuFlags,
            uint uTimeout,
            out System.UIntPtr lpdwResult
        );
'@
}

# 1. Resolve target display resolution ('auto' -> 4k if any connected monitor exceeds 1920x1080)
if ($Resolution -eq 'auto') {
    $screenWidth  = 0
    $screenHeight = 0
    # Query physical pixels via WMI video controllers (unaffected by DPI scaling)
    try {
        $controllers = Get-CimInstance -ClassName Win32_VideoController -ErrorAction Stop |
            Where-Object { $_.CurrentHorizontalResolution -and $_.CurrentVerticalResolution }
        foreach ($vc in $controllers) {
            $screenWidth  = [Math]::Max($screenWidth,  [int]$vc.CurrentHorizontalResolution)
            $screenHeight = [Math]::Max($screenHeight, [int]$vc.CurrentVerticalResolution)
        }
    } catch {}
    # Enable Per-Monitor V2 DPI awareness (-4) and inspect ALL connected screens
    try {
        $null = [RfsThemes.NativeWin32]::SetProcessDpiAwarenessContext([System.IntPtr](-4))
    } catch {}
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        foreach ($scr in [System.Windows.Forms.Screen]::AllScreens) {
            $screenWidth  = [Math]::Max($screenWidth,  [int]$scr.Bounds.Width)
            $screenHeight = [Math]::Max($screenHeight, [int]$scr.Bounds.Height)
        }
    } catch {}
    if ($screenWidth -le 0) {
        $screenWidth = 1920
    }
    $Resolution = if ($screenWidth -gt 1920 -or $screenHeight -gt 1080) { '4k' } else { '1080p' }
}

# 2. Copy wallpapers and native Windows 11 .theme files to permanent directories
New-Item -ItemType Directory -Path $WallpaperDest -Force | Out-Null
New-Item -ItemType Directory -Path $WinThemesDir -Force | Out-Null

$SourceWallpapers = Join-Path $ScriptDir 'wallpapers'
if (Test-Path -LiteralPath $SourceWallpapers) {
    Get-ChildItem -LiteralPath $SourceWallpapers -Filter 'cyclorama-*.png' | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $WallpaperDest $_.Name) -Force
    }
}

$wpPath = Join-Path $WallpaperDest "$VariantId-$Resolution.png"
if (-not (Test-Path -LiteralPath $wpPath)) {
    throw "Wallpaper not found at $wpPath. Run this script from apps/windows/."
}

Get-ChildItem -LiteralPath $ScriptDir -Filter 'Cyclorama *.theme' | ForEach-Object {
    $themeContent = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
    $themeContent = $themeContent -replace '-1080p\.png', "-$Resolution.png"
    $destLocal = Join-Path $InstallRoot $_.Name
    $destWin   = Join-Path $WinThemesDir $_.Name
    [System.IO.File]::WriteAllText($destLocal, $themeContent, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($destWin, $themeContent, [System.Text.UTF8Encoding]::new($false))
}

# 3. Export one-time registry backup before modifying any Windows personalization keys
if (-not (Test-Path -LiteralPath $BackupRegPath)) {
    $keysToBackup = @(
        'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
        'HKCU\Software\Microsoft\Windows\DWM',
        'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent',
        'HKCU\Control Panel\Desktop',
        'HKCU\Control Panel\Colors'
    )
    $mergedLines = New-Object System.Collections.Generic.List[string]
    $mergedLines.Add('Windows Registry Editor Version 5.00')
    $mergedLines.Add('')
    foreach ($regKey in $keysToBackup) {
        $psRegPath = $regKey -replace '^HKCU\\', 'HKCU:\'
        if (-not (Test-Path -LiteralPath $psRegPath)) {
            continue
        }
        $tmpFile = Join-Path $env:TEMP ("rfs-backup-" + [System.Guid]::NewGuid().ToString('N') + '.reg')
        $prevEap = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & reg.exe export $regKey $tmpFile /y 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $tmpFile)) {
                $exported = Get-Content -LiteralPath $tmpFile -Encoding Unicode
                foreach ($line in ($exported | Select-Object -Skip 1)) {
                    $mergedLines.Add($line)
                }
                $mergedLines.Add('')
            }
        } finally {
            $ErrorActionPreference = $prevEap
            if (Test-Path -LiteralPath $tmpFile) {
                Remove-Item -LiteralPath $tmpFile -Force -ErrorAction SilentlyContinue
            }
        }
    }
    Set-Content -LiteralPath $BackupRegPath -Value $mergedLines -Encoding Unicode
    Write-Host "[ok] Saved one-time pre-RFS registry backup to $BackupRegPath"
}

function Set-RegistryValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string]$Type
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -Path $Path -Force | Out-Null
    }
    New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
}

# 4. Personalize (Dark/Light mode, transparency, taskbar color prevalence)
$PersonalizeKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
$TaskbarTintVal = if ($TintTaskbar.IsPresent) { 1 } else { 0 }
Set-RegistryValue -Path $PersonalizeKey -Name 'AppsUseLightTheme'    -Value 0 -Type DWord
Set-RegistryValue -Path $PersonalizeKey -Name 'SystemUsesLightTheme' -Value 0 -Type DWord
Set-RegistryValue -Path $PersonalizeKey -Name 'ColorPrevalence'      -Value $TaskbarTintVal -Type DWord
Set-RegistryValue -Path $PersonalizeKey -Name 'EnableTransparency'   -Value 1 -Type DWord

# 5. DWM Accent & Colorization (#F06E2B: ABGR=0xFF2B6EF0, ARGB=0xC4F06E2B)
$DwmKey = 'HKCU:\Software\Microsoft\Windows\DWM'
Set-RegistryValue -Path $DwmKey -Name 'AccentColor'           -Value 0xFF2B6EF0 -Type DWord
Set-RegistryValue -Path $DwmKey -Name 'ColorizationColor'     -Value 0xC4F06E2B -Type DWord
Set-RegistryValue -Path $DwmKey -Name 'ColorizationAfterglow' -Value 0xC4F06E2B -Type DWord
Set-RegistryValue -Path $DwmKey -Name 'ColorPrevalence'       -Value 0 -Type DWord

# 6. Explorer Accent Menu & 32-byte AccentPalette (8 slots x RR GG BB 00)
$AccentKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent'
[byte[]]$AccentPalette = @(
    0xFF,0xD2,0xB3,0x00, 0xFF,0xB0,0x7A,0x00, 0xFF,0x92,0x54,0x00, 0xF0,0x6E,0x2B,0x00, 0xCC,0x50,0x16,0x00, 0x9E,0x3B,0x0C,0x00, 0x5C,0x20,0x06,0x00, 0x74,0xB8,0xE8,0x00
)
Set-RegistryValue -Path $AccentKey -Name 'AccentColorMenu' -Value 0xFF2B6EF0 -Type DWord
Set-RegistryValue -Path $AccentKey -Name 'StartColorMenu'  -Value 0xFF1650CC -Type DWord
Set-RegistryValue -Path $AccentKey -Name 'AccentPalette'   -Value $AccentPalette -Type Binary

# 7. Desktop solid fallback background + wallpaper fit mode
$ColorsKey  = 'HKCU:\Control Panel\Colors'
$DesktopKey = 'HKCU:\Control Panel\Desktop'
Set-RegistryValue -Path $ColorsKey  -Name 'Background'     -Value '5 5 7' -Type String
Set-RegistryValue -Path $DesktopKey -Name 'WallpaperStyle' -Value '10' -Type String
Set-RegistryValue -Path $DesktopKey -Name 'TileWallpaper'  -Value '0'  -Type String

# 8. Apply wallpaper live and broadcast WM_SETTINGCHANGE ("ImmersiveColorSet")
$null = [RfsThemes.NativeWin32]::SystemParametersInfoW(0x0014, 0, $wpPath, 3)
$broadcastResult = [System.UIntPtr]::Zero
$null = [RfsThemes.NativeWin32]::SendMessageTimeoutW(
    [System.IntPtr]0xFFFF,
    0x001A,
    [System.UIntPtr]::Zero,
    'ImmersiveColorSet',
    0x0002,
    5000,
    [ref]$broadcastResult
)

Write-Host "[ok] Installed $ThemeName ($Resolution, Dark mode, TintTaskbar=$($TintTaskbar.IsPresent))"
Write-Host "[i]  Theme registered in Settings -> Personalization -> Themes ($ThemeFileName)"
Write-Host "[i]  To revert original Windows colors later, merge: $BackupRegPath"
