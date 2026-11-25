#!/usr/bin/env python3
"""Generate Cyclorama Dawn terminal emulator ports and SVG previews for rfs-themes.

Builds 5 terminal ports (15 total variants across Dawn, Steel, and Day):
  1. apps/windows-terminal/  (Windows Terminal JSON schemes + PowerShell PSReadLine .ps1)
  2. apps/wezterm/           (WezTerm .toml color schemes)
  3. apps/alacritty/         (Alacritty v0.13+ .toml color schemes)
  4. apps/ghostty/           (Ghostty native theme files)
  5. apps/kitty/             (Kitty .conf theme files)

Zero external dependencies (Python 3.11+ standard library only).
Deterministic UTF-8 LF output across Windows and Linux CI.
"""
from __future__ import annotations

import json
import os
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from rfs_palette import (  # noqa: E402
    AUTHOR,
    BRAND_NAME,
    REPO_URL,
    VARIANT_ORDER,
    VARIANTS,
    ansi_list,
    hex_to_rgb,
)
from svg_previews import render_terminal_preview, write_preview_pair  # noqa: E402

BRAND_REPO_URL = "https://github.com/Real-Fruit-Snacks/rfs-brand"


def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _write_json(path: str, data: object) -> str:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    _write_text(path, text)
    return text


def _swatches(v: dict) -> list[dict[str, str]]:
    ui = v["ui"]
    secondary_label = "BEACON" if v["id"] == "cyclorama-steel" else "STEEL"
    return [
        {"label": "BG", "hex": ui["bg"]},
        {"label": "TEXT", "hex": ui["text"]},
        {"label": "CURSOR", "hex": ui["cursor"]},
        {"label": "SELECT", "hex": ui["selection_active"]},
        {"label": "ACCENT", "hex": ui["accent"]},
        {"label": secondary_label, "hex": ui["secondary"]},
    ]


def _manifest_entry(
    slug: str,
    app_name: str,
    homepage: str,
    fmt: str,
    install: str,
) -> dict:
    return {
        "slug": slug,
        "name": app_name,
        "category": "Terminals",
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "variants": [
            {
                "id": VARIANTS[vid]["id"],
                "name": VARIANTS[vid]["name"],
                "lx": VARIANTS[vid]["lx"],
                "mode": VARIANTS[vid]["mode"],
                "accentRole": VARIANTS[vid]["accentRole"],
                "summary": VARIANTS[vid]["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
            }
            for vid in VARIANT_ORDER
        ],
        "path": f"apps/{slug}",
        "data": f"apps/{slug}/themes.json",
    }


def _render_previews(app_name: str, slug: str, shell_cmd: str) -> None:
    for vid in VARIANT_ORDER:
        svg = render_terminal_preview(app_name, slug, VARIANTS[vid], shell_cmd=shell_cmd)
        write_preview_pair(slug, vid, svg)


def _ansi_markdown_table() -> str:
    dawn = VARIANTS["cyclorama-dawn"]
    steel = VARIANTS["cyclorama-steel"]
    day = VARIANTS["cyclorama-day"]
    rows = [
        ("Background / Foreground", f"`{dawn['ui']['bg']}` / `{dawn['ui']['text']}`", f"`{steel['ui']['bg']}` / `{steel['ui']['text']}`", f"`{day['ui']['bg']}` / `{day['ui']['text']}`"),
        ("Cursor / Cursor Text", f"`{dawn['ui']['cursor']}` / `{dawn['ui']['cursor_text']}`", f"`{steel['ui']['cursor']}` / `{steel['ui']['cursor_text']}`", f"`{day['ui']['cursor']}` / `{day['ui']['cursor_text']}`"),
        ("Selection Background", f"`{dawn['ui']['selection_active']}`", f"`{steel['ui']['selection_active']}`", f"`{day['ui']['selection_active']}`"),
        ("Accent / Secondary", f"`{dawn['ui']['accent']}` / `{dawn['ui']['secondary']}`", f"`{steel['ui']['accent']}` / `{steel['ui']['secondary']}`", f"`{day['ui']['accent']}` / `{day['ui']['secondary']}`"),
        ("ANSI Red / Green / Yellow", f"`{dawn['ansi']['red']}` / `{dawn['ansi']['green']}` / `{dawn['ansi']['yellow']}`", f"`{steel['ansi']['red']}` / `{steel['ansi']['green']}` / `{steel['ansi']['yellow']}`", f"`{day['ansi']['red']}` / `{day['ansi']['green']}` / `{day['ansi']['yellow']}`"),
        ("ANSI Blue / Magenta / Cyan", f"`{dawn['ansi']['blue']}` / `{dawn['ansi']['magenta']}` / `{dawn['ansi']['cyan']}`", f"`{steel['ansi']['blue']}` / `{steel['ansi']['magenta']}` / `{steel['ansi']['cyan']}`", f"`{day['ansi']['blue']}` / `{day['ansi']['magenta']}` / `{day['ansi']['cyan']}`"),
    ]
    lines = [
        "| Role | Cyclorama Dawn (`LX 263`) | Cyclorama Steel (`LX 263`) | Cyclorama Day (`LX 512`) |",
        "|---|---|---|---|",
    ]
    for role, c1, c2, c3 in rows:
        lines.append(f"| {role} | {c1} | {c2} | {c3} |")
    return "\n".join(lines)


def _variant_table(file_links: dict[str, str], extra_col: tuple[str, dict[str, str]] | None = None) -> str:
    if extra_col:
        extra_title, extra_map = extra_col
        lines = [
            f"| Variant | Lighting | Mode | Accent Role | Theme File | {extra_title} |",
            "|---|---|---|---|---|---|",
        ]
        for vid in VARIANT_ORDER:
            v = VARIANTS[vid]
            lines.append(
                f"| **{v['name']}** | `{v['lx']}` | `{v['mode']}` | {v['accentRole']} | {file_links[vid]} | {extra_map[vid]} |"
            )
    else:
        lines = [
            "| Variant | Lighting | Mode | Accent Role | Theme File |",
            "|---|---|---|---|---|",
        ]
        for vid in VARIANT_ORDER:
            v = VARIANTS[vid]
            lines.append(
                f"| **{v['name']}** | `{v['lx']}` | `{v['mode']}` | {v['accentRole']} | {file_links[vid]} |"
            )
    return "\n".join(lines)


def _previews_markdown(app_name: str) -> str:
    blocks = []
    for idx, vid in enumerate(VARIANT_ORDER, start=1):
        v = VARIANTS[vid]
        mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
        blocks.append(
            f"### {idx}. {v['name']} (`{v['lx']} {mode_lbl} · {v['accentRole']}`)\n\n"
            f"{v['summary']}\n\n"
            f"![{v['name']} {app_name} preview](previews/{vid}.svg)"
        )
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# 1. Windows Terminal + PowerShell PSReadLine
# ---------------------------------------------------------------------------

def _wt_scheme(v: dict) -> dict[str, str]:
    ui = v["ui"]
    a = v["ansi"]
    return {
        "name": v["name"],
        "background": ui["bg"],
        "foreground": ui["text"],
        "cursorColor": ui["cursor"],
        "selectionBackground": ui["selection_active"],
        "black": a["black"],
        "red": a["red"],
        "green": a["green"],
        "yellow": a["yellow"],
        "blue": a["blue"],
        "purple": a["magenta"],
        "cyan": a["cyan"],
        "white": a["white"],
        "brightBlack": a["brightBlack"],
        "brightRed": a["brightRed"],
        "brightGreen": a["brightGreen"],
        "brightYellow": a["brightYellow"],
        "brightBlue": a["brightBlue"],
        "brightPurple": a["brightMagenta"],
        "brightCyan": a["brightCyan"],
        "brightWhite": a["brightWhite"],
    }


def _psreadline_script(v: dict) -> str:
    ui = v["ui"]
    syn = v["syntax"]
    fr, fg, fb = hex_to_rgb(ui["text"])
    br, bg, bb = hex_to_rgb(ui["selection_active"])
    sel_vt = f"$([char]0x1b)[38;2;{fr};{fg};{fb};48;2;{br};{bg};{bb}m"
    mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
    return (
        f"# {v['name']} ({v['lx']} {mode_lbl} · {v['accentRole']}) — PowerShell PSReadLine Theme\n"
        f"# Author: {AUTHOR} | Brand: {BRAND_NAME} v{v['version']}\n"
        f"# Source: {REPO_URL}\n"
        f"# Requires PSReadLine 2.2+ (PowerShell 7+ or `Update-Module PSReadLine`).\n\n"
        f"Set-PSReadLineOption -Colors @{{\n"
        f"    Command          = '{syn['function']}'\n"
        f"    Parameter        = '{syn['parameter']}'\n"
        f"    Operator         = '{syn['operator']}'\n"
        f"    Variable         = '{syn['constant']}'\n"
        f"    String           = '{syn['string']}'\n"
        f"    Number           = '{syn['number']}'\n"
        f"    Type             = '{syn['type']}'\n"
        f"    Comment          = '{syn['comment']}'\n"
        f"    Keyword          = '{syn['keyword']}'\n"
        f"    Error            = '{ui['fault']}'\n"
        f"    Selection        = \"{sel_vt}\" # {ui['text']} on {ui['selection_active']}\n"
        f"    InlinePrediction = '{ui['subtle']}'\n"
        f"    Member           = '{syn['property']}'\n"
        f"    Emphasis         = '{ui['accent']}'\n"
        f"    Default          = '{ui['text']}'\n"
        f"}}\n"
    )


def build_windows_terminal() -> dict:
    slug = "windows-terminal"
    app_name = "Windows Terminal"
    homepage = "https://learn.microsoft.com/en-us/windows/terminal/"
    fmt = "JSON Schemes + PSReadLine .ps1"
    install = "Paste scheme into settings.json \"schemes\" array + dot-source PSReadLine .ps1"
    app_dir = os.path.join(ROOT, "apps", slug)
    version = VARIANTS["cyclorama-dawn"]["version"]

    schemes = []
    theme_entries = []
    files = [{"label": "All schemes (schemes.json)", "path": f"apps/{slug}/schemes.json"}]

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        scheme = _wt_scheme(v)
        schemes.append(scheme)
        scheme_text = _write_json(os.path.join(app_dir, f"{vid}.json"), scheme)
        ps_text = _psreadline_script(v)
        _write_text(os.path.join(app_dir, "psreadline", f"{vid}.ps1"), ps_text)

        files.append({"label": f"{v['name']} scheme ({vid}.json)", "path": f"apps/{slug}/{vid}.json"})
        files.append({"label": f"{v['name']} PSReadLine (psreadline/{vid}.ps1)", "path": f"apps/{slug}/psreadline/{vid}.ps1"})

        theme_entries.append({
            "id": v["id"],
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": v["summary"],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{vid}.json",
            "copyLang": "json",
            "copyLabel": f"Copy {v['name']} Windows Terminal JSON",
            "copySnippet": scheme_text.rstrip("\n"),
            "swatches": _swatches(v),
        })

    _write_json(os.path.join(app_dir, "schemes.json"), schemes)
    _render_previews(app_name, slug, shell_cmd="pwsh -NoLogo")

    install_steps = [
        "Open Windows Terminal Settings (Ctrl+,) and select Open JSON file to open settings.json.",
        "Paste one variant from cyclorama-dawn.json (or all three from schemes.json) into the \"schemes\" array, then set \"colorScheme\": \"Cyclorama Dawn\" in profiles.defaults.",
        "Optional: dot-source psreadline/cyclorama-dawn.ps1 in your PowerShell $PROFILE (PSReadLine 2.2+) for matching command-line syntax highlighting.",
    ]

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": "Terminals",
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": version,
        "primaryFile": f"apps/{slug}/schemes.json",
        "files": files,
        "themes": theme_entries,
    })

    readme = f"""# {BRAND_NAME} for Windows Terminal & PowerShell

Three **{BRAND_NAME} v{version} (Steel & Beacon Orange)** color schemes for **[Windows Terminal]({homepage})** plus matching **PowerShell PSReadLine** syntax highlighting scripts, built from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}).

## Variants

{_variant_table({vid: f"[`{vid}.json`]({vid}.json)" for vid in VARIANT_ORDER}, extra_col=("PSReadLine", {vid: f"[`psreadline/{vid}.ps1`](psreadline/{vid}.ps1)" for vid in VARIANT_ORDER}))}

All three schemes are also bundled together in [`schemes.json`](schemes.json).

## Install

1. Open Windows Terminal **Settings** (`Ctrl+,`) and click **Open JSON file** to edit `settings.json`.
2. Add the desired scheme object from `cyclorama-dawn.json` (or all three from `schemes.json`) into the `"schemes": [ ... ]` array, then activate it under `"profiles": {{ "defaults": {{ "colorScheme": "Cyclorama Dawn" }} }}`.
3. Optional: add matching PowerShell syntax coloring (requires PSReadLine 2.2+ / PowerShell 7+) by dot-sourcing the matching `.ps1` file in your `$PROFILE`:

```powershell
. "$HOME\\rfs-themes\\apps\\windows-terminal\\psreadline\\cyclorama-dawn.ps1"
```

## Previews

{_previews_markdown(app_name)}

## Palette Mapping

{_ansi_markdown_table()}

## Regenerating

```sh
python tools/build_terminals.py
```
"""
    _write_text(os.path.join(app_dir, "README.md"), readme)
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# ---------------------------------------------------------------------------
# 2. WezTerm
# ---------------------------------------------------------------------------

def _wezterm_toml(v: dict) -> str:
    ui = v["ui"]
    colors = ansi_list(v)
    normal = ", ".join(f'"{c}"' for c in colors[:8])
    brights = ", ".join(f'"{c}"' for c in colors[8:])
    mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
    return (
        f"# {v['name']} ({v['lx']} {mode_lbl} · {v['accentRole']}) — WezTerm Color Scheme\n"
        f"# Brand: {BRAND_NAME} v{v['version']} | Author: {AUTHOR}\n\n"
        f"[metadata]\n"
        f'name = "{v["name"]}"\n'
        f'author = "{AUTHOR}"\n'
        f'origin_url = "{REPO_URL}"\n\n'
        f"[colors]\n"
        f'foreground = "{ui["text"]}"\n'
        f'background = "{ui["bg"]}"\n'
        f'cursor_bg = "{ui["cursor"]}"\n'
        f'cursor_fg = "{ui["cursor_text"]}"\n'
        f'cursor_border = "{ui["cursor"]}"\n'
        f'selection_fg = "{ui["text"]}"\n'
        f'selection_bg = "{ui["selection_active"]}"\n'
        f'scrollbar_thumb = "{ui["border_strong"]}"\n'
        f'split = "{ui["border"]}"\n'
        f"ansi = [{normal}]\n"
        f"brights = [{brights}]\n\n"
        f"[colors.tab_bar]\n"
        f'background = "{ui["rail"]}"\n'
        f'inactive_tab_edge = "{ui["border"]}"\n\n'
        f"[colors.tab_bar.active_tab]\n"
        f'bg_color = "{ui["accent_fill"]}"\n'
        f'fg_color = "{ui["on_accent"]}"\n'
        f'intensity = "Bold"\n'
        f'underline = "None"\n'
        f"italic = false\n"
        f"strikethrough = false\n\n"
        f"[colors.tab_bar.inactive_tab]\n"
        f'bg_color = "{ui["surface"]}"\n'
        f'fg_color = "{ui["mute"]}"\n\n'
        f"[colors.tab_bar.inactive_tab_hover]\n"
        f'bg_color = "{ui["raised"]}"\n'
        f'fg_color = "{ui["text"]}"\n'
        f"italic = false\n\n"
        f"[colors.tab_bar.new_tab]\n"
        f'bg_color = "{ui["rail"]}"\n'
        f'fg_color = "{ui["mute"]}"\n\n'
        f"[colors.tab_bar.new_tab_hover]\n"
        f'bg_color = "{ui["raised"]}"\n'
        f'fg_color = "{ui["accent"]}"\n'
        f"italic = false\n"
    )


def build_wezterm() -> dict:
    slug = "wezterm"
    app_name = "WezTerm"
    homepage = "https://wezterm.org/"
    fmt = "WezTerm .toml Color Scheme"
    install = "Copy .toml into ~/.config/wezterm/colors/ and set config.color_scheme"
    app_dir = os.path.join(ROOT, "apps", slug)
    version = VARIANTS["cyclorama-dawn"]["version"]

    files = []
    theme_entries = []
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        toml_text = _wezterm_toml(v)
        _write_text(os.path.join(app_dir, f"{vid}.toml"), toml_text)
        files.append({"label": f"{v['name']} ({vid}.toml)", "path": f"apps/{slug}/{vid}.toml"})
        theme_entries.append({
            "id": v["id"],
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": v["summary"],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{vid}.toml",
            "copyLang": "toml",
            "copyLabel": f"Copy {v['name']} WezTerm TOML",
            "copySnippet": toml_text.rstrip("\n"),
            "swatches": _swatches(v),
        })

    _render_previews(app_name, slug, shell_cmd="wezterm ls-fonts")

    install_steps = [
        "Copy cyclorama-dawn.toml, cyclorama-steel.toml, and cyclorama-day.toml into ~/.config/wezterm/colors/ (Windows: %USERPROFILE%\\.config\\wezterm\\colors\\).",
        "Set config.color_scheme = \"Cyclorama Dawn\" (or \"Cyclorama Steel\" / \"Cyclorama Day\") in your wezterm.lua.",
        "Reload WezTerm (config auto-reloads on save).",
    ]

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": "Terminals",
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": version,
        "primaryFile": f"apps/{slug}/cyclorama-dawn.toml",
        "files": files,
        "themes": theme_entries,
    })

    readme = f"""# {BRAND_NAME} for WezTerm

Three **{BRAND_NAME} v{version} (Steel & Beacon Orange)** color schemes for **[WezTerm]({homepage})**, calibrated from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}).

## Variants

{_variant_table({vid: f"[`{vid}.toml`]({vid}.toml)" for vid in VARIANT_ORDER})}

## Install

1. Copy the `.toml` file(s) into `~/.config/wezterm/colors/` (on Windows: `%USERPROFILE%\\.config\\wezterm\\colors\\`).
2. Select the scheme in `~/.wezterm.lua` (or `~/.config/wezterm/wezterm.lua`):

```lua
local wezterm = require("wezterm")
local config = wezterm.config_builder()
config.color_scheme = "Cyclorama Dawn" -- or "Cyclorama Steel", "Cyclorama Day"
return config
```

## Previews

{_previews_markdown(app_name)}

## Palette Mapping

{_ansi_markdown_table()}

## Regenerating

```sh
python tools/build_terminals.py
```
"""
    _write_text(os.path.join(app_dir, "README.md"), readme)
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# ---------------------------------------------------------------------------
# 3. Alacritty (v0.13+ TOML)
# ---------------------------------------------------------------------------

def _alacritty_toml(v: dict) -> str:
    ui = v["ui"]
    a = v["ansi"]
    mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
    return (
        f"# {v['name']} ({v['lx']} {mode_lbl} · {v['accentRole']}) — Alacritty v0.13+ Theme\n"
        f"# Brand: {BRAND_NAME} v{v['version']} | Author: {AUTHOR}\n"
        f"# Source: {REPO_URL}\n\n"
        f"[colors.primary]\n"
        f'background = "{ui["bg"]}"\n'
        f'foreground = "{ui["text"]}"\n'
        f'dim_foreground = "{ui["mute"]}"\n'
        f'bright_foreground = "{ui["text"]}"\n\n'
        f"[colors.cursor]\n"
        f'text = "{ui["cursor_text"]}"\n'
        f'cursor = "{ui["cursor"]}"\n\n'
        f"[colors.vi_mode_cursor]\n"
        f'text = "{ui["cursor_text"]}"\n'
        f'cursor = "{ui["secondary"]}"\n\n'
        f"[colors.selection]\n"
        f'text = "{ui["text"]}"\n'
        f'background = "{ui["selection_active"]}"\n\n'
        f"[colors.search.matches]\n"
        f'foreground = "{ui["text"]}"\n'
        f'background = "{ui["find_match"]}"\n\n'
        f"[colors.search.focused_match]\n"
        f'foreground = "{ui["on_accent"]}"\n'
        f'background = "{ui["accent_fill"]}"\n\n'
        f"[colors.hints.start]\n"
        f'foreground = "{ui["on_accent"]}"\n'
        f'background = "{ui["accent_fill"]}"\n\n'
        f"[colors.hints.end]\n"
        f'foreground = "{ui["on_accent"]}"\n'
        f'background = "{ui["secondary_fill"]}"\n\n'
        f"[colors.normal]\n"
        f'black = "{a["black"]}"\n'
        f'red = "{a["red"]}"\n'
        f'green = "{a["green"]}"\n'
        f'yellow = "{a["yellow"]}"\n'
        f'blue = "{a["blue"]}"\n'
        f'magenta = "{a["magenta"]}"\n'
        f'cyan = "{a["cyan"]}"\n'
        f'white = "{a["white"]}"\n\n'
        f"[colors.bright]\n"
        f'black = "{a["brightBlack"]}"\n'
        f'red = "{a["brightRed"]}"\n'
        f'green = "{a["brightGreen"]}"\n'
        f'yellow = "{a["brightYellow"]}"\n'
        f'blue = "{a["brightBlue"]}"\n'
        f'magenta = "{a["brightMagenta"]}"\n'
        f'cyan = "{a["brightCyan"]}"\n'
        f'white = "{a["brightWhite"]}"\n'
    )


def build_alacritty() -> dict:
    slug = "alacritty"
    app_name = "Alacritty"
    homepage = "https://alacritty.org/"
    fmt = "Alacritty v0.13+ .toml"
    install = "Import .toml under [general].import in alacritty.toml"
    app_dir = os.path.join(ROOT, "apps", slug)
    version = VARIANTS["cyclorama-dawn"]["version"]

    files = []
    theme_entries = []
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        toml_text = _alacritty_toml(v)
        _write_text(os.path.join(app_dir, f"{vid}.toml"), toml_text)
        files.append({"label": f"{v['name']} ({vid}.toml)", "path": f"apps/{slug}/{vid}.toml"})
        theme_entries.append({
            "id": v["id"],
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": v["summary"],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{vid}.toml",
            "copyLang": "toml",
            "copyLabel": f"Copy {v['name']} Alacritty TOML",
            "copySnippet": toml_text.rstrip("\n"),
            "swatches": _swatches(v),
        })

    _render_previews(app_name, slug, shell_cmd="alacritty --print-events")

    install_steps = [
        "Copy cyclorama-dawn.toml (or steel/day) into ~/.config/alacritty/themes/ (Windows: %APPDATA%\\alacritty\\themes\\).",
        "Import the theme in alacritty.toml under [general] with import = [\"~/.config/alacritty/themes/cyclorama-dawn.toml\"].",
        "Save alacritty.toml — Alacritty reloads colors live.",
    ]

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": "Terminals",
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": version,
        "primaryFile": f"apps/{slug}/cyclorama-dawn.toml",
        "files": files,
        "themes": theme_entries,
    })

    readme = f"""# {BRAND_NAME} for Alacritty

Three **{BRAND_NAME} v{version} (Steel & Beacon Orange)** TOML themes for **[Alacritty]({homepage})** (v0.13+), calibrated from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}).

## Variants

{_variant_table({vid: f"[`{vid}.toml`]({vid}.toml)" for vid in VARIANT_ORDER})}

## Install

1. Copy the desired `.toml` file into `~/.config/alacritty/themes/` (on Windows: `%APPDATA%\\alacritty\\themes\\`).
2. Import it in `alacritty.toml`:

```toml
[general]
import = ["~/.config/alacritty/themes/cyclorama-dawn.toml"]
```

## Previews

{_previews_markdown(app_name)}

## Palette Mapping

{_ansi_markdown_table()}

## Regenerating

```sh
python tools/build_terminals.py
```
"""
    _write_text(os.path.join(app_dir, "README.md"), readme)
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# ---------------------------------------------------------------------------
# 4. Ghostty
# ---------------------------------------------------------------------------

def _ghostty_theme(v: dict) -> str:
    ui = v["ui"]
    colors = ansi_list(v)
    mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
    lines = [
        f"# {v['name']} ({v['lx']} {mode_lbl} · {v['accentRole']}) — Ghostty Theme",
        f"# Brand: {BRAND_NAME} v{v['version']} | Author: {AUTHOR}",
        f"# Source: {REPO_URL}",
        "",
    ]
    for idx, hx in enumerate(colors):
        lines.append(f"palette = {idx}={hx}")
    lines.extend([
        f"background = {ui['bg']}",
        f"foreground = {ui['text']}",
        f"cursor-color = {ui['cursor']}",
        f"cursor-text = {ui['cursor_text']}",
        f"selection-background = {ui['selection_active']}",
        f"selection-foreground = {ui['text']}",
        "",
    ])
    return "\n".join(lines)


def build_ghostty() -> dict:
    slug = "ghostty"
    app_name = "Ghostty"
    homepage = "https://ghostty.org/"
    fmt = "Ghostty Theme File"
    install = "Copy theme into ~/.config/ghostty/themes/ and set theme = cyclorama-dawn"
    app_dir = os.path.join(ROOT, "apps", slug)
    version = VARIANTS["cyclorama-dawn"]["version"]

    files = []
    theme_entries = []
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        theme_text = _ghostty_theme(v)
        _write_text(os.path.join(app_dir, vid), theme_text)
        files.append({"label": f"{v['name']} ({vid})", "path": f"apps/{slug}/{vid}"})
        theme_entries.append({
            "id": v["id"],
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": v["summary"],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{vid}",
            "copyLang": "conf",
            "copyLabel": f"Copy {v['name']} Ghostty theme",
            "copySnippet": theme_text.rstrip("\n"),
            "swatches": _swatches(v),
        })

    _render_previews(app_name, slug, shell_cmd="ghostty +list-themes")

    install_steps = [
        "Copy cyclorama-dawn, cyclorama-steel, and cyclorama-day into ~/.config/ghostty/themes/.",
        "Set theme = cyclorama-dawn (or theme = dark:cyclorama-dawn,light:cyclorama-day) in ~/.config/ghostty/config.",
        "Reload Ghostty configuration (Cmd+Shift+, on macOS or Ctrl+Shift+, on Linux).",
    ]

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": "Terminals",
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": version,
        "primaryFile": f"apps/{slug}/cyclorama-dawn",
        "files": files,
        "themes": theme_entries,
    })

    readme = f"""# {BRAND_NAME} for Ghostty

Three **{BRAND_NAME} v{version} (Steel & Beacon Orange)** native theme files for **[Ghostty]({homepage})**, calibrated from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}).

## Variants

{_variant_table({vid: f"[`{vid}`]({vid})" for vid in VARIANT_ORDER})}

## Install

1. Copy the theme file(s) into `~/.config/ghostty/themes/`.
2. Enable a theme in `~/.config/ghostty/config`:

```conf
theme = cyclorama-dawn
# Or pair dark & light automatically:
# theme = dark:cyclorama-dawn,light:cyclorama-day
```

3. Verify Ghostty recognizes the themes with `ghostty +list-themes`.

## Previews

{_previews_markdown(app_name)}

## Palette Mapping

{_ansi_markdown_table()}

## Regenerating

```sh
python tools/build_terminals.py
```
"""
    _write_text(os.path.join(app_dir, "README.md"), readme)
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# ---------------------------------------------------------------------------
# 5. Kitty
# ---------------------------------------------------------------------------

def _kitty_conf(v: dict) -> str:
    ui = v["ui"]
    colors = ansi_list(v)
    mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
    lines = [
        f"## name: {v['name']}",
        f"## author: {AUTHOR}",
        "## license: MIT",
        f"## upstream: {REPO_URL}",
        f"## blurb: {v['summary']} ({v['lx']} {mode_lbl} · {BRAND_NAME} v{v['version']})",
        "",
        "# Basic colors",
        f"foreground              {ui['text']}",
        f"background              {ui['bg']}",
        f"selection_foreground    {ui['text']}",
        f"selection_background    {ui['selection_active']}",
        "",
        "# Cursor & URLs",
        f"cursor                  {ui['cursor']}",
        f"cursor_text_color       {ui['cursor_text']}",
        f"url_color               {ui['accent']}",
        "",
        "# Window borders",
        f"active_border_color     {ui['accent']}",
        f"inactive_border_color   {ui['border']}",
        f"bell_border_color       {ui['warning']}",
        "",
        "# Tab bar",
        f"active_tab_foreground   {ui['on_accent']}",
        f"active_tab_background   {ui['accent_fill']}",
        f"inactive_tab_foreground {ui['mute']}",
        f"inactive_tab_background {ui['surface']}",
        f"tab_bar_background      {ui['rail']}",
        "",
        "# Marks",
        f"mark1_foreground        {ui['on_accent']}",
        f"mark1_background        {ui['accent_fill']}",
        f"mark2_foreground        {ui['on_accent']}",
        f"mark2_background        {ui['secondary_fill']}",
        f"mark3_foreground        {ui['on_accent']}",
        f"mark3_background        {ui['fault_fill']}",
        "",
        "# ANSI 0-15 color table",
    ]
    for idx, hx in enumerate(colors):
        lines.append(f"color{idx:<18} {hx}")
    lines.append("")
    return "\n".join(lines)


def build_kitty() -> dict:
    slug = "kitty"
    app_name = "Kitty"
    homepage = "https://sw.kovidgoyal.net/kitty/"
    fmt = "Kitty .conf Theme"
    install = "Include .conf from ~/.config/kitty/themes/ in kitty.conf"
    app_dir = os.path.join(ROOT, "apps", slug)
    version = VARIANTS["cyclorama-dawn"]["version"]

    files = []
    theme_entries = []
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        conf_text = _kitty_conf(v)
        _write_text(os.path.join(app_dir, f"{vid}.conf"), conf_text)
        files.append({"label": f"{v['name']} ({vid}.conf)", "path": f"apps/{slug}/{vid}.conf"})
        theme_entries.append({
            "id": v["id"],
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": v["summary"],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{vid}.conf",
            "copyLang": "conf",
            "copyLabel": f"Copy {v['name']} Kitty .conf",
            "copySnippet": conf_text.rstrip("\n"),
            "swatches": _swatches(v),
        })

    _render_previews(app_name, slug, shell_cmd="kitten themes")

    install_steps = [
        "Copy cyclorama-dawn.conf, cyclorama-steel.conf, and cyclorama-day.conf into ~/.config/kitty/themes/.",
        "Add `include themes/cyclorama-dawn.conf` to ~/.config/kitty/kitty.conf.",
        "Reload Kitty config (Ctrl+Shift+F5) or switch interactively with `kitten themes`.",
    ]

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": "Terminals",
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": version,
        "primaryFile": f"apps/{slug}/cyclorama-dawn.conf",
        "files": files,
        "themes": theme_entries,
    })

    readme = f"""# {BRAND_NAME} for Kitty

Three **{BRAND_NAME} v{version} (Steel & Beacon Orange)** configuration themes for **[Kitty]({homepage})**, calibrated from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}).

## Variants

{_variant_table({vid: f"[`{vid}.conf`]({vid}.conf)" for vid in VARIANT_ORDER})}

## Install

1. Copy the `.conf` file(s) into `~/.config/kitty/themes/`.
2. Include your chosen variant in `~/.config/kitty/kitty.conf`:

```conf
include themes/cyclorama-dawn.conf
```

3. Reload Kitty (`Ctrl+Shift+F5`) or browse installed themes with `kitten themes`.

## Previews

{_previews_markdown(app_name)}

## Palette Mapping

{_ansi_markdown_table()}

## Regenerating

```sh
python tools/build_terminals.py
```
"""
    _write_text(os.path.join(app_dir, "README.md"), readme)
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# ---------------------------------------------------------------------------
# Entrypoint & self-verification
# ---------------------------------------------------------------------------

def build() -> list[dict]:
    """Generate all 5 terminal app ports and return their apps/manifest.json entries."""
    return [
        build_windows_terminal(),
        build_wezterm(),
        build_alacritty(),
        build_ghostty(),
        build_kitty(),
    ]


def _verify_generated(entries: list[dict]) -> None:
    json_count = 0
    toml_count = 0
    svg_count = 0

    for entry in entries:
        slug = entry["slug"]
        app_dir = os.path.join(ROOT, "apps", slug)
        for root_dir, _, filenames in os.walk(app_dir):
            for fn in sorted(filenames):
                fp = os.path.join(root_dir, fn)
                if fn.endswith(".json"):
                    with open(fp, encoding="utf-8") as fh:
                        json.loads(fh.read())
                    json_count += 1
                elif fn.endswith(".toml"):
                    with open(fp, encoding="utf-8") as fh:
                        tomllib.loads(fh.read())
                    toml_count += 1
                elif fn.endswith(".svg"):
                    svg_count += 1
                    docs_svg = os.path.join(ROOT, "docs", "assets", "previews", slug, fn)
                    if not os.path.exists(docs_svg):
                        raise AssertionError(f"missing docs preview mirror: {docs_svg}")

    print(
        f"[ok] built {len(entries)} terminal ports "
        f"({json_count} JSON, {toml_count} TOML, {svg_count} preview pairs verified)"
    )


if __name__ == "__main__":
    manifest_entries = build()
    _verify_generated(manifest_entries)
