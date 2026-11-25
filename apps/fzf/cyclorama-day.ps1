# Cyclorama Dawn v2.1.0 — fzf Color Palette (PowerShell / pwsh)
# Variant: Cyclorama Day (LX 512 · Light · Alabaster Day)
# Author:  Real-Fruit-Snacks
# Source:  https://github.com/Real-Fruit-Snacks/rfs-themes

$cycloramaFzfColors = @(
  'bg:#F5F7F9'
  'bg+:#DCE7F0'
  'fg:#252A34'
  'fg+:#0D1016'
  'hl:#164669'
  'hl+:#AD3D0A'
  'info:#885800'
  'marker:#127247'
  'pointer:#AD3D0A'
  'prompt:#AD3D0A'
  'spinner:#164669'
  'header:#474D59'
  'border:#C8D0DA'
  'gutter:#FFFFFF'
  'label:#0D1016'
  'query:#0D1016'
) -join ','

$env:FZF_DEFAULT_OPTS = ("$env:FZF_DEFAULT_OPTS --color=$cycloramaFzfColors").Trim()
