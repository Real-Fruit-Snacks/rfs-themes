#!/usr/bin/env python3
"""Generate 3 Cyclorama Dawn v2.1.0 Terminal & Console ports for rfs-themes.

Builds 3 self-contained app ports (9 total variants across Dawn, Steel, and Day)
plus mirrored SVG previews in apps/<slug>/previews/ and docs/assets/previews/<slug>/:
  1. apps/git-bash/        — Git Bash (Mintty .minttyrc) + Native Git CLI (.gitconfig)
  2. apps/qterminal/       — QTerminal / QTermWidget6 (.colorscheme INI)
  3. apps/windows-console/ — Windows Console Host / conhost (.reg HKCU\\Console + restore-defaults.reg)

Zero external dependencies (Python 3.11+ standard library only).
Zero hardcoded hex literals — every color derives from tools/rfs_palette.py.
Deterministic UTF-8 LF output across Windows and Linux CI.
"""
from __future__ import annotations

import configparser
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from rfs_palette import (  # noqa: E402
    AUTHOR,
    BRAND_NAME,
    GALLERY_URL,
    REPO_URL,
    VARIANT_ORDER,
    VARIANTS,
    contrast,
    hex_to_rgb,
    rgb_to_hex,
)
from svg_previews import (  # noqa: E402
    render_terminal_preview,
    write_preview_pair,
)

BRAND_REPO_URL = "https://github.com/Real-Fruit-Snacks/rfs-brand"

# Official Windows 10/11 Campbell default console palette (RGB tuples in ColorTable00..15 order)
CAMPBELL_RGB: tuple[tuple[int, int, int], ...] = (
    (12, 12, 12),     # 00 Black
    (0, 55, 218),     # 01 DarkBlue
    (19, 161, 14),    # 02 DarkGreen
    (58, 150, 221),   # 03 DarkCyan
    (197, 15, 31),    # 04 DarkRed
    (136, 23, 152),   # 05 DarkMagenta
    (193, 156, 0),    # 06 DarkYellow
    (204, 204, 204),  # 07 Gray
    (118, 118, 118),  # 08 DarkGray
    (59, 120, 255),   # 09 Blue
    (22, 198, 12),    # 10 Green
    (97, 214, 214),   # 11 Cyan
    (231, 72, 86),    # 12 Red
    (180, 0, 158),    # 13 Magenta
    (249, 241, 165),  # 14 Yellow
    (242, 242, 242),  # 15 White
)


# ---------------------------------------------------------------------------
# Shared IO & Manifest Helpers
# ---------------------------------------------------------------------------

def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _write_json(path: str, data: object) -> str:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    _write_text(path, text)
    return text


def _rgb_decimal(hx: str) -> str:
    r, g, b = hex_to_rgb(hx)
    return f"{r},{g},{b}"


def _rgb_to_colorref_dword(r: int, g: int, b: int) -> str:
    """Format RGB tuple as Windows COLORREF registry dword:00bbggrr."""
    return f"dword:00{b:02x}{g:02x}{r:02x}"


def _hex_to_colorref_dword(hx: str) -> str:
    r, g, b = hex_to_rgb(hx)
    return _rgb_to_colorref_dword(r, g, b)


def _terminal_swatches(v: dict) -> list[dict[str, str]]:
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
    *,
    slug: str,
    name: str,
    category: str,
    homepage: str,
    fmt: str,
    install: str,
    summaries: dict[str, str] | None = None,
) -> dict:
    return {
        "slug": slug,
        "name": name,
        "category": category,
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
                "summary": summaries[vid] if summaries else VARIANTS[vid]["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
            }
            for vid in VARIANT_ORDER
        ],
        "path": f"apps/{slug}",
        "data": f"apps/{slug}/themes.json",
    }


def _md_file_link(rel_path: str) -> str:
    return f"[`{rel_path}`]({quote(rel_path, safe='/')})"


def _ansi_markdown_table() -> str:
    dawn = VARIANTS["cyclorama-dawn"]
    steel = VARIANTS["cyclorama-steel"]
    day = VARIANTS["cyclorama-day"]
    rows = [
        (
            "Background / Foreground",
            f"`{dawn['ui']['bg']}` / `{dawn['ui']['text']}`",
            f"`{steel['ui']['bg']}` / `{steel['ui']['text']}`",
            f"`{day['ui']['bg']}` / `{day['ui']['text']}`",
        ),
        (
            "Cursor / Cursor Text",
            f"`{dawn['ui']['cursor']}` / `{dawn['ui']['cursor_text']}`",
            f"`{steel['ui']['cursor']}` / `{steel['ui']['cursor_text']}`",
            f"`{day['ui']['cursor']}` / `{day['ui']['cursor_text']}`",
        ),
        (
            "Accent / Secondary",
            f"`{dawn['ui']['accent']}` / `{dawn['ui']['secondary']}`",
            f"`{steel['ui']['accent']}` / `{steel['ui']['secondary']}`",
            f"`{day['ui']['accent']}` / `{day['ui']['secondary']}`",
        ),
        (
            "ANSI Red / Green / Yellow",
            f"`{dawn['ansi']['red']}` / `{dawn['ansi']['green']}` / `{dawn['ansi']['yellow']}`",
            f"`{steel['ansi']['red']}` / `{steel['ansi']['green']}` / `{steel['ansi']['yellow']}`",
            f"`{day['ansi']['red']}` / `{day['ansi']['green']}` / `{day['ansi']['yellow']}`",
        ),
        (
            "ANSI Blue / Magenta / Cyan",
            f"`{dawn['ansi']['blue']}` / `{dawn['ansi']['magenta']}` / `{dawn['ansi']['cyan']}`",
            f"`{steel['ansi']['blue']}` / `{steel['ansi']['magenta']}` / `{steel['ansi']['cyan']}`",
            f"`{day['ansi']['blue']}` / `{day['ansi']['magenta']}` / `{day['ansi']['cyan']}`",
        ),
    ]
    lines = [
        "| Role | Cyclorama Dawn (`LX 263`) | Cyclorama Steel (`LX 263`) | Cyclorama Day (`LX 512`) |",
        "|---|---|---|---|",
    ]
    for role, c1, c2, c3 in rows:
        lines.append(f"| {role} | {c1} | {c2} | {c3} |")
    return "\n".join(lines)


def _variant_table(
    file_links: dict[str, str],
    extra_col: tuple[str, dict[str, str]] | None = None,
) -> str:
    if extra_col:
        extra_title, extra_map = extra_col
        lines = [
            f"| Variant | Lighting | Mode | Accent Role | Theme File | {extra_title} |",
            "|---|---|---|---|---|---|",
        ]
        for vid in VARIANT_ORDER:
            v = VARIANTS[vid]
            lines.append(
                f"| **{v['name']}** | `{v['lx']}` | `{v['mode']}` | {v['accentRole']} "
                f"| {file_links[vid]} | {extra_map[vid]} |"
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


def _previews_markdown(app_name: str, summaries: dict[str, str] | None = None) -> str:
    blocks = []
    for idx, vid in enumerate(VARIANT_ORDER, start=1):
        v = VARIANTS[vid]
        mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
        desc = summaries[vid] if summaries else v["summary"]
        blocks.append(
            f"### {idx}. {v['name']} (`{v['lx']} {mode_lbl} · {v['accentRole']}`)\n\n"
            f"{desc}\n\n"
            f"![{v['name']} {app_name} preview](previews/{vid}.svg)"
        )
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# 1. Git Bash (Mintty) + Native Git CLI (apps/git-bash/)
# ---------------------------------------------------------------------------

def _mintty_rc(v: dict) -> str:
    ui = v["ui"]
    a = v["ansi"]
    mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
    lines = [
        f"# {v['name']} ({v['lx']} {mode_lbl} · {v['accentRole']}) — Git Bash (Mintty) Theme",
        f"# Author: {AUTHOR} | Brand: {BRAND_NAME} v{v['version']}",
        f"# Source: {REPO_URL}",
        "",
        f"ForegroundColour={_rgb_decimal(ui['text'])}",
        f"BackgroundColour={_rgb_decimal(ui['bg'])}",
        f"CursorColour={_rgb_decimal(ui['cursor'])}",
        f"Black={_rgb_decimal(a['black'])}",
        f"BoldBlack={_rgb_decimal(a['brightBlack'])}",
        f"Red={_rgb_decimal(a['red'])}",
        f"BoldRed={_rgb_decimal(a['brightRed'])}",
        f"Green={_rgb_decimal(a['green'])}",
        f"BoldGreen={_rgb_decimal(a['brightGreen'])}",
        f"Yellow={_rgb_decimal(a['yellow'])}",
        f"BoldYellow={_rgb_decimal(a['brightYellow'])}",
        f"Blue={_rgb_decimal(a['blue'])}",
        f"BoldBlue={_rgb_decimal(a['brightBlue'])}",
        f"Magenta={_rgb_decimal(a['magenta'])}",
        f"BoldMagenta={_rgb_decimal(a['brightMagenta'])}",
        f"Cyan={_rgb_decimal(a['cyan'])}",
        f"BoldCyan={_rgb_decimal(a['brightCyan'])}",
        f"White={_rgb_decimal(a['white'])}",
        f"BoldWhite={_rgb_decimal(a['brightWhite'])}",
        "",
    ]
    return "\n".join(lines)


def _git_colors_config(v: dict) -> str:
    ui = v["ui"]
    syn = v["syntax"]
    mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
    lines = [
        f"# {v['name']} ({v['lx']} {mode_lbl} · {v['accentRole']}) — Native Git CLI Truecolor Theme",
        f"# Author: {AUTHOR} | Brand: {BRAND_NAME} v{v['version']}",
        f"# Source: {REPO_URL}",
        "# Include from ~/.gitconfig via [include] path = ...",
        "",
        "[color]",
        "\tui = auto",
        "",
        '[color "diff"]',
        f'\tmeta = "{ui["secondary"]} bold"',
        f'\tfrag = "{ui["cyan"]} bold"',
        f'\told = "{syn["diff_del"]}"',
        f'\tnew = "{syn["diff_add"]}"',
        f'\tcontext = "{ui["mute"]}"',
        f'\twhitespace = "{ui["on_accent"]} {ui["fault_fill"]}"',
        f'\tfunc = "{ui["accent"]}"',
        "",
        '[color "status"]',
        f'\theader = "{ui["mute"]}"',
        f'\tadded = "{syn["diff_add"]} bold"',
        f'\tchanged = "{ui["warning"]} bold"',
        f'\tuntracked = "{ui["accent"]}"',
        f'\tbranch = "{ui["secondary"]} bold"',
        f'\tnobranch = "{ui["fault"]} bold"',
        "",
        '[color "branch"]',
        f'\tcurrent = "{ui["accent"]} bold"',
        f'\tlocal = "{ui["text"]}"',
        f'\tremote = "{ui["secondary"]}"',
        f'\tupstream = "{ui["signal"]}"',
        "",
        '[color "grep"]',
        f'\tfilename = "{ui["secondary"]} bold"',
        f'\tlinenumber = "{ui["subtle"]}"',
        f'\tmatch = "{ui["on_accent"]} {ui["accent_fill"]} bold"',
        f'\tseparator = "{ui["mute"]}"',
        "",
    ]
    return "\n".join(lines)


def build_git_bash() -> dict:
    slug = "git-bash"
    app_name = "Git Bash (Mintty)"
    category = "Terminals"
    homepage = "https://gitforwindows.org/"
    fmt = "Mintty .minttyrc + Git .gitconfig"
    install = "Copy .minttyrc to ~/.mintty/themes/ + include git-colors-*.gitconfig in ~/.gitconfig"
    app_dir = os.path.join(ROOT, "apps", slug)
    version = VARIANTS["cyclorama-dawn"]["version"]

    files: list[dict[str, str]] = []
    theme_entries: list[dict] = []
    mintty_links: dict[str, str] = {}
    git_links: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        short = v["short"].lower()
        rc_name = f"{vid}.minttyrc"
        git_name = f"git-colors-{short}.gitconfig"

        rc_text = _mintty_rc(v)
        git_text = _git_colors_config(v)
        _write_text(os.path.join(app_dir, rc_name), rc_text)
        _write_text(os.path.join(app_dir, git_name), git_text)

        files.append({"label": f"{v['name']} Mintty ({rc_name})", "path": f"apps/{slug}/{rc_name}"})
        files.append({"label": f"{v['name']} Git CLI ({git_name})", "path": f"apps/{slug}/{git_name}"})
        mintty_links[vid] = _md_file_link(rc_name)
        git_links[vid] = _md_file_link(git_name)

        theme_entries.append({
            "id": v["id"],
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": v["summary"],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{rc_name}",
            "copyLang": "conf",
            "copyLabel": f"Copy {v['name']} Mintty .minttyrc",
            "copySnippet": rc_text.rstrip("\n"),
            "swatches": _terminal_swatches(v),
        })

        svg = render_terminal_preview(
            app_name,
            slug,
            v,
            shell_cmd="git status -sb && git diff --stat",
        )
        write_preview_pair(slug, vid, svg)

    install_steps = [
        "Copy `cyclorama-dawn.minttyrc` (or `steel` / `day`) into `~/.mintty/themes/` (or `C:\\Program Files\\Git\\usr\\share\\mintty\\themes\\`), then add `ThemeFile=cyclorama-dawn.minttyrc` to `~/.minttyrc` — or select it in **Mintty Options -> Looks -> Theme**.",
        "Alternatively, paste the `.minttyrc` color lines directly into `~/.minttyrc` and restart Git Bash.",
        "Enable matching truecolor `git diff`, `git status`, `git branch`, and `git grep` output by adding `[include]` -> `path = ~/rfs-themes/apps/git-bash/git-colors-dawn.gitconfig` to `~/.gitconfig`.",
    ]

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": version,
        "primaryFile": f"apps/{slug}/cyclorama-dawn.minttyrc",
        "files": files,
        "themes": theme_entries,
    })

    readme = f"""# {BRAND_NAME} for Git Bash (Mintty) & Git CLI

Three **{BRAND_NAME} v{version} (Steel & Beacon Orange)** themes for **[Git Bash / Mintty]({homepage})** (official decimal `R,G,B` `.minttyrc` format) paired with native truecolor **Git CLI** `.gitconfig` color profiles (`diff`, `status`, `branch`, `grep`), calibrated from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}).

## Variants

{_variant_table(mintty_links, extra_col=("Git CLI Colors", git_links))}

## Install

### 1. Git Bash (Mintty)

1. Copy the desired `.minttyrc` file into `~/.mintty/themes/` (or `C:\\Program Files\\Git\\usr\\share\\mintty\\themes\\`).
2. Add the theme selector to `~/.minttyrc` (or choose it via **Right-click title bar -> Options -> Looks -> Theme**):

```conf
ThemeFile=cyclorama-dawn.minttyrc
```

### 2. Native Git CLI Truecolor Output

Include the matching `git-colors-*.gitconfig` file in your `~/.gitconfig`:

```ini
[include]
    path = ~/rfs-themes/apps/git-bash/git-colors-dawn.gitconfig
```

Verify the loaded colors with:

```sh
git config --list --show-origin | grep '^.*color\\.'
```

## Previews

{_previews_markdown(app_name)}

## Palette Mapping

{_ansi_markdown_table()}

## Regenerating

```sh
python tools/build_extras_shells.py
```

Browse all ports in the [{BRAND_NAME} Theme Gallery]({GALLERY_URL}) or on [GitHub]({REPO_URL}).
"""
    _write_text(os.path.join(app_dir, "README.md"), readme)

    return _manifest_entry(
        slug=slug,
        name=app_name,
        category=category,
        homepage=homepage,
        fmt=fmt,
        install=install,
    )


# ---------------------------------------------------------------------------
# 2. QTerminal / QTermWidget6 (apps/qterminal/)
# ---------------------------------------------------------------------------

def _qterminal_colorscheme(v: dict) -> str:
    ui = v["ui"]
    a = v["ansi"]
    normal_ansi = (
        a["black"],
        a["red"],
        a["green"],
        a["yellow"],
        a["blue"],
        a["magenta"],
        a["cyan"],
        a["white"],
    )
    intense_ansi = (
        a["brightBlack"],
        a["brightRed"],
        a["brightGreen"],
        a["brightYellow"],
        a["brightBlue"],
        a["brightMagenta"],
        a["brightCyan"],
        a["brightWhite"],
    )
    mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
    lines = [
        f"# {v['name']} ({v['lx']} {mode_lbl} · {v['accentRole']}) — QTerminal / QTermWidget6 Color Scheme",
        f"# Author: {AUTHOR} | Brand: {BRAND_NAME} v{v['version']}",
        f"# Source: {REPO_URL}",
        "",
        "[General]",
        f"Description={v['name']}",
        "Opacity=1",
        "",
        "[Background]",
        "Bold=false",
        f"Color={_rgb_decimal(ui['bg'])}",
        "",
        "[BackgroundIntense]",
        "Bold=false",
        f"Color={_rgb_decimal(ui['surface'])}",
        "",
        "[Foreground]",
        "Bold=false",
        f"Color={_rgb_decimal(ui['text'])}",
        "",
        "[ForegroundIntense]",
        "Bold=false",
        f"Color={_rgb_decimal(ui['text'])}",
        "",
    ]
    for idx, (norm_hx, int_hx) in enumerate(zip(normal_ansi, intense_ansi)):
        lines.extend([
            f"[Color{idx}]",
            "Bold=false",
            f"Color={_rgb_decimal(norm_hx)}",
            "",
            f"[Color{idx}Intense]",
            "Bold=false",
            f"Color={_rgb_decimal(int_hx)}",
            "",
        ])
    return "\n".join(lines)


def build_qterminal() -> dict:
    slug = "qterminal"
    app_name = "QTerminal"
    category = "Terminals"
    homepage = "https://github.com/lxqt/qterminal"
    fmt = "QTermWidget .colorscheme INI"
    install = "Copy .colorscheme into ~/.local/share/qtermwidget6/color-schemes/ and select in Preferences"
    app_dir = os.path.join(ROOT, "apps", slug)
    version = VARIANTS["cyclorama-dawn"]["version"]

    files: list[dict[str, str]] = []
    theme_entries: list[dict] = []
    scheme_links: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        fname = f"{v['name']}.colorscheme"
        ini_text = _qterminal_colorscheme(v)
        _write_text(os.path.join(app_dir, fname), ini_text)

        files.append({"label": f"{v['name']} ({fname})", "path": f"apps/{slug}/{fname}"})
        scheme_links[vid] = _md_file_link(fname)

        theme_entries.append({
            "id": v["id"],
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": v["summary"],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{fname}",
            "copyLang": "ini",
            "copyLabel": f"Copy {v['name']} QTerminal .colorscheme",
            "copySnippet": ini_text.rstrip("\n"),
            "swatches": _terminal_swatches(v),
        })

        svg = render_terminal_preview(
            app_name,
            slug,
            v,
            shell_cmd="uname -a && ls --color=auto",
        )
        write_preview_pair(slug, vid, svg)

    install_steps = [
        "Copy `Cyclorama Dawn.colorscheme`, `Cyclorama Steel.colorscheme`, and `Cyclorama Day.colorscheme` into `~/.local/share/qtermwidget6/color-schemes/` (or `~/.local/share/qtermwidget5/color-schemes/` on Qt5 builds; system-wide: `/usr/share/qtermwidget6/color-schemes/`).",
        "Open QTerminal -> **File -> Preferences -> Appearance -> Color scheme** and select **Cyclorama Dawn** (or **Cyclorama Steel** / **Cyclorama Day**).",
        "Click **Apply** — compatible with QTerminal on WSLg, LXQt, and Konsole-format QTermWidget terminals.",
    ]

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": version,
        "primaryFile": f"apps/{slug}/Cyclorama Dawn.colorscheme",
        "files": files,
        "themes": theme_entries,
    })

    readme = f"""# {BRAND_NAME} for QTerminal

Three **{BRAND_NAME} v{version} (Steel & Beacon Orange)** QTermWidget / Konsole INI color schemes for **[QTerminal]({homepage})** (WSL / Linux / LXQt), calibrated from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}).

## Variants

{_variant_table(scheme_links)}

## Install

1. Copy the `.colorscheme` files into your user QTermWidget color-schemes directory:

```sh
mkdir -p ~/.local/share/qtermwidget6/color-schemes
cp "Cyclorama Dawn.colorscheme" "Cyclorama Steel.colorscheme" "Cyclorama Day.colorscheme" \\
   ~/.local/share/qtermwidget6/color-schemes/
```

*(For Qt5-based QTerminal builds, copy to `~/.local/share/qtermwidget5/color-schemes/` instead.)*

2. Open QTerminal -> **File -> Preferences -> Appearance -> Color scheme** and select **Cyclorama Dawn**, **Cyclorama Steel**, or **Cyclorama Day**.
3. Click **OK** or **Apply** to activate immediately.

## Previews

{_previews_markdown(app_name)}

## Palette Mapping

{_ansi_markdown_table()}

## Regenerating

```sh
python tools/build_extras_shells.py
```

Browse all ports in the [{BRAND_NAME} Theme Gallery]({GALLERY_URL}) or on [GitHub]({REPO_URL}).
"""
    _write_text(os.path.join(app_dir, "README.md"), readme)

    return _manifest_entry(
        slug=slug,
        name=app_name,
        category=category,
        homepage=homepage,
        fmt=fmt,
        install=install,
    )


# ---------------------------------------------------------------------------
# 3. Windows Console Host / cmd.exe / conhost (apps/windows-console/)
# ---------------------------------------------------------------------------

def _windows_console_table(v: dict) -> tuple[list[str], int, int]:
    """Return 16-slot Windows Console ColorTable (BGR order) + (ScreenColors, PopupColors).

    Windows Console ColorTable order (legacy CGA/VGA bit order, NOT ANSI order):
      00=Black(bg), 01=DarkBlue, 02=DarkGreen, 03=DarkCyan,
      04=DarkRed,   05=DarkMagenta, 06=DarkYellow, 07=Gray(fg),
      08=DarkGray,  09=Blue, 10=Green, 11=Cyan,
      12=Red,       13=Magenta, 14=Yellow, 15=White
    """
    ui = v["ui"]
    a = v["ansi"]
    table = [
        ui["bg"],             # 00 Black (default console background)
        a["blue"],            # 01 DarkBlue
        a["green"],           # 02 DarkGreen
        a["cyan"],            # 03 DarkCyan
        a["red"],             # 04 DarkRed
        a["magenta"],         # 05 DarkMagenta
        a["yellow"],          # 06 DarkYellow
        ui["text"],           # 07 Gray (default console foreground)
        a["brightBlack"],     # 08 DarkGray
        a["brightBlue"],      # 09 Blue
        a["brightGreen"],     # 10 Green
        a["brightCyan"],      # 11 Cyan
        a["brightRed"],       # 12 Red (Beacon Orange)
        a["brightMagenta"],   # 13 Magenta
        a["brightYellow"],    # 14 Yellow
        a["brightWhite"],     # 15 White
    ]
    screen_colors = 0x07  # bg=00 (ui["bg"]), fg=07 (ui["text"])
    # Distinct high-contrast popup palette (F7 history dialog):
    #   Dark mode : bg=15 (brightWhite) / fg=00 (dark bg) -> 0xF0 (~18.7:1)
    #   Light mode: bg=07 (dark text)   / fg=15 (white)   -> 0x7F (~19.0:1)
    popup_colors = 0xF0 if v["mode"] == "dark" else 0x7F
    return table, screen_colors, popup_colors


def _windows_console_reg_body(v: dict) -> str:
    table, screen_colors, popup_colors = _windows_console_table(v)
    mode_lbl = "Dark" if v["mode"] == "dark" else "Light"
    lines = [
        f"; {v['name']} ({v['lx']} {mode_lbl} · {v['accentRole']}) — Windows Console Host (HKCU\\Console)",
        f"; Author: {AUTHOR} | Brand: {BRAND_NAME} v{v['version']}",
        f"; Source: {REPO_URL}",
        "; Revert anytime by importing restore-defaults.reg (Windows 10/11 Campbell defaults).",
        "",
        "[HKEY_CURRENT_USER\\Console]",
    ]
    for idx, hx in enumerate(table):
        lines.append(f'"ColorTable{idx:02d}"={_hex_to_colorref_dword(hx)}')
    lines.append(f'"ScreenColors"=dword:{screen_colors:08x}')
    lines.append(f'"PopupColors"=dword:{popup_colors:08x}')
    lines.append("")
    return "\n".join(lines)


def _windows_console_reg_file(v: dict) -> str:
    return "Windows Registry Editor Version 5.00\n\n" + _windows_console_reg_body(v)


def _windows_console_restore_reg() -> str:
    lines = [
        "Windows Registry Editor Version 5.00",
        "",
        "; Official Windows 10/11 Campbell Default Palette — Windows Console Host (HKCU\\Console)",
        f"; Provided by {AUTHOR} ({REPO_URL}) for 1-click revert.",
        "",
        "[HKEY_CURRENT_USER\\Console]",
    ]
    for idx, (r, g, b) in enumerate(CAMPBELL_RGB):
        lines.append(f'"ColorTable{idx:02d}"={_rgb_to_colorref_dword(r, g, b)}')
    lines.append('"ScreenColors"=dword:00000007')
    lines.append('"PopupColors"=dword:000000f5')
    lines.append("")
    return "\n".join(lines)


def build_windows_console() -> dict:
    slug = "windows-console"
    app_name = "Windows Console"
    category = "Terminals"
    homepage = "https://learn.microsoft.com/en-us/windows/console/"
    fmt = "Windows Registry .reg (HKCU\\Console)"
    install = "Double-click cyclorama-dawn.reg (or run reg import) and open a new cmd.exe window"
    app_dir = os.path.join(ROOT, "apps", slug)
    version = VARIANTS["cyclorama-dawn"]["version"]

    files: list[dict[str, str]] = []
    theme_entries: list[dict] = []
    reg_links: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        fname = f"{vid}.reg"
        reg_text = _windows_console_reg_file(v)
        ini_snippet = _windows_console_reg_body(v).rstrip("\n")
        _write_text(os.path.join(app_dir, fname), reg_text)

        files.append({"label": f"{v['name']} Registry ({fname})", "path": f"apps/{slug}/{fname}"})
        reg_links[vid] = _md_file_link(fname)

        theme_entries.append({
            "id": v["id"],
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": v["summary"],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{fname}",
            "copyLang": "ini",
            "copyLabel": f"Copy {v['name']} HKCU\\Console Registry Values",
            "copySnippet": ini_snippet,
            "swatches": _terminal_swatches(v),
        })

        svg = render_terminal_preview(
            app_name,
            slug,
            v,
            shell_cmd="ver && dir /b",
        )
        write_preview_pair(slug, vid, svg)

    restore_name = "restore-defaults.reg"
    _write_text(os.path.join(app_dir, restore_name), _windows_console_restore_reg())
    files.append({"label": "Restore Windows Campbell Defaults (restore-defaults.reg)", "path": f"apps/{slug}/{restore_name}"})

    install_steps = [
        "Double-click `cyclorama-dawn.reg` (or `cyclorama-steel.reg` / `cyclorama-day.reg`) and confirm the Registry Editor prompt — or run `reg import apps\\windows-console\\cyclorama-dawn.reg` in `cmd.exe`.",
        "Open a new **Command Prompt** (`cmd.exe`) or legacy `conhost.exe` window to see the Cyclorama palette (`ScreenColors` maps slot `00` background and slot `07` foreground automatically).",
        "Revert to official Windows 10/11 Campbell defaults anytime in one click by importing `restore-defaults.reg`.",
    ]

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": version,
        "primaryFile": f"apps/{slug}/cyclorama-dawn.reg",
        "files": files,
        "themes": theme_entries,
    })

    dawn_tbl, _, _ = _windows_console_table(VARIANTS["cyclorama-dawn"])
    steel_tbl, _, _ = _windows_console_table(VARIANTS["cyclorama-steel"])
    day_tbl, _, _ = _windows_console_table(VARIANTS["cyclorama-day"])

    slot_names = (
        "00 Black (Screen BG)", "01 DarkBlue", "02 DarkGreen", "03 DarkCyan",
        "04 DarkRed", "05 DarkMagenta", "06 DarkYellow", "07 Gray (Screen FG)",
        "08 DarkGray", "09 Blue", "10 Green", "11 Cyan",
        "12 Red (Beacon)", "13 Magenta", "14 Yellow", "15 White",
    )
    table_rows = [
        "| Console Slot | Dawn (`COLORREF`) | Steel (`COLORREF`) | Day (`COLORREF`) |",
        "|---|---|---|---|",
    ]
    for idx, label in enumerate(slot_names):
        table_rows.append(
            f"| `{label}` "
            f"| `{dawn_tbl[idx]}` (`{_hex_to_colorref_dword(dawn_tbl[idx])}`) "
            f"| `{steel_tbl[idx]}` (`{_hex_to_colorref_dword(steel_tbl[idx])}`) "
            f"| `{day_tbl[idx]}` (`{_hex_to_colorref_dword(day_tbl[idx])}`) |"
        )
    slot_table_md = "\n".join(table_rows)

    readme = f"""# {BRAND_NAME} for Windows Console Host (`cmd.exe` / `conhost`)

Three **{BRAND_NAME} v{version} (Steel & Beacon Orange)** Windows Registry (`.reg`) themes targeting `HKEY_CURRENT_USER\\Console` for **[Windows Console Host]({homepage})** (`cmd.exe` / `conhost.exe`), plus a 1-click [`restore-defaults.reg`](restore-defaults.reg) revert file (official Windows 10/11 Campbell defaults), calibrated from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}).

## Variants

{_variant_table(reg_links)}

**1-Click Revert:** [`restore-defaults.reg`](restore-defaults.reg) restores official Windows 10/11 Campbell `ColorTable00..15`, `ScreenColors`, and `PopupColors`.

## Install

1. Double-click `cyclorama-dawn.reg` (or `cyclorama-steel.reg` / `cyclorama-day.reg`) and confirm the Registry Editor prompt, or import from the command line:

```cmd
reg import apps\\windows-console\\cyclorama-dawn.reg
```

2. Open a new `cmd.exe` window — `ScreenColors` (`0x00000007`) pairs slot `00` (background) and slot `07` (foreground), while `PopupColors` sets a high-contrast `F7` command history popup (`>= 18:1`).
3. To revert to stock Windows defaults at any time:

```cmd
reg import apps\\windows-console\\restore-defaults.reg
```

*(Note: Shortcut-specific `.lnk` files such as pinned Command Prompt shortcuts may store per-shortcut overrides; unpinned `cmd.exe` launches inherit `HKCU\\Console` directly.)*

## Previews

{_previews_markdown(app_name)}

## Windows Console ColorTable Mapping (`dword:00bbggrr`)

Windows Console maps `ColorTable00..15` in legacy VGA bit order (`01=Blue, 04=Red`) rather than ANSI order (`01=Red, 04=Blue`), with little-endian `COLORREF` (`00BBGGRR`) DWORDs:

{slot_table_md}

## Regenerating

```sh
python tools/build_extras_shells.py
```

Browse all ports in the [{BRAND_NAME} Theme Gallery]({GALLERY_URL}) or on [GitHub]({REPO_URL}).
"""
    _write_text(os.path.join(app_dir, "README.md"), readme)

    return _manifest_entry(
        slug=slug,
        name=app_name,
        category=category,
        homepage=homepage,
        fmt=fmt,
        install=install,
    )


# ---------------------------------------------------------------------------
# Entrypoint & Self-Verification
# ---------------------------------------------------------------------------

def build() -> list[dict]:
    """Generate all 3 shell & console app ports and return manifest entries."""
    return [
        build_git_bash(),
        build_qterminal(),
        build_windows_console(),
    ]


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _parse_ini_strict(text: str) -> configparser.RawConfigParser:
    cp = configparser.RawConfigParser(interpolation=None, strict=True)
    cp.optionxform = lambda optionstr: optionstr
    cp.read_string(text)
    return cp


def _colorref_dword_to_hex(dword_str: str) -> str:
    m = re.match(r"^dword:00([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$", dword_str)
    if not m:
        raise AssertionError(f"invalid COLORREF dword format: {dword_str!r}")
    b, g, r = (int(x, 16) for x in m.groups())
    return rgb_to_hex((r, g, b))


def _verify_generated(entries: list[dict]) -> None:
    expected_slugs = {"git-bash", "qterminal", "windows-console"}
    got_slugs = {e["slug"] for e in entries}
    if got_slugs != expected_slugs:
        raise AssertionError(f"slug mismatch: {got_slugs ^ expected_slugs}")

    # Zero hardcoded hex literals inside this builder script itself
    with open(os.path.abspath(__file__), "rb") as fh:
        self_bytes = fh.read()
    if b"\r\n" in self_bytes:
        raise AssertionError("CRLF line endings in tools/build_extras_shells.py")
    self_src = self_bytes.decode("utf-8")
    hex_rx = re.compile(r"#[0-9A-Fa-f]{6}\b")
    if hex_rx.search(self_src):
        raise AssertionError(f"hardcoded hex literal found in build_extras_shells.py: {hex_rx.findall(self_src)}")

    rgb_csv_rx = re.compile(r"^(\d{1,3}),(\d{1,3}),(\d{1,3})$")
    mintty_keys = {
        "ForegroundColour", "BackgroundColour", "CursorColour",
        "Black", "BoldBlack", "Red", "BoldRed", "Green", "BoldGreen",
        "Yellow", "BoldYellow", "Blue", "BoldBlue", "Magenta", "BoldMagenta",
        "Cyan", "BoldCyan", "White", "BoldWhite",
    }
    qterm_sections = {
        "General", "Background", "BackgroundIntense", "Foreground", "ForegroundIntense",
        *(f"Color{i}" for i in range(8)),
        *(f"Color{i}Intense" for i in range(8)),
    }
    md_link_rx = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    bad_space_link_rx = re.compile(r"!?\[[^\]]*\]\((?!<)[^)\n]+\s+[^)\n]*\)")

    git_exe = shutil.which("git")
    if not git_exe:
        raise AssertionError("git executable not found for .gitconfig verification")

    svg_count = 0
    gitconfig_count = 0
    colorscheme_count = 0
    reg_count = 0

    for entry in entries:
        slug = entry["slug"]
        app_dir = os.path.join(ROOT, "apps", slug)

        # 1. Verify themes.json contract & copySnippets
        with open(os.path.join(app_dir, "themes.json"), encoding="utf-8") as fh:
            tj = json.load(fh)
        assert tj["slug"] == slug
        assert len(tj.get("installSteps", [])) >= 2
        assert os.path.isfile(os.path.join(ROOT, tj["primaryFile"])), f"missing primaryFile {tj['primaryFile']}"
        for f_ent in tj["files"]:
            assert os.path.isfile(os.path.join(ROOT, f_ent["path"])), f"missing file {f_ent['path']}"
        assert tuple(t["id"] for t in tj["themes"]) == VARIANT_ORDER
        for t in tj["themes"]:
            assert os.path.isfile(os.path.join(ROOT, t["file"])), f"missing variant file {t['file']}"
            assert len(t["swatches"]) == 6
            snip = t["copySnippet"]
            lang = t["copyLang"]
            if lang == "ini":
                _parse_ini_strict(snip)
            elif lang == "conf":
                assert "=" in snip and len(snip.splitlines()) >= 19

        # 2. Verify zero CRLF & validate every generated file
        for root_dir, _, filenames in os.walk(app_dir):
            for fn in sorted(filenames):
                fp = os.path.join(root_dir, fn)
                with open(fp, "rb") as fh:
                    raw_b = fh.read()
                if b"\r\n" in raw_b:
                    raise AssertionError(f"CRLF detected in {fp}")
                txt = raw_b.decode("utf-8")

                if fn.endswith(".minttyrc"):
                    found: dict[str, str] = {}
                    for ln in txt.splitlines():
                        ln = ln.strip()
                        if not ln or ln.startswith("#"):
                            continue
                        k, val = ln.split("=", 1)
                        m = rgb_csv_rx.match(val)
                        assert m and all(0 <= int(c) <= 255 for c in m.groups()), f"{fn}: bad RGB {k}={val!r}"
                        found[k] = val
                    assert set(found.keys()) == mintty_keys, f"{fn}: key mismatch {set(found.keys()) ^ mintty_keys}"

                elif fn.endswith(".gitconfig"):
                    res = subprocess.run([git_exe, "config", "--file", fp, "--list"], capture_output=True, text=True)
                    if res.returncode != 0:
                        raise AssertionError(f"{fn} git config --list failed: {res.stderr.strip()}")
                    for req_key in (
                        "color.ui=auto",
                        "color.diff.meta=",
                        "color.diff.frag=",
                        "color.diff.old=",
                        "color.diff.new=",
                        "color.diff.context=",
                        "color.diff.whitespace=",
                        "color.diff.func=",
                        "color.status.header=",
                        "color.status.added=",
                        "color.status.changed=",
                        "color.status.untracked=",
                        "color.status.branch=",
                        "color.status.nobranch=",
                        "color.branch.current=",
                        "color.branch.local=",
                        "color.branch.remote=",
                        "color.branch.upstream=",
                        "color.grep.filename=",
                        "color.grep.linenumber=",
                        "color.grep.match=",
                        "color.grep.separator=",
                    ):
                        assert req_key in res.stdout, f"{fn}: missing {req_key}"
                    # Also validate every color.* key resolves cleanly through git --get-color
                    for line in res.stdout.splitlines():
                        k, _ = line.split("=", 1)
                        if k == "color.ui":
                            continue
                        gc = subprocess.run([git_exe, "config", "--file", fp, "--get-color", k], capture_output=True, text=True)
                        if gc.returncode != 0:
                            raise AssertionError(f"{fn}: git --get-color {k} failed: {gc.stderr.strip()}")
                    gitconfig_count += 1

                elif fn.endswith(".colorscheme"):
                    cp = _parse_ini_strict(txt)
                    assert set(cp.sections()) == qterm_sections, f"{fn}: section mismatch {set(cp.sections()) ^ qterm_sections}"
                    assert cp.get("General", "Opacity") == "1"
                    for sec in qterm_sections - {"General"}:
                        m = rgb_csv_rx.match(cp.get(sec, "Color"))
                        assert m and all(0 <= int(c) <= 255 for c in m.groups()), f"{fn}: bad Color in [{sec}]"
                        assert cp.get(sec, "Bold") in ("true", "false")
                    colorscheme_count += 1

                elif fn.endswith(".reg"):
                    lines = txt.splitlines()
                    assert lines and lines[0] == "Windows Registry Editor Version 5.00", f"{fn}: bad .reg header"
                    body_ini = "\n".join(lines[1:])
                    cp = _parse_ini_strict(body_ini)
                    sec = r"HKEY_CURRENT_USER\Console"
                    assert cp.has_section(sec), f"{fn}: missing [{sec}]"
                    tbl_hex: list[str] = []
                    for idx in range(16):
                        val = cp.get(sec, f'"ColorTable{idx:02d}"')
                        tbl_hex.append(_colorref_dword_to_hex(val))
                    sc_val = cp.get(sec, '"ScreenColors"')
                    pc_val = cp.get(sec, '"PopupColors"')
                    assert re.match(r"^dword:000000[0-9a-f]{2}$", sc_val), f"{fn}: bad ScreenColors={sc_val!r}"
                    assert re.match(r"^dword:000000[0-9a-f]{2}$", pc_val), f"{fn}: bad PopupColors={pc_val!r}"
                    sc_byte = int(sc_val.split(":")[1], 16)
                    pc_byte = int(pc_val.split(":")[1], 16)
                    sc_bg, sc_fg = (sc_byte >> 4) & 0xF, sc_byte & 0xF
                    pc_bg, pc_fg = (pc_byte >> 4) & 0xF, pc_byte & 0xF
                    assert contrast(tbl_hex[sc_fg], tbl_hex[sc_bg]) >= 4.5, f"{fn}: ScreenColors contrast < 4.5:1"
                    assert contrast(tbl_hex[pc_fg], tbl_hex[pc_bg]) >= 4.5, f"{fn}: PopupColors contrast < 4.5:1"
                    reg_count += 1

                elif fn.endswith(".svg"):
                    docs_svg = os.path.join(ROOT, "docs", "assets", "previews", slug, fn)
                    assert os.path.isfile(docs_svg), f"missing docs preview mirror {docs_svg}"
                    assert _sha256(fp) == _sha256(docs_svg), f"SVG mirror drift: {fp} != {docs_svg}"
                    with open(docs_svg, "rb") as fh:
                        if b"\r\n" in fh.read():
                            raise AssertionError(f"CRLF detected in {docs_svg}")
                    svg_root = ET.fromstring(txt)
                    rects = [el for el in svg_root.iter("{http://www.w3.org/2000/svg}rect") if el.attrib.get("y") == "357"]
                    texts = [el for el in svg_root.iter("{http://www.w3.org/2000/svg}text") if el.attrib.get("y") == "378"]
                    if len(rects) == 10 and len(texts) == 10:
                        ribbon = {("".join(t.itertext())).strip(): r.attrib.get("fill", "").upper() for r, t in zip(rects, texts)}
                        if "STEEL" in ribbon:
                            vid = fn[:-4]
                            exp_steel = VARIANTS[vid]["ui"]["accent"] if vid == "cyclorama-steel" else VARIANTS[vid]["ui"]["secondary"]
                            assert ribbon["STEEL"] == exp_steel, f"{slug}/{fn}: STEEL swatch {ribbon['STEEL']} != {exp_steel}"
                    svg_count += 1

                elif fn == "README.md":
                    stripped = re.sub(r"```.*?```", "", txt, flags=re.S)
                    stripped = re.sub(r"`[^`\n]+`", "", stripped)
                    bad_sp = list(bad_space_link_rx.finditer(stripped))
                    assert not bad_sp, f"{slug}/README.md unescaped space in link: {bad_sp[0].group(0)}"
                    for m in md_link_rx.finditer(stripped):
                        target = m.group(1).strip().strip("<>")
                        if target.startswith(("http://", "https://", "#", "mailto:")):
                            continue
                        clean = unquote(target.split("#")[0].split("?")[0])
                        if clean:
                            resolved = os.path.normpath(os.path.join(app_dir, clean))
                            assert os.path.exists(resolved), f"{slug}/README.md broken relative link: {target}"

    print(
        f"[ok] built & verified {len(entries)} shell/console ports "
        f"({gitconfig_count} .gitconfig, {colorscheme_count} .colorscheme, "
        f"{reg_count} .reg, {svg_count} SVG preview pairs)"
    )


if __name__ == "__main__":
    manifest_entries = build()
    _verify_generated(manifest_entries)
