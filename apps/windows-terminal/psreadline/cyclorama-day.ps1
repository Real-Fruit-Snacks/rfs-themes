# Cyclorama Day (LX 512 Light · Alabaster Day) — PowerShell PSReadLine Theme
# Author: Real-Fruit-Snacks | Brand: Cyclorama Dawn v2.1.0
# Source: https://github.com/Real-Fruit-Snacks/rfs-themes
# Compatible with Windows PowerShell 5.1 (PSReadLine 2.0+) and PowerShell 7+ (PSReadLine 2.2+).

Set-PSReadLineOption -Colors @{
    Command          = '#AD3D0A'
    Parameter        = '#943207'
    Operator         = '#252A34'
    Variable         = '#6B38B8'
    String           = '#885800'
    Number           = '#127247'
    Type             = '#0E6674'
    Comment          = '#58606E'
    Keyword          = '#164669'
    Error            = '#B91C2E'
    Selection        = "$([char]0x1b)[38;2;13;16;22;48;2;198;218;235m" # #0D1016 on #C6DAEB
    Member           = '#1F547A'
    Emphasis         = '#AD3D0A'
    Default          = '#0D1016'
}

if ((Get-Module PSReadLine).Version -ge [version]'2.1.0') {
    Set-PSReadLineOption -Colors @{ InlinePrediction = '#58606E' }
}
