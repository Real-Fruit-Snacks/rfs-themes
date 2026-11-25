#!/usr/bin/env python3
"""Generate Cyclorama Dawn v2.1.0 desktop, notes, browser & chat app ports.

Generates 5 self-contained app ports under apps/<slug>/ plus paired SVG previews
in apps/<slug>/previews/ and docs/assets/previews/<slug>/:
  1. apps/obsidian/       — Obsidian (manifest.json, theme.css, snippets/*.css)
  2. apps/chromium/       — Brave / Chrome / Edge (MV3 theme manifest.json x3)
  3. apps/discord/        — Discord / Vencord / BetterDiscord (*.theme.css x3)
  4. apps/qbittorrent/    — qBittorrent (stylesheet.qss + config.json x3)
  5. apps/flow-launcher/  — Flow Launcher (WPF ResourceDictionary .xaml x3)

Zero external dependencies (Python 3.11+ stdlib only). Deterministic UTF-8 LF output.
"""
from __future__ import annotations

import colorsys
import json
import os
import sys
import xml.etree.ElementTree as ET
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from rfs_palette import (  # noqa: E402
    AUTHOR,
    BRAND_NAME,
    GALLERY_URL,
    REPO_URL,
    ROOT,
    VARIANT_ORDER,
    VARIANTS,
    argb_hex,
    hex_to_rgb,
    mix,
)
from svg_previews import (  # noqa: E402
    render_browser_preview,
    render_chat_preview,
    render_notes_preview,
    render_utility_preview,
    write_preview_pair,
)


def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _write_json(path: str, payload: dict) -> None:
    _write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _rgb_csv(h: str) -> str:
    r, g, b = hex_to_rgb(h)
    return f"{r}, {g}, {b}"


def _rgba(h: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(h)
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"


def _hsl_components(h: str) -> tuple[int, int, int]:
    r, g, b = hex_to_rgb(h)
    hue, lit, sat = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return round(hue * 360), round(sat * 100), round(lit * 100)


def _chromium_tint(h: str) -> list[float]:
    r, g, b = hex_to_rgb(h)
    hue, lit, sat = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return [round(hue, 3), round(sat, 3), round(lit, 3)]


def _six_swatches(v: dict) -> list[dict[str, str]]:
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
    summaries: dict[str, str],
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
                "id": vid,
                "name": VARIANTS[vid]["name"],
                "lx": VARIANTS[vid]["lx"],
                "mode": VARIANTS[vid]["mode"],
                "accentRole": VARIANTS[vid]["accentRole"],
                "summary": summaries[vid],
                "preview": f"apps/{slug}/previews/{vid}.svg",
            }
            for vid in VARIANT_ORDER
        ],
        "path": f"apps/{slug}",
        "data": f"apps/{slug}/themes.json",
    }


def _render_readme(
    *,
    app_name: str,
    slug: str,
    homepage: str,
    fmt: str,
    intro: str,
    install_steps: list[str],
    files: list[dict[str, str]],
    variant_notes: dict[str, str],
    extra_notes: str = "",
) -> str:
    ver = VARIANTS["cyclorama-dawn"]["version"]
    lines = [
        f"# {BRAND_NAME} for {app_name}",
        "",
        f"{intro} Calibrated from [`brand/rfs.tokens.json`](../../brand/rfs.tokens.json) "
        f"(**{BRAND_NAME} v{ver}**) for **[{app_name}]({homepage})** (`{fmt}`).",
        "",
        "## Install",
        "",
    ]
    for idx, step in enumerate(install_steps, 1):
        lines.append(f"{idx}. {step}")
    lines += [
        "",
        "## Included Files",
        "",
        "| Artifact | Path |",
        "|---|---|",
    ]
    prefix = f"apps/{slug}/"
    for item in files:
        rel = item["path"][len(prefix):] if item["path"].startswith(prefix) else item["path"]
        href = quote(rel, safe="/")
        lines.append(f"| {item['label']} | [`{rel}`]({href}) |")

    lines += [
        "",
        "## Variants",
        "",
        "| Variant | Lighting Cue | Mode | Primary Accent | Background | Surface | Accent | Secondary |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        ui = v["ui"]
        lines.append(
            f"| **{v['name']}** | `{v['lx']}` | {v['mode']} | {v['accentRole']} "
            f"| `{ui['bg']}` | `{ui['surface']}` | `{ui['accent']}` | `{ui['secondary']}` |"
        )

    lines.append("")
    for idx, vid in enumerate(VARIANT_ORDER, 1):
        v = VARIANTS[vid]
        lines += [
            f"### {idx}. {v['name']} (`{v['lx']} · {v['accentRole']}`)",
            "",
            variant_notes[vid],
            "",
            f"![{v['name']} {app_name} preview](previews/{vid}.svg)",
            "",
        ]

    if extra_notes:
        lines += [extra_notes.rstrip(), ""]

    lines += [
        "## Regenerating",
        "",
        "```sh",
        "python tools/build_desktop.py",
        "```",
        "",
        f"Browse all ports in the [{BRAND_NAME} Theme Gallery]({GALLERY_URL}) or on [GitHub]({REPO_URL}).",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1. Obsidian
# ---------------------------------------------------------------------------

def _obsidian_vars_block(v: dict) -> str:
    ui = v["ui"]
    syn = v["syntax"]
    is_dark = v["mode"] == "dark"
    ah, asat, alit = _hsl_components(ui["accent_fill"] if is_dark else ui["accent"])
    hover_bg = mix(ui["surface"], ui["raised"], 0.65)
    active_nav = mix(ui["surface"], ui["accent"], 0.16 if is_dark else 0.12)
    tag_bg = mix(ui["surface"], ui["secondary"], 0.16 if is_dark else 0.12)
    tag_bg_hover = mix(ui["surface"], ui["accent"], 0.20 if is_dark else 0.14)
    shadow = _rgba(ui["bg"], 0.55) if is_dark else _rgba(ui["text"], 0.12)

    return f"""  /* Surfaces & Chrome */
  --background-primary: {ui["bg"]};
  --background-primary-alt: {ui["code_bg"]};
  --background-secondary: {ui["surface"]};
  --background-secondary-alt: {ui["rail"]};
  --background-modifier-hover: {hover_bg};
  --background-modifier-active-hover: {active_nav};
  --background-modifier-border: {ui["border"]};
  --background-modifier-border-hover: {ui["border_strong"]};
  --background-modifier-border-focus: {ui["accent"]};
  --background-modifier-form-field: {ui["raised"]};
  --background-modifier-form-field-highlighted: {ui["overlay"]};
  --background-modifier-box-shadow: {shadow};
  --background-modifier-success: {ui["signal"]};
  --background-modifier-error: {ui["fault_fill"]};
  --background-modifier-error-hover: {ui["fault_hover"]};
  --background-modifier-cover: {_rgba(ui["bg"], 0.78)};
  --titlebar-background: {ui["rail"]};
  --titlebar-background-focused: {ui["surface"]};
  --ribbon-background: {ui["rail"]};
  --ribbon-background-collapsed: {ui["rail"]};
  --status-bar-background: {ui["surface"]};
  --status-bar-border-color: {ui["border"]};
  --status-bar-text-color: {ui["mute"]};
  --tab-background-active: {ui["bg"]};
  --tab-container-background: {ui["rail"]};
  --tab-outline-color: {ui["border"]};
  --tab-divider-color: {ui["border_subtle"]};
  --divider-color: {ui["border"]};
  --divider-color-hover: {ui["accent"]};

  /* Typography & Ink */
  --text-normal: {ui["text"]};
  --text-muted: {ui["mute"]};
  --text-faint: {ui["subtle"]};
  --text-on-accent: {ui["on_accent"]};
  --text-on-accent-inverted: {ui["bg"]};
  --text-error: {ui["fault"]};
  --text-warning: {ui["warning"]};
  --text-success: {ui["signal"]};
  --text-selection: {ui["selection_active"]};
  --text-highlight-bg: {ui["find_match"]};
  --text-accent: {ui["accent"]};
  --text-accent-hover: {ui["accent_hover"]};

  /* Interactive Accents */
  --accent-h: {ah};
  --accent-s: {asat}%;
  --accent-l: {alit}%;
  --interactive-normal: {ui["raised"]};
  --interactive-hover: {ui["overlay"]};
  --interactive-accent: {ui["accent_fill"]};
  --interactive-accent-hover: {ui["accent_fill_hover"]};
  --interactive-accent-rgb: {_rgb_csv(ui["accent_fill"])};
  --caret-color: {ui["cursor"]};

  /* Links, Tags & Navigation */
  --link-color: {ui["accent"]};
  --link-color-hover: {ui["accent_hover"]};
  --link-external-color: {ui["secondary"]};
  --link-external-color-hover: {ui["secondary_hover"]};
  --link-unresolved-color: {ui["mute"]};
  --tag-color: {ui["secondary"]};
  --tag-color-hover: {ui["accent"]};
  --tag-background: {tag_bg};
  --tag-background-hover: {tag_bg_hover};
  --tag-border-color: {ui["border"]};
  --tag-border-width: 1px;
  --nav-item-color: {ui["text_soft"]};
  --nav-item-color-hover: {ui["text"]};
  --nav-item-color-active: {ui["text"]};
  --nav-item-background-hover: {hover_bg};
  --nav-item-background-active: {active_nav};
  --nav-indentation-guide-color: {ui["border_subtle"]};

  /* Headings */
  --h1-color: {ui["text"]};
  --h2-color: {ui["accent"]};
  --h3-color: {ui["secondary"]};
  --h4-color: {ui["signal"]};
  --h5-color: {ui["warning"]};
  --h6-color: {ui["mute"]};

  /* Code & Syntax */
  --code-background: {ui["code_bg"]};
  --code-normal: {ui["text_soft"]};
  --code-comment: {syn["comment"]};
  --code-function: {syn["function"]};
  --code-important: {ui["warning"]};
  --code-keyword: {syn["keyword"]};
  --code-operator: {syn["operator"]};
  --code-property: {syn["property"]};
  --code-punctuation: {syn["punctuation"]};
  --code-string: {syn["string"]};
  --code-tag: {syn["tag"]};
  --code-value: {syn["number"]};

  /* Blockquotes, Callouts & Tables */
  --blockquote-border-color: {ui["secondary"]};
  --blockquote-background-color: {ui["surface"]};
  --callout-default: {_rgb_csv(ui["secondary"])};
  --callout-info: {_rgb_csv(ui["secondary"])};
  --callout-tip: {_rgb_csv(ui["cyan"])};
  --callout-success: {_rgb_csv(ui["signal"])};
  --callout-warning: {_rgb_csv(ui["warning"])};
  --callout-fail: {_rgb_csv(ui["fault"])};
  --callout-error: {_rgb_csv(ui["fault"])};
  --callout-bug: {_rgb_csv(ui["fault"])};
  --callout-example: {_rgb_csv(ui["magenta"])};
  --callout-quote: {_rgb_csv(ui["mute"])};
  --table-header-background: {ui["surface"]};
  --table-header-background-hover: {ui["raised"]};
  --table-border-color: {ui["border"]};
  --table-row-alt-background: {ui["code_bg"]};
  --hr-color: {ui["border"]};

  /* Graph View */
  --graph-line: {ui["border_strong"]};
  --graph-node: {ui["secondary"]};
  --graph-node-unresolved: {ui["subtle"]};
  --graph-node-focused: {ui["accent"]};
  --graph-node-tag: {ui["signal"]};
  --graph-node-attachment: {ui["warning"]};
  --graph-text: {ui["text_soft"]};

  /* Scrollbars & Horizon Beam */
  --scrollbar-bg: transparent;
  --scrollbar-thumb-bg: {ui["border"]};
  --scrollbar-active-thumb-bg: {ui["border_strong"]};
  --rfs-beam-start: {ui["beam_start"]};
  --rfs-beam-end: {ui["beam_end"]};
  --rfs-accent-line: {ui["accent"]};"""


def _build_obsidian_theme_css() -> str:
    dawn = VARIANTS["cyclorama-dawn"]
    steel = VARIANTS["cyclorama-steel"]
    day = VARIANTS["cyclorama-day"]
    ver = dawn["version"]

    return f"""/*
 * {BRAND_NAME} v{ver} for Obsidian
 * Author: {AUTHOR}
 * Source: {REPO_URL}
 * Default dark: Cyclorama Dawn (LX 263, Beacon Orange)
 * Alternate dark: Cyclorama Steel (LX 263, Steel Blue — toggle via Style Settings or snippet)
 * Light mode: Cyclorama Day (LX 512, Alabaster Day)
 */

/* @settings
name: Cyclorama Dawn
id: cyclorama-dawn
settings:
  - id: cyclorama-dark-variant
    title: Dark Mode Accent Preset
    description: Switch between Cyclorama Dawn (Beacon Orange) and Cyclorama Steel (Steel Blue) in dark mode.
    type: class-select
    allowEmpty: false
    default: cyclorama-dawn-accent
    options:
      - label: Cyclorama Dawn (LX 263 · Beacon Orange)
        value: cyclorama-dawn-accent
      - label: Cyclorama Steel (LX 263 · Steel Blue)
        value: cyclorama-steel-accent
  - id: cyclorama-horizon-beam
    title: Horizon Beam Accent Bar
    description: Display the 2px Steel-to-Beacon gradient beam on active tabs and callout headers.
    type: class-toggle
    default: true
*/

.theme-dark,
.theme-dark.cyclorama-dawn-accent {{
{_obsidian_vars_block(dawn)}
}}

.theme-dark.cyclorama-steel-accent {{
{_obsidian_vars_block(steel)}
}}

.theme-light {{
{_obsidian_vars_block(day)}
}}

/* Active tab horizon indicator (Cartesian oklab interpolation) */
.workspace-tab-header.is-active {{
  background-color: var(--tab-background-active);
  box-shadow: inset 0 2px 0 0 var(--rfs-accent-line);
}}

body.cyclorama-horizon-beam .workspace-tab-header.is-active::before {{
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg in oklab, var(--rfs-beam-start), var(--rfs-beam-end));
}}

/* Headings */
.markdown-rendered h1,
.cm-header-1 {{
  color: var(--h1-color);
  font-weight: 800;
  letter-spacing: -0.02em;
}}

.markdown-rendered h2,
.cm-header-2 {{
  color: var(--h2-color);
  font-weight: 700;
  border-bottom: 1px solid var(--background-modifier-border);
  padding-bottom: 0.25em;
}}

.markdown-rendered h3,
.cm-header-3 {{
  color: var(--h3-color);
  font-weight: 700;
}}

.markdown-rendered h4,
.cm-header-4 {{
  color: var(--h4-color);
  font-weight: 600;
}}

.markdown-rendered h5,
.cm-header-5 {{
  color: var(--h5-color);
  font-weight: 600;
}}

.markdown-rendered h6,
.cm-header-6 {{
  color: var(--h6-color);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}}

/* Callouts */
.callout {{
  background-color: var(--background-secondary);
  border: 1px solid var(--background-modifier-border);
  border-left: 3px solid rgb(var(--callout-color, var(--callout-default)));
  border-radius: 6px;
}}

.callout-title {{
  color: rgb(var(--callout-color, var(--callout-default)));
  font-weight: 700;
}}

/* Tables */
.markdown-rendered table {{
  border-collapse: collapse;
  border: 1px solid var(--table-border-color);
}}

.markdown-rendered thead tr {{
  background-color: var(--table-header-background);
}}

.markdown-rendered th,
.markdown-rendered td {{
  border: 1px solid var(--table-border-color);
  padding: 0.45em 0.75em;
}}

.markdown-rendered tbody tr:nth-child(even) {{
  background-color: var(--table-row-alt-background);
}}

/* Code blocks */
.markdown-rendered pre,
.markdown-rendered code {{
  background-color: var(--code-background);
  color: var(--code-normal);
  border-radius: 4px;
}}

.markdown-rendered pre {{
  border: 1px solid var(--background-modifier-border);
  padding: 0.85em 1em;
}}

/* Navigation & tags */
.nav-file-title.is-active,
.nav-folder-title.is-active {{
  background-color: var(--nav-item-background-active);
  border-left: 2px solid var(--rfs-accent-line);
  color: var(--nav-item-color-active);
}}

a.tag {{
  background-color: var(--tag-background);
  color: var(--tag-color);
  border: 1px solid var(--tag-border-color);
  border-radius: 4px;
  padding: 1px 6px;
}}

a.tag:hover {{
  background-color: var(--tag-background-hover);
  color: var(--tag-color-hover);
}}

/* Scrollbars */
::-webkit-scrollbar {{
  width: 8px;
  height: 8px;
}}

::-webkit-scrollbar-track {{
  background: var(--scrollbar-bg);
}}

::-webkit-scrollbar-thumb {{
  background-color: var(--scrollbar-thumb-bg);
  border-radius: 4px;
}}

::-webkit-scrollbar-thumb:hover {{
  background-color: var(--scrollbar-active-thumb-bg);
}}
"""


def _build_obsidian_snippet(v: dict) -> str:
    selector = ".theme-dark" if v["mode"] == "dark" else ".theme-light"
    return f"""/*
 * {v["name"]} ({v["lx"]} · {v["accentRole"]}) — Standalone Obsidian CSS Snippet
 * Author: {AUTHOR} · {BRAND_NAME} v{v["version"]}
 * Drop into <vault>/.obsidian/snippets/ and enable in Settings -> Appearance -> CSS snippets.
 */

{selector} {{
{_obsidian_vars_block(v)}
}}

{selector} .workspace-tab-header.is-active {{
  box-shadow: inset 0 2px 0 0 var(--rfs-accent-line);
  background-image: linear-gradient(90deg in oklab, var(--rfs-beam-start), var(--rfs-beam-end));
  background-size: 100% 2px;
  background-repeat: no-repeat;
  background-position: top;
}}
"""


def _obsidian_copy_snippet(v: dict) -> str:
    ui = v["ui"]
    selector = ".theme-dark" if v["mode"] == "dark" else ".theme-light"
    return (
        f"/* {v['name']} ({v['lx']}) — Obsidian CSS Snippet */\n"
        f"{selector} {{\n"
        f"  --background-primary: {ui['bg']};\n"
        f"  --background-secondary: {ui['surface']};\n"
        f"  --background-modifier-border: {ui['border']};\n"
        f"  --text-normal: {ui['text']};\n"
        f"  --text-muted: {ui['mute']};\n"
        f"  --interactive-accent: {ui['accent_fill']};\n"
        f"  --text-accent: {ui['accent']};\n"
        f"  --link-color: {ui['accent']};\n"
        f"  --tag-color: {ui['secondary']};\n"
        f"  --code-background: {ui['code_bg']};\n"
        f"}}"
    )


def build_obsidian() -> dict:
    slug = "obsidian"
    app_name = "Obsidian"
    category = "Notes & Writing"
    homepage = "https://obsidian.md/"
    fmt = "Obsidian Theme (manifest.json + theme.css)"
    install = "Copy manifest.json + theme.css into .obsidian/themes/Cyclorama Dawn/"
    install_steps = [
        "Copy `manifest.json` and `theme.css` into your vault's `.obsidian/themes/Cyclorama Dawn/` folder.",
        "Open Obsidian -> Settings -> Appearance -> Themes and select **Cyclorama Dawn**.",
        "Use Base color scheme to switch between **Cyclorama Dawn** (`LX 263` Dark) and **Cyclorama Day** (`LX 512` Light), or enable `snippets/cyclorama-steel.css` (or Style Settings) for **Cyclorama Steel**.",
    ]

    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    manifest = {
        "name": BRAND_NAME,
        "version": ver,
        "minAppVersion": "1.5.0",
        "author": AUTHOR,
        "authorUrl": REPO_URL,
    }
    _write_json(os.path.join(app_dir, "manifest.json"), manifest)
    _write_text(os.path.join(app_dir, "theme.css"), _build_obsidian_theme_css())

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        _write_text(os.path.join(app_dir, "snippets", f"{vid}.css"), _build_obsidian_snippet(v))
        svg = render_notes_preview(app_name, slug, v)
        write_preview_pair(slug, vid, svg)

    files = [
        {"label": "Theme Manifest", "path": "apps/obsidian/manifest.json"},
        {"label": "Complete Theme CSS", "path": "apps/obsidian/theme.css"},
        {"label": "Dawn Snippet (LX 263)", "path": "apps/obsidian/snippets/cyclorama-dawn.css"},
        {"label": "Steel Snippet (LX 263)", "path": "apps/obsidian/snippets/cyclorama-steel.css"},
        {"label": "Day Snippet (LX 512)", "path": "apps/obsidian/snippets/cyclorama-day.css"},
    ]

    summaries = {
        "cyclorama-dawn": "Matte #050507 dark vault with Beacon Orange links, Steel Blue tags, and AA-calibrated callouts and graph nodes.",
        "cyclorama-steel": "Cool steel-charcoal dark vault with Steel Blue controls and Beacon Orange secondary highlights via Style Settings or snippet.",
        "cyclorama-day": "Crisp #F5F7F9 Alabaster Day light vault with white sidebars, burnt Beacon links, and Steel Blue tags.",
    }

    themes_json = {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": "apps/obsidian/theme.css",
        "files": files,
        "themes": [
            {
                "id": vid,
                "name": VARIANTS[vid]["name"],
                "lx": VARIANTS[vid]["lx"],
                "mode": VARIANTS[vid]["mode"],
                "accentRole": VARIANTS[vid]["accentRole"],
                "tagline": summaries[vid],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": f"apps/{slug}/snippets/{vid}.css",
                "copyLang": "css",
                "copyLabel": "Copy Obsidian CSS Snippet",
                "copySnippet": _obsidian_copy_snippet(VARIANTS[vid]),
                "swatches": _six_swatches(VARIANTS[vid]),
            }
            for vid in VARIANT_ORDER
        ],
    }
    _write_json(os.path.join(app_dir, "themes.json"), themes_json)

    readme = _render_readme(
        app_name=app_name,
        slug=slug,
        homepage=homepage,
        fmt=fmt,
        intro="Full community theme (`manifest.json` + `theme.css`) with built-in Style Settings support and three standalone CSS snippets.",
        install_steps=install_steps,
        files=files,
        variant_notes=summaries,
    )
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
# 2. Chromium (Brave / Chrome / Edge)
# ---------------------------------------------------------------------------

def _build_chromium_manifest(v: dict) -> dict:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    frame_inactive = ui["bg"] if is_dark else mix(ui["rail"], ui["border_subtle"], 0.35)
    frame_incognito = ui["steel_wash"] if is_dark else mix(ui["rail"], ui["overlay"], 0.50)

    return {
        "manifest_version": 3,
        "name": f"{v['name']} ({v['lx']})",
        "version": v["version"],
        "description": f"{v['summary']} ({BRAND_NAME} v{v['version']} by {AUTHOR})",
        "theme": {
            "colors": {
                "frame": list(hex_to_rgb(ui["rail"])),
                "frame_inactive": list(hex_to_rgb(frame_inactive)),
                "frame_incognito": list(hex_to_rgb(frame_incognito)),
                "toolbar": list(hex_to_rgb(ui["surface"])),
                "tab_text": list(hex_to_rgb(ui["text"])),
                "tab_background_text": list(hex_to_rgb(ui["mute"])),
                "tab_background_text_inactive": list(hex_to_rgb(ui["subtle"])),
                "bookmark_text": list(hex_to_rgb(ui["text_soft"])),
                "ntp_background": list(hex_to_rgb(ui["bg"])),
                "ntp_text": list(hex_to_rgb(ui["text"])),
                "ntp_link": list(hex_to_rgb(ui["accent"])),
                "ntp_header": list(hex_to_rgb(ui["surface"])),
                "omnibox_background": list(hex_to_rgb(ui["raised"])),
                "omnibox_text": list(hex_to_rgb(ui["text"])),
                "toolbar_button_icon": list(hex_to_rgb(ui["text_soft"])),
                "button_background": list(hex_to_rgb(ui["raised"])),
            },
            "tints": {
                "buttons": _chromium_tint(ui["accent"]),
                "frame": [-1.0, -1.0, -1.0],
                "frame_inactive": [-1.0, -1.0, -1.0],
                "frame_incognito": [-1.0, -1.0, -1.0],
                "background_tab": [-1.0, -1.0, -1.0],
            },
        },
    }


def build_chromium() -> dict:
    slug = "chromium"
    app_name = "Brave / Chrome / Edge"
    category = "Browsers & Desktop"
    homepage = "https://brave.com/"
    fmt = "Chromium MV3 Browser Theme"
    install = "Extensions -> Developer mode -> Load unpacked variant folder"
    install_steps = [
        "Open `brave://extensions`, `chrome://extensions`, or `edge://extensions` and enable **Developer mode**.",
        "Click **Load unpacked** and select `apps/chromium/cyclorama-dawn` (or `cyclorama-steel` / `cyclorama-day`).",
        "Switch variants anytime by loading another folder or clicking **Reset to default** in Appearance settings.",
    ]

    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    manifests: dict[str, dict] = {}
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        m = _build_chromium_manifest(v)
        manifests[vid] = m
        _write_json(os.path.join(app_dir, vid, "manifest.json"), m)
        svg = render_browser_preview(app_name, slug, v)
        write_preview_pair(slug, vid, svg)

    files = [
        {"label": "Cyclorama Dawn MV3 Manifest", "path": "apps/chromium/cyclorama-dawn/manifest.json"},
        {"label": "Cyclorama Steel MV3 Manifest", "path": "apps/chromium/cyclorama-steel/manifest.json"},
        {"label": "Cyclorama Day MV3 Manifest", "path": "apps/chromium/cyclorama-day/manifest.json"},
    ]

    summaries = {
        "cyclorama-dawn": "Matte #050507 New Tab canvas, #070709 tab strip, #0C0C10 toolbar, and Beacon Orange NTP links & button tint.",
        "cyclorama-steel": "Cool steel-charcoal browser chrome with #131820 omnibox and Steel Blue NTP links & button tint.",
        "cyclorama-day": "Crisp #F5F7F9 Alabaster Day light browser chrome with white toolbar, soft rail frame, and burnt Beacon links.",
    }

    themes_json = {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": "apps/chromium/cyclorama-dawn/manifest.json",
        "files": files,
        "themes": [
            {
                "id": vid,
                "name": VARIANTS[vid]["name"],
                "lx": VARIANTS[vid]["lx"],
                "mode": VARIANTS[vid]["mode"],
                "accentRole": VARIANTS[vid]["accentRole"],
                "tagline": summaries[vid],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": f"apps/{slug}/{vid}/manifest.json",
                "copyLang": "json",
                "copyLabel": "Copy MV3 manifest.json",
                "copySnippet": json.dumps(manifests[vid], indent=2, ensure_ascii=False),
                "swatches": _six_swatches(VARIANTS[vid]),
            }
            for vid in VARIANT_ORDER
        ],
    }
    _write_json(os.path.join(app_dir, "themes.json"), themes_json)

    readme = _render_readme(
        app_name=app_name,
        slug=slug,
        homepage=homepage,
        fmt=fmt,
        intro="Three unpacked Manifest V3 browser themes for Chromium-based browsers (Brave, Chrome, Edge, Vivaldi).",
        install_steps=install_steps,
        files=files,
        variant_notes=summaries,
    )
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
# 3. Discord (Vencord / BetterDiscord)
# ---------------------------------------------------------------------------

def _build_discord_css(v: dict) -> str:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    selector = ".theme-dark" if is_dark else ".theme-light"
    hover_bg = _rgba(ui["overlay"], 0.55 if is_dark else 0.45)
    active_bg = _rgba(ui["accent"], 0.16 if is_dark else 0.14)
    selected_bg = mix(ui["surface"], ui["accent"], 0.16 if is_dark else 0.12)
    mention_bg = _rgba(ui["accent"], 0.14 if is_dark else 0.12)

    return f"""/**
 * @name {v["name"]}
 * @author {AUTHOR}
 * @version {v["version"]}
 * @description {v["summary"]} ({v["lx"]} · {v["accentRole"]})
 * @source {REPO_URL}
 * @website {GALLERY_URL}
 */

{selector} {{
  /* Background Overlays */
  --bg-overlay-app-frame: {ui["rail"]};
  --bg-overlay-floating: {ui["surface"]};
  --bg-overlay-chat: {ui["bg"]};
  --bg-overlay-home: {ui["bg"]};
  --bg-overlay-selected: {selected_bg};
  --bg-overlay-hover: {hover_bg};
  --bg-overlay-active: {active_bg};
  --bg-overlay-1: {ui["surface"]};
  --bg-overlay-2: {ui["raised"]};
  --bg-overlay-3: {ui["overlay"]};
  --bg-overlay-4: {ui["rail"]};

  /* Core Backgrounds */
  --background-primary: {ui["bg"]};
  --background-secondary: {ui["surface"]};
  --background-secondary-alt: {ui["rail"]};
  --background-tertiary: {ui["rail"]};
  --background-accent: {ui["raised"]};
  --background-floating: {ui["surface"]};
  --background-nested-floating: {ui["raised"]};
  --background-mobile-primary: {ui["bg"]};
  --background-mobile-secondary: {ui["surface"]};
  --background-modifier-hover: {hover_bg};
  --background-modifier-active: {active_bg};
  --background-modifier-selected: {selected_bg};
  --background-modifier-accent: {ui["border"]};
  --background-mentioned: {mention_bg};
  --background-mentioned-hover: {_rgba(ui["accent"], 0.22 if is_dark else 0.18)};
  --home-background: {ui["bg"]};

  /* Composer & Inputs */
  --channeltextarea-background: {ui["raised"]};
  --input-background: {ui["raised"]};
  --input-placeholder-text: {ui["subtle"]};
  --textbox-markdown-syntax: {ui["mute"]};

  /* Typography & Links */
  --text-normal: {ui["text"]};
  --text-muted: {ui["mute"]};
  --text-link: {ui["accent"]};
  --text-positive: {ui["signal"]};
  --text-warning: {ui["warning"]};
  --text-danger: {ui["fault"]};
  --text-brand: {ui["accent"]};
  --header-primary: {ui["text"]};
  --header-secondary: {ui["text_soft"]};
  --channels-default: {ui["mute"]};
  --channel-icon: {ui["subtle"]};
  --interactive-normal: {ui["text_soft"]};
  --interactive-hover: {ui["text"]};
  --interactive-active: {ui["text"]};
  --interactive-muted: {ui["subtle"]};

  /* Brand & Accent Controls */
  --brand-experiment: {ui["accent_fill"]};
  --brand-experiment-500: {ui["accent_fill"]};
  --brand-experiment-560: {ui["accent_fill_hover"]};
  --brand-experiment-600: {ui["accent_fill_hover"]};
  --brand-500: {ui["accent_fill"]};
  --brand-560: {ui["accent_fill_hover"]};
  --brand-600: {ui["accent_fill_hover"]};
  --control-brand-foreground: {ui["accent"]};
  --focus-primary: {ui["accent"]};

  /* Semantic Status */
  --status-positive: {ui["signal"]};
  --status-positive-background: {ui["signal"]};
  --status-warning: {ui["warning"]};
  --status-warning-background: {ui["warning"]};
  --status-danger: {ui["fault"]};
  --status-danger-background: {ui["fault_fill"]};
  --info-warning-foreground: {ui["warning"]};
  --info-danger-foreground: {ui["fault"]};
  --info-positive-foreground: {ui["signal"]};
  --info-help-foreground: {ui["secondary"]};

  /* Scrollbars */
  --scrollbar-thin-thumb: {ui["border"]};
  --scrollbar-thin-track: transparent;
  --scrollbar-auto-thumb: {ui["border_strong"]};
  --scrollbar-auto-track: {ui["rail"]};
  --scrollbar-auto-scrollbar-color-thumb: {ui["border_strong"]};
  --scrollbar-auto-scrollbar-color-track: {ui["rail"]};
}}

/* Crisp code blocks, embeds & selection */
{selector} pre,
{selector} code {{
  background-color: {ui["code_bg"]} !important;
  border-color: {ui["border"]} !important;
}}

{selector} ::selection {{
  background-color: {ui["selection_active"]};
  color: {ui["text"]};
}}

{selector} [class*="embedFull"] {{
  background-color: {ui["surface"]};
  border-color: {ui["border"]};
}}
"""


def _discord_copy_snippet(v: dict) -> str:
    ui = v["ui"]
    selector = ".theme-dark" if v["mode"] == "dark" else ".theme-light"
    return (
        f"/* {v['name']} ({v['lx']}) — Discord Quick CSS */\n"
        f"{selector} {{\n"
        f"  --background-primary: {ui['bg']};\n"
        f"  --background-secondary: {ui['surface']};\n"
        f"  --background-tertiary: {ui['rail']};\n"
        f"  --channeltextarea-background: {ui['raised']};\n"
        f"  --text-normal: {ui['text']};\n"
        f"  --text-muted: {ui['mute']};\n"
        f"  --text-link: {ui['accent']};\n"
        f"  --brand-experiment: {ui['accent_fill']};\n"
        f"  --brand-500: {ui['accent_fill']};\n"
        f"}}"
    )


def build_discord() -> dict:
    slug = "discord"
    app_name = "Discord (Vencord / BetterDiscord)"
    category = "Browsers & Desktop"
    homepage = "https://vencord.dev/"
    fmt = "Vencord / BetterDiscord .theme.css"
    install = "Drop .theme.css into Vencord/BetterDiscord themes folder and enable"
    install_steps = [
        "Open Discord -> Settings -> **Themes** (Vencord or BetterDiscord) -> **Open Themes Folder**.",
        "Copy `cyclorama-dawn.theme.css`, `cyclorama-steel.theme.css`, or `cyclorama-day.theme.css` into the folder.",
        "Enable the theme in Settings -> Themes (match Discord Appearance to Dark for Dawn/Steel, Light for Day).",
    ]

    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        _write_text(os.path.join(app_dir, f"{vid}.theme.css"), _build_discord_css(v))
        svg = render_chat_preview(app_name, slug, v)
        write_preview_pair(slug, vid, svg)

    files = [
        {"label": "Cyclorama Dawn Theme CSS", "path": "apps/discord/cyclorama-dawn.theme.css"},
        {"label": "Cyclorama Steel Theme CSS", "path": "apps/discord/cyclorama-steel.theme.css"},
        {"label": "Cyclorama Day Theme CSS", "path": "apps/discord/cyclorama-day.theme.css"},
    ]

    summaries = {
        "cyclorama-dawn": "Matte #050507 chat canvas with #0C0C10 channel rail, Beacon Orange links/mentions, and Signal status indicators.",
        "cyclorama-steel": "Cool steel-charcoal Discord theme with Steel Blue brand buttons, #131820 composer, and high-contrast channel lists.",
        "cyclorama-day": "Alabaster Day #F5F7F9 light chat workspace with white channel sidebar, burnt Beacon links, and Steel brand buttons.",
    }

    themes_json = {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": "apps/discord/cyclorama-dawn.theme.css",
        "files": files,
        "themes": [
            {
                "id": vid,
                "name": VARIANTS[vid]["name"],
                "lx": VARIANTS[vid]["lx"],
                "mode": VARIANTS[vid]["mode"],
                "accentRole": VARIANTS[vid]["accentRole"],
                "tagline": summaries[vid],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": f"apps/{slug}/{vid}.theme.css",
                "copyLang": "css",
                "copyLabel": "Copy Discord Quick CSS",
                "copySnippet": _discord_copy_snippet(VARIANTS[vid]),
                "swatches": _six_swatches(VARIANTS[vid]),
            }
            for vid in VARIANT_ORDER
        ],
    }
    _write_json(os.path.join(app_dir, "themes.json"), themes_json)

    readme = _render_readme(
        app_name=app_name,
        slug=slug,
        homepage=homepage,
        fmt=fmt,
        intro="Three drop-in `.theme.css` files compatible with Vencord and BetterDiscord.",
        install_steps=install_steps,
        files=files,
        variant_notes=summaries,
    )
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
# 4. qBittorrent
# ---------------------------------------------------------------------------

def _build_qbittorrent_qss(v: dict) -> str:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    sel_bg = mix(ui["surface"], ui["accent"], 0.18 if is_dark else 0.14)
    alt_row = ui["surface"] if is_dark else ui["list"]

    return f"""/*
 * {v["name"]} ({v["lx"]} · {v["accentRole"]}) — qBittorrent Qt QSS Stylesheet
 * Author: {AUTHOR} · {BRAND_NAME} v{v["version"]}
 * Source: {REPO_URL}
 */

QWidget {{
  background-color: {ui["bg"]};
  color: {ui["text"]};
  selection-background-color: {sel_bg};
  selection-color: {ui["text"]};
}}

QMainWindow {{
  background-color: {ui["bg"]};
  color: {ui["text"]};
}}

QMenuBar {{
  background-color: {ui["rail"]};
  color: {ui["text_soft"]};
  border-bottom: 1px solid {ui["border"]};
  spacing: 4px;
  padding: 2px 4px;
}}

QMenuBar::item {{
  background: transparent;
  padding: 4px 8px;
  border-radius: 4px;
}}

QMenuBar::item:selected {{
  background-color: {ui["raised"]};
  color: {ui["text"]};
}}

QMenu {{
  background-color: {ui["surface"]};
  color: {ui["text"]};
  border: 1px solid {ui["border"]};
  padding: 4px;
}}

QMenu::item {{
  padding: 5px 22px 5px 12px;
  border-radius: 4px;
}}

QMenu::item:selected {{
  background-color: {sel_bg};
  color: {ui["text"]};
}}

QMenu::separator {{
  height: 1px;
  background-color: {ui["border_subtle"]};
  margin: 4px 8px;
}}

QToolBar {{
  background-color: {ui["surface"]};
  border-bottom: 1px solid {ui["border"]};
  spacing: 4px;
  padding: 3px 6px;
}}

QToolButton {{
  background-color: transparent;
  color: {ui["text_soft"]};
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 4px 6px;
}}

QToolButton:hover {{
  background-color: {ui["raised"]};
  border-color: {ui["border"]};
  color: {ui["text"]};
}}

QToolButton:checked {{
  background-color: {sel_bg};
  border-color: {ui["accent"]};
  color: {ui["text"]};
}}

QHeaderView::section {{
  background-color: {ui["rail"]};
  color: {ui["mute"]};
  border: none;
  border-right: 1px solid {ui["border_subtle"]};
  border-bottom: 1px solid {ui["border"]};
  padding: 5px 8px;
  font-weight: 600;
}}

QHeaderView::section:hover {{
  background-color: {ui["raised"]};
  color: {ui["text"]};
}}

QTreeView,
QTableView {{
  background-color: {ui["bg"]};
  alternate-background-color: {alt_row};
  color: {ui["text"]};
  gridline-color: {ui["border_subtle"]};
  border: 1px solid {ui["border"]};
  outline: 0;
}}

QTreeView::item,
QTableView::item {{
  padding: 4px 6px;
}}

QTreeView::item:hover,
QTableView::item:hover {{
  background-color: {ui["raised"]};
}}

QTreeView::item:selected,
QTableView::item:selected {{
  background-color: {sel_bg};
  color: {ui["text"]};
}}

QTabWidget::pane {{
  border: 1px solid {ui["border"]};
  background-color: {ui["surface"]};
}}

QTabBar::tab {{
  background-color: {ui["rail"]};
  color: {ui["mute"]};
  border: 1px solid {ui["border_subtle"]};
  border-bottom: none;
  padding: 6px 12px;
  margin-right: 2px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
}}

QTabBar::tab:hover {{
  background-color: {ui["raised"]};
  color: {ui["text"]};
}}

QTabBar::tab:selected {{
  background-color: {ui["surface"]};
  color: {ui["text"]};
  border-color: {ui["border"]};
  border-top: 2px solid {ui["accent"]};
}}

QProgressBar {{
  background-color: {ui["raised"]};
  color: {ui["text"]};
  border: 1px solid {ui["border"]};
  border-radius: 4px;
  text-align: center;
  min-height: 14px;
}}

QProgressBar::chunk {{
  background-color: {ui["accent_fill"]};
  border-radius: 3px;
}}

QPushButton {{
  background-color: {ui["raised"]};
  color: {ui["text"]};
  border: 1px solid {ui["border"]};
  border-radius: 4px;
  padding: 5px 12px;
}}

QPushButton:hover {{
  background-color: {ui["overlay"]};
  border-color: {ui["accent"]};
}}

QPushButton:pressed {{
  background-color: {ui["accent_fill"]};
  border-color: {ui["accent_fill"]};
  color: {ui["on_accent"]};
}}

QPushButton:disabled {{
  background-color: {ui["surface"]};
  color: {ui["subtle"]};
  border-color: {ui["border_subtle"]};
}}

QLineEdit,
QComboBox {{
  background-color: {ui["raised"]};
  color: {ui["text"]};
  border: 1px solid {ui["border"]};
  border-radius: 4px;
  padding: 4px 8px;
}}

QLineEdit:focus,
QComboBox:focus {{
  border-color: {ui["accent"]};
}}

QComboBox QAbstractItemView {{
  background-color: {ui["surface"]};
  color: {ui["text"]};
  border: 1px solid {ui["border"]};
  selection-background-color: {sel_bg};
  selection-color: {ui["text"]};
}}

QScrollBar:vertical {{
  background: {ui["rail"]};
  width: 10px;
  margin: 0;
}}

QScrollBar::handle:vertical {{
  background: {ui["border"]};
  min-height: 24px;
  border-radius: 4px;
  margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
  background: {ui["border_strong"]};
}}

QScrollBar:horizontal {{
  background: {ui["rail"]};
  height: 10px;
  margin: 0;
}}

QScrollBar::handle:horizontal {{
  background: {ui["border"]};
  min-width: 24px;
  border-radius: 4px;
  margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
  background: {ui["border_strong"]};
}}

QScrollBar::add-line,
QScrollBar::sub-line {{
  width: 0;
  height: 0;
  border: none;
  background: none;
}}

QStatusBar {{
  background-color: {ui["rail"]};
  color: {ui["text_soft"]};
  border-top: 1px solid {ui["border"]};
}}

QStatusBar::item {{
  border: none;
}}

QSplitter::handle {{
  background-color: {ui["border_subtle"]};
}}

QSplitter::handle:hover {{
  background-color: {ui["accent"]};
}}

QToolTip {{
  background-color: {ui["surface"]};
  color: {ui["text"]};
  border: 1px solid {ui["border_strong"]};
  padding: 4px 6px;
}}
"""


def _build_qbittorrent_config(v: dict) -> dict:
    ui = v["ui"]
    return {
        "colors": {
            "Log.Normal": ui["text"],
            "Log.Info": ui["secondary"],
            "Log.Warning": ui["warning"],
            "Log.Critical": ui["fault"],
            "TransferList.Downloading": ui["secondary"],
            "TransferList.ForcedDownloading": ui["cyan"],
            "TransferList.DownloadingMetadata": ui["cyan"],
            "TransferList.Allocating": ui["warning"],
            "TransferList.StalledDownloading": ui["mute"],
            "TransferList.StalledUploading": ui["subtle"],
            "TransferList.Uploading": ui["signal"],
            "TransferList.ForcedUploading": ui["signal"],
            "TransferList.Seeding": ui["signal"],
            "TransferList.Paused": ui["warning"],
            "TransferList.PausedDownloading": ui["warning"],
            "TransferList.PausedUploading": ui["mute"],
            "TransferList.Queued": ui["mute"],
            "TransferList.Checking": ui["accent"],
            "TransferList.CheckingResumeData": ui["accent"],
            "TransferList.Moving": ui["magenta"],
            "TransferList.MissingFiles": ui["fault"],
            "TransferList.Error": ui["fault"],
        }
    }


def build_qbittorrent() -> dict:
    slug = "qbittorrent"
    app_name = "qBittorrent"
    category = "Browsers & Desktop"
    homepage = "https://www.qbittorrent.org/"
    fmt = "Qt QSS Stylesheet + config.json"
    install = "Package stylesheet.qss + config.json into .qbtheme and select in Behavior -> Use custom UI Theme"
    install_steps = [
        "Choose a variant folder (`apps/qbittorrent/cyclorama-dawn/`, `cyclorama-steel/`, or `cyclorama-day/`) containing `stylesheet.qss` and `config.json`.",
        "Bundle into a `.qbtheme` resource bundle with Qt `rcc` (or load `stylesheet.qss` via your qBittorrent theme pack).",
        "Open qBittorrent -> Tools -> Options -> **Behavior** -> enable **Use custom UI Theme**, pick the bundle, and restart.",
    ]

    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    configs: dict[str, dict] = {}
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        v_dir = os.path.join(app_dir, vid)
        _write_text(os.path.join(v_dir, "stylesheet.qss"), _build_qbittorrent_qss(v))
        cfg = _build_qbittorrent_config(v)
        configs[vid] = cfg
        _write_json(os.path.join(v_dir, "config.json"), cfg)
        svg = render_utility_preview(app_name, slug, v, kind="qbittorrent")
        write_preview_pair(slug, vid, svg)

    files = [
        {"label": "Dawn Stylesheet (QSS)", "path": "apps/qbittorrent/cyclorama-dawn/stylesheet.qss"},
        {"label": "Dawn Transfer Palette (JSON)", "path": "apps/qbittorrent/cyclorama-dawn/config.json"},
        {"label": "Steel Stylesheet (QSS)", "path": "apps/qbittorrent/cyclorama-steel/stylesheet.qss"},
        {"label": "Steel Transfer Palette (JSON)", "path": "apps/qbittorrent/cyclorama-steel/config.json"},
        {"label": "Day Stylesheet (QSS)", "path": "apps/qbittorrent/cyclorama-day/stylesheet.qss"},
        {"label": "Day Transfer Palette (JSON)", "path": "apps/qbittorrent/cyclorama-day/config.json"},
    ]

    summaries = {
        "cyclorama-dawn": "Matte #050507 transfer table with Beacon Orange progress bars, Signal green seeding, and Steel Blue active downloads.",
        "cyclorama-steel": "Cool steel-charcoal Qt stylesheet with Steel Blue progress chunks, crisp #27313D gridlines, and Beacon checking states.",
        "cyclorama-day": "Alabaster Day #F5F7F9 light Qt stylesheet with alternating cool rows and WCAG AA transfer status inks.",
    }

    themes_json = {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": "apps/qbittorrent/cyclorama-dawn/stylesheet.qss",
        "files": files,
        "themes": [
            {
                "id": vid,
                "name": VARIANTS[vid]["name"],
                "lx": VARIANTS[vid]["lx"],
                "mode": VARIANTS[vid]["mode"],
                "accentRole": VARIANTS[vid]["accentRole"],
                "tagline": summaries[vid],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": f"apps/{slug}/{vid}/stylesheet.qss",
                "copyLang": "json",
                "copyLabel": "Copy config.json Palette",
                "copySnippet": json.dumps(configs[vid], indent=2, ensure_ascii=False),
                "swatches": _six_swatches(VARIANTS[vid]),
            }
            for vid in VARIANT_ORDER
        ],
    }
    _write_json(os.path.join(app_dir, "themes.json"), themes_json)

    readme = _render_readme(
        app_name=app_name,
        slug=slug,
        homepage=homepage,
        fmt=fmt,
        intro="Three Qt QSS stylesheets paired with qBittorrent `config.json` transfer-list and log color palettes.",
        install_steps=install_steps,
        files=files,
        variant_notes=summaries,
    )
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
# 5. Flow Launcher
# ---------------------------------------------------------------------------

def _build_flow_launcher_xaml(v: dict) -> str:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    sel_bg = mix(ui["surface"], ui["accent"], 0.18 if is_dark else 0.14)

    return f"""<?xml version="1.0" encoding="utf-8"?>
<!--
  {v["name"]} ({v["lx"]} · {v["accentRole"]}) — Flow Launcher WPF XAML Theme
  Author: {AUTHOR} · {BRAND_NAME} v{v["version"]}
  Source: {REPO_URL}
-->
<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
    <ResourceDictionary.MergedDictionaries>
        <ResourceDictionary Source="pack://application:,,,/Themes/Base.xaml" />
    </ResourceDictionary.MergedDictionaries>

    <!-- Selected Row Background Brush -->
    <SolidColorBrush x:Key="ItemSelectedBackgroundColor" Color="{argb_hex(sel_bg, 'FF')}" />

    <!-- Base Query TextBox -->
    <Style x:Key="BaseQueryTextBoxStyle" TargetType="{{x:Type TextBox}}">
        <Setter Property="Background" Value="{argb_hex(ui['raised'], 'FF')}" />
        <Setter Property="Foreground" Value="{argb_hex(ui['text'], 'FF')}" />
        <Setter Property="CaretBrush" Value="{argb_hex(ui['cursor'], 'FF')}" />
        <Setter Property="SelectionBrush" Value="{argb_hex(ui['selection_active'], 'FF')}" />
        <Setter Property="BorderBrush" Value="{argb_hex(ui['border'], 'FF')}" />
        <Setter Property="BorderThickness" Value="0" />
        <Setter Property="FontSize" Value="24" />
        <Setter Property="Padding" Value="6,4" />
    </Style>

    <!-- Active Query Input Box -->
    <Style x:Key="QueryBoxStyle" BasedOn="{{StaticResource BaseQueryTextBoxStyle}}" TargetType="{{x:Type TextBox}}">
        <Setter Property="Background" Value="Transparent" />
        <Setter Property="Foreground" Value="{argb_hex(ui['text'], 'FF')}" />
        <Setter Property="CaretBrush" Value="{argb_hex(ui['cursor'], 'FF')}" />
        <Setter Property="SelectionBrush" Value="{argb_hex(ui['selection_active'], 'FF')}" />
    </Style>

    <!-- Autocomplete Suggestion Overlay -->
    <Style x:Key="QuerySuggestionBoxStyle" BasedOn="{{StaticResource BaseQueryTextBoxStyle}}" TargetType="{{x:Type TextBox}}">
        <Setter Property="Background" Value="Transparent" />
        <Setter Property="Foreground" Value="{argb_hex(ui['subtle'], 'FF')}" />
    </Style>

    <!-- Outer Spotlight Frame & Window -->
    <Style x:Key="WindowBorderStyle" TargetType="{{x:Type Border}}">
        <Setter Property="Background" Value="{argb_hex(ui['bg'], 'F5')}" />
        <Setter Property="BorderBrush" Value="{argb_hex(ui['border_strong'], 'FF')}" />
        <Setter Property="BorderThickness" Value="1" />
        <Setter Property="CornerRadius" Value="10" />
        <Setter Property="UseLayoutRounding" Value="True" />
    </Style>

    <Style x:Key="WindowStyle" TargetType="{{x:Type Window}}">
        <Setter Property="Background" Value="{argb_hex(ui['bg'], 'F5')}" />
        <Setter Property="Foreground" Value="{argb_hex(ui['text'], 'FF')}" />
        <Setter Property="Width" Value="620" />
    </Style>

    <!-- Pending Activity Accent Line -->
    <Style x:Key="PendingLineStyle" TargetType="{{x:Type Line}}">
        <Setter Property="Stroke" Value="{argb_hex(ui['accent'], 'FF')}" />
        <Setter Property="StrokeThickness" Value="2" />
    </Style>

    <!-- Result Item Typography -->
    <Style x:Key="ItemTitleStyle" TargetType="{{x:Type TextBlock}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['text_soft'], 'FF')}" />
        <Setter Property="FontSize" Value="15" />
        <Setter Property="FontWeight" Value="SemiBold" />
    </Style>

    <Style x:Key="ItemSubTitleStyle" TargetType="{{x:Type TextBlock}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['mute'], 'FF')}" />
        <Setter Property="FontSize" Value="12" />
    </Style>

    <Style x:Key="ItemTitleSelectedStyle" TargetType="{{x:Type TextBlock}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['text'], 'FF')}" />
        <Setter Property="FontSize" Value="15" />
        <Setter Property="FontWeight" Value="Bold" />
    </Style>

    <Style x:Key="ItemSubTitleSelectedStyle" TargetType="{{x:Type TextBlock}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['accent'], 'FF')}" />
        <Setter Property="FontSize" Value="12" />
    </Style>

    <!-- Match Highlight & Divider -->
    <Style x:Key="HighlightStyle" TargetType="{{x:Type Run}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['accent'], 'FF')}" />
        <Setter Property="FontWeight" Value="Bold" />
    </Style>

    <Style x:Key="SeparatorStyle" TargetType="{{x:Type Rectangle}}">
        <Setter Property="Fill" Value="{argb_hex(ui['border'], 'FF')}" />
        <Setter Property="Height" Value="1" />
        <Setter Property="Margin" Value="12,4,12,4" />
    </Style>

    <!-- Scrollbar & Thumb -->
    <Style x:Key="ThumbStyle" TargetType="{{x:Type Thumb}}">
        <Setter Property="Background" Value="{argb_hex(ui['border_strong'], 'CC')}" />
        <Setter Property="Template">
            <Setter.Value>
                <ControlTemplate TargetType="{{x:Type Thumb}}">
                    <Border Background="{{TemplateBinding Background}}" CornerRadius="3" />
                </ControlTemplate>
            </Setter.Value>
        </Setter>
    </Style>

    <Style x:Key="ScrollBarStyle" TargetType="{{x:Type ScrollBar}}">
        <Setter Property="Background" Value="{argb_hex(ui['rail'], 'FF')}" />
        <Setter Property="Width" Value="6" />
        <Setter Property="Margin" Value="0,4,4,4" />
    </Style>

    <!-- Clock & Date Readout -->
    <Style x:Key="ClockBox" TargetType="{{x:Type TextBlock}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['secondary'], 'FF')}" />
        <Setter Property="FontSize" Value="12" />
        <Setter Property="FontWeight" Value="SemiBold" />
        <Setter Property="VerticalAlignment" Value="Center" />
    </Style>

    <Style x:Key="DateBox" TargetType="{{x:Type TextBlock}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['mute'], 'FF')}" />
        <Setter Property="FontSize" Value="11" />
        <Setter Property="VerticalAlignment" Value="Center" />
    </Style>
</ResourceDictionary>
"""


def _flow_copy_snippet(v: dict) -> str:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    sel_bg = mix(ui["surface"], ui["accent"], 0.18 if is_dark else 0.14)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
    <ResourceDictionary.MergedDictionaries>
        <ResourceDictionary Source="pack://application:,,,/Themes/Base.xaml" />
    </ResourceDictionary.MergedDictionaries>
    <SolidColorBrush x:Key="ItemSelectedBackgroundColor" Color="{argb_hex(sel_bg, 'FF')}" />
    <Style x:Key="WindowBorderStyle" TargetType="{{x:Type Border}}">
        <Setter Property="Background" Value="{argb_hex(ui['bg'], 'F5')}" />
        <Setter Property="BorderBrush" Value="{argb_hex(ui['border_strong'], 'FF')}" />
        <Setter Property="BorderThickness" Value="1" />
        <Setter Property="CornerRadius" Value="10" />
    </Style>
    <Style x:Key="WindowStyle" TargetType="{{x:Type Window}}">
        <Setter Property="Background" Value="{argb_hex(ui['bg'], 'F5')}" />
        <Setter Property="Foreground" Value="{argb_hex(ui['text'], 'FF')}" />
    </Style>
    <Style x:Key="QueryBoxStyle" BasedOn="{{StaticResource BaseQueryTextBoxStyle}}" TargetType="{{x:Type TextBox}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['text'], 'FF')}" />
        <Setter Property="CaretBrush" Value="{argb_hex(ui['cursor'], 'FF')}" />
    </Style>
    <Style x:Key="ItemTitleStyle" TargetType="{{x:Type TextBlock}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['text_soft'], 'FF')}" />
    </Style>
    <Style x:Key="ItemTitleSelectedStyle" TargetType="{{x:Type TextBlock}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['text'], 'FF')}" />
    </Style>
    <Style x:Key="ItemSubTitleSelectedStyle" TargetType="{{x:Type TextBlock}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['accent'], 'FF')}" />
    </Style>
    <Style x:Key="HighlightStyle" TargetType="{{x:Type Run}}">
        <Setter Property="Foreground" Value="{argb_hex(ui['accent'], 'FF')}" />
    </Style>
    <Style x:Key="SeparatorStyle" TargetType="{{x:Type Rectangle}}">
        <Setter Property="Fill" Value="{argb_hex(ui['border'], 'FF')}" />
    </Style>
</ResourceDictionary>"""


def build_flow_launcher() -> dict:
    slug = "flow-launcher"
    app_name = "Flow Launcher"
    category = "Browsers & Desktop"
    homepage = "https://www.flowlauncher.com/"
    fmt = "WPF XAML Theme"
    install = "Copy .xaml files to %APPDATA%\\FlowLauncher\\Themes\\ and choose in Settings -> Appearance"
    install_steps = [
        "Copy `Cyclorama Dawn.xaml`, `Cyclorama Steel.xaml`, and `Cyclorama Day.xaml` into `%APPDATA%\\FlowLauncher\\Themes\\`.",
        "Restart Flow Launcher and open **Settings -> Appearance -> Theme**.",
        "Select **Cyclorama Dawn**, **Cyclorama Steel**, or **Cyclorama Day**.",
    ]

    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    filenames = {
        "cyclorama-dawn": "Cyclorama Dawn.xaml",
        "cyclorama-steel": "Cyclorama Steel.xaml",
        "cyclorama-day": "Cyclorama Day.xaml",
    }

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        xaml = _build_flow_launcher_xaml(v)
        ET.fromstring(xaml)
        _write_text(os.path.join(app_dir, filenames[vid]), xaml)
        svg = render_utility_preview(app_name, slug, v, kind="launcher")
        write_preview_pair(slug, vid, svg)

    files = [
        {"label": "Cyclorama Dawn XAML (LX 263)", "path": f"apps/{slug}/{filenames['cyclorama-dawn']}"},
        {"label": "Cyclorama Steel XAML (LX 263)", "path": f"apps/{slug}/{filenames['cyclorama-steel']}"},
        {"label": "Cyclorama Day XAML (LX 512)", "path": f"apps/{slug}/{filenames['cyclorama-day']}"},
    ]

    summaries = {
        "cyclorama-dawn": "Matte #050507 spotlight dialog with crisp #62646D frame, Beacon Orange caret/matches, and Steel Blue clock readout.",
        "cyclorama-steel": "Cool steel-charcoal spotlight window with Steel Blue selection accent, crisp separators, and Beacon Orange clock readout.",
        "cyclorama-day": "Alabaster Day #F5F7F9 light spotlight dialog with high-contrast dark ink and burnt Beacon match highlights.",
    }

    themes_json = {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": f"apps/{slug}/{filenames['cyclorama-dawn']}",
        "files": files,
        "themes": [
            {
                "id": vid,
                "name": VARIANTS[vid]["name"],
                "lx": VARIANTS[vid]["lx"],
                "mode": VARIANTS[vid]["mode"],
                "accentRole": VARIANTS[vid]["accentRole"],
                "tagline": summaries[vid],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": f"apps/{slug}/{filenames[vid]}",
                "copyLang": "xml",
                "copyLabel": "Copy WPF XAML Theme",
                "copySnippet": _flow_copy_snippet(VARIANTS[vid]),
                "swatches": _six_swatches(VARIANTS[vid]),
            }
            for vid in VARIANT_ORDER
        ],
    }
    _write_json(os.path.join(app_dir, "themes.json"), themes_json)

    readme = _render_readme(
        app_name=app_name,
        slug=slug,
        homepage=homepage,
        fmt=fmt,
        intro="Three native WPF `ResourceDictionary` `.xaml` themes ready to drop into `%APPDATA%\\FlowLauncher\\Themes\\`.",
        install_steps=install_steps,
        files=files,
        variant_notes=summaries,
    )
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
# Entrypoint
# ---------------------------------------------------------------------------

def build() -> list[dict]:
    """Generate all 5 desktop/notes/browser/chat app ports and return manifest entries."""
    return [
        build_obsidian(),
        build_chromium(),
        build_discord(),
        build_qbittorrent(),
        build_flow_launcher(),
    ]


def verify_generated() -> None:
    """Validate every generated JSON, XAML, CSS, and SVG pair."""
    desktop_slugs = ("obsidian", "chromium", "discord", "qbittorrent", "flow-launcher")
    json_count = 0
    xaml_count = 0
    css_count = 0
    svg_count = 0

    for slug in desktop_slugs:
        app_dir = os.path.join(ROOT, "apps", slug)
        for root, _, filenames in os.walk(app_dir):
            for fn in filenames:
                fp = os.path.join(root, fn)
                with open(fp, "rb") as fh:
                    raw = fh.read()
                if b"\r\n" in raw:
                    raise AssertionError(f"CRLF detected in {fp}")
                text = raw.decode("utf-8")
                if fn.endswith(".json"):
                    parsed = json.loads(text)
                    json_count += 1
                    if fn == "themes.json":
                        for t in parsed.get("themes", []):
                            if t.get("copyLang") == "xml":
                                ET.fromstring(t["copySnippet"])
                elif fn.endswith(".xaml"):
                    ET.fromstring(text)
                    xaml_count += 1
                elif fn.endswith(".css"):
                    if "in oklch" in text:
                        raise AssertionError(f"Forbidden 'in oklch' found in {fp}")
                    css_count += 1
                elif fn.endswith(".svg"):
                    ET.fromstring(text)
                    svg_count += 1

        for vid in VARIANT_ORDER:
            p1 = os.path.join(ROOT, "apps", slug, "previews", f"{vid}.svg")
            p2 = os.path.join(ROOT, "docs", "assets", "previews", slug, f"{vid}.svg")
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                if f1.read() != f2.read():
                    raise AssertionError(f"Preview mismatch: {p1} != {p2}")

    print(
        f"[ok] verified {len(desktop_slugs)} desktop app ports: "
        f"{json_count} JSON, {xaml_count} XAML, {css_count} CSS, {svg_count} SVG files (all LF, zero oklch)"
    )


if __name__ == "__main__":
    entries = build()
    print(f"[ok] generated {len(entries)} desktop app ports: {', '.join(e['slug'] for e in entries)}")
    verify_generated()
