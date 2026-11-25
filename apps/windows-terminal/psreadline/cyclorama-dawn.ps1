# Cyclorama Dawn (LX 263 Dark · Beacon Orange) — PowerShell PSReadLine Theme
# Author: Real-Fruit-Snacks | Brand: Cyclorama Dawn v2.1.0
# Source: https://github.com/Real-Fruit-Snacks/rfs-themes
# Requires PSReadLine 2.2+ (PowerShell 7+ or `Update-Module PSReadLine`).

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
    InlinePrediction = '#8C8F9D'
    Member           = '#99CDF2'
    Emphasis         = '#FF9254'
    Default          = '#F4F5F8'
}
