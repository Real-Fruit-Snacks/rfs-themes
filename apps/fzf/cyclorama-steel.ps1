# Cyclorama Dawn v2.3.2 — fzf Color Palette (PowerShell / pwsh)
# Variant: Cyclorama Steel (LX 263 · Dark · Steel Blue)
# Author:  Real-Fruit-Snacks
# Source:  https://github.com/Real-Fruit-Snacks/rfs-themes

$cycloramaFzfColors = @(
  'bg:#050507'
  'bg+:#1D3B57'
  'fg:#D6DCE4'
  'fg+:#F4F5F8'
  'hl:#FF9254'
  'hl+:#74B8E8'
  'info:#FFC247'
  'marker:#3DDC97'
  'pointer:#74B8E8'
  'prompt:#74B8E8'
  'spinner:#FF9254'
  'header:#B3B5C0'
  'border:#27313D'
  'gutter:#0C0C10'
  'label:#F4F5F8'
  'query:#F4F5F8'
) -join ','

$env:FZF_DEFAULT_OPTS = ("$env:FZF_DEFAULT_OPTS --color=$cycloramaFzfColors").Trim()
