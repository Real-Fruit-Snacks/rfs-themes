#!/usr/bin/env python3
"""Verify rfs-themes integrity across all 20 apps (60 variants), WCAG AA contrast,
native format schemas, relative links, SVG previews, and Cyclorama Dawn invariants.

Zero external dependencies (Python 3.11+ standard library only).

Exit codes (RFS CLI standard):
    0  all checks passed
    1  one or more checks failed
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.parse
import xml.etree.ElementTree as ET

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

LUA_RESERVED = {
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "if", "in", "local", "nil", "not", "or", "repeat",
    "return", "then", "true", "until", "while",
}

EXPECTED_VARIANTS = ("cyclorama-dawn", "cyclorama-steel", "cyclorama-day")
EXPECTED_APPS = {
    "vscode", "neovim", "zed", "jetbrains",
    "windows-terminal", "wezterm", "alacritty", "ghostty", "kitty",
    "starship", "oh-my-posh", "bat", "delta", "fzf",
    "privacynotes", "obsidian",
    "chromium", "discord", "qbittorrent", "flow-launcher",
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
    # 3. apps/manifest.json validation (20 apps x 3 variants)
    # ------------------------------------------------------------------
    e0 = len(errors)
    manifest_path = os.path.join(ROOT, "apps", "manifest.json")
    manifest = json.loads(read_utf8(manifest_path))
    m_apps = manifest.get("apps", [])
    m_slugs = [a.get("slug") for a in m_apps]
    if len(m_apps) != 20 or set(m_slugs) != EXPECTED_APPS:
        fail(f"apps/manifest.json expected 20 canonical apps, got {len(m_apps)} ({set(m_slugs) ^ EXPECTED_APPS})")
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
    # 4. docs/assets/catalog.json validation
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
        if catalog.get("stats", {}).get("apps") != 20 or catalog.get("stats", {}).get("variants") != 60:
            fail(f"catalog.json stats invalid: {catalog.get('stats')}")
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
            ok("docs/assets/catalog.json valid (20 apps, 60 variants, snippets & swatches verified)")

    # ------------------------------------------------------------------
    # 5. All 60 SVG preview pairs (SHA-256 sync + XML parse + swatch check)
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
            svg_count += 1
    if len(errors) == e0 and svg_count == 60:
        ok("all 60 SVG preview pairs synced, XML-valid, and swatch-accurate")

    # ------------------------------------------------------------------
    # 6. Native format schema & syntax verification for ALL 20 apps
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

    # 6.6 Windows Terminal + PSReadLine
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
    for idx, vid in enumerate(EXPECTED_VARIANTS):
        single = json.loads(read_utf8(os.path.join(wt_dir, f"{vid}.json")))
        if idx < len(wt_schemes) and single != wt_schemes[idx]:
            fail(f"windows-terminal/{vid}.json out of sync with schemes.json[{idx}]")
        if set(single.keys()) != wt_req_keys:
            fail(f"windows-terminal/{vid}.json key mismatch: {set(single.keys()) ^ wt_req_keys}")
        for k, v in single.items():
            if k != "name" and not HEX6_RE.match(v):
                fail(f"windows-terminal/{vid}.json invalid hex {k}={v!r}")
        ps1_txt = read_utf8(os.path.join(wt_dir, "psreadline", f"{vid}.ps1"))
        if "Set-PSReadLineOption" not in ps1_txt or not check_balanced_delimiters(
            re.sub(r"#[^\n]*", "", re.sub(r'"(?:[^"`]|`.)*"|\'[^\']*\'', '""', ps1_txt))
        ):
            fail(f"windows-terminal/psreadline/{vid}.ps1 failed syntax/brace check")
    if len(errors) == e0:
        ok("windows-terminal: schemes.json, 3 scheme JSONs, and 3 PSReadLine .ps1 scripts verified")

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
        ps_txt = read_utf8(os.path.join(ROOT, "apps", "fzf", f"{vid}.ps1"))
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

    # 6.16 qBittorrent
    e0 = len(errors)
    for vid in EXPECTED_VARIANTS:
        qb_dir = os.path.join(ROOT, "apps", "qbittorrent", vid)
        qb_cfg = json.loads(read_utf8(os.path.join(qb_dir, "config.json")))
        if not isinstance(qb_cfg.get("colors"), dict) or len(qb_cfg["colors"]) < 8:
            fail(f"qbittorrent/{vid}/config.json missing colors dict")
        for qk, qhx in qb_cfg.get("colors", {}).items():
            if not HEX6_RE.match(qhx):
                fail(f"qbittorrent/{vid}/config.json invalid hex {qk}={qhx!r}")
        qss = read_utf8(os.path.join(qb_dir, "stylesheet.qss"))
        if not check_balanced_braces_css(qss):
            fail(f"qbittorrent/{vid}/stylesheet.qss unbalanced braces")
    if len(errors) == e0:
        ok("qbittorrent: 3 config.json palettes + 3 Qt QSS stylesheets verified")

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

    # ------------------------------------------------------------------
    # 7. Relative Markdown & HTML link integrity
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
        ok(f"all relative links & assets verified across {len(md_files)} Markdown files and docs/index.html")

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
                "const allowed = {json:['.json'],toml:['.toml'],lua:['.lua'],css:['.css'],sh:['.sh'],ps1:['.ps1'],ini:['.gitconfig','.ini'],conf:['.conf',''],xml:['.xaml','.xml'],pn1:['.txt']};\n"
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
                ".html", ".js", ".json", ".toml", ".md", ".py", ".txt", ".css",
                ".lua", ".ps1", ".sh", ".gitconfig", ".conf", ".xaml", ".icls", ".tmTheme",
            )):
                txt = open(fp, encoding="utf-8", errors="ignore").read()
                if rx_private.search(txt):
                    fail(f"private repo reference in {rel_norm}")

    if not errors:
        ok("zero `in oklch`, native modals, `innerHTML`, private-repo leaks, or CRLF drift")
        ok("all rfs-themes checks passed (20 apps · 60 variants)")
        return 0

    print(f"[x]  verification failed with {len(errors)} error(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
