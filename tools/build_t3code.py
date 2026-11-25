#!/usr/bin/env python3
"""Generate Cyclorama Dawn v2.1.0 T3 Code v1 themes, previews, and metadata.

Generates deterministic, WCAG AA calibrated T3 Code v1 theme ports (UTF-8 LF) in
apps/t3code/:
  - cyclorama-dawn.json   (LX 263 Dark  · Beacon Orange accent)
  - cyclorama-steel.json  (LX 263 Dark  · Steel Blue accent)
  - cyclorama-day.json    (LX 512 Light · Alabaster Day light mode)
  - previews/cyclorama-{dawn,steel,day}.svg (+ docs/assets/previews/t3code/)
  - themes.json
  - README.md

Zero external dependencies (Python 3.11+ standard library only).
Zero hardcoded hex literals — every color derives from tools/rfs_palette.py.
"""
from __future__ import annotations

from html import escape
import json
import os
import re
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from rfs_palette import (  # noqa: E402
    AUTHOR,
    BRAND_NAME,
    GALLERY_URL,
    ROOT,
    VARIANT_ORDER,
    VARIANTS,
    contrast,
    mix,
    with_alpha,
)
from svg_previews import (  # noqa: E402
    _frame_shell,
    _standard_swatches,
    write_preview_pair,
)

SLUG = "t3code"
APP_NAME = "T3 Code"
CATEGORY = "Editors & IDEs"
HOMEPAGE = "https://github.com/pingdotgg/t3code"
FORMAT_NAME = "T3 Code Theme JSON + CSS (v1)"
BRAND_REPO_URL = "https://github.com/Real-Fruit-Snacks/rfs-brand"

# Exact 61 official T3 Code v1 THEME_COLOR_ROLES (camelCase, no unknown keys)
THEME_COLOR_ROLES: tuple[str, ...] = (
    "canvas",
    "chrome",
    "toolbar",
    "toolbarForeground",
    "toolbarBorder",
    "toolbarControl",
    "toolbarControlForeground",
    "toolbarControlHover",
    "surface",
    "surfaceRaised",
    "surfaceOverlay",
    "text",
    "textMuted",
    "border",
    "input",
    "focus",
    "accent",
    "accentForeground",
    "secondary",
    "secondaryForeground",
    "muted",
    "mutedForeground",
    "placeholder",
    "secondaryLabel",
    "iconMuted",
    "error",
    "errorForeground",
    "errorSurface",
    "warning",
    "warningForeground",
    "warningSurface",
    "update",
    "updateForeground",
    "updateSurface",
    "accentSurface",
    "accentSurfaceForeground",
    "messageSurface",
    "messageForeground",
    "messageAction",
    "messageActionForeground",
    "messageActionHover",
    "codeBackground",
    "codeForeground",
    "searchMatchBackground",
    "searchMatchForeground",
    "searchMatchActiveBackground",
    "searchMatchActiveForeground",
    "sidebar",
    "sidebarForeground",
    "sidebarMutedForeground",
    "sidebarControlSurface",
    "sidebarRowHover",
    "sidebarRowActive",
    "sidebarRowSelected",
    "sidebarBorder",
    "terminalBackground",
    "terminalForeground",
    "terminalCursor",
    "terminalSelection",
    "terminalScrollbar",
    "terminalScrollbarHover",
)

# Mandatory WCAG AA (>= 4.5:1) foreground/background verification pairs
CONTRAST_PAIRS: tuple[tuple[str, str], ...] = (
    ("text", "canvas"),
    ("text", "surface"),
    ("text", "surfaceRaised"),
    ("text", "surfaceOverlay"),
    ("textMuted", "canvas"),
    ("textMuted", "surface"),
    ("textMuted", "muted"),
    ("mutedForeground", "canvas"),
    ("mutedForeground", "surface"),
    ("mutedForeground", "muted"),
    ("placeholder", "canvas"),
    ("placeholder", "surface"),
    ("placeholder", "muted"),
    ("placeholder", "input"),
    ("secondaryLabel", "canvas"),
    ("secondaryLabel", "surface"),
    ("secondaryLabel", "muted"),
    ("iconMuted", "canvas"),
    ("iconMuted", "surface"),
    ("iconMuted", "muted"),
    ("toolbarForeground", "toolbar"),
    ("toolbarForeground", "toolbarControl"),
    ("toolbarForeground", "toolbarControlHover"),
    ("toolbarControlForeground", "toolbar"),
    ("toolbarControlForeground", "toolbarControl"),
    ("toolbarControlForeground", "toolbarControlHover"),
    ("accentForeground", "accent"),
    ("secondaryForeground", "secondary"),
    ("errorForeground", "errorSurface"),
    ("errorForeground", "canvas"),
    ("warningForeground", "warningSurface"),
    ("warningForeground", "canvas"),
    ("updateForeground", "updateSurface"),
    ("updateForeground", "canvas"),
    ("accentSurfaceForeground", "accentSurface"),
    ("messageForeground", "messageSurface"),
    ("messageActionForeground", "messageAction"),
    ("messageActionForeground", "messageActionHover"),
    ("codeForeground", "codeBackground"),
    ("searchMatchForeground", "searchMatchBackground"),
    ("searchMatchActiveForeground", "searchMatchActiveBackground"),
    ("sidebarForeground", "sidebar"),
    ("sidebarForeground", "sidebarControlSurface"),
    ("sidebarForeground", "sidebarRowHover"),
    ("sidebarForeground", "sidebarRowActive"),
    ("sidebarForeground", "sidebarRowSelected"),
    ("sidebarMutedForeground", "sidebar"),
    ("sidebarMutedForeground", "sidebarControlSurface"),
    ("sidebarMutedForeground", "sidebarRowHover"),
    ("sidebarMutedForeground", "sidebarRowActive"),
    ("sidebarMutedForeground", "sidebarRowSelected"),
    ("terminalForeground", "terminalBackground"),
    ("terminalForeground", "terminalSelection"),
)

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
_HEX6_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_HEX6_8_RE = re.compile(r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")
_FORBIDDEN_CSS_RE = re.compile(
    r"(?:@import\b|image-set\s*\(|(?:^|[^a-zA-Z0-9_-])src\s*\(|url\s*\(|\bin\s+oklch\b)",
    re.I,
)


def _write_text(rel_path: str, content: str) -> str:
    abs_path = os.path.join(ROOT, *rel_path.split("/"))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    return abs_path


def _write_json(rel_path: str, data: object) -> str:
    return _write_text(rel_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _t3code_colors(v: dict) -> dict[str, str]:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    is_dawn = v["id"] == "cyclorama-dawn"

    # Dawn uses vivid Beacon Orange (ui["accent_vivid"]) with matte stage fg (ui["on_vivid"]);
    # Steel uses luminous Steel Ink (ui["accent"]) with matte stage fg (ui["bg"]);
    # Day uses burnt Beacon Ink (ui["accent"]) with crisp white fg (ui["on_accent"]).
    accent = ui["accent_vivid"] if is_dawn else ui["accent"]
    accent_fg = ui["on_vivid"] if is_dawn else (ui["bg"] if is_dark else ui["on_accent"])

    error_surface = mix(ui["bg"], ui["fault"], 0.14 if is_dark else 0.10)
    warning_surface = mix(ui["bg"], ui["warning"], 0.14 if is_dark else 0.10)
    update_surface = mix(ui["bg"], ui["signal"], 0.14 if is_dark else 0.10)
    accent_surface = mix(ui["bg"], accent, 0.16 if is_dark else 0.09)

    colors: dict[str, str] = {
        "canvas": ui["bg"],
        "chrome": ui["rail"],
        "toolbar": ui["surface"],
        "toolbarForeground": ui["text"],
        "toolbarBorder": ui["border"],
        "toolbarControl": ui["raised"],
        "toolbarControlForeground": ui["text"],
        "toolbarControlHover": ui["overlay"],
        "surface": ui["surface"],
        "surfaceRaised": ui["raised"],
        "surfaceOverlay": ui["overlay"],
        "text": ui["text"],
        "textMuted": ui["mute"],
        "border": ui["border"],
        "input": ui["code_bg"],
        "focus": ui["accent"],
        "accent": accent,
        "accentForeground": accent_fg,
        "secondary": ui["raised"],
        "secondaryForeground": ui["text"],
        "muted": ui["list"],
        "mutedForeground": ui["mute"],
        "placeholder": ui["subtle"],
        "secondaryLabel": ui["mute"],
        "iconMuted": ui["subtle"],
        "error": ui["fault"],
        "errorForeground": ui["fault"],
        "errorSurface": error_surface,
        "warning": ui["warning"],
        "warningForeground": ui["warning"],
        "warningSurface": warning_surface,
        "update": ui["signal"],
        "updateForeground": ui["signal"],
        "updateSurface": update_surface,
        "accentSurface": accent_surface,
        "accentSurfaceForeground": ui["accent"],
        "messageSurface": ui["raised"] if is_dark else ui["surface"],
        "messageForeground": ui["text"],
        "messageAction": ui["accent_fill"],
        "messageActionForeground": ui["on_accent"],
        "messageActionHover": ui["accent_fill_hover"],
        "codeBackground": ui["code_bg"],
        "codeForeground": ui["text"],
        "searchMatchBackground": ui["find_match"],
        "searchMatchForeground": ui["text"],
        "searchMatchActiveBackground": accent,
        "searchMatchActiveForeground": accent_fg,
        "sidebar": ui["rail"],
        "sidebarForeground": ui["text"],
        "sidebarMutedForeground": ui["mute"],
        "sidebarControlSurface": ui["surface"],
        "sidebarRowHover": mix(ui["rail"], ui["accent"], 0.10 if is_dark else 0.08),
        "sidebarRowActive": mix(ui["rail"], ui["secondary"], 0.14 if is_dark else 0.10),
        "sidebarRowSelected": mix(ui["rail"], ui["accent"], 0.18 if is_dark else 0.12),
        "sidebarBorder": ui["border"],
        "terminalBackground": ui["code_bg"],
        "terminalForeground": ui["text"],
        "terminalCursor": ui["cursor"],
        "terminalSelection": ui["selection_active"],
        "terminalScrollbar": with_alpha(ui["border_strong"], "66"),
        "terminalScrollbarHover": with_alpha(ui["border_strong"], "AA"),
    }
    return colors


def _t3code_css(v: dict, colors: dict[str, str]) -> str:
    ui = v["ui"]
    scope = ".dark" if v["mode"] == "dark" else ":root:not(.dark)"
    lines = [
        f"{scope} svg.lucide {{",
        "  stroke-width: 1.75;",
        "  stroke-linecap: square;",
        "  stroke-linejoin: miter;",
        "}",
        f"{scope} [data-chat-header] {{",
        f"  background-image: linear-gradient(90deg, {ui['beam_start']}, {ui['beam_end']});",
        "  background-size: 100% 2px;",
        "  background-position: 0 100%;",
        "  background-repeat: no-repeat;",
        "}",
        f"{scope} [data-slot='composer-host']:focus-within {{",
        f"  border-color: {colors['focus']};",
        f"  box-shadow: 0 0 0 1px {colors['focus']};",
        "}",
        f"{scope} [data-slot='scroll-area-thumb'] {{",
        f"  background-color: {colors['terminalScrollbar']};",
        "  border-radius: 2px;",
        "}",
        f"{scope} [data-slot='scroll-area-thumb']:hover {{",
        f"  background-color: {colors['terminalScrollbarHover']};",
        "}",
        f"{scope} ::selection {{",
        f"  background-color: {ui['selection_active']};",
        f"  color: {colors['text']};",
        "}",
        f"{scope} input,",
        f"{scope} textarea,",
        f"{scope} .composer-tiptap {{",
        f"  caret-color: {colors['terminalCursor']};",
        "}",
        f"{scope} [data-thread-item][data-active='true'],",
        f"{scope} [data-thread-item][aria-current='page'] {{",
        f"  box-shadow: inset 2px 0 0 0 {colors['accent']};",
        "}",
    ]
    return "\n".join(lines)


def _t3code_payload(v: dict) -> dict:
    colors = _t3code_colors(v)
    css = _t3code_css(v, colors)
    desc = f"{v['lx']} ({v['accentRole']}) — {v['summary']}"
    payload = {
        "version": 1,
        "id": v["id"],
        "name": v["name"],
        "appearance": v["mode"],
        "author": AUTHOR,
        "description": desc,
        "canvas": colors["canvas"],
        "accent": colors["accent"],
        "colors": colors,
        "css": css,
    }
    _self_check_payload(payload)
    return payload


def _self_check_payload(payload: dict) -> None:
    vid = payload["id"]
    assert payload["version"] == 1, f"{vid}: version must be 1"
    assert _ID_RE.match(vid), f"{vid}: invalid id format"
    assert 1 <= len(payload["name"]) <= 48, f"{vid}: name length out of bounds"
    assert payload["appearance"] in ("dark", "light"), f"{vid}: invalid appearance"
    assert len(payload["description"]) <= 200, f"{vid}: description exceeds 200 chars"
    assert _HEX6_RE.match(payload["canvas"]), f"{vid}: canvas must be #RRGGBB"
    assert _HEX6_RE.match(payload["accent"]), f"{vid}: accent must be #RRGGBB"

    colors = payload["colors"]
    if tuple(colors.keys()) != THEME_COLOR_ROLES:
        missing = set(THEME_COLOR_ROLES) - set(colors.keys())
        extra = set(colors.keys()) - set(THEME_COLOR_ROLES)
        raise AssertionError(f"{vid}: color role mismatch (missing={missing}, extra={extra})")

    for role, val in colors.items():
        if not _HEX6_8_RE.match(val):
            raise AssertionError(f"{vid}: invalid hex colors[{role}]={val!r}")

    for fg_role, bg_role in CONTRAST_PAIRS:
        fg_hex = colors[fg_role]
        bg_hex = colors[bg_role]
        ratio = contrast(fg_hex, bg_hex)
        if ratio < 4.5:
            raise AssertionError(
                f"{vid}: WCAG AA fail {fg_role} ({fg_hex}) on {bg_role} ({bg_hex}) = {ratio:.2f}:1 (< 4.5:1)"
            )

    css = payload.get("css", "")
    assert len(css) <= 3000, f"{vid}: css exceeds 3000 chars ({len(css)})"
    assert "\\" not in css, f"{vid}: backslash forbidden in T3 Code css"
    if _FORBIDDEN_CSS_RE.search(css):
        raise AssertionError(f"{vid}: forbidden directive/function in T3 Code css")
    depth = 0
    for ch in css:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                raise AssertionError(f"{vid}: unbalanced CSS braces")
    assert depth == 0 and "{" in css, f"{vid}: unbalanced CSS braces"


def render_t3code_preview(v: dict, colors: dict[str, str]) -> str:
    """Render a bespoke 660x390 3-region T3 Code desktop workspace SVG preview."""
    syn = v["syntax"]
    c = colors
    vid = escape(v["id"])
    mode = escape(v["mode"])
    ver = escape(v["version"])

    body = f'''
    <!-- Left sidebar (x=0..176, y=36..346) -->
    <rect x="0" y="36" width="176" height="310" fill="{c["sidebar"]}"/>
    <line x1="176" y1="36" x2="176" y2="346" stroke="{c["sidebarBorder"]}" stroke-width="1"/>

    <!-- Project monogram header -->
    <rect x="12" y="48" width="24" height="24" rx="5" fill="{c["messageAction"]}"/>
    <text x="24" y="63.5" text-anchor="middle" fill="{c["messageActionForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">RFS</text>
    <text x="44" y="58.5" fill="{c["sidebarForeground"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5" font-weight="700">rfs-themes</text>
    <text x="44" y="70.5" fill="{c["sidebarMutedForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8">main · 29 apps</text>

    <!-- New thread sidebar control -->
    <rect x="12" y="82" width="152" height="22" rx="4" fill="{c["sidebarControlSurface"]}" stroke="{c["sidebarBorder"]}" stroke-width="1"/>
    <text x="22" y="96.5" fill="{c["sidebarForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.8" font-weight="600">+ New thread</text>
    <text x="156" y="96.5" text-anchor="end" fill="{c["sidebarMutedForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8">Ctrl+N</text>

    <!-- Thread list -->
    <text x="14" y="121" fill="{c["sidebarMutedForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700" letter-spacing="0.8">THREADS</text>

    <!-- Selected thread row (left accent stripe inset inside rx=5 corners) -->
    <rect x="10" y="128" width="156" height="36" rx="5" fill="{c["sidebarRowSelected"]}"/>
    <rect x="10" y="133" width="2.5" height="26" rx="1" fill="{c["accent"]}"/>
    <text x="21" y="143.5" fill="{c["sidebarForeground"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5" font-weight="700">Add T3 Code v1 port</text>
    <text x="21" y="156.5" fill="{c["sidebarMutedForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8">now · 61 roles · AA</text>

    <!-- Hovered secondary thread -->
    <rect x="10" y="170" width="156" height="26" rx="5" fill="{c["sidebarRowHover"]}"/>
    <text x="21" y="186.5" fill="{c["sidebarForeground"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.2">Verify WCAG AA pairs</text>

    <!-- Muted secondary threads -->
    <text x="21" y="213" fill="{c["sidebarMutedForeground"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.2">Sync rfs.tokens.json</text>
    <text x="21" y="235" fill="{c["sidebarMutedForeground"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.2">Build SVG previews</text>
    <text x="21" y="257" fill="{c["sidebarMutedForeground"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.2">Update docs gallery</text>

    <!-- Sidebar footer CLI indicator -->
    <rect x="12" y="310" width="152" height="24" rx="4" fill="{c["sidebarControlSurface"]}" stroke="{c["sidebarBorder"]}" stroke-width="1"/>
    <text x="21" y="325.5" fill="{c["updateForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.2" font-weight="700">[ok] t3 theme active</text>

    <!-- Main conversation canvas (x=176..660, y=36..346) -->
    <rect x="176" y="36" width="484" height="310" fill="{c["canvas"]}"/>

    <!-- Conversation header with 2px Steel->Beacon horizon bottom border -->
    <rect x="176" y="36" width="484" height="30" fill="{c["toolbar"]}"/>
    <rect x="176" y="66" width="484" height="2" fill="url(#hbeam)"/>
    <text x="192" y="55" fill="{c["toolbarForeground"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5" font-weight="700">Add T3 Code v1 port</text>
    <rect x="536" y="42" width="110" height="18" rx="4" fill="{c["toolbarControl"]}" stroke="{c["toolbarBorder"]}" stroke-width="1"/>
    <text x="591" y="54" text-anchor="middle" fill="{c["toolbarControlForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="600">t3 theme set</text>

    <!-- User message bubble (left stripe inset strictly inside rx=6 corners) -->
    <rect x="192" y="79" width="452" height="40" rx="6" fill="{c["messageSurface"]}" stroke="{c["border"]}" stroke-width="1"/>
    <rect x="192" y="85" width="2.5" height="28" rx="1" fill="{c["accent"]}"/>
    <text x="204" y="95" fill="{c["accentSurfaceForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">YOU</text>
    <text x="204" y="110" fill="{c["messageForeground"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.8">Generate Cyclorama Dawn v1 themes for T3 Code with all 61 roles &amp; AA checks.</text>

    <!-- Assistant response header + status badge -->
    <text x="192" y="139" fill="{c["textMuted"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.2" font-weight="700">ASSISTANT · T3 CODE</text>
    <rect x="524" y="127" width="120" height="17" rx="4" fill="{c["updateSurface"]}" stroke="{c["update"]}" stroke-width="0.9"/>
    <text x="584" y="138.5" text-anchor="middle" fill="{c["updateForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">[ok] tests passing</text>

    <text x="192" y="157" fill="{c["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.8">Generated 3 verified theme JSON files and CSS hooks from <tspan fill="{c["accentSurfaceForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">rfs_palette.py</tspan>:</text>

    <!-- Syntax-colored code snippet card -->
    <rect x="192" y="167" width="452" height="86" rx="6" fill="{c["codeBackground"]}" stroke="{c["border"]}" stroke-width="1"/>
    <g font-family="ui-monospace,Consolas,monospace" font-size="9.3">
      <text x="204" y="185"><tspan fill="{syn["punctuation"]}">&#123; </tspan><tspan fill="{syn["property"]}">"version"</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["number"]}" font-weight="700">1</tspan><tspan fill="{syn["punctuation"]}">, </tspan><tspan fill="{syn["property"]}">"id"</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["string"]}">"{vid}"</tspan><tspan fill="{syn["punctuation"]}">, </tspan><tspan fill="{syn["property"]}">"appearance"</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["string"]}">"{mode}"</tspan><tspan fill="{syn["punctuation"]}">,</tspan></text>
      <text x="204" y="203"><tspan fill="{syn["property"]}">  "canvas"</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["string"]}">"{c["canvas"]}"</tspan><tspan fill="{syn["punctuation"]}">, </tspan><tspan fill="{syn["property"]}">"accent"</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["function"]}">"{c["accent"]}"</tspan><tspan fill="{syn["punctuation"]}">,</tspan></text>
      <text x="204" y="221"><tspan fill="{syn["property"]}">  "colors"</tspan><tspan fill="{syn["punctuation"]}">: &#123; </tspan><tspan fill="{syn["keyword"]}">/* 61 T3 Code v1 roles calibrated */</tspan><tspan fill="{syn["punctuation"]}"> &#125; &#125;</tspan></text>
      <text x="204" y="239" fill="{syn["comment"]}">// [ok] 53/53 WCAG AA pairs &gt;= 4.5:1 · CSS hooks verified</text>
    </g>

    <!-- Bottom composer card with accent focus ring + messageAction Send button -->
    <rect x="192" y="264" width="452" height="70" rx="7" fill="{c["surfaceRaised"]}" stroke="{c["focus"]}" stroke-width="1.3"/>
    <text x="206" y="285" fill="{c["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.8">Run python tools/build_all.py and confirm zero-byte drift</text>
    <rect x="468" y="274" width="1.8" height="13" fill="{c["terminalCursor"]}"/>

    <rect x="206" y="303" width="102" height="20" rx="4" fill="{c["surface"]}" stroke="{c["border"]}" stroke-width="1"/>
    <text x="257" y="316" text-anchor="middle" fill="{c["textMuted"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.2">Cyclorama v{ver}</text>
    <rect x="316" y="303" width="84" height="20" rx="4" fill="{c["accentSurface"]}"/>
    <text x="358" y="316" text-anchor="middle" fill="{c["accentSurfaceForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.2" font-weight="700">61 roles · AA</text>

    <rect x="564" y="302" width="68" height="22" rx="5" fill="{c["messageAction"]}"/>
    <text x="598" y="316.5" text-anchor="middle" fill="{c["messageActionForeground"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.8" font-weight="700">Send</text>
    '''
    return _frame_shell(v, f"[{SLUG}]", APP_NAME, "V1 · 61 ROLES", body, _standard_swatches(v))


def _swatches(v: dict, colors: dict[str, str]) -> list[dict]:
    ui = v["ui"]
    return [
        {"label": "Canvas", "hex": colors["canvas"]},
        {"label": "Sidebar", "hex": colors["sidebar"]},
        {"label": "Surface", "hex": colors["surface"]},
        {"label": "Accent", "hex": colors["accent"]},
        {"label": "Action", "hex": colors["messageAction"]},
        {"label": "Signal", "hex": ui["signal"]},
    ]


def _render_readme(payloads: dict[str, dict]) -> str:
    brand_ver = VARIANTS["cyclorama-dawn"]["version"]
    lines = [
        f"# {BRAND_NAME} for {APP_NAME}",
        "",
        f"Three **{BRAND_NAME} v{brand_ver} (Steel & Beacon Orange)** themes for "
        f"**[{APP_NAME}]({HOMEPAGE})**, built from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}) "
        f"using T3 Code's v1 theme schema (all **61** official `THEME_COLOR_ROLES` + scoped `THEME_CSS_HOOKS` finishing touches) "
        f"with every foreground/background contrast pair verified at **>= 4.5:1 WCAG AA**.",
        "",
        f"- **Category:** {CATEGORY}",
        f"- **Format:** `{FORMAT_NAME}`",
        f"- **Gallery:** [{GALLERY_URL}]({GALLERY_URL})",
        "",
        "## Install",
        "",
        "### Option 1 — T3 Code CLI (Recommended)",
        "",
        "Apply any variant directly with `t3 theme set`:",
        "",
        "```sh",
        "t3 theme set apps/t3code/cyclorama-dawn.json",
        "# Switch to Steel Blue or Alabaster Day:",
        "# t3 theme set apps/t3code/cyclorama-steel.json",
        "# t3 theme set apps/t3code/cyclorama-day.json",
        "",
        "# Inspect or reset the active theme:",
        "t3 theme show",
        "t3 theme clear",
        "```",
        "",
        "### Option 2 — Desktop Settings UI",
        "",
        "1. Open **T3 Code** -> **Settings** -> **Themes** -> **Import theme**.",
        "2. Paste the full contents of `cyclorama-dawn.json`, `cyclorama-steel.json`, or `cyclorama-day.json` (or click **Copy** in the web gallery).",
        "3. Alternatively, copy the `cyclorama-*.json` files directly into `~/.t3/userdata/themes/` and select the variant in Settings.",
        "",
        "## Variants",
        "",
        "| Variant | LX | Appearance | Accent Role | Canvas | Accent | Message Action | File |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        p = payloads[vid]
        c = p["colors"]
        fname = f"{vid}.json"
        lines.append(
            f"| **{v['name']}** | `{v['lx']}` | `{p['appearance']}` | {v['accentRole']} "
            f"| `{c['canvas']}` | `{c['accent']}` | `{c['messageAction']}` "
            f"| [`{fname}`]({quote(fname, safe='/')}) |"
        )

    lines.extend(["", "## Previews", ""])
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        lines.extend(
            [
                f"### {v['name']} (`{v['lx']}` · {v['accentRole']})",
                "",
                v["summary"],
                "",
                f"![{v['name']} {APP_NAME} preview](previews/{vid}.svg)",
                "",
            ]
        )

    lines.extend(
        [
            "## Regenerating",
            "",
            "```sh",
            "python tools/build_t3code.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build() -> dict:
    install_summary = "Run `t3 theme set apps/t3code/cyclorama-dawn.json` or Settings -> Themes -> Import theme"
    install_steps = [
        "**CLI one-liner:** Run `t3 theme set apps/t3code/cyclorama-dawn.json` (inspect with `t3 theme show`, reset with `t3 theme clear`).",
        "**Desktop UI:** Open T3 Code -> **Settings** -> **Themes** -> **Import theme** and paste the complete JSON snippet below.",
        "**Manual folder:** Copy `cyclorama-*.json` into `~/.t3/userdata/themes/` and choose **Cyclorama Dawn**, **Cyclorama Steel**, or **Cyclorama Day**.",
    ]

    payloads: dict[str, dict] = {}
    themes_entries: list[dict] = []

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        payload = _t3code_payload(v)
        payloads[vid] = payload

        rel_file = f"apps/{SLUG}/{vid}.json"
        _write_json(rel_file, payload)

        svg = render_t3code_preview(v, payload["colors"])
        write_preview_pair(SLUG, vid, svg)

        themes_entries.append(
            {
                "id": vid,
                "name": v["name"],
                "lx": v["lx"],
                "mode": v["mode"],
                "accentRole": v["accentRole"],
                "tagline": v["summary"],
                "preview": f"apps/{SLUG}/previews/{vid}.svg",
                "file": rel_file,
                "copyLang": "json",
                "copyLabel": "Copy T3 Code JSON",
                "copySnippet": json.dumps(payload, indent=2, ensure_ascii=False),
                "swatches": _swatches(v, payload["colors"]),
            }
        )

    files_list = [
        {"label": f"{VARIANTS[vid]['name']} ({vid}.json)", "path": f"apps/{SLUG}/{vid}.json"}
        for vid in VARIANT_ORDER
    ]
    files_list.extend(
        [
            {"label": "Theme Metadata (themes.json)", "path": f"apps/{SLUG}/themes.json"},
            {"label": "Install Guide (README.md)", "path": f"apps/{SLUG}/README.md"},
        ]
    )

    themes_json = {
        "brand": BRAND_NAME,
        "version": VARIANTS["cyclorama-dawn"]["version"],
        "author": AUTHOR,
        "slug": SLUG,
        "app": APP_NAME,
        "category": CATEGORY,
        "homepage": HOMEPAGE,
        "format": FORMAT_NAME,
        "install": install_summary,
        "installSteps": install_steps,
        "primaryFile": f"apps/{SLUG}/cyclorama-dawn.json",
        "files": files_list,
        "themes": themes_entries,
    }
    _write_json(f"apps/{SLUG}/themes.json", themes_json)
    _write_text(f"apps/{SLUG}/README.md", _render_readme(payloads))

    print(
        f"[ok] built apps/{SLUG}/ (3 T3 Code v1 JSON+CSS themes, 61 roles each, "
        f"{len(CONTRAST_PAIRS)} AA contrast checks/variant, 3 synced SVG previews)"
    )
    return themes_json


if __name__ == "__main__":
    build()
