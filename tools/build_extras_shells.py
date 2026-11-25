#!/usr/bin/env python3
"""Generate 4 Cyclorama Dawn v2.1.0 Terminal, Console & Mail ports for rfs-themes.

Builds 4 self-contained app ports (12 total variants across Dawn, Steel, and Day)
plus mirrored SVG previews in apps/<slug>/previews/ and docs/assets/previews/<slug>/:
  1. apps/git-bash/        — Git Bash (Mintty .minttyrc) + Native Git CLI (.gitconfig)
  2. apps/qterminal/       — QTerminal / QTermWidget6 (.colorscheme INI)
  3. apps/windows-console/ — Windows Console Host / conhost (.reg HKCU\\Console + restore-defaults.reg)
  4. apps/proton-mail/     — Proton Mail (Custom Theme CSS + 3-pane SVG previews)

Zero external dependencies (Python 3.11+ standard library only).
Zero hardcoded hex literals — every color derives from tools/rfs_palette.py.
Deterministic UTF-8 LF output across Windows and Linux CI.
"""
from __future__ import annotations

import configparser
import hashlib
from html import escape
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
    mix,
    rgb_to_hex,
)
from svg_previews import (  # noqa: E402
    _frame_shell,
    _standard_swatches,
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

PROTON_REQUIRED_VARS: tuple[str, ...] = (
    "--background-norm",
    "--background-weak",
    "--background-strong",
    "--background-elevated",
    "--background-lowered",
    "--interaction-norm",
    "--interaction-norm-major-1",
    "--interaction-norm-major-2",
    "--interaction-norm-major-3",
    "--interaction-norm-contrast",
    "--interaction-weak",
    "--interaction-weak-major-1",
    "--interaction-weak-major-2",
    "--interaction-default",
    "--interaction-default-hover",
    "--text-norm",
    "--text-weak",
    "--text-hint",
    "--text-disabled",
    "--text-invert",
    "--border-norm",
    "--border-weak",
    "--signal-danger",
    "--signal-danger-major-1",
    "--signal-warning",
    "--signal-success",
    "--signal-info",
    "--focus-outline",
    "--primary",
    "--primary-contrast",
    "--scrollbar-thumb-color",
    "--scrollbar-thumb-hover-color",
    "--navigation-current-item-background-color",
    "--navigation-current-item-text-color",
    "--email-item-unread-background-color",
    "--email-item-read-background-color",
    "--email-item-selected-background-color",
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


def _desktop_swatches(v: dict) -> list[dict[str, str]]:
    ui = v["ui"]
    return [
        {"label": "Background", "hex": ui["bg"]},
        {"label": "Surface", "hex": ui["surface"]},
        {"label": "Border", "hex": ui["border"]},
        {"label": "Text", "hex": ui["text"]},
        {"label": "Accent", "hex": ui["accent"]},
        {"label": "Secondary", "hex": ui["secondary"]},
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
# 4. Proton Mail (apps/proton-mail/)
# ---------------------------------------------------------------------------

def _proton_mail_css(v: dict) -> str:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    mode_lbl = "Dark" if is_dark else "Light"
    color_scheme = "dark" if is_dark else "light"

    norm_m2 = mix(ui["accent_fill_hover"], ui["bg"] if is_dark else ui["text"], 0.18)
    norm_m3 = mix(ui["accent_fill_hover"], ui["bg"] if is_dark else ui["text"], 0.32)
    weak_m2 = mix(ui["overlay"], ui["border_strong"], 0.28)
    hover_default = mix(ui["surface"], ui["raised"], 0.65)
    disabled_ink = mix(ui["subtle"], ui["bg"], 0.30)
    nav_active_bg = mix(ui["surface"], ui["accent"], 0.16 if is_dark else 0.12)
    signal_contrast = ui["bg"] if is_dark else ui["on_accent"]
    danger_m1 = mix(ui["fault"], ui["text"], 0.16) if is_dark else ui["fault_hover"]
    danger_m2 = mix(ui["fault"], ui["text"], 0.30) if is_dark else mix(ui["fault_hover"], ui["text"], 0.16)

    return f"""/*
 * {v["name"]} ({v["lx"]} {mode_lbl} · {v["accentRole"]}) — Proton Mail Custom Theme
 * Author: {AUTHOR} | Brand: {BRAND_NAME} v{v["version"]}
 * Source: {REPO_URL}
 * Install: Proton Mail -> Settings -> Appearance -> Custom theme -> Paste & Save
 */

:root {{
  color-scheme: {color_scheme};

  /* Surfaces & Elevation */
  --background-norm: {ui["bg"]};
  --background-weak: {ui["surface"]};
  --background-strong: {ui["raised"]};
  --background-elevated: {ui["overlay"]};
  --background-lowered: {ui["rail"]};

  /* Primary & Norm Interactions */
  --primary: {ui["accent_fill"]};
  --primary-contrast: {ui["on_accent"]};
  --interaction-norm: {ui["accent_fill"]};
  --interaction-norm-major-1: {ui["accent_fill_hover"]};
  --interaction-norm-major-2: {norm_m2};
  --interaction-norm-major-3: {norm_m3};
  --interaction-norm-contrast: {ui["on_accent"]};

  /* Secondary / Weak & Default Interactions */
  --interaction-weak: {ui["raised"]};
  --interaction-weak-major-1: {ui["overlay"]};
  --interaction-weak-major-2: {weak_m2};
  --interaction-default: transparent;
  --interaction-default-hover: {hover_default};
  --interaction-default-active: {ui["raised"]};

  /* Typography & Ink */
  --text-norm: {ui["text"]};
  --text-weak: {ui["mute"]};
  --text-hint: {ui["subtle"]};
  --text-disabled: {disabled_ink};
  --text-invert: {ui["bg"]};

  /* Borders & Hairlines */
  --border-norm: {ui["border"]};
  --border-weak: {ui["border_subtle"]};

  /* Semantic Signals & Focus */
  --signal-danger: {ui["fault"]};
  --signal-danger-major-1: {danger_m1};
  --signal-danger-major-2: {danger_m2};
  --signal-danger-contrast: {signal_contrast};
  --signal-warning: {ui["warning"]};
  --signal-warning-contrast: {signal_contrast};
  --signal-success: {ui["signal"]};
  --signal-success-contrast: {signal_contrast};
  --signal-info: {ui["secondary"]};
  --signal-info-contrast: {signal_contrast};
  --focus-outline: {ui["accent"]};
  --focus-ring: {ui["accent"]};

  /* Scrollbars */
  --scrollbar-thumb-color: {ui["border"]};
  --scrollbar-thumb-hover-color: {ui["border_strong"]};

  /* Navigation & Mailbox List */
  --navigation-current-item-background-color: {nav_active_bg};
  --navigation-current-item-text-color: {ui["text"]};
  --navigation-current-item-marker-color: {ui["accent"]};
  --email-item-unread-background-color: {ui["bg"]};
  --email-item-read-background-color: {ui["surface"]};
  --email-item-selected-background-color: {ui["selection_active"]};
  --email-item-selected-text-color: {ui["text"]};

  /* Cyclorama Dawn Horizon Tokens */
  --rfs-link-color: {ui["accent"]};
  --rfs-link-hover: {ui["accent_hover"]};
  --rfs-secondary-ink: {ui["secondary"]};
  --rfs-beam-start: {ui["beam_start"]};
  --rfs-beam-end: {ui["beam_end"]};
}}

/* Active sidebar item & horizon indicator */
.navigation-link[aria-current="page"],
.navigation-link.active {{
  background-color: var(--navigation-current-item-background-color);
  color: var(--navigation-current-item-text-color);
  box-shadow: inset 3px 0 0 0 var(--navigation-current-item-marker-color);
}}

/* Unread & selected message rows */
.item-container.unread {{
  background-color: var(--email-item-unread-background-color);
  color: var(--text-norm);
}}

.item-container.read {{
  background-color: var(--email-item-read-background-color);
}}

.item-container.item-is-selected {{
  background-color: var(--email-item-selected-background-color);
  color: var(--email-item-selected-text-color);
  box-shadow: inset 3px 0 0 0 var(--focus-outline);
}}

/* Links & top horizon hairline */
.link,
a.link {{
  color: var(--rfs-link-color);
}}

.link:hover,
a.link:hover {{
  color: var(--rfs-link-hover);
}}

.header::before {{
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--rfs-beam-start), var(--rfs-beam-end));
  pointer-events: none;
}}
"""


def render_proton_mail_preview(variant: dict) -> str:
    """Render a 660x390 3-pane Proton Mail inbox SVG preview reusing _frame_shell."""
    ui = variant["ui"]
    is_dark = variant["mode"] == "dark"
    sel_nav = mix(ui["surface"], ui["accent"], 0.16 if is_dark else 0.12)
    unread_dot = ui["accent"]
    secondary_dot = ui["secondary"]

    body = f'''
    <!-- Pane 1: Sidebar folders (x=0..146, y=36..346) -->
    <rect x="0" y="36" width="146" height="310" fill="{ui["rail"]}"/>
    <line x1="146" y1="36" x2="146" y2="346" stroke="{ui["border"]}" stroke-width="1"/>

    <!-- Compose primary CTA -->
    <rect x="12" y="48" width="122" height="26" rx="5" fill="{ui["accent_fill"]}"/>
    <text x="73" y="64.5" text-anchor="middle" fill="{ui["on_accent"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="700">+ New message</text>

    <!-- Active folder: Inbox -->
    <rect x="8" y="86" width="130" height="24" rx="4" fill="{sel_nav}"/>
    <rect x="8" y="88" width="3" height="20" rx="1" fill="{ui["accent"]}"/>
    <text x="20" y="101.5" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="700">Inbox</text>
    <rect x="114" y="91" width="18" height="14" rx="7" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.8"/>
    <text x="123" y="101" text-anchor="middle" fill="{ui["accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">3</text>

    <!-- Other folders -->
    <g font-family="system-ui,-apple-system,sans-serif" font-size="9.8">
      <text x="20" y="127" fill="{ui["text_soft"]}">Drafts</text>
      <text x="20" y="149" fill="{ui["mute"]}">Sent</text>
      <text x="20" y="171" fill="{ui["mute"]}">Starred</text>
      <text x="20" y="193" fill="{ui["mute"]}">Archive</text>
      <text x="20" y="215" fill="{ui["mute"]}">All Mail</text>
    </g>

    <!-- Labels section -->
    <line x1="12" y1="229" x2="134" y2="229" stroke="{ui["border_subtle"]}" stroke-width="1"/>
    <text x="16" y="245" fill="{ui["subtle"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700" letter-spacing="0.8">LABELS</text>
    <circle cx="20" cy="262" r="3.5" fill="{ui["signal"]}"/>
    <text x="30" y="265.5" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">Security</text>
    <circle cx="20" cy="282" r="3.5" fill="{ui["secondary"]}"/>
    <text x="30" y="285.5" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">Releases</text>
    <circle cx="20" cy="302" r="3.5" fill="{ui["accent"]}"/>
    <text x="30" y="305.5" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">Brand Kit</text>

    <!-- Encryption status pill -->
    <rect x="12" y="317" width="122" height="20" rx="4" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.9"/>
    <text x="73" y="330" text-anchor="middle" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">[ok] E2E PGP Active</text>

    <!-- Pane 2: Inbox message list (x=146..356, y=36..346) -->
    <rect x="146" y="36" width="210" height="310" fill="{ui["surface"]}"/>
    <line x1="356" y1="36" x2="356" y2="346" stroke="{ui["border"]}" stroke-width="1"/>

    <!-- List header bar -->
    <rect x="146" y="36" width="210" height="28" fill="{ui["surface"]}"/>
    <line x1="146" y1="64" x2="356" y2="64" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="158" y="54" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5" font-weight="700">Inbox</text>
    <text x="344" y="54" text-anchor="end" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5">3 unread</text>

    <!-- Message 1: Selected + Unread -->
    <rect x="146" y="64" width="210" height="68" fill="{ui["selection_active"]}"/>
    <rect x="146" y="64" width="3" height="68" fill="{ui["accent"]}"/>
    <circle cx="160" cy="81" r="3.5" fill="{unread_dot}"/>
    <text x="170" y="84.5" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="700">Real-Fruit-Snacks</text>
    <text x="346" y="84.5" text-anchor="end" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8">14:05</text>
    <text x="158" y="102" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.8" font-weight="700">Cyclorama Dawn v2.1.0</text>
    <text x="158" y="118" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9">Custom CSS tokens · AA verified</text>
    <line x1="146" y1="132" x2="356" y2="132" stroke="{ui["border"]}" stroke-width="1"/>

    <!-- Message 2: Unread -->
    <rect x="146" y="132" width="210" height="68" fill="{ui["bg"]}"/>
    <circle cx="160" cy="149" r="3.5" fill="{secondary_dot}"/>
    <text x="170" y="152.5" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="700">Proton Security</text>
    <text x="346" y="152.5" text-anchor="end" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8">12:40</text>
    <text x="158" y="170" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.6" font-weight="600">PGP key fingerprint verified</text>
    <text x="158" y="186" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9">Zero-access mailbox sealed</text>
    <line x1="146" y1="200" x2="356" y2="200" stroke="{ui["border_subtle"]}" stroke-width="1"/>

    <!-- Message 3: Read -->
    <rect x="146" y="200" width="210" height="68" fill="{ui["surface"]}"/>
    <text x="158" y="220" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="600">GitHub Releases</text>
    <text x="346" y="220" text-anchor="end" fill="{ui["subtle"]}" font-family="ui-monospace,Consolas,monospace" font-size="8">Nov 24</text>
    <text x="158" y="237" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">rfs-themes tagged v2.1.0</text>
    <text x="158" y="253" fill="{ui["subtle"]}" font-family="system-ui,-apple-system,sans-serif" font-size="8.8">CI passed · zero external deps</text>
    <line x1="146" y1="268" x2="356" y2="268" stroke="{ui["border_subtle"]}" stroke-width="1"/>

    <!-- Message 4: Read -->
    <rect x="146" y="268" width="210" height="78" fill="{ui["surface"]}"/>
    <text x="158" y="288" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="600">Design Telemetry</text>
    <text x="346" y="288" text-anchor="end" fill="{ui["subtle"]}" font-family="ui-monospace,Consolas,monospace" font-size="8">Nov 23</text>
    <text x="158" y="305" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">LX 263 / LX 512 audit</text>
    <text x="158" y="321" fill="{ui["subtle"]}" font-family="system-ui,-apple-system,sans-serif" font-size="8.8">All contrast ratios &gt;= 4.5:1</text>

    <!-- Pane 3: Encrypted Reading Pane (x=356..660, y=36..346) -->
    <rect x="356" y="36" width="304" height="310" fill="{ui["bg"]}"/>

    <!-- Reading toolbar -->
    <rect x="356" y="36" width="304" height="28" fill="{ui["surface"]}"/>
    <line x1="356" y1="64" x2="660" y2="64" stroke="{ui["border"]}" stroke-width="1"/>
    <rect x="368" y="42" width="44" height="17" rx="3.5" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.9"/>
    <text x="390" y="53.5" text-anchor="middle" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="8.5" font-weight="600">Reply</text>
    <rect x="418" y="42" width="52" height="17" rx="3.5" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.9"/>
    <text x="444" y="53.5" text-anchor="middle" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="8.5" font-weight="600">Archive</text>
    <rect x="568" y="42" width="80" height="17" rx="3.5" fill="{ui["raised"]}" stroke="{ui["signal"]}" stroke-width="0.9"/>
    <text x="608" y="53.5" text-anchor="middle" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">PGP VERIFIED</text>

    <!-- Message subject & sender header -->
    <text x="372" y="88" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="13.5" font-weight="800">Cyclorama Dawn v2.1.0</text>
    <circle cx="384" cy="112" r="11" fill="{ui["accent_fill"]}"/>
    <text x="384" y="115.5" text-anchor="middle" fill="{ui["on_accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">RF</text>
    <text x="402" y="109" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="700">Real-Fruit-Snacks</text>
    <text x="402" y="122" fill="{ui["secondary"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5">&lt;themes@rfs.tools&gt; · Encrypted</text>
    <text x="646" y="109" text-anchor="end" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8">14:05</text>
    <line x1="372" y1="134" x2="646" y2="134" stroke="{ui["border_subtle"]}" stroke-width="1"/>

    <!-- Encrypted message card -->
    <rect x="372" y="146" width="274" height="114" rx="6" fill="{ui["surface"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <rect x="372" y="152" width="3" height="102" rx="1.5" fill="{ui["secondary"]}"/>
    <g font-family="system-ui,-apple-system,sans-serif" font-size="10">
      <text x="386" y="167" fill="{ui["text_soft"]}">Your Proton Mail workspace is calibrated</text>
      <text x="386" y="183" fill="{ui["text_soft"]}">to <tspan fill="{ui["accent"]}" font-weight="700">{escape(variant["name"])}</tspan> ({escape(variant["lx"])}).</text>
    </g>
    <g font-family="ui-monospace,Consolas,monospace" font-size="8.6">
      <text x="386" y="207"><tspan fill="{ui["secondary"]}">--background-norm:</tspan><tspan fill="{ui["text"]}"> {ui["bg"]}</tspan></text>
      <text x="386" y="223"><tspan fill="{ui["secondary"]}">--interaction-norm:</tspan><tspan fill="{ui["accent"]}"> {ui["accent_fill"]}</tspan></text>
      <text x="386" y="242"><tspan fill="{ui["signal"]}" font-weight="700">[ok]</tspan><tspan fill="{ui["mute"]}"> Zero-access CSS · WCAG AA</tspan></text>
    </g>

    <!-- Quick reply composer -->
    <rect x="372" y="274" width="274" height="56" rx="6" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="384" y="293" fill="{ui["subtle"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">Reply encrypted to Real-Fruit-Snacks...</text>
    <rect x="582" y="302" width="54" height="20" rx="4" fill="{ui["accent_fill"]}"/>
    <text x="609" y="315" text-anchor="middle" fill="{ui["on_accent"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9" font-weight="700">Send</text>
    '''
    return _frame_shell(variant, "[proton-mail]", "Proton Mail", "E2E CSS", body, _standard_swatches(variant))


def build_proton_mail() -> dict:
    slug = "proton-mail"
    app_name = "Proton Mail"
    category = "Browsers & Desktop"
    homepage = "https://proton.me/mail"
    fmt = "Custom Theme CSS"
    install = "Proton Mail -> Settings -> Appearance -> Custom theme -> Paste CSS"
    app_dir = os.path.join(ROOT, "apps", slug)
    version = VARIANTS["cyclorama-dawn"]["version"]

    summaries = {
        "cyclorama-dawn": (
            f"Matte {VARIANTS['cyclorama-dawn']['ui']['bg']} Proton Mail dark workspace with "
            f"Beacon Orange ({VARIANTS['cyclorama-dawn']['ui']['accent']}) active indicators, "
            f"high-contrast compose CTA ({VARIANTS['cyclorama-dawn']['ui']['accent_fill']}), and Steel Blue info signals."
        ),
        "cyclorama-steel": (
            f"Cool steel-charcoal Proton Mail dark workspace with Steel Blue ({VARIANTS['cyclorama-steel']['ui']['accent']}) "
            f"focus rings, {VARIANTS['cyclorama-steel']['ui']['accent_fill']} primary buttons, and Beacon Orange secondary highlights."
        ),
        "cyclorama-day": (
            f"Crisp {VARIANTS['cyclorama-day']['ui']['bg']} Alabaster Day light mailbox with white message panes, "
            f"burnt Beacon ({VARIANTS['cyclorama-day']['ui']['accent']}) focus markers, and Steel Blue primary buttons."
        ),
    }

    files: list[dict[str, str]] = []
    theme_entries: list[dict] = []
    css_links: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        fname = f"{vid}.css"
        css_text = _proton_mail_css(v)
        _write_text(os.path.join(app_dir, fname), css_text)

        files.append({"label": f"{v['name']} CSS ({fname})", "path": f"apps/{slug}/{fname}"})
        css_links[vid] = _md_file_link(fname)

        theme_entries.append({
            "id": v["id"],
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": summaries[vid],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{fname}",
            "copyLang": "css",
            "copyLabel": f"Copy {v['name']} Proton Mail CSS",
            "copySnippet": css_text.rstrip("\n"),
            "swatches": _desktop_swatches(v),
        })

        svg = render_proton_mail_preview(v)
        write_preview_pair(slug, vid, svg)

    install_steps = [
        "Open **Proton Mail** (`proton.me/mail`) -> **Settings (gear icon) -> All settings -> Appearance**.",
        "Scroll to **Custom theme** (or toggle **Custom theme** on) and open the CSS editor.",
        "Paste the full contents of `cyclorama-dawn.css` (or `cyclorama-steel.css` / `cyclorama-day.css`) and click **Save** — applies across Proton Mail, Calendar, and Drive.",
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
        "primaryFile": f"apps/{slug}/cyclorama-dawn.css",
        "files": files,
        "themes": theme_entries,
    })

    dawn_ui = VARIANTS["cyclorama-dawn"]["ui"]
    steel_ui = VARIANTS["cyclorama-steel"]["ui"]
    day_ui = VARIANTS["cyclorama-day"]["ui"]

    token_table = "\n".join([
        "| Proton Design Token | Cyclorama Dawn (`LX 263`) | Cyclorama Steel (`LX 263`) | Cyclorama Day (`LX 512`) |",
        "|---|---|---|---|",
        f"| `--background-norm` / `--background-weak` | `{dawn_ui['bg']}` / `{dawn_ui['surface']}` | `{steel_ui['bg']}` / `{steel_ui['surface']}` | `{day_ui['bg']}` / `{day_ui['surface']}` |",
        f"| `--background-strong` / `--background-lowered` | `{dawn_ui['raised']}` / `{dawn_ui['rail']}` | `{steel_ui['raised']}` / `{steel_ui['rail']}` | `{day_ui['raised']}` / `{day_ui['rail']}` |",
        f"| `--interaction-norm` / `--primary` | `{dawn_ui['accent_fill']}` | `{steel_ui['accent_fill']}` | `{day_ui['accent_fill']}` |",
        f"| `--text-norm` / `--text-weak` | `{dawn_ui['text']}` / `{dawn_ui['mute']}` | `{steel_ui['text']}` / `{steel_ui['mute']}` | `{day_ui['text']}` / `{day_ui['mute']}` |",
        f"| `--focus-outline` / `--signal-info` | `{dawn_ui['accent']}` / `{dawn_ui['secondary']}` | `{steel_ui['accent']}` / `{steel_ui['secondary']}` | `{day_ui['accent']}` / `{day_ui['secondary']}` |",
        f"| `--signal-success` / `--signal-danger` | `{dawn_ui['signal']}` / `{dawn_ui['fault']}` | `{steel_ui['signal']}` / `{steel_ui['fault']}` | `{day_ui['signal']}` / `{day_ui['fault']}` |",
    ])

    readme = f"""# {BRAND_NAME} for Proton Mail

Three **{BRAND_NAME} v{version} (Steel & Beacon Orange)** ready-to-paste Custom Theme CSS files for **[Proton Mail]({homepage})** (Proton Design System `:root` tokens), calibrated from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}).

## Variants

{_variant_table(css_links)}

## Install

1. Open **Proton Mail** and go to **Settings -> All settings -> Appearance**.
2. Enable **Custom theme** and open the custom CSS text box.
3. Paste the full contents of `cyclorama-dawn.css` (or `cyclorama-steel.css` / `cyclorama-day.css`) and click **Save**.

## Previews

{_previews_markdown(app_name, summaries=summaries)}

## Token Mapping

{token_table}

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
        summaries=summaries,
    )


# ---------------------------------------------------------------------------
# Entrypoint & Self-Verification
# ---------------------------------------------------------------------------

def build() -> list[dict]:
    """Generate all 4 shell, console & mail app ports and return manifest entries."""
    return [
        build_git_bash(),
        build_qterminal(),
        build_windows_console(),
        build_proton_mail(),
    ]


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _parse_ini_strict(text: str) -> configparser.RawConfigParser:
    cp = configparser.RawConfigParser(interpolation=None, strict=True)
    cp.optionxform = lambda optionstr: optionstr
    cp.read_string(text)
    return cp


def _check_balanced_braces_css(text: str) -> bool:
    no_cmt = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    no_str = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', '""', no_cmt)
    depth = 0
    for ch in no_str:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and "{" in no_str


def _colorref_dword_to_hex(dword_str: str) -> str:
    m = re.match(r"^dword:00([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$", dword_str)
    if not m:
        raise AssertionError(f"invalid COLORREF dword format: {dword_str!r}")
    b, g, r = (int(x, 16) for x in m.groups())
    return rgb_to_hex((r, g, b))


def _verify_generated(entries: list[dict]) -> None:
    expected_slugs = {"git-bash", "qterminal", "windows-console", "proton-mail"}
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
    rx_oklch = re.compile(r"\bin\s+oklch\b", re.I)
    md_link_rx = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    bad_space_link_rx = re.compile(r"!?\[[^\]]*\]\((?!<)[^)\n]+\s+[^)\n]*\)")

    git_exe = shutil.which("git")
    if not git_exe:
        raise AssertionError("git executable not found for .gitconfig verification")

    svg_count = 0
    gitconfig_count = 0
    colorscheme_count = 0
    reg_count = 0
    css_count = 0

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
            elif lang == "css":
                assert _check_balanced_braces_css(snip), f"{slug}/{t['id']}: unbalanced CSS copySnippet"
                assert not rx_oklch.search(snip), f"{slug}/{t['id']}: forbidden in oklch"
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

                elif fn.endswith(".css"):
                    assert _check_balanced_braces_css(txt), f"{fn}: unbalanced CSS braces"
                    assert not rx_oklch.search(txt), f"{fn}: forbidden `in oklch` detected"
                    css_vars = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", txt))
                    for prop in PROTON_REQUIRED_VARS:
                        assert prop in css_vars, f"{fn}: missing required Proton token {prop}"
                    for bg_var, fg_var in (
                        ("--interaction-norm", "--interaction-norm-contrast"),
                        ("--interaction-norm-major-1", "--interaction-norm-contrast"),
                        ("--interaction-norm-major-2", "--interaction-norm-contrast"),
                        ("--interaction-norm-major-3", "--interaction-norm-contrast"),
                        ("--signal-danger", "--signal-danger-contrast"),
                        ("--signal-danger-major-1", "--signal-danger-contrast"),
                        ("--signal-danger-major-2", "--signal-danger-contrast"),
                        ("--signal-warning", "--signal-warning-contrast"),
                        ("--signal-success", "--signal-success-contrast"),
                        ("--signal-info", "--signal-info-contrast"),
                    ):
                        assert contrast(css_vars[fg_var].strip(), css_vars[bg_var].strip()) >= 4.5, (
                            f"{fn}: {fg_var} on {bg_var} contrast < 4.5:1"
                        )
                    css_count += 1

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
        f"[ok] built & verified {len(entries)} shell/console/mail ports "
        f"({gitconfig_count} .gitconfig, {colorscheme_count} .colorscheme, "
        f"{reg_count} .reg, {css_count} .css, {svg_count} SVG preview pairs)"
    )


if __name__ == "__main__":
    manifest_entries = build()
    _verify_generated(manifest_entries)
