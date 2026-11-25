#!/usr/bin/env python3
"""Verify rfs-themes integrity across all 28 apps (84 variants), WCAG AA contrast,
native format schemas, relative links, SVG previews, Oklab PNG wallpapers, and
Cyclorama Dawn invariants.

Zero external dependencies (Python 3.11+ standard library only).

Exit codes (RFS CLI standard):
    0  all checks passed
    1  one or more checks failed
"""
from __future__ import annotations

import configparser
import hashlib
import importlib.util
import json
import os
import plistlib
import re
import shutil
import struct
import subprocess
import sys
import tomllib
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import rfs_palette as pal  # noqa: E402

# Load PrivacyNotes contrast & pn1: engine from build-privacynotes.py
_pn_spec = importlib.util.spec_from_file_location("build_pn", os.path.join(HERE, "build-privacynotes.py"))
assert _pn_spec is not None and _pn_spec.loader is not None
build_pn = importlib.util.module_from_spec(_pn_spec)
_pn_spec.loader.exec_module(build_pn)

HEX6_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
HEX6_8_RE = re.compile(r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")
XAML_HEX_RE = re.compile(r"^#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")
ICLS_HEX_RE = re.compile(r"^[0-9A-F]{6}$")
GUID_RE = re.compile(r"^\{[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\}$")

LUA_RESERVED = {
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "if", "in", "local", "nil", "not", "or", "repeat",
    "return", "then", "true", "until", "while",
}

EXPECTED_VARIANTS = ("cyclorama-dawn", "cyclorama-steel", "cyclorama-day")
EXPECTED_APP_ORDER = (
    "vscode", "neovim", "zed", "jetbrains", "notepad-plus-plus", "python-idle", "powershell-ise",
    "windows-terminal", "wezterm", "alacritty", "ghostty", "kitty", "git-bash", "qterminal", "windows-console",
    "starship", "oh-my-posh", "bat", "delta", "fzf",
    "privacynotes", "obsidian",
    "windows", "chromium", "discord", "proton-mail", "qbittorrent", "flow-launcher",
)
EXPECTED_APPS = set(EXPECTED_APP_ORDER)

NPP_EXPECTED_LEXERS = {
    "c", "cpp", "cs", "rust", "python", "powershell", "bash",
    "javascript.js", "typescript", "json", "yaml", "html", "css",
    "xml", "markdown", "sql", "ini", "diff", "batch",
}
NPP_EXPECTED_GLOBALS = {
    "Global override", "Default Style", "Indent guideline style",
    "Brace highlight style", "Bad brace colour", "Current line background colour",
    "Selected text colour", "Caret colour", "Multi-selected text color",
    "Line number margin", "Bookmark margin", "Change History margin",
    "Fold", "Fold active", "Fold margin", "White space symbol",
    "Smart Highlighting", "Find Mark Style", "Active tab focused indicator",
    "Active tab unfocused indicator", "Active tab text", "Inactive tabs",
    "URL hovered", "EOL custom color", "Non-printing characters custom color",
}

IDLE_EXPECTED_KEYS = {
    "normal-foreground", "normal-background",
    "keyword-foreground", "keyword-background",
    "builtin-foreground", "builtin-background",
    "comment-foreground", "comment-background",
    "string-foreground", "string-background",
    "definition-foreground", "definition-background",
    "hilite-foreground", "hilite-background",
    "break-foreground", "break-background",
    "hit-foreground", "hit-background",
    "error-foreground", "error-background",
    "context-foreground", "context-background",
    "linenumber-foreground", "linenumber-background",
    "cursor-foreground",
    "stdout-foreground", "stdout-background",
    "stderr-foreground", "stderr-background",
    "console-foreground", "console-background",
}

ISE_PANE_KEYS = (
    "ErrorForegroundColor", "ErrorBackgroundColor",
    "WarningForegroundColor", "WarningBackgroundColor",
    "VerboseForegroundColor", "VerboseBackgroundColor",
    "DebugForegroundColor", "DebugBackgroundColor",
    "ConsolePaneBackgroundColor", "ConsolePaneTextBackgroundColor",
    "ConsolePaneForegroundColor", "ScriptPaneBackgroundColor",
    "ScriptPaneForegroundColor",
)
ISE_TOKEN_NAMES = (
    "Attribute", "Command", "CommandArgument", "CommandParameter", "Comment",
    "GroupEnd", "GroupStart", "Keyword", "LineContinuation", "LoopLabel",
    "Member", "NewLine", "Number", "Operator", "Position",
    "StatementSeparator", "String", "Type", "Unknown", "Variable",
)
ISE_XML_TOKEN_NAMES = (
    "CharacterData", "QuotedString", "Comment", "CommentDelimiter",
    "15", "13", "12", "14", "18", "MarkupExtension", "Quote", "17",
    "ElementName", "11", "19", "16", "Attribute", "10", "Tag", "Text",
)
ISE_EXPECTED_73_KEYS = (
    *ISE_PANE_KEYS,
    *(f"TokenColors\\{k}" for k in ISE_TOKEN_NAMES),
    *(f"ConsoleTokenColors\\{k}" for k in ISE_TOKEN_NAMES),
    *(f"XmlTokenColors\\{k}" for k in ISE_XML_TOKEN_NAMES),
)

MINTTY_EXPECTED_KEYS = {
    "ForegroundColour", "BackgroundColour", "CursorColour",
    "Black", "BoldBlack", "Red", "BoldRed", "Green", "BoldGreen",
    "Yellow", "BoldYellow", "Blue", "BoldBlue", "Magenta", "BoldMagenta",
    "Cyan", "BoldCyan", "White", "BoldWhite",
}

QTERMINAL_EXPECTED_SECTIONS = {
    "General", "Background", "BackgroundIntense", "Foreground", "ForegroundIntense",
    *(f"Color{i}" for i in range(8)),
    *(f"Color{i}Intense" for i in range(8)),
}

PROTON_EXPECTED_VARS = (
    "--background-norm", "--background-weak", "--background-strong",
    "--background-elevated", "--background-lowered",
    "--primary", "--primary-contrast",
    "--interaction-norm", "--interaction-norm-major-1",
    "--interaction-norm-major-2", "--interaction-norm-major-3",
    "--interaction-norm-contrast",
    "--interaction-weak", "--interaction-weak-major-1", "--interaction-weak-major-2",
    "--interaction-default", "--interaction-default-hover",
    "--text-norm", "--text-weak", "--text-hint", "--text-disabled", "--text-invert",
    "--border-norm", "--border-weak",
    "--signal-danger", "--signal-danger-major-1", "--signal-danger-contrast",
    "--signal-warning", "--signal-warning-contrast",
    "--signal-success", "--signal-success-contrast",
    "--signal-info", "--signal-info-contrast",
    "--focus-outline",
    "--scrollbar-thumb-color", "--scrollbar-thumb-hover-color",
    "--navigation-current-item-background-color", "--navigation-current-item-text-color",
    "--email-item-unread-background-color", "--email-item-read-background-color",
    "--email-item-selected-background-color",
)

WINDOWS_EXPECTED_SPECS: dict[str, dict] = {
    "cyclorama-dawn": {
        "mode_win": "Dark",
        "light_val": 0,
        "bg_rgb_str": "5 5 7",
        "bg_rgb": (5, 5, 7),
        "colorization_argb": "0xC4F06E2B",
        "accent_abgr": "0xFF2B6EF0",
        "start_abgr": "0xFF1650CC",
        "palette": [
            "#FFD2B3", "#FFB07A", "#FF9254", "#F06E2B",
            "#CC5016", "#9E3B0C", "#5C2006", "#74B8E8",
        ],
    },
    "cyclorama-steel": {
        "mode_win": "Dark",
        "light_val": 0,
        "bg_rgb_str": "5 5 7",
        "bg_rgb": (5, 5, 7),
        "colorization_argb": "0xC41F547A",
        "accent_abgr": "0xFF7A541F",
        "start_abgr": "0xFF6B4918",
        "palette": [
            "#CDE7FA", "#99CDF2", "#74B8E8", "#1F547A",
            "#18496B", "#123955", "#0B2436", "#FF9254",
        ],
    },
    "cyclorama-day": {
        "mode_win": "Light",
        "light_val": 1,
        "bg_rgb_str": "245 247 249",
        "bg_rgb": (245, 247, 249),
        "colorization_argb": "0xC4AD3D0A",
        "accent_abgr": "0xFF0A3DAD",
        "start_abgr": "0xFF062F8B",
        "palette": [
            "#F8C9B0", "#F09B6E", "#D45B24", "#AD3D0A",
            "#8B2F06", "#6A2304", "#471602", "#18496B",
        ],
    },
}


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_utf8(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def check_balanced_braces_css(text: str) -> bool:
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


def check_balanced_delimiters(text: str) -> bool:
    stack: list[str] = []
    pairs = {")": "(", "}": "{", "]": "["}
    for ch in text:
        if ch in "({[":
            stack.append(ch)
        elif ch in ")}]":
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
    return not stack


def strip_ps1_strings_and_comments(ps1_txt: str) -> str:
    no_here = re.sub(r"@'[\s\S]*?'@|@\"[\s\S]*?\"@", '""', ps1_txt)
    no_blk_cmt = re.sub(r"<#[\s\S]*?#>", "", no_here)
    no_str = re.sub(r'"(?:[^"`]|`.)*"|\'(?:[^\']|\'\')*\'', '""', no_blk_cmt)
    return re.sub(r"#[^\n]*", "", no_str)


def parse_ini_strict(text: str) -> configparser.RawConfigParser:
    cp = configparser.RawConfigParser(interpolation=None, strict=True)
    cp.optionxform = lambda optionstr: optionstr
    cp.read_string(text)
    return cp


def verify_png_file(path: str, expected_size: tuple[int, int], expected_top_rgb: tuple[int, int, int]) -> list[str]:
    errs: list[str] = []
    rel = os.path.relpath(path, ROOT)
    if not os.path.isfile(path):
        return [f"missing PNG wallpaper: {rel}"]
    data = open(path, "rb").read()
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return [f"{rel}: invalid PNG signature"]

    pos = 8
    chunks: list[str] = []
    idat_parts: list[bytes] = []
    dims: tuple[int, int] | None = None

    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        ctype_b = data[pos + 4 : pos + 8]
        if pos + 12 + length > len(data):
            errs.append(f"{rel}: truncated PNG chunk {ctype_b!r}")
            break
        cdata = data[pos + 8 : pos + 8 + length]
        crc_read = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])[0]
        crc_calc = zlib.crc32(cdata, zlib.crc32(ctype_b)) & 0xFFFFFFFF
        if crc_read != crc_calc:
            errs.append(f"{rel}: CRC32 mismatch in chunk {ctype_b.decode('latin1')}")
        ctype = ctype_b.decode("latin1")
        chunks.append(ctype)
        if ctype == "IHDR":
            if length != 13:
                errs.append(f"{rel}: invalid IHDR length {length}")
            else:
                w, h, bit_depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", cdata)
                dims = (w, h)
                if (bit_depth, color_type, comp, filt, interlace) != (8, 2, 0, 0, 0):
                    errs.append(
                        f"{rel}: unexpected IHDR format {(bit_depth, color_type, comp, filt, interlace)} (expected 8-bit RGB)"
                    )
        elif ctype == "IDAT":
            idat_parts.append(cdata)
        pos += 12 + length
        if ctype == "IEND":
            break

    if pos != len(data):
        errs.append(f"{rel}: trailing/unparsed bytes ({len(data) - pos})")
    if dims != expected_size:
        errs.append(f"{rel}: IHDR dimensions {dims} != expected {expected_size}")
    if "tIME" in chunks:
        errs.append(f"{rel}: non-deterministic tIME chunk forbidden")
    for req_chunk in ("IHDR", "sRGB", "IDAT", "IEND"):
        if req_chunk not in chunks:
            errs.append(f"{rel}: missing required PNG chunk {req_chunk}")
    if chunks and (chunks[0] != "IHDR" or chunks[-1] != "IEND"):
        errs.append(f"{rel}: invalid PNG chunk ordering {chunks}")

    if idat_parts and dims == expected_size:
        try:
            raw = zlib.decompress(b"".join(idat_parts))
            w, h = dims
            expected_raw_len = h * (1 + w * 3)
            if len(raw) != expected_raw_len:
                errs.append(f"{rel}: decompressed scanline byte count {len(raw)} != {expected_raw_len}")
            elif raw[0] == 0 and tuple(raw[1:4]) != expected_top_rgb:
                errs.append(f"{rel}: top scanline RGB {tuple(raw[1:4])} != expected matte stage {expected_top_rgb}")
        except zlib.error as exc:
            errs.append(f"{rel}: invalid zlib IDAT stream ({exc})")

    return errs


def main() -> int:
    errors: list[str] = []

    def ok(msg: str) -> None:
        print(f"[ok] {msg}")

    def fail(msg: str) -> None:
        print(f"[x]  {msg}")
        errors.append(msg)

    # ------------------------------------------------------------------
    # 1. Brand token sync
    # ------------------------------------------------------------------
    b_tok = os.path.join(ROOT, "brand", "rfs.tokens.json")
    d_tok = os.path.join(ROOT, "docs", "assets", "rfs.tokens.json")
    if not os.path.exists(b_tok) or not os.path.exists(d_tok):
        fail("missing brand/rfs.tokens.json or docs/assets/rfs.tokens.json")
    elif sha256(b_tok) != sha256(d_tok):
        fail("brand/rfs.tokens.json != docs/assets/rfs.tokens.json")
    else:
        ver = json.loads(read_utf8(b_tok))["meta"]["version"]
        ok(f"rfs.tokens.json synced (v{ver})")

    # ------------------------------------------------------------------
    # 2. Canonical palette WCAG AA contrast engine (137 checks >= 4.5:1)
    # ------------------------------------------------------------------
    pal_checks = pal.verify_palette_contrast()
    pal_fails = [c for c in pal_checks if not c[4]]
    if len(pal_checks) < 137:
        fail(f"rfs_palette.verify_palette_contrast() ran {len(pal_checks)} checks, expected >= 137")
    elif pal_fails:
        for vid, role, ratio, need, _ in pal_fails:
            fail(f"palette contrast fail: {vid} {role} = {ratio:.2f}:1 (< {need:.1f}:1)")
    else:
        ok(f"rfs_palette WCAG AA contrast verified ({len(pal_checks)}/{len(pal_checks)} checks >= 4.5:1)")

    # ------------------------------------------------------------------
    # 3. apps/manifest.json validation (28 apps x 3 variants = 84)
    # ------------------------------------------------------------------
    e0 = len(errors)
    manifest_path = os.path.join(ROOT, "apps", "manifest.json")
    manifest = json.loads(read_utf8(manifest_path))
    m_apps = manifest.get("apps", [])
    m_slugs = [a.get("slug") for a in m_apps]
    if len(m_apps) != 28 or tuple(m_slugs) != EXPECTED_APP_ORDER:
        fail(f"apps/manifest.json expected 28 canonical apps in category order, got {len(m_apps)} ({set(m_slugs) ^ EXPECTED_APPS})")
    for app in m_apps:
        slug = app["slug"]
        for rel in (app["path"], app["data"]):
            if not os.path.exists(os.path.join(ROOT, rel)):
                fail(f"manifest path missing ({slug}): {rel}")
        vids = tuple(v["id"] for v in app.get("variants", []))
        if vids != EXPECTED_VARIANTS:
            fail(f"manifest {slug} variants mismatch: {vids}")
        for var in app.get("variants", []):
            if not os.path.exists(os.path.join(ROOT, var["preview"])):
                fail(f"manifest preview missing ({slug}): {var['preview']}")
    if len(errors) == e0:
        ok(f"apps/manifest.json valid ({len(m_apps)} apps, {sum(len(a['variants']) for a in m_apps)} variants)")

    # ------------------------------------------------------------------
    # 4. docs/assets/catalog.json validation (28 apps x 3 variants = 84)
    # ------------------------------------------------------------------
    e0 = len(errors)
    catalog_path = os.path.join(ROOT, "docs", "assets", "catalog.json")
    if not os.path.exists(catalog_path):
        fail("missing docs/assets/catalog.json")
        catalog = {"apps": []}
    else:
        catalog = json.loads(read_utf8(catalog_path))
        c_apps = catalog.get("apps", [])
        if [a.get("slug") for a in c_apps] != m_slugs:
            fail("docs/assets/catalog.json app order/slugs do not match apps/manifest.json")
        if catalog.get("stats", {}).get("apps") != 28 or catalog.get("stats", {}).get("variants") != 84 or catalog.get("stats", {}).get("categories") != 5:
            fail(f"catalog.json stats invalid (expected 28 apps, 84 variants, 5 categories): {catalog.get('stats')}")
        for app in c_apps:
            slug = app["slug"]
            steps = app.get("installSteps", [])
            if not isinstance(steps, list) or len(steps) < 2 or not all(isinstance(s, str) and s.strip() for s in steps):
                fail(f"catalog {slug}: invalid installSteps")
            if not os.path.exists(os.path.join(ROOT, app.get("primaryFile", ""))):
                fail(f"catalog {slug}: missing primaryFile {app.get('primaryFile')}")
            files_list = app.get("files", [])
            if not files_list:
                fail(f"catalog {slug}: empty files[]")
            for f_entry in files_list:
                if not os.path.exists(os.path.join(ROOT, f_entry.get("path", ""))):
                    fail(f"catalog {slug}: missing files[].path {f_entry.get('path')}")
            vids = tuple(v["id"] for v in app.get("variants", []))
            if vids != EXPECTED_VARIANTS:
                fail(f"catalog {slug}: variant order mismatch {vids}")
            for v in app.get("variants", []):
                vid = v["id"]
                dp = os.path.join(ROOT, "docs", v.get("preview", ""))
                if not os.path.isfile(dp):
                    fail(f"catalog {slug}/{vid}: missing docs preview {v.get('preview')}")
                if not os.path.isfile(os.path.join(ROOT, v.get("file", ""))):
                    fail(f"catalog {slug}/{vid}: missing file {v.get('file')}")
                snip = v.get("copySnippet", "")
                if not isinstance(snip, str) or not snip.strip():
                    fail(f"catalog {slug}/{vid}: empty copySnippet")
                lang = v.get("copyLang", "")
                if lang == "json":
                    try:
                        json.loads(snip)
                    except Exception as exc:
                        fail(f"catalog {slug}/{vid}: invalid JSON copySnippet ({exc})")
                elif lang == "toml":
                    try:
                        tomllib.loads(snip)
                    except Exception as exc:
                        fail(f"catalog {slug}/{vid}: invalid TOML copySnippet ({exc})")
                elif lang == "ini":
                    try:
                        parse_ini_strict(snip)
                    except Exception as exc:
                        fail(f"catalog {slug}/{vid}: invalid INI copySnippet ({exc})")
                elif lang == "css" and not check_balanced_braces_css(snip):
                    fail(f"catalog {slug}/{vid}: unbalanced CSS copySnippet")
                elif lang == "xml":
                    try:
                        ET.fromstring(snip)
                    except ET.ParseError as exc:
                        fail(f"catalog {slug}/{vid}: invalid XML copySnippet ({exc})")
                swatches = v.get("swatches", [])
                if len(swatches) != 6:
                    fail(f"catalog {slug}/{vid}: expected 6 swatches, got {len(swatches)}")
                for sw in swatches:
                    if not sw.get("label") or not HEX6_RE.match(sw.get("hex", "")):
                        fail(f"catalog {slug}/{vid}: invalid swatch {sw}")
        if len(errors) == e0:
            ok("docs/assets/catalog.json valid (28 apps, 84 variants, snippets & swatches verified)")

    # ------------------------------------------------------------------
    # 5. All 84 SVG preview pairs (SHA-256 sync + XML parse + swatch check)
    # ------------------------------------------------------------------
    e0 = len(errors)
    svg_count = 0
    for slug in sorted(EXPECTED_APPS):
        for vid in EXPECTED_VARIANTS:
            p1 = os.path.join(ROOT, "apps", slug, "previews", f"{vid}.svg")
            p2 = os.path.join(ROOT, "docs", "assets", "previews", slug, f"{vid}.svg")
            if not os.path.isfile(p1) or not os.path.isfile(p2):
                fail(f"missing SVG preview pair for {slug}/{vid}")
                continue
            if sha256(p1) != sha256(p2):
                fail(f"SVG preview drift: apps/{slug}/previews/{vid}.svg != docs/assets/previews/{slug}/{vid}.svg")
            svg_txt = read_utf8(p1)
            try:
                svg_root = ET.fromstring(svg_txt)
            except ET.ParseError as exc:
                fail(f"invalid XML in {slug}/{vid}.svg: {exc}")
                continue
            rects = [el for el in svg_root.iter("{http://www.w3.org/2000/svg}rect") if el.attrib.get("y") == "357"]
            texts = [el for el in svg_root.iter("{http://www.w3.org/2000/svg}text") if el.attrib.get("y") == "378"]
            if len(rects) == 10 and len(texts) == 10:
                ribbon = {("".join(t.itertext())).strip(): r.attrib.get("fill", "").upper() for r, t in zip(rects, texts)}
                if "STEEL" in ribbon:
                    expected_steel = pal.VARIANTS[vid]["ui"]["accent"] if vid == "cyclorama-steel" else pal.VARIANTS[vid]["ui"]["secondary"]
                    if ribbon["STEEL"] != expected_steel:
                        fail(f"{slug}/{vid}.svg bottom ribbon STEEL swatch is {ribbon['STEEL']} (expected {expected_steel})")
            if slug == "windows":
                # Ensure Settings window (x=84, y=52) has its own clipPath so the left rail does not bleed over rx=8 bottom-left corner
                clips = list(svg_root.iter("{http://www.w3.org/2000/svg}clipPath"))
                has_win_clip = any(
                    r.attrib.get("x") in ("84", "84.5")
                    for cp_el in clips
                    for r in cp_el.iter("{http://www.w3.org/2000/svg}rect")
                )
                if not has_win_clip:
                    fail(f"windows/{vid}.svg Settings window missing inner <clipPath> (left rail bleeds over rounded bottom-left border)")
            if slug == "proton-mail":
                # Ensure encrypted message card (x=372, y=146, height=114, rx=6) left stripe is either inset or clipped so it does not poke past rx=6 corners
                clips = list(svg_root.iter("{http://www.w3.org/2000/svg}clipPath"))
                has_card_clip = any(
                    r.attrib.get("x") == "372" and r.attrib.get("y") == "146"
                    for cp_el in clips
                    for r in cp_el.iter("{http://www.w3.org/2000/svg}rect")
                )
                unclipped_bleed = any(
                    r.attrib.get("x") == "372"
                    and r.attrib.get("width") == "3"
                    and r.attrib.get("y") == "146"
                    and r.attrib.get("height") == "114"
                    for r in svg_root.iter("{http://www.w3.org/2000/svg}rect")
                )
                if unclipped_bleed and not has_card_clip:
                    fail(f"proton-mail/{vid}.svg encrypted message card left bar (y=146, height=114) bleeds outside rx=6 rounded corners")
            svg_count += 1
    if len(errors) == e0 and svg_count == 84:
        ok("all 84 SVG preview pairs synced, XML-valid, and swatch-accurate")

    # ------------------------------------------------------------------
    # 6. Native format schema & syntax verification for ALL 28 apps
    # ------------------------------------------------------------------

    # 6.1 PrivacyNotes
    e0 = len(errors)
    pn_data = json.loads(read_utf8(build_pn.THEMES_JSON))
    pn_author = pn_data.get("author", "Real-Fruit-Snacks")
    codes_body = read_utf8(build_pn.CODES_TXT) if os.path.exists(build_pn.CODES_TXT) else ""
    for t in pn_data["themes"]:
        name = t["name"]
        if len(name) > 20 or ":" in name or "," in name:
            fail(f"PrivacyNotes theme name invalid: {name!r}")
        canonical = build_pn.serialize_pn1(t, pn_author)
        if len(canonical) > 512:
            fail(f"privacynotes/{t['id']}: pn1 code exceeds 512 chars ({len(canonical)})")
        if t["code"] != canonical:
            fail(f"privacynotes/{t['id']}: themes.json code does not match canonical serializer")
        if canonical not in codes_body:
            fail(f"privacynotes/{t['id']}: missing from apps/privacynotes/codes.txt")
        bad = [ch for ch in build_pn.check_theme(t) if not ch[3]]
        if bad:
            fail(f"privacynotes/{t['id']}: failed contrast check(s): {bad}")
    if len(errors) == e0:
        ok("privacynotes: 3 pn1: codes & 51/51 contrast checks verified")

    # 6.2 VS Code
    e0 = len(errors)
    vsc_dir = os.path.join(ROOT, "apps", "vscode")
    vsc_pkg = json.loads(read_utf8(os.path.join(vsc_dir, "package.json")))
    vsc_contribs = vsc_pkg.get("contributes", {}).get("themes", [])
    if len(vsc_contribs) != 3:
        fail(f"vscode/package.json expected 3 contributed themes, got {len(vsc_contribs)}")
    for th in vsc_contribs:
        tp = os.path.normpath(os.path.join(vsc_dir, th.get("path", "")))
        if not os.path.isfile(tp):
            fail(f"vscode theme file missing: {th.get('path')}")
            continue
        td = json.loads(read_utf8(tp))
        if td.get("semanticHighlighting") is not True:
            fail(f"vscode {th['label']}: semanticHighlighting must be true")
        if not td.get("colors") or not td.get("semanticTokenColors") or not td.get("tokenColors"):
            fail(f"vscode {th['label']}: missing colors, semanticTokenColors, or tokenColors")
        expected_type = "light" if th.get("uiTheme") == "vs" else "dark"
        if td.get("type") != expected_type:
            fail(f"vscode {th['label']}: type={td.get('type')!r} mismatches uiTheme={th.get('uiTheme')!r}")
        for ck, cv in td["colors"].items():
            if not HEX6_8_RE.match(cv):
                fail(f"vscode {th['label']} invalid hex colors[{ck}]={cv!r}")
        for rule in td["tokenColors"]:
            fg = rule.get("settings", {}).get("foreground")
            if fg is not None and not HEX6_8_RE.match(fg):
                fail(f"vscode {th['label']} invalid tokenColors hex {fg!r}")
    if len(errors) == e0:
        ok("vscode: package.json + 3 workbench/TextMate/semantic JSON themes verified")

    # 6.3 Neovim
    e0 = len(errors)
    nvim_dir = os.path.join(ROOT, "apps", "neovim")
    nvim_files = [
        os.path.join(nvim_dir, "lua", "cyclorama", "palette.lua"),
        os.path.join(nvim_dir, "lua", "cyclorama", "init.lua"),
        os.path.join(nvim_dir, "lua", "cyclorama", "lualine.lua"),
        *(os.path.join(nvim_dir, "colors", f"{vid}.lua") for vid in EXPECTED_VARIANTS),
    ]
    for lf in nvim_files:
        if not os.path.isfile(lf):
            fail(f"neovim missing file: {os.path.relpath(lf, ROOT)}")
            continue
        ltxt = read_utf8(lf)
        no_cmt = re.sub(r"--[^\n]*", "", ltxt)
        no_str = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', '""', no_cmt)
        if not check_balanced_delimiters(no_str):
            fail(f"neovim unbalanced delimiters in {os.path.relpath(lf, ROOT)}")
        for m in re.finditer(r"(?<![.\w])([a-z]+)\s*=\s*(?!=)", no_str):
            if m.group(1) in LUA_RESERVED:
                fail(f"neovim bare Lua reserved keyword `{m.group(1)} =` in {os.path.relpath(lf, ROOT)}")
        for m in re.finditer(r"\.\s*([a-z]+)\b", no_str):
            if m.group(1) in LUA_RESERVED:
                fail(f"neovim bare Lua reserved field `.{m.group(1)}` in {os.path.relpath(lf, ROOT)}")
        for hx in re.findall(r"#[0-9A-Za-z]+", ltxt):
            if not HEX6_RE.match(hx):
                fail(f"neovim invalid hex {hx!r} in {os.path.relpath(lf, ROOT)}")
    init_lua = read_utf8(os.path.join(nvim_dir, "lua", "cyclorama", "init.lua"))
    if "vim.g.colors_name" not in init_lua:
        fail("neovim init.lua does not set vim.g.colors_name")
    if len(errors) == e0:
        ok("neovim: 6 Lua plugin & colorscheme files verified")

    # 6.4 Zed (v0.2.0 schema)
    e0 = len(errors)
    zed_dir = os.path.join(ROOT, "apps", "zed", "themes")
    zed_specs = [("cyclorama.json", 3)] + [(f"{vid}.json", 1) for vid in EXPECTED_VARIANTS]
    for zname, expected_count in zed_specs:
        zp = os.path.join(zed_dir, zname)
        if not os.path.isfile(zp):
            fail(f"zed missing {zname}")
            continue
        zd = json.loads(read_utf8(zp))
        if zd.get("$schema") != "https://zed.dev/schema/themes/v0.2.0.json":
            fail(f"zed/{zname}: missing or invalid $schema")
        zthemes = zd.get("themes", [])
        if len(zthemes) != expected_count:
            fail(f"zed/{zname}: expected {expected_count} theme(s), got {len(zthemes)}")
        for zt in zthemes:
            expected_app = "light" if "Day" in zt.get("name", "") else "dark"
            if zt.get("appearance") != expected_app:
                fail(f"zed/{zname} {zt.get('name')}: appearance={zt.get('appearance')!r} != {expected_app!r}")
            st = zt.get("style", {})
            for req in ("background", "editor.background", "editor.foreground", "terminal.ansi.black", "players", "syntax"):
                if req not in st:
                    fail(f"zed/{zname} {zt.get('name')}: missing style.{req}")
            for sk, sv in st.items():
                if sk == "players":
                    for pl in sv:
                        for pk, pv in pl.items():
                            if not HEX6_8_RE.match(pv):
                                fail(f"zed/{zname} invalid player color {pk}={pv!r}")
                elif sk == "syntax":
                    for syn_k, syn_v in sv.items():
                        if not HEX6_8_RE.match(syn_v.get("color", "")):
                            fail(f"zed/{zname} invalid syntax.{syn_k} color {syn_v}")
                elif isinstance(sv, str) and not HEX6_8_RE.match(sv):
                    fail(f"zed/{zname} invalid style.{sk}={sv!r}")
    if len(errors) == e0:
        ok("zed: unified + 3 standalone v0.2.0 JSON theme packs verified")

    # 6.5 JetBrains (.icls + .theme.json + plugin.xml)
    e0 = len(errors)
    jb_dir = os.path.join(ROOT, "apps", "jetbrains")
    plug_xml = ET.fromstring(read_utf8(os.path.join(jb_dir, "META-INF", "plugin.xml")))
    providers = plug_xml.findall(".//themeProvider")
    if len(providers) != 3:
        fail(f"jetbrains plugin.xml expected 3 themeProviders, got {len(providers)}")
    for tp in providers:
        rel_theme = tp.attrib.get("path", "").lstrip("/")
        full_theme = os.path.join(jb_dir, rel_theme)
        if not os.path.isfile(full_theme):
            fail(f"jetbrains plugin.xml missing themeProvider target: {rel_theme}")
            continue
        td = json.loads(read_utf8(full_theme))
        rel_icls = td.get("editorScheme", "").lstrip("/")
        full_icls = os.path.join(jb_dir, rel_icls)
        if not os.path.isfile(full_icls):
            fail(f"jetbrains {rel_theme} missing editorScheme target: {rel_icls}")
            continue
        named_colors = set(td.get("colors", {}).keys())
        for cname, chx in td.get("colors", {}).items():
            if not HEX6_8_RE.match(chx):
                fail(f"jetbrains {rel_theme} invalid color {cname}={chx!r}")

        def _check_jb_ui(node: dict, prefix: str = "") -> None:
            for uk, uv in node.items():
                if isinstance(uv, dict):
                    _check_jb_ui(uv, f"{prefix}.{uk}")
                elif isinstance(uv, str) and uv not in named_colors and not HEX6_8_RE.match(uv):
                    fail(f"jetbrains {rel_theme} unresolved ui{prefix}.{uk}={uv!r}")

        _check_jb_ui(td.get("ui", {}))
        icls_root = ET.fromstring(read_utf8(full_icls))
        color_opts = set(icls_root.findall("./colors/option"))
        for opt in icls_root.findall(".//option"):
            oname = opt.attrib.get("name", "")
            oval = opt.attrib.get("value")
            if oval is not None and (
                opt in color_opts or oname in ("FOREGROUND", "BACKGROUND", "EFFECT_COLOR", "ERROR_STRIPE_COLOR")
            ):
                if not ICLS_HEX_RE.match(oval):
                    fail(f"jetbrains {rel_icls} invalid .icls hex {oname}={oval!r} (must be 6 uppercase hex without #)")
    if len(errors) == e0:
        ok("jetbrains: plugin.xml, 3 .theme.json UI themes, and 3 .icls schemes verified")

    # 6.6 Windows Terminal + PSReadLine (including PSReadLine 2.0 / <2.1.0 guard)
    e0 = len(errors)
    wt_dir = os.path.join(ROOT, "apps", "windows-terminal")
    wt_req_keys = {
        "name", "background", "foreground", "cursorColor", "selectionBackground",
        "black", "red", "green", "yellow", "blue", "purple", "cyan", "white",
        "brightBlack", "brightRed", "brightGreen", "brightYellow",
        "brightBlue", "brightPurple", "brightCyan", "brightWhite",
    }
    wt_schemes = json.loads(read_utf8(os.path.join(wt_dir, "schemes.json")))
    if not isinstance(wt_schemes, list) or len(wt_schemes) != 3:
        fail("windows-terminal/schemes.json must be a 3-item array")
    ps1_files_to_parse: list[str] = []
    for idx, vid in enumerate(EXPECTED_VARIANTS):
        single = json.loads(read_utf8(os.path.join(wt_dir, f"{vid}.json")))
        if idx < len(wt_schemes) and single != wt_schemes[idx]:
            fail(f"windows-terminal/{vid}.json out of sync with schemes.json[{idx}]")
        if set(single.keys()) != wt_req_keys:
            fail(f"windows-terminal/{vid}.json key mismatch: {set(single.keys()) ^ wt_req_keys}")
        for k, v in single.items():
            if k != "name" and not HEX6_RE.match(v):
                fail(f"windows-terminal/{vid}.json invalid hex {k}={v!r}")
        psrl_path = os.path.join(wt_dir, "psreadline", f"{vid}.ps1")
        ps1_files_to_parse.append(psrl_path)
        ps1_txt = read_utf8(psrl_path)
        if "Set-PSReadLineOption" not in ps1_txt or not check_balanced_delimiters(strip_ps1_strings_and_comments(ps1_txt)):
            fail(f"windows-terminal/psreadline/{vid}.ps1 failed syntax/brace check")
        # Backport check: InlinePrediction must NOT be in the base hashtable; must be guarded by 2.1.0 version check
        guard_m = re.search(
            r"if\s*\(\s*\(Get-Module\s+PSReadLine\)\.Version\s*-ge\s*\[version\]['\"]2\.1\.0['\"]\s*\)\s*\{([^}]*)\}",
            ps1_txt,
            flags=re.S,
        )
        if not guard_m or "InlinePrediction" not in guard_m.group(1):
            fail(f"windows-terminal/psreadline/{vid}.ps1 missing PSReadLine 2.1.0 version guard for InlinePrediction")
        outside_guard = ps1_txt[: guard_m.start()] if guard_m else ps1_txt
        if "InlinePrediction" in outside_guard:
            fail(f"windows-terminal/psreadline/{vid}.ps1 sets InlinePrediction outside 2.1.0 version guard")
    if len(errors) == e0:
        ok("windows-terminal: schemes.json, 3 scheme JSONs, and 3 PSReadLine 2.0-safe .ps1 scripts verified")

    # 6.7 WezTerm, Alacritty, Starship (.toml via tomllib)
    e0 = len(errors)
    for vid in EXPECTED_VARIANTS:
        wz = tomllib.loads(read_utf8(os.path.join(ROOT, "apps", "wezterm", f"{vid}.toml")))
        if "colors" not in wz or len(wz["colors"].get("ansi", [])) != 8 or len(wz["colors"].get("brights", [])) != 8:
            fail(f"wezterm/{vid}.toml missing [colors] ansi/brights")
        if "tab_bar" not in wz["colors"]:
            fail(f"wezterm/{vid}.toml missing [colors.tab_bar]")

        al = tomllib.loads(read_utf8(os.path.join(ROOT, "apps", "alacritty", f"{vid}.toml")))
        al_c = al.get("colors", {})
        for sec in ("primary", "cursor", "selection", "normal", "bright"):
            if sec not in al_c:
                fail(f"alacritty/{vid}.toml missing [colors.{sec}]")

        st = tomllib.loads(read_utf8(os.path.join(ROOT, "apps", "starship", f"{vid}.toml")))
        pname = st.get("palette", "")
        if pname not in st.get("palettes", {}):
            fail(f"starship/{vid}.toml palette {pname!r} missing in [palettes]")
    st_all = tomllib.loads(read_utf8(os.path.join(ROOT, "apps", "starship", "palettes.toml")))
    if len(st_all.get("palettes", {})) != 3:
        fail("starship/palettes.toml must define all 3 palettes")
    if len(errors) == e0:
        ok("wezterm, alacritty, starship: all 10 .toml configs parsed & verified via tomllib")

    # 6.8 Ghostty & Kitty
    e0 = len(errors)
    for vid in EXPECTED_VARIANTS:
        gh_lines = read_utf8(os.path.join(ROOT, "apps", "ghostty", vid)).splitlines()
        gh_pals: dict[int, str] = {}
        gh_keys: dict[str, str] = {}
        for ln in gh_lines:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            k, v = [p.strip() for p in ln.split("=", 1)]
            if k == "palette":
                idx_s, hx = v.split("=", 1)
                gh_pals[int(idx_s)] = hx
            else:
                gh_keys[k] = v
        if set(gh_pals.keys()) != set(range(16)) or not all(HEX6_RE.match(h) for h in gh_pals.values()):
            fail(f"ghostty/{vid} incomplete or invalid palette 0..15")
        for rk in ("background", "foreground", "cursor-color", "selection-background"):
            if not HEX6_RE.match(gh_keys.get(rk, "")):
                fail(f"ghostty/{vid} missing or invalid {rk}")

        kt_lines = read_utf8(os.path.join(ROOT, "apps", "kitty", f"{vid}.conf")).splitlines()
        kt_keys: dict[str, str] = {}
        for ln in kt_lines:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = ln.split(None, 1)
            if len(parts) == 2:
                kt_keys[parts[0]] = parts[1]
        for rk in ("foreground", "background", "cursor", *(f"color{i}" for i in range(16))):
            if not HEX6_RE.match(kt_keys.get(rk, "")):
                fail(f"kitty/{vid}.conf missing or invalid {rk}")
    if len(errors) == e0:
        ok("ghostty & kitty: all 6 terminal configs verified")

    # 6.9 Oh My Posh (v3 JSON + p:<key> resolution + segment contrast)
    e0 = len(errors)
    omp_ref_rx = re.compile(r"\bp:([A-Za-z0-9_-]+)\b")
    for vid in EXPECTED_VARIANTS:
        omp_raw = read_utf8(os.path.join(ROOT, "apps", "oh-my-posh", f"{vid}.omp.json"))
        omp = json.loads(omp_raw)
        if omp.get("version") != 3 or not isinstance(omp.get("palette"), dict):
            fail(f"oh-my-posh/{vid}.omp.json invalid version or palette")
            continue
        p_dict = omp["palette"]
        for pk, phx in p_dict.items():
            if not HEX6_RE.match(phx):
                fail(f"oh-my-posh/{vid}.omp.json invalid palette[{pk}]={phx!r}")
        unresolved = set(omp_ref_rx.findall(omp_raw)) - set(p_dict.keys())
        if unresolved:
            fail(f"oh-my-posh/{vid}.omp.json unresolved p:<key> refs: {sorted(unresolved)}")
        for blk in omp.get("blocks", []):
            for seg in blk.get("segments", []):
                fg_ref = seg.get("foreground", "")
                bg_ref = seg.get("background", "p:bg")
                if fg_ref.startswith("p:") and bg_ref.startswith("p:"):
                    fg_h, bg_h = p_dict.get(fg_ref[2:]), p_dict.get(bg_ref[2:])
                    if fg_h and bg_h and pal.contrast(fg_h, bg_h) < 4.5:
                        fail(f"oh-my-posh/{vid} segment {seg.get('type')} contrast < 4.5:1 ({fg_h} on {bg_h})")
    if len(errors) == e0:
        ok("oh-my-posh: 3 v3 configs & all p:<key> palette references verified")

    # 6.10 bat (.tmTheme XML + plistlib)
    e0 = len(errors)
    for tname in ("Cyclorama Dawn.tmTheme", "Cyclorama Steel.tmTheme", "Cyclorama Day.tmTheme"):
        bp = os.path.join(ROOT, "apps", "bat", tname)
        raw_b = open(bp, "rb").read()
        ET.fromstring(raw_b.decode("utf-8"))
        pl = plistlib.loads(raw_b)
        settings = pl.get("settings", [])
        if len(settings) < 15 or "background" not in settings[0].get("settings", {}):
            fail(f"bat/{tname}: missing global settings or scope rules")
    if len(errors) == e0:
        ok("bat: 3 .tmTheme files verified via ElementTree & plistlib")

    # 6.11 delta (.gitconfig via git config --file --list)
    e0 = len(errors)
    delta_dir = os.path.join(ROOT, "apps", "delta")
    for gname, expected_sections in [
        ("cyclorama.gitconfig", list(EXPECTED_VARIANTS)),
        *((f"{vid}.gitconfig", [vid]) for vid in EXPECTED_VARIANTS),
    ]:
        gp = os.path.join(delta_dir, gname)
        res = subprocess.run(["git", "config", "--file", gp, "--list"], capture_output=True, text=True)
        if res.returncode != 0:
            fail(f"delta/{gname} git config parse error: {res.stderr.strip()}")
            continue
        for sec_vid in expected_sections:
            if f"delta.{sec_vid}.syntax-theme=" not in res.stdout:
                fail(f"delta/{gname} missing [delta \"{sec_vid}\"] syntax-theme")
    if len(errors) == e0:
        ok("delta: unified + 3 standalone .gitconfig files verified via git config")

    # 6.12 fzf (.sh + .ps1 + active-row WCAG AA text contrast)
    e0 = len(errors)
    fzf_slots = {
        "bg", "bg+", "fg", "fg+", "hl", "hl+", "info", "marker",
        "pointer", "prompt", "spinner", "header", "border", "gutter", "label", "query",
    }
    for vid in EXPECTED_VARIANTS:
        sh_txt = read_utf8(os.path.join(ROOT, "apps", "fzf", f"{vid}.sh"))
        fzf_ps_path = os.path.join(ROOT, "apps", "fzf", f"{vid}.ps1")
        ps1_files_to_parse.append(fzf_ps_path)
        ps_txt = read_utf8(fzf_ps_path)
        if "FZF_DEFAULT_OPTS" not in sh_txt or "FZF_DEFAULT_OPTS" not in ps_txt:
            fail(f"fzf/{vid}: missing FZF_DEFAULT_OPTS in .sh or .ps1")
        sh_map = dict(re.findall(r"([a-z+]+):(#[0-9A-Fa-f]{6})", sh_txt))
        ps_map = dict(re.findall(r"([a-z+]+):(#[0-9A-Fa-f]{6})", ps_txt))
        if set(sh_map.keys()) != fzf_slots or sh_map != ps_map:
            fail(f"fzf/{vid}: .sh/.ps1 color slots mismatch ({fzf_slots ^ set(sh_map.keys())})")
            continue
        for fg_k, bg_k in (("fg", "bg"), ("fg+", "bg+"), ("hl", "bg"), ("hl+", "bg+"), ("prompt", "bg"), ("info", "bg")):
            cr = pal.contrast(sh_map[fg_k], sh_map[bg_k])
            if cr < 4.5:
                fail(f"fzf/{vid}: {fg_k} ({sh_map[fg_k]}) on {bg_k} ({sh_map[bg_k]}) = {cr:.2f}:1 (< 4.5:1 WCAG AA)")
    if len(errors) == e0:
        ok("fzf: 3 .sh + 3 .ps1 configs & active-row contrast verified")

    # 6.13 Obsidian
    e0 = len(errors)
    obs_dir = os.path.join(ROOT, "apps", "obsidian")
    obs_manifest = json.loads(read_utf8(os.path.join(obs_dir, "manifest.json")))
    if not obs_manifest.get("name") or not obs_manifest.get("minAppVersion"):
        fail("obsidian/manifest.json missing name or minAppVersion")
    obs_css = read_utf8(os.path.join(obs_dir, "theme.css"))
    if not check_balanced_braces_css(obs_css) or "@settings" not in obs_css:
        fail("obsidian/theme.css unbalanced braces or missing Style Settings block")
    for vid in EXPECTED_VARIANTS:
        snip_css = read_utf8(os.path.join(obs_dir, "snippets", f"{vid}.css"))
        if not check_balanced_braces_css(snip_css):
            fail(f"obsidian/snippets/{vid}.css unbalanced braces")
    if len(errors) == e0:
        ok("obsidian: manifest.json, theme.css, and 3 snippets verified")

    # 6.14 Chromium MV3
    e0 = len(errors)
    for vid in EXPECTED_VARIANTS:
        cm = json.loads(read_utf8(os.path.join(ROOT, "apps", "chromium", vid, "manifest.json")))
        if cm.get("manifest_version") != 3 or "colors" not in cm.get("theme", {}):
            fail(f"chromium/{vid}/manifest.json invalid MV3 theme structure")
            continue
        for ck, cv in cm["theme"]["colors"].items():
            if not (isinstance(cv, list) and len(cv) in (3, 4) and all(isinstance(x, int) and 0 <= x <= 255 for x in cv[:3])):
                fail(f"chromium/{vid} invalid RGB array {ck}={cv!r}")
        for tk, tv in cm["theme"].get("tints", {}).items():
            if not (isinstance(tv, list) and len(tv) == 3 and all(isinstance(x, (int, float)) and (x == -1.0 or 0.0 <= x <= 1.0) for x in tv)):
                fail(f"chromium/{vid} invalid HSL tint {tk}={tv!r}")
    if len(errors) == e0:
        ok("chromium: 3 MV3 browser theme manifests verified")

    # 6.15 Discord (BetterDiscord / Vencord)
    e0 = len(errors)
    for vid in EXPECTED_VARIANTS:
        dcss = read_utf8(os.path.join(ROOT, "apps", "discord", f"{vid}.theme.css"))
        if not dcss.startswith("/**") or not check_balanced_braces_css(dcss):
            fail(f"discord/{vid}.theme.css invalid metadata header or braces")
        hdr = dcss[: dcss.find("*/")]
        for meta_tag in ("@name", "@author", "@version", "@description"):
            if meta_tag not in hdr:
                fail(f"discord/{vid}.theme.css missing {meta_tag}")
    if len(errors) == e0:
        ok("discord: 3 Vencord/BetterDiscord .theme.css files verified")

    # 6.16 qBittorrent (including 5.x colors.dark / colors.light FolderThemeSource backport)
    e0 = len(errors)
    qb_root = os.path.join(ROOT, "apps", "qbittorrent")
    qb_readme = read_utf8(os.path.join(qb_root, "README.md"))
    qb_themes = json.loads(read_utf8(os.path.join(qb_root, "themes.json")))
    if "config.json" not in qb_readme or "FolderThemeSource" not in qb_readme:
        fail("qbittorrent/README.md missing qBittorrent 5.x config.json (FolderThemeSource) guidance")
    if "config.json" not in qb_themes.get("install", ""):
        fail("qbittorrent/themes.json install summary must reference config.json")
    for vid in EXPECTED_VARIANTS:
        qb_dir = os.path.join(qb_root, vid)
        qb_cfg = json.loads(read_utf8(os.path.join(qb_dir, "config.json")))
        mode_key = "colors.light" if vid == "cyclorama-day" else "colors.dark"
        forbidden_key = "colors.dark" if vid == "cyclorama-day" else "colors.light"
        if not isinstance(qb_cfg.get("colors"), dict) or len(qb_cfg["colors"]) < 8:
            fail(f"qbittorrent/{vid}/config.json missing colors dict")
        if not isinstance(qb_cfg.get(mode_key), dict) or qb_cfg.get(mode_key) != qb_cfg.get("colors"):
            fail(f"qbittorrent/{vid}/config.json missing or mismatched {mode_key} dict")
        if forbidden_key in qb_cfg:
            fail(f"qbittorrent/{vid}/config.json must not contain {forbidden_key}")
        for sec_k in ("colors", mode_key):
            for qk, qhx in qb_cfg.get(sec_k, {}).items():
                if not HEX6_RE.match(qhx):
                    fail(f"qbittorrent/{vid}/config.json invalid hex {sec_k}[{qk}]={qhx!r}")
        qss = read_utf8(os.path.join(qb_dir, "stylesheet.qss"))
        if not check_balanced_braces_css(qss):
            fail(f"qbittorrent/{vid}/stylesheet.qss unbalanced braces")
    if len(errors) == e0:
        ok("qbittorrent: 3 config.json palettes (colors + colors.dark/light) + 3 Qt QSS stylesheets verified")

    # 6.17 Flow Launcher (WPF XAML)
    e0 = len(errors)
    xaml_req = {
        "ItemSelectedBackgroundColor", "BaseQueryTextBoxStyle", "QueryBoxStyle",
        "WindowBorderStyle", "WindowStyle", "ItemTitleStyle", "ItemSubTitleStyle",
        "ItemTitleSelectedStyle", "ItemSubTitleSelectedStyle", "SeparatorStyle",
        "HighlightStyle", "ThumbStyle", "ScrollBarStyle", "ClockBox", "DateBox",
    }
    x_key_attr = "{http://schemas.microsoft.com/winfx/2006/xaml}Key"
    for xname in ("Cyclorama Dawn.xaml", "Cyclorama Steel.xaml", "Cyclorama Day.xaml"):
        xp = os.path.join(ROOT, "apps", "flow-launcher", xname)
        xtxt = read_utf8(xp)
        xroot = ET.fromstring(xtxt)
        sources = [el.attrib.get("Source", "") for el in xroot.iter() if "Source" in el.attrib]
        if not any("Base.xaml" in s for s in sources):
            fail(f"flow-launcher/{xname} does not merge Base.xaml")
        found_keys = {el.attrib[x_key_attr] for el in xroot.iter() if x_key_attr in el.attrib}
        missing_x = xaml_req - found_keys
        if missing_x:
            fail(f"flow-launcher/{xname} missing required keys: {sorted(missing_x)}")
        for hx in re.findall(r"#[0-9A-Za-z]+", xtxt):
            if not XAML_HEX_RE.match(hx):
                fail(f"flow-launcher/{xname} invalid XAML color {hx!r}")
    if len(errors) == e0:
        ok("flow-launcher: 3 WPF ResourceDictionary .xaml themes verified")

    # 6.18 Windows 11 (.theme INI + 6 Oklab PNG wallpapers + 3 backup-first .ps1 installers)
    e0 = len(errors)
    win_dir = os.path.join(ROOT, "apps", "windows")
    seen_theme_guids: set[str] = set()

    for vid in EXPECTED_VARIANTS:
        v = pal.VARIANTS[vid]
        wspec = WINDOWS_EXPECTED_SPECS[vid]

        # A. Verify .theme INI schema & exact values
        theme_file = os.path.join(win_dir, f"{v['name']}.theme")
        if not os.path.isfile(theme_file):
            fail(f"windows missing {v['name']}.theme")
        else:
            raw_theme_b = open(theme_file, "rb").read()
            if raw_theme_b.startswith(b"\xef\xbb\xbf"):
                fail(f"windows/{v['name']}.theme must not start with UTF-8 BOM (breaks Win32 GetPrivateProfileStringW)")
            theme_txt = raw_theme_b.decode("utf-8")
            try:
                cp = parse_ini_strict(theme_txt)
            except Exception as exc:
                fail(f"windows/{v['name']}.theme INI parse error: {exc}")
                cp = None
            if cp is not None:
                for req_sec in ("Theme", r"Control Panel\Desktop", r"Control Panel\Colors", "VisualStyles", "MasterThemeSelector", "boot"):
                    if not cp.has_section(req_sec):
                        fail(f"windows/{v['name']}.theme missing [{req_sec}]")
                if cp.get("Theme", "DisplayName", fallback="") != v["name"]:
                    fail(f"windows/{v['name']}.theme DisplayName mismatch")
                t_guid = cp.get("Theme", "ThemeId", fallback="")
                if not GUID_RE.match(t_guid) or t_guid in seen_theme_guids:
                    fail(f"windows/{v['name']}.theme invalid or duplicate ThemeId={t_guid!r}")
                seen_theme_guids.add(t_guid)
                expected_wp = f"%LOCALAPPDATA%\\rfs-themes\\windows\\wallpapers\\{vid}-1080p.png"
                if cp.get(r"Control Panel\Desktop", "Wallpaper", fallback="") != expected_wp:
                    fail(f"windows/{v['name']}.theme Wallpaper != {expected_wp!r}")
                if cp.get(r"Control Panel\Colors", "Background", fallback="") != wspec["bg_rgb_str"]:
                    fail(f"windows/{v['name']}.theme Background != {wspec['bg_rgb_str']!r}")
                if cp.get("VisualStyles", "ColorizationColor", fallback="") != wspec["colorization_argb"]:
                    fail(f"windows/{v['name']}.theme ColorizationColor != {wspec['colorization_argb']!r}")
                if cp.get("VisualStyles", "SystemMode", fallback="") != wspec["mode_win"]:
                    fail(f"windows/{v['name']}.theme SystemMode != {wspec['mode_win']!r}")
                if cp.get("VisualStyles", "AppMode", fallback="") != wspec["mode_win"]:
                    fail(f"windows/{v['name']}.theme AppMode != {wspec['mode_win']!r}")

        # B. Verify 1080p (1920x1080) and 4K (3840x2160) PNG wallpapers
        wp_dir = os.path.join(win_dir, "wallpapers")
        for res_tag, exp_dims in (("1080p", (1920, 1080)), ("4k", (3840, 2160))):
            for png_err in verify_png_file(os.path.join(wp_dir, f"{vid}-{res_tag}.png"), exp_dims, wspec["bg_rgb"]):
                fail(png_err)

        # C. Verify backup-first PowerShell installer (install-cyclorama-*.ps1)
        inst_path = os.path.join(win_dir, f"install-{vid}.ps1")
        ps1_files_to_parse.append(inst_path)
        if not os.path.isfile(inst_path):
            fail(f"windows missing install-{vid}.ps1")
            continue
        inst_txt = read_utf8(inst_path)
        if not check_balanced_delimiters(strip_ps1_strings_and_comments(inst_txt)):
            fail(f"windows/install-{vid}.ps1 unbalanced delimiters")

        # C1. Registry backup safety: must NOT overwrite BackupRegPath directly in reg.exe export,
        # and must guard against PS 5.1 $ErrorActionPreference='Stop' RemoteException on reg.exe 2>$null!
        if re.search(r"reg\.exe\s+export\s+\S+\s+\$BackupRegPath", inst_txt, re.I):
            fail(f"windows/install-{vid}.ps1 overwrites $BackupRegPath across multiple reg.exe export calls")
        if "backup-pre-rfs.reg" not in inst_txt or "Select-Object -Skip 1" not in inst_txt:
            fail(f"windows/install-{vid}.ps1 missing multi-key .reg header merge into backup-pre-rfs.reg")
        if re.search(r"reg\.exe\s+export[^\n]*2>\$null", inst_txt) and not re.search(
            r"\$ErrorActionPreference\s*=\s*['\"]Continue['\"]", inst_txt
        ):
            fail(
                f"windows/install-{vid}.ps1 calls `reg.exe export ... 2>$null` under `$ErrorActionPreference = 'Stop'` "
                "(throws terminating RemoteException in Windows PowerShell 5.1 if a registry key is absent)"
            )

        # C2. DPI-aware 4K auto-detection: Win32_VideoController / GetDeviceCaps must NOT be unreachable inside
        # a catch block behind DPI-virtualized System.Windows.Forms.Screen.PrimaryScreen.Bounds.Width!
        auto_m = re.search(r"if\s*\(\$Resolution\s*-eq\s*'auto'\)\s*\{([\s\S]*?)\n\}", inst_txt)
        if not auto_m:
            fail(f"windows/install-{vid}.ps1 missing `-Resolution -eq 'auto'` block")
        else:
            auto_blk = auto_m.group(1)
            if re.search(
                r"Screen\]::PrimaryScreen\.Bounds\.Width[\s\S]*?\}\s*catch\s*\{[\s\S]*?Win32_VideoController",
                auto_blk,
            ):
                fail(
                    f"windows/install-{vid}.ps1 queries Win32_VideoController only when Screen.PrimaryScreen.Bounds.Width "
                    "throws (on 150%/200%-scaled 4K displays in PS 5.1, WinForms returns 2560/1920 without throwing)"
                )

        # C3. Exact DWord byte order (ABGR vs AARRGGBB) & bare 0xXXXXXXXX Int32 literal check
        expected_dwords = {
            "AppsUseLightTheme": str(wspec["light_val"]),
            "SystemUsesLightTheme": str(wspec["light_val"]),
            "AccentColor": wspec["accent_abgr"],
            "ColorizationColor": wspec["colorization_argb"],
            "ColorizationAfterglow": wspec["colorization_argb"],
            "AccentColorMenu": wspec["accent_abgr"],
            "StartColorMenu": wspec["start_abgr"],
        }
        for reg_name, exp_lit in expected_dwords.items():
            pat = rf"-Name\s+'{re.escape(reg_name)}'\s+-Value\s+({re.escape(exp_lit)})\s+-Type\s+DWord\b"
            if not re.search(pat, inst_txt):
                fail(f"windows/install-{vid}.ps1 missing exact DWord `{reg_name} = {exp_lit}`")

        # C4. Exact 32-byte Explorer AccentPalette (8 x [R, G, B, 0x00])
        pal_m = re.search(r"\[byte\[\]\]\$AccentPalette\s*=\s*@\(([\s\S]*?)\)", inst_txt)
        if not pal_m:
            fail(f"windows/install-{vid}.ps1 missing [byte[]]$AccentPalette array")
        else:
            byte_vals = [int(tok, 16) for tok in re.findall(r"0x[0-9A-Fa-f]{2}", pal_m.group(1))]
            expected_bytes: list[int] = []
            for slot_hx in wspec["palette"]:
                sr, sg, sb = pal.hex_to_rgb(slot_hx)
                expected_bytes.extend((sr, sg, sb, 0x00))
            if len(byte_vals) != 32 or byte_vals != expected_bytes:
                fail(f"windows/install-{vid}.ps1 AccentPalette bytes mismatch (got {len(byte_vals)} bytes)")

        # C5. P/Invoke live apply & broadcast
        for req_tok in ("SystemParametersInfoW", "0x0014", "SendMessageTimeoutW", "ImmersiveColorSet"):
            if req_tok not in inst_txt:
                fail(f"windows/install-{vid}.ps1 missing {req_tok}")

    if len(errors) == e0:
        ok("windows: 3 .theme packs, 6 Oklab PNG wallpapers (1080p + 4K), and 3 .ps1 installers verified")

    # 6.19 Notepad++ (3 XML themes + 19 LexerTypes + GlobalStyles + 3 backup-first Dark Mode .ps1 appliers)
    e0 = len(errors)
    npp_dir = os.path.join(ROOT, "apps", "notepad-plus-plus")

    def _colorref_int(hx: str) -> int:
        r, g, b = pal.hex_to_rgb(hx)
        return r + (g << 8) + (b << 16)

    for vid in EXPECTED_VARIANTS:
        v = pal.VARIANTS[vid]
        ui = v["ui"]
        xml_name = f"{v['name']}.xml"
        xp = os.path.join(npp_dir, xml_name)
        if not os.path.isfile(xp):
            fail(f"notepad-plus-plus missing {xml_name}")
        else:
            xroot = ET.fromstring(read_utf8(xp))
            if xroot.tag != "NotepadPlus":
                fail(f"notepad-plus-plus/{xml_name}: root tag {xroot.tag!r} != 'NotepadPlus'")
            lex_els = xroot.findall("./LexerStyles/LexerType")
            found_lexers = {el.attrib.get("name", "") for el in lex_els}
            if len(lex_els) != 19 or found_lexers != NPP_EXPECTED_LEXERS:
                fail(f"notepad-plus-plus/{xml_name}: expected 19 LexerTypes, diff={found_lexers ^ NPP_EXPECTED_LEXERS}")
            glob_els = xroot.findall("./GlobalStyles/WidgetStyle")
            found_globals = {el.attrib.get("name", "") for el in glob_els}
            missing_globals = NPP_EXPECTED_GLOBALS - found_globals
            if missing_globals:
                fail(f"notepad-plus-plus/{xml_name}: missing GlobalStyles WidgetStyle(s): {sorted(missing_globals)}")
            for el in xroot.iter():
                for attr in ("fgColor", "bgColor"):
                    cval = el.attrib.get(attr)
                    if cval is not None and not ICLS_HEX_RE.match(cval):
                        fail(f"notepad-plus-plus/{xml_name}: invalid {attr}={cval!r} (must be 6 uppercase hex without #)")
                if el.tag == "WordsStyle":
                    fg_c, bg_c = el.attrib.get("fgColor"), el.attrib.get("bgColor")
                    if fg_c and bg_c and ICLS_HEX_RE.match(fg_c) and ICLS_HEX_RE.match(bg_c) and fg_c != bg_c:
                        cr = pal.contrast(f"#{fg_c}", f"#{bg_c}")
                        if cr < 4.5:
                            fail(
                                f"notepad-plus-plus/{xml_name} WordsStyle {el.attrib.get('name')!r}: "
                                f"#{fg_c} on #{bg_c} = {cr:.2f}:1 (< 4.5:1 WCAG AA)"
                            )

        ps_path = os.path.join(npp_dir, f"apply-{vid}.ps1")
        ps1_files_to_parse.append(ps_path)
        if not os.path.isfile(ps_path):
            fail(f"notepad-plus-plus missing apply-{vid}.ps1")
            continue
        ps_txt = read_utf8(ps_path)
        if not check_balanced_delimiters(strip_ps1_strings_and_comments(ps_txt)):
            fail(f"notepad-plus-plus/apply-{vid}.ps1 unbalanced delimiters")
        if "config.xml.pre-rfs.bak" not in ps_txt:
            fail(f"notepad-plus-plus/apply-{vid}.ps1 missing config.xml.pre-rfs.bak backup")

        # Verify exact Notepad++ 8.x DarkMode attributes & Win32 COLORREF values:
        # In Notepad++ 8.x (PowerEditor/src/NppDarkMode.h & NppConstants.h):
        #   NppDarkMode::ColorTone::customizedTone == 32 (colorTone="5" is cyanTone!)
        #   FluentColor::custom == 9 (*TbFluentColor="5" is FluentColor::cyan!)
        if v["mode"] == "dark":
            exp_npp_attrs = {
                "enable": "yes",
                "colorTone": "32",
                "customColorTop": str(_colorref_int(ui["rail"])),
                "customColorMenuHotTrack": str(_colorref_int(ui["raised"])),
                "customColorActive": str(_colorref_int(ui["surface"])),
                "customColorMain": str(_colorref_int(ui["bg"])),
                "customColorError": str(_colorref_int(ui["fault_fill"])),
                "customColorText": str(_colorref_int(ui["text"])),
                "customColorDarkText": str(_colorref_int(ui["mute"])),
                "customColorDisabledText": str(_colorref_int(ui["subtle"])),
                "customColorLinkText": str(_colorref_int(ui["accent"])),
                "customColorEdge": str(_colorref_int(ui["border"])),
                "customColorHotEdge": str(_colorref_int(ui["accent"])),
                "customColorDisabledEdge": str(_colorref_int(ui["border_subtle"])),
                "darkThemeName": xml_name,
                "darkTbFluentColor": "9",
                "darkTbFluentCustomColor": str(_colorref_int(ui["accent"])),
            }
        else:
            exp_npp_attrs = {
                "enable": "no",
                "lightThemeName": xml_name,
                "lightTbFluentColor": "9",
                "lightTbFluentCustomColor": str(_colorref_int(ui["accent"])),
            }
            if "stylerTheme" not in ps_txt:
                fail(f"notepad-plus-plus/apply-{vid}.ps1 missing stylerTheme update for light mode")

        for ak, aval in exp_npp_attrs.items():
            if not re.search(rf"'{re.escape(ak)}'\s*=\s*'{re.escape(aval)}'", ps_txt):
                fail(f"notepad-plus-plus/apply-{vid}.ps1 missing or wrong DarkMode attribute '{ak}' = '{aval}'")

    if len(errors) == e0:
        ok("notepad-plus-plus: 3 XML themes (19 lexers + GlobalStyles) & 3 Custom Dark Mode .ps1 appliers verified")

    # 6.20 Python IDLE (config-highlight.cfg + cyclorama-*.cfg + config-main-*.cfg + 48 WCAG AA pairs)
    e0 = len(errors)
    idle_dir = os.path.join(ROOT, "apps", "python-idle")
    idle_unified_cp = parse_ini_strict(read_utf8(os.path.join(idle_dir, "config-highlight.cfg")))
    idle_roles = (
        "normal", "keyword", "builtin", "comment", "string", "definition",
        "hilite", "break", "hit", "error", "context", "linenumber",
        "stdout", "stderr", "console",
    )
    for vid in EXPECTED_VARIANTS:
        v = pal.VARIANTS[vid]
        sec = v["name"]
        short = v["short"].lower()
        single_cp = parse_ini_strict(read_utf8(os.path.join(idle_dir, f"{vid}.cfg")))
        main_cp = parse_ini_strict(read_utf8(os.path.join(idle_dir, f"config-main-{short}.cfg")))
        if not idle_unified_cp.has_section(sec) or list(single_cp.sections()) != [sec]:
            fail(f"python-idle: missing or invalid section [{sec}]")
            continue
        u_items = dict(idle_unified_cp.items(sec))
        s_items = dict(single_cp.items(sec))
        if u_items != s_items:
            fail(f"python-idle/{vid}.cfg out of sync with config-highlight.cfg [{sec}]")
        if set(u_items.keys()) != IDLE_EXPECTED_KEYS:
            fail(f"python-idle [{sec}] key mismatch: {set(u_items.keys()) ^ IDLE_EXPECTED_KEYS}")
            continue
        for ik, iv in u_items.items():
            if not HEX6_RE.match(iv):
                fail(f"python-idle [{sec}] invalid hex {ik}={iv!r}")
        for role in idle_roles:
            fg_h, bg_h = u_items[f"{role}-foreground"], u_items[f"{role}-background"]
            cr = pal.contrast(fg_h, bg_h)
            if cr < 4.5:
                fail(f"python-idle [{sec}] {role} contrast {cr:.2f}:1 < 4.5:1 ({fg_h} on {bg_h})")
        cur_cr = pal.contrast(u_items["cursor-foreground"], u_items["normal-background"])
        if cur_cr < 4.5:
            fail(f"python-idle [{sec}] cursor-foreground contrast {cur_cr:.2f}:1 < 4.5:1")
        if not main_cp.has_section("Theme") or main_cp.get("Theme", "default", fallback="") != "False" or main_cp.get("Theme", "name", fallback="") != sec:
            fail(f"python-idle/config-main-{short}.cfg invalid [Theme] selector")
    if len(errors) == e0:
        ok("python-idle: unified + 3 highlight .cfg + 3 config-main .cfg (31 keys & 48/48 AA checks) verified")

    # 6.21 Windows PowerShell ISE (3 .StorableColorTheme.ps1xml + 73 keys + 3 .ps1 installers)
    e0 = len(errors)
    ise_dir = os.path.join(ROOT, "apps", "powershell-ise")
    ise_xml_paths: list[tuple[str, str]] = []

    def _srgb_linear(ch: int) -> float:
        s = ch / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    for vid in EXPECTED_VARIANTS:
        v = pal.VARIANTS[vid]
        ps1xml_name = f"{v['name']}.StorableColorTheme.ps1xml"
        xp = os.path.join(ise_dir, ps1xml_name)
        ise_xml_paths.append((vid, xp))
        if not os.path.isfile(xp):
            fail(f"powershell-ise missing {ps1xml_name}")
        else:
            xroot = ET.fromstring(read_utf8(xp))
            keys = tuple(el.text or "" for el in xroot.findall("./Keys/string"))
            colors = xroot.findall("./Values/Color")
            if keys != ISE_EXPECTED_73_KEYS or len(colors) != 73:
                fail(f"powershell-ise/{ps1xml_name}: expected exact 73 keys/values, got {len(keys)}/{len(colors)}")
            if xroot.findtext("./Name") != v["name"] or not xroot.findtext("./FontFamily") or not (xroot.findtext("./FontSize") or "").isdigit():
                fail(f"powershell-ise/{ps1xml_name}: missing or invalid Name, FontFamily, or FontSize")
            for k_name, c_el in zip(keys, colors):
                try:
                    ca = int(c_el.findtext("A") or "-1")
                    cr_i = int(c_el.findtext("R") or "-1")
                    cg_i = int(c_el.findtext("G") or "-1")
                    cb_i = int(c_el.findtext("B") or "-1")
                    sca = float(c_el.findtext("ScA") or "-1")
                    scr = float(c_el.findtext("ScR") or "-1")
                    scg = float(c_el.findtext("ScG") or "-1")
                    scb = float(c_el.findtext("ScB") or "-1")
                except ValueError:
                    fail(f"powershell-ise/{ps1xml_name}: non-numeric ARGB/ScRGB in {k_name}")
                    break
                if not all(0 <= x <= 255 for x in (ca, cr_i, cg_i, cb_i)):
                    fail(f"powershell-ise/{ps1xml_name}: out-of-range ARGB in {k_name}")
                if (
                    abs(sca - (ca / 255.0)) > 1e-4
                    or abs(scr - _srgb_linear(cr_i)) > 1e-4
                    or abs(scg - _srgb_linear(cg_i)) > 1e-4
                    or abs(scb - _srgb_linear(cb_i)) > 1e-4
                ):
                    fail(f"powershell-ise/{ps1xml_name}: ScRGB mismatch in {k_name}")
                if ca == 255 and k_name not in ("ConsolePaneBackgroundColor", "ConsolePaneTextBackgroundColor", "ScriptPaneBackgroundColor"):
                    hx_fg = pal.rgb_to_hex((cr_i, cg_i, cb_i))
                    bg_ref = v["ui"]["code_bg"] if k_name.startswith(("Console", "Error", "Warning", "Verbose", "Debug")) else v["ui"]["bg"]
                    if pal.contrast(hx_fg, bg_ref) < 4.5:
                        fail(f"powershell-ise/{ps1xml_name}: {k_name} ({hx_fg}) contrast < 4.5:1 on {bg_ref}")

        ise_ps_path = os.path.join(ise_dir, f"install-{vid}.ps1")
        ps1_files_to_parse.append(ise_ps_path)
        if not os.path.isfile(ise_ps_path):
            fail(f"powershell-ise missing install-{vid}.ps1")
            continue
        ise_ps_txt = read_utf8(ise_ps_path)
        if not check_balanced_delimiters(strip_ps1_strings_and_comments(ise_ps_txt)):
            fail(f"powershell-ise/install-{vid}.ps1 unbalanced delimiters")
        for req_tok in ("StorableColorTheme", "FromFile", "Validate", "StoreTheme", "Get-Variable -Name 'psISE'"):
            if req_tok not in ise_ps_txt:
                fail(f"powershell-ise/install-{vid}.ps1 missing {req_tok!r}")

    win_ps51 = shutil.which("powershell.exe")
    if os.name == "nt" and win_ps51 and all(os.path.isfile(p) for _, p in ise_xml_paths):
        ise_pairs_lit = ", ".join(
            f"@('{p.replace(chr(39), chr(39)*2)}', '{'Light Console, Light Editor' if vid == 'cyclorama-day' else 'Dark Console, Dark Editor'}')"
            for vid, p in ise_xml_paths
        )
        ise_validate_cmd = (
            "Add-Type -AssemblyName PresentationFramework; "
            "Add-Type -AssemblyName Microsoft.PowerShell.GPowerShell; "
            "if ($null -eq [System.Windows.Application]::Current) { $null = New-Object System.Windows.Application }; "
            "$asm = [System.Reflection.Assembly]::LoadWithPartialName('Microsoft.PowerShell.GPowerShell'); "
            "$flags = [System.Reflection.BindingFlags]'Public,NonPublic,Static,Instance'; "
            "$t = $asm.GetType('Microsoft.Windows.PowerShell.Gui.Internal.StorableColorTheme'); "
            "$pt = $asm.GetType('Microsoft.Windows.PowerShell.Gui.Internal.PresetThemes'); "
            "$presets = $pt.GetProperty('Themes', $flags).GetValue($null); "
            "$fromFile = $t.GetMethod('FromFile', $flags); "
            "$validate = $t.GetMethod('Validate', $flags); "
            f"foreach ($pair in @({ise_pairs_lit})) {{ "
            "  $obj = $fromFile.Invoke($null, [object[]]@($pair[0])); "
            "  $errs = $validate.Invoke($obj, [object[]]@($presets[$pair[1]])); "
            "  if ($errs.Count -ne 0) { Write-Error ($pair[0] + ': ' + ($errs -join '; ')); exit 3 } "
            "}"
        )
        ise_res = subprocess.run([win_ps51, "-NoProfile", "-STA", "-Command", ise_validate_cmd], capture_output=True, text=True)
        if ise_res.returncode != 0:
            fail(f"powershell-ise StorableColorTheme::FromFile().Validate() failed: {ise_res.stderr.strip()}")

    if len(errors) == e0:
        ok("powershell-ise: 3 .StorableColorTheme.ps1xml (73 keys, ScRGB, live Validate) & 3 .ps1 installers verified")

    # 6.22 Git Bash (Mintty .minttyrc + Native Git CLI .gitconfig)
    e0 = len(errors)
    gb_dir = os.path.join(ROOT, "apps", "git-bash")
    rgb_csv_rx = re.compile(r"^(\d{1,3}),(\d{1,3}),(\d{1,3})$")
    git_exe = shutil.which("git")
    for vid in EXPECTED_VARIANTS:
        v = pal.VARIANTS[vid]
        short = v["short"].lower()
        rc_txt = read_utf8(os.path.join(gb_dir, f"{vid}.minttyrc"))
        rc_map: dict[str, str] = {}
        for ln in rc_txt.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if "=" not in ln:
                fail(f"git-bash/{vid}.minttyrc malformed line: {ln!r}")
                continue
            mk, mv = ln.split("=", 1)
            m_rgb = rgb_csv_rx.match(mv.strip())
            if not m_rgb or not all(0 <= int(x) <= 255 for x in m_rgb.groups()):
                fail(f"git-bash/{vid}.minttyrc invalid RGB {mk}={mv!r}")
            rc_map[mk.strip()] = mv.strip()
        if set(rc_map.keys()) != MINTTY_EXPECTED_KEYS:
            fail(f"git-bash/{vid}.minttyrc key mismatch: {set(rc_map.keys()) ^ MINTTY_EXPECTED_KEYS}")

        gpath = os.path.join(gb_dir, f"git-colors-{short}.gitconfig")
        gtxt = read_utf8(gpath)
        for sec_hdr in ("[color]", '[color "diff"]', '[color "status"]', '[color "branch"]', '[color "grep"]'):
            if sec_hdr not in gtxt:
                fail(f"git-bash/git-colors-{short}.gitconfig missing section {sec_hdr}")
        if git_exe:
            gres = subprocess.run([git_exe, "config", "--file", gpath, "--list"], capture_output=True, text=True)
            if gres.returncode != 0:
                fail(f"git-bash/git-colors-{short}.gitconfig git config --list failed: {gres.stderr.strip()}")
            gc_res = subprocess.run(
                [git_exe, "config", "--file", gpath, "--get-color", "color.diff.new", ""],
                capture_output=True,
                text=True,
            )
            if gc_res.returncode != 0 or not gc_res.stdout.startswith("\x1b["):
                fail(f"git-bash/git-colors-{short}.gitconfig git --get-color color.diff.new failed")
    if len(errors) == e0:
        ok("git-bash: 3 Mintty .minttyrc (19 keys) + 3 native Git CLI .gitconfig files verified")

    # 6.23 QTerminal (.colorscheme INI)
    e0 = len(errors)
    qt_dir = os.path.join(ROOT, "apps", "qterminal")
    for vid in EXPECTED_VARIANTS:
        v = pal.VARIANTS[vid]
        cs_name = f"{v['name']}.colorscheme"
        cs_cp = parse_ini_strict(read_utf8(os.path.join(qt_dir, cs_name)))
        if set(cs_cp.sections()) != QTERMINAL_EXPECTED_SECTIONS:
            fail(f"qterminal/{cs_name} section mismatch: {set(cs_cp.sections()) ^ QTERMINAL_EXPECTED_SECTIONS}")
            continue
        if cs_cp.get("General", "Description", fallback="") != v["name"]:
            fail(f"qterminal/{cs_name} Description mismatch")
        for sec in QTERMINAL_EXPECTED_SECTIONS - {"General"}:
            c_str = cs_cp.get(sec, "Color", fallback="")
            m_rgb = rgb_csv_rx.match(c_str)
            if not m_rgb or not all(0 <= int(x) <= 255 for x in m_rgb.groups()):
                fail(f"qterminal/{cs_name} invalid Color={c_str!r} in [{sec}]")
    if len(errors) == e0:
        ok("qterminal: 3 QTermWidget6 .colorscheme INI files verified")

    # 6.24 Windows Console Host (.reg HKCU\Console + restore-defaults.reg + VGA order + WCAG AA)
    e0 = len(errors)
    wc_dir = os.path.join(ROOT, "apps", "windows-console")
    dword_colorref_rx = re.compile(r"^dword:00([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$")
    reg_targets = [*(f"{vid}.reg" for vid in EXPECTED_VARIANTS), "restore-defaults.reg"]
    for rname in reg_targets:
        rpath = os.path.join(wc_dir, rname)
        if not os.path.isfile(rpath):
            fail(f"windows-console missing {rname}")
            continue
        rlines = read_utf8(rpath).splitlines()
        if not rlines or rlines[0] != "Windows Registry Editor Version 5.00":
            fail(f"windows-console/{rname}: missing 'Windows Registry Editor Version 5.00' header")
            continue
        rcp = parse_ini_strict("\n".join(rlines[1:]))
        sec = r"HKEY_CURRENT_USER\Console"
        if not rcp.has_section(sec):
            fail(f"windows-console/{rname}: missing [{sec}]")
            continue
        slot_hexes: list[str] = []
        for idx in range(16):
            raw_dw = rcp.get(sec, f'"ColorTable{idx:02d}"', fallback="")
            m_dw = dword_colorref_rx.match(raw_dw)
            if not m_dw:
                fail(f"windows-console/{rname}: invalid ColorTable{idx:02d}={raw_dw!r} (expected dword:00bbggrr)")
                break
            b_i, g_i, r_i = (int(x, 16) for x in m_dw.groups())
            slot_hexes.append(pal.rgb_to_hex((r_i, g_i, b_i)))
        if len(slot_hexes) != 16:
            continue
        if rname != "restore-defaults.reg":
            vid = rname[:-4]
            v = pal.VARIANTS[vid]
            a = v["ansi"]
            exp_vga = [
                v["ui"]["bg"], a["blue"], a["green"], a["cyan"],
                a["red"], a["magenta"], a["yellow"], v["ui"]["text"],
                a["brightBlack"], a["brightBlue"], a["brightGreen"], a["brightCyan"],
                a["brightRed"], a["brightMagenta"], a["brightYellow"], a["brightWhite"],
            ]
            if slot_hexes != exp_vga:
                fail(f"windows-console/{rname}: VGA ColorTable00..15 / 00bbggrr mismatch")
        for key_lbl in ('"ScreenColors"', '"PopupColors"'):
            attr_dw = rcp.get(sec, key_lbl, fallback="")
            if not re.match(r"^dword:000000[0-9a-f]{2}$", attr_dw):
                fail(f"windows-console/{rname}: invalid {key_lbl}={attr_dw!r}")
                continue
            byte_v = int(attr_dw.split(":")[1], 16)
            bg_idx, fg_idx = (byte_v >> 4) & 0xF, byte_v & 0xF
            cr = pal.contrast(slot_hexes[fg_idx], slot_hexes[bg_idx])
            if cr < 4.5:
                fail(
                    f"windows-console/{rname} {key_lbl}: slot {fg_idx:02d} ({slot_hexes[fg_idx]}) on "
                    f"slot {bg_idx:02d} ({slot_hexes[bg_idx]}) = {cr:.2f}:1 (< 4.5:1 WCAG AA)"
                )
    if len(errors) == e0:
        ok("windows-console: 3 Cyclorama .reg + restore-defaults.reg (VGA 00bbggrr & Screen/Popup AA) verified")

    # 6.25 Proton Mail (3 Custom Theme CSS files + Proton Design System tokens + WCAG AA)
    e0 = len(errors)
    pm_dir = os.path.join(ROOT, "apps", "proton-mail")
    pm_contrast_pairs = (
        ("--text-norm", "--background-norm"),
        ("--text-norm", "--background-weak"),
        ("--text-norm", "--background-strong"),
        ("--text-weak", "--background-norm"),
        ("--text-hint", "--background-norm"),
        ("--primary-contrast", "--primary"),
        ("--interaction-norm-contrast", "--interaction-norm"),
        ("--interaction-norm-contrast", "--interaction-norm-major-1"),
        ("--signal-danger-contrast", "--signal-danger"),
        ("--signal-danger-contrast", "--signal-danger-major-1"),
        ("--signal-warning-contrast", "--signal-warning"),
        ("--signal-success-contrast", "--signal-success"),
        ("--signal-info-contrast", "--signal-info"),
        ("--navigation-current-item-text-color", "--navigation-current-item-background-color"),
        ("--email-item-selected-text-color", "--email-item-selected-background-color"),
    )
    for vid in EXPECTED_VARIANTS:
        pm_css = read_utf8(os.path.join(pm_dir, f"{vid}.css"))
        if not check_balanced_braces_css(pm_css):
            fail(f"proton-mail/{vid}.css unbalanced braces")
        if re.search(r"\bin\s+oklch\b", pm_css, re.I):
            fail(f"proton-mail/{vid}.css contains forbidden `in oklch`")
        for req_var in PROTON_EXPECTED_VARS:
            if f"{req_var}:" not in pm_css:
                fail(f"proton-mail/{vid}.css missing Proton Design System token {req_var}")
        pm_props = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9A-Fa-f]{6})\s*;", pm_css))
        for fg_var, bg_var in pm_contrast_pairs:
            if fg_var in pm_props and bg_var in pm_props:
                cr = pal.contrast(pm_props[fg_var], pm_props[bg_var])
                if cr < 4.5:
                    fail(
                        f"proton-mail/{vid}.css: {fg_var} ({pm_props[fg_var]}) on "
                        f"{bg_var} ({pm_props[bg_var]}) = {cr:.2f}:1 (< 4.5:1 WCAG AA)"
                    )
    if len(errors) == e0:
        ok("proton-mail: 3 Proton Design System Custom Theme .css files & contrast pairs verified")

    # Optional native PowerShell AST Parser check across ALL .ps1 scripts when running on Windows
    ps_exe = shutil.which("powershell.exe") or shutil.which("pwsh")
    if ps_exe and ps1_files_to_parse:
        ps_list_lit = ", ".join("'" + p.replace("'", "''") + "'" for p in ps1_files_to_parse)
        ps_cmd = (
            f"$files = @({ps_list_lit}); $bad = 0; "
            "foreach ($f in $files) { $t = $null; $e = $null; "
            "[void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$t, [ref]$e); "
            "if ($e.Count -gt 0) { Write-Error ($f + ': ' + $e[0].Message); $bad++ } }; "
            "if ($bad -gt 0) { exit 2 }"
        )
        ps_res = subprocess.run([ps_exe, "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
        if ps_res.returncode != 0:
            fail(f"PowerShell AST parser reported syntax error(s): {ps_res.stderr.strip()}")
        else:
            ok(f"powershell AST: all {len(ps1_files_to_parse)} .ps1 scripts parsed with 0 syntax errors")

    # ------------------------------------------------------------------
    # 7. Relative Markdown & HTML link integrity + 28-app/84-variant telemetry
    # ------------------------------------------------------------------
    e0 = len(errors)
    md_files = [
        os.path.join(ROOT, "README.md"),
        os.path.join(ROOT, "AGENTS.md"),
        *(os.path.join(ROOT, "apps", slug, "README.md") for slug in sorted(EXPECTED_APPS)),
    ]
    md_link_rx = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    bad_space_link_rx = re.compile(r"!?\[[^\]]*\]\((?!<)[^)\n]+\s+[^)\n]*\)")
    html_attr_rx = re.compile(r'(?:href|src|srcset)="([^"]+)"')
    placeholder_rx = re.compile(r"(?:localhost|127\.0\.0\.1|example\.com)", re.I)

    for mf in md_files:
        rel_mf = os.path.relpath(mf, ROOT)
        if not os.path.isfile(mf):
            fail(f"missing README: {rel_mf}")
            continue
        mtxt = read_utf8(mf)
        stripped = re.sub(r"```.*?```", "", mtxt, flags=re.S)
        stripped = re.sub(r"`[^`\n]+`", "", stripped)
        for sm in bad_space_link_rx.finditer(stripped):
            fail(f"unescaped space in Markdown link ({rel_mf}): {sm.group(0)}")
        for m in md_link_rx.finditer(stripped):
            target = m.group(1).strip().strip("<>")
            if placeholder_rx.search(target):
                fail(f"placeholder/localhost URL in {rel_mf}: {target}")
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            clean = urllib.parse.unquote(target.split("#")[0].split("?")[0])
            if clean and not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(mf), clean))):
                fail(f"broken relative link in {rel_mf}: {target}")
        for m in html_attr_rx.finditer(stripped):
            for part in m.group(1).split(","):
                u = part.strip().split()[0]
                if not u.startswith(("http://", "https://", "#", "data:", "mailto:")):
                    clean = urllib.parse.unquote(u.split("#")[0].split("?")[0])
                    if clean and not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(mf), clean))):
                        fail(f"broken HTML asset link in {rel_mf}: {u}")

    docs_html_path = os.path.join(ROOT, "docs", "index.html")
    docs_html = read_utf8(docs_html_path)
    for req_html_copy in ("28 · Across 5 categories", "84 · Dawn, Steel, Day", "Showing 28 of 28 apps"):
        if req_html_copy not in docs_html:
            fail(f"docs/index.html missing updated 28-app/84-variant copy: {req_html_copy!r}")
    if re.search(r"\b(?:20\s+everyday|60\s+verified|20\s+ports|Showing\s+20|21\s+everyday|63\s+verified|21\s+ports|Showing\s+21|21\s*·\s*Across|63\s*·\s*Dawn)\b", docs_html, re.I):
        fail("docs/index.html contains stale 20/21-app or 60/63-variant telemetry copy")

    doc_ids = set(re.findall(r'\bid="([^"]+)"', docs_html))
    for m in html_attr_rx.finditer(docs_html):
        u = m.group(1).strip()
        if placeholder_rx.search(u):
            fail(f"placeholder/localhost URL in docs/index.html: {u}")
        elif u.startswith("#"):
            if len(u) > 1 and u[1:] not in doc_ids:
                fail(f"broken anchor in docs/index.html: {u}")
        elif not u.startswith(("http://", "https://", "data:", "mailto:")):
            parts = u.split("#")
            clean = urllib.parse.unquote(parts[0].split("?")[0])
            resolved = os.path.normpath(os.path.join(ROOT, "docs", clean))
            if not os.path.exists(resolved):
                fail(f"broken relative asset in docs/index.html: {u}")
            elif len(parts) > 1 and clean.endswith(".svg"):
                if f'id="{parts[1]}"' not in read_utf8(resolved):
                    fail(f"missing SVG symbol #{parts[1]} referenced in docs/index.html")

    if len(errors) == e0:
        ok(f"all relative links & 28-app telemetry verified across {len(md_files)} Markdown files and docs/index.html")

    # ------------------------------------------------------------------
    # 8. Brand & hygiene invariants (oklch, modals, innerHTML, URLs, CRLF)
    # ------------------------------------------------------------------
    if "rfs-shell" not in docs_html or "rfs-scroll-region" not in docs_html:
        fail("docs/index.html missing below-header .rfs-shell / .rfs-scroll-region layout")

    app_js_path = os.path.join(ROOT, "docs", "app.js")
    app_js = read_utf8(app_js_path)
    if re.search(r"\.innerHTML\b", app_js):
        fail("docs/app.js must not use .innerHTML (use XSS-safe DOM APIs)")
    if "${REPO_BLOB_BASE}${f.path}" in app_js or "${REPO_BLOB_BASE}${variant.file}" in app_js:
        fail("docs/app.js constructs GitHub URLs without encodeURI() for file paths containing spaces")
    if shutil.which("node"):
        chk = subprocess.run(["node", "--check", app_js_path], capture_output=True, text=True)
        if chk.returncode != 0:
            fail(f"node --check docs/app.js failed: {chk.stderr.strip()}")
        m_fn = re.search(r"const deriveDownloadFilename = \(app, variant\) => \{.*?\n  \};", app_js, flags=re.S)
        if m_fn and catalog.get("apps"):
            js_probe = (
                f"{m_fn.group(0)}\n"
                f"const cat = JSON.parse(require('fs').readFileSync({json.dumps(catalog_path)}, 'utf8'));\n"
                "const allowed = {"
                "json:['.json'],toml:['.toml'],lua:['.lua'],css:['.css'],sh:['.sh'],ps1:['.ps1'],"
                "ini:['.gitconfig','.ini','.theme','.cfg','.colorscheme','.reg'],"
                "conf:['.conf','.minttyrc',''],"
                "xml:['.xaml','.xml','.ps1xml'],"
                "pn1:['.txt']};\n"
                "for (const a of cat.apps) { for (const v of a.variants) {\n"
                "  const fn = deriveDownloadFilename(a, v);\n"
                "  if (/\\s/.test(fn)) { console.error(`${a.slug}/${v.id}: whitespace in download filename ${fn}`); process.exit(2); }\n"
                "  const dot = fn.lastIndexOf('.'); const ext = dot === -1 ? '' : fn.slice(dot).toLowerCase();\n"
                "  const okExts = allowed[v.copyLang] || ['.txt'];\n"
                "  if (!okExts.includes(ext)) { console.error(`${a.slug}/${v.id}: download filename '${fn}' mismatches copyLang='${v.copyLang}'`); process.exit(2); }\n"
                "} }\n"
            )
            probe = subprocess.run(["node", "-e", js_probe], capture_output=True, text=True)
            if probe.returncode != 0:
                for err_ln in probe.stderr.strip().splitlines():
                    fail(f"docs/app.js deriveDownloadFilename: {err_ln}")

    rx_oklch = re.compile(r"\bin\s+oklch\b", re.I)
    rx_modal = re.compile(r"\b(?:window\.)?(?:alert|confirm|prompt)\s*\(")
    rx_private = re.compile(r"\b(?:pn-selfhost|Eddy)\b")

    for r, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for fn in files:
            fp = os.path.join(r, fn)
            rel = os.path.relpath(fp, ROOT)
            rel_norm = rel.replace("\\", "/")

            if rel_norm.startswith(("apps/", "docs/assets/previews/", "tools/")) or rel_norm == "docs/assets/catalog.json":
                if not fn.endswith((".png", ".ico", ".woff2", ".pyc")):
                    raw_b = open(fp, "rb").read()
                    if b"\r\n" in raw_b:
                        fail(f"CRLF line endings in {rel_norm}")

            if fn == "verify-themes.py":
                continue

            if fn.endswith((".css", ".qss", ".html", ".js")):
                txt = open(fp, encoding="utf-8", errors="ignore").read()
                if rx_oklch.search(txt):
                    fail(f"`in oklch` forbidden in {rel_norm}")
                if fn.endswith(".js") and rx_modal.search(txt):
                    fail(f"native modal call in {rel_norm}")
            if fn.endswith((
                ".html", ".js", ".json", ".toml", ".md", ".py", ".txt", ".css", ".qss",
                ".lua", ".ps1", ".sh", ".gitconfig", ".conf", ".xaml", ".icls", ".tmTheme", ".theme", ".svg",
                ".xml", ".ps1xml", ".cfg", ".minttyrc", ".colorscheme", ".reg",
            )):
                txt = open(fp, encoding="utf-8", errors="ignore").read()
                if rx_private.search(txt):
                    fail(f"private repo reference in {rel_norm}")

    if not errors:
        ok("zero `in oklch`, native modals, `innerHTML`, private-repo leaks, or CRLF drift")
        ok("all rfs-themes checks passed (28 apps · 84 variants)")
        return 0

    print(f"[x]  verification failed with {len(errors)} error(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
