# Cyclorama Dawn (LX 263 Dark · Beacon Orange) — PowerShell PSReadLine Theme
# Author: Real-Fruit-Snacks | Brand: Cyclorama Dawn v2.3.2
# Source: https://github.com/Real-Fruit-Snacks/rfs-themes
# Compatible with Windows PowerShell 5.1 (PSReadLine 2.0+) and PowerShell 7+ (PSReadLine 2.2+).

Set-PSReadLineOption -Colors @{
    Command          = '#FF9254'
    Parameter        = '#FFB07A'
    Operator         = '#D6D8E0'
    Variable         = '#C996F5'
    String           = '#FFC247'
    Number           = '#3DDC97'
    Type             = '#56D4E0'
    Comment          = '#8C8F9D'
    Keyword          = '#74B8E8'
    Error            = '#FF5C6C'
    Selection        = "$([char]0x1b)[38;2;244;245;248;48;2;61;43;36m" # #F4F5F8 on #3D2B24
    Member           = '#99CDF2'
    Emphasis         = '#FF9254'
    Default          = '#F4F5F8'
}

if ((Get-Module PSReadLine).Version -ge [version]'2.1.0') {
    Set-PSReadLineOption -Colors @{ InlinePrediction = '#8C8F9D' }
}
