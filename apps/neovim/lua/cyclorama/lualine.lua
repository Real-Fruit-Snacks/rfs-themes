-- Cyclorama Dawn v2.1.0 Lualine theme helper
-- Usage: require("lualine").setup({ options = { theme = require("cyclorama.lualine") } })
local cyclorama = require("cyclorama")
local p = cyclorama.get_palette(vim.g.colors_name)
local ui = p.ui

return {
  normal = {
    a = { fg = ui.on_accent, bg = ui.accent_fill, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  insert = {
    a = { fg = ui.bg, bg = ui.signal, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  visual = {
    a = { fg = ui.on_accent, bg = ui.secondary_fill, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  replace = {
    a = { fg = ui.on_accent, bg = ui.fault_fill, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  command = {
    a = { fg = ui.bg, bg = ui.warning, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  inactive = {
    a = { fg = ui.mute, bg = ui.rail },
    b = { fg = ui.subtle, bg = ui.rail },
    c = { fg = ui.subtle, bg = ui.rail },
  },
}
