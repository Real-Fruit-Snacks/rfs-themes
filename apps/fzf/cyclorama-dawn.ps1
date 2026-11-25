# Cyclorama Dawn v2.1.0 — fzf Color Palette (PowerShell / pwsh)
# Variant: Cyclorama Dawn (LX 263 · Dark · Beacon Orange)
# Author:  Real-Fruit-Snacks
# Source:  https://github.com/Real-Fruit-Snacks/rfs-themes

$cycloramaFzfColors = @(
  'bg:#050507'
  'bg+:#3D2B24'
  'fg:#D6D8E0'
  'fg+:#F4F5F8'
  'hl:#74B8E8'
  'hl+:#FF9254'
  'info:#FFC247'
  'marker:#3DDC97'
  'pointer:#FF9254'
  'prompt:#FF9254'
  'spinner:#74B8E8'
  'header:#B3B5C0'
  'border:#2A2C35'
  'gutter:#0C0C10'
  'label:#F4F5F8'
  'query:#F4F5F8'
) -join ','

$env:FZF_DEFAULT_OPTS = ("$env:FZF_DEFAULT_OPTS --color=$cycloramaFzfColors").Trim()
