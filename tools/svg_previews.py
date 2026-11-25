#!/usr/bin/env python3
"""Reusable 660x390 Cyclorama Dawn SVG preview renderers for rfs-themes.

Every preview shares the exact Cyclorama Dawn telemetry framing (3px Steel->Beacon
horizon beam, crisp 1px outer frame, zero macOS traffic lights, bottom 10-swatch
telemetry ribbon) while depicting the authentic UI of each app archetype:
  - render_editor_preview()   : Code editors & IDEs (VS Code, Neovim, Zed, JetBrains)
  - render_terminal_preview() : Terminal emulators (Windows Terminal, WezTerm, Alacritty, Ghostty, Kitty)
  - render_cli_preview()      : CLI/TUI tools (Starship, Oh My Posh, bat, delta, fzf)
  - render_notes_preview()    : Markdown & knowledge apps (Obsidian)
  - render_browser_preview()  : Chromium / Brave browser chrome
  - render_chat_preview()     : Discord / Vencord / BetterDiscord chat client
  - render_utility_preview()  : Desktop utilities (qBittorrent transfers, Flow Launcher spotlight)
  - render_windows_preview()  : Windows 11 desktop wallpaper stage, Settings Colors, and taskbar
"""
from __future__ import annotations

from html import escape
import os

from rfs_palette import VARIANTS, ansi_list, mix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_preview_pair(slug: str, variant_id: str, svg: str) -> tuple[str, str]:
    """Write identical SVG to apps/<slug>/previews/ and docs/assets/previews/<slug>/."""
    p1_dir = os.path.join(ROOT, "apps", slug, "previews")
    p2_dir = os.path.join(ROOT, "docs", "assets", "previews", slug)
    os.makedirs(p1_dir, exist_ok=True)
    os.makedirs(p2_dir, exist_ok=True)
    p1 = os.path.join(p1_dir, f"{variant_id}.svg")
    p2 = os.path.join(p2_dir, f"{variant_id}.svg")
    for p in (p1, p2):
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
    return p1, p2


def _frame_shell(variant: dict, badge_tag: str, app_title: str, status_tag: str, body: str, swatches: list[tuple[str, str]]) -> str:
    ui = variant["ui"]
    mode_lbl = "DARK" if variant["mode"] == "dark" else "LIGHT"
    name = escape(variant["name"])
    lx = escape(variant["lx"])
    tag = escape(badge_tag)
    title = escape(app_title)
    st = escape(status_tag)

    sw_svg = []
    sw_w = 56
    for idx, (lbl, hx) in enumerate(swatches[:10]):
        sx = 18 + idx * (sw_w + 6.4)
        sw_svg.append(
            f'<rect x="{sx:.1f}" y="357" width="{sw_w}" height="10" rx="2.5" fill="{hx}" stroke="{ui["border"]}" stroke-width="0.8"/>'
            f'<text x="{sx + sw_w / 2:.1f}" y="378" text-anchor="middle" fill="{ui["mute"]}" '
            f'font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="600">{escape(lbl)}</text>'
        )

    tag_w = max(84, len(badge_tag) * 6.4 + 22)
    title_x = 14 + tag_w + 12

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 390" width="660" height="390" role="img" aria-label="{title} {name} ({lx} {mode_lbl}) theme preview">
  <defs>
    <linearGradient id="hbeam" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{ui["beam_start"]}"/>
      <stop offset="100%" stop-color="{ui["beam_end"]}"/>
    </linearGradient>
    <clipPath id="frame-clip"><rect x="1" y="1" width="658" height="388" rx="11"/></clipPath>
  </defs>
  <g clip-path="url(#frame-clip)">
    <rect width="660" height="390" fill="{ui["bg"]}"/>
    <rect width="660" height="3" fill="url(#hbeam)"/>

    <!-- Top chrome bar -->
    <rect x="0" y="3" width="660" height="33" fill="{ui["surface"]}"/>
    <line x1="0" y1="36" x2="660" y2="36" stroke="{ui["border"]}" stroke-width="1"/>
    <rect x="14" y="10" width="{tag_w:.0f}" height="19" rx="4" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="23" y="23" fill="{ui["accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">{tag}</text>
    <text x="{title_x:.0f}" y="23" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11.5" font-weight="700">{name}</text>
    <text x="646" y="23" text-anchor="end" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="600">{lx} · {mode_lbl} · {st}</text>

    {body}

    <!-- Bottom palette telemetry ribbon -->
    <rect x="0" y="346" width="660" height="44" fill="{ui["surface"]}"/>
    <line x1="0" y1="346" x2="660" y2="346" stroke="{ui["border"]}" stroke-width="1"/>
    {''.join(sw_svg)}
  </g>
  <rect x="0.5" y="0.5" width="659" height="389" rx="11.5" fill="none" stroke="{ui["border"]}" stroke-width="1"/>
</svg>
'''


def _standard_swatches(v: dict) -> list[tuple[str, str]]:
    ui, syn = v["ui"], v["syntax"]
    return [
        ("BG", ui["bg"]), ("SURF", ui["surface"]), ("RAISED", ui["raised"]), ("ACCENT", ui["accent"]),
        ("STEEL", ui["accent"] if v["id"] == "cyclorama-steel" else ui["secondary"]),
        ("KW", syn["keyword"]), ("FN", syn["function"]), ("STR", syn["string"]),
        ("OK", ui["signal"]), ("ERR", ui["fault"]),
    ]


def render_editor_preview(app_name: str, slug: str, variant: dict, active_file: str = "palette.rs", footer_left: str = "main  ·  UTF-8") -> str:
    ui, syn = variant["ui"], variant["syntax"]
    sel = mix(ui["surface"], ui["accent"], 0.16 if variant["mode"] == "dark" else 0.12)
    body = f'''
    <!-- Activity rail + File tree (x=0..168) -->
    <rect x="0" y="36" width="32" height="288" fill="{ui["rail"]}"/>
    <line x1="32" y1="36" x2="32" y2="324" stroke="{ui["border"]}" stroke-width="1"/>
    <rect x="0" y="50" width="2.5" height="20" fill="{ui["accent"]}"/>
    <rect x="10" y="54" width="12" height="12" rx="2" fill="none" stroke="{ui["accent"]}" stroke-width="1.5"/>
    <circle cx="16" cy="90" r="5.5" fill="none" stroke="{ui["mute"]}" stroke-width="1.4"/>
    <rect x="10" y="114" width="12" height="10" rx="1.5" fill="none" stroke="{ui["mute"]}" stroke-width="1.4"/>

    <rect x="32" y="36" width="136" height="288" fill="{ui["surface"]}"/>
    <line x1="168" y1="36" x2="168" y2="324" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="44" y="55" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700" letter-spacing="0.8">EXPLORER</text>
    <text x="44" y="76" fill="{ui["text_soft"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">v src/</text>
    <rect x="38" y="84" width="124" height="22" rx="4" fill="{sel}"/>
    <rect x="38" y="86" width="2.5" height="18" rx="1" fill="{ui["accent"]}"/>
    <text x="50" y="98.5" fill="{ui["text"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">{escape(active_file)}</text>
    <text x="50" y="120" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5">tokens.json</text>
    <text x="50" y="140" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5">theme.rs</text>
    <text x="50" y="160" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5">contrast.rs  M</text>
    <text x="44" y="186" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700" letter-spacing="0.8">DIAGNOSTICS</text>
    <rect x="44" y="196" width="112" height="20" rx="4" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="52" y="209.5" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">[ok] 0 errors</text>
    <rect x="44" y="222" width="112" height="20" rx="4" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="52" y="235.5" fill="{ui["warning"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">[!] 1 warning</text>

    <!-- Editor tab bar (x=168..660, y=36..64) -->
    <rect x="168" y="36" width="492" height="28" fill="{ui["rail"]}"/>
    <line x1="168" y1="64" x2="660" y2="64" stroke="{ui["border"]}" stroke-width="1"/>
    <rect x="168" y="36" width="128" height="28" fill="{ui["bg"]}"/>
    <rect x="168" y="36" width="128" height="2" fill="{ui["accent"]}"/>
    <text x="182" y="54" fill="{ui["text"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">{escape(active_file)}</text>
    <text x="312" y="54" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5">tokens.json</text>
    <text x="412" y="54" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5">contrast.rs</text>

    <!-- Code canvas (x=168..660, y=64..324) -->
    <rect x="168" y="64" width="492" height="260" fill="{ui["bg"]}"/>
    <!-- Active line highlight -->
    <rect x="168" y="138" width="492" height="21" fill="{ui["raised"]}"/>
    <!-- Selection highlight -->
    <rect x="286" y="160" width="136" height="18" rx="2" fill="{ui["selection_active"]}"/>
    <!-- Diff gutter markers -->
    <rect x="200" y="139" width="2.5" height="19" fill="{ui["signal"]}"/>
    <rect x="200" y="223" width="2.5" height="19" fill="{ui["secondary"]}"/>

    <!-- Line numbers -->
    <g fill="{ui["subtle"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" text-anchor="end">
      <text x="194" y="88">01</text><text x="194" y="109">02</text><text x="194" y="130">03</text>
      <text x="194" y="151" fill="{ui["text"]}" font-weight="700">04</text>
      <text x="194" y="172">05</text><text x="194" y="193">06</text><text x="194" y="214">07</text>
      <text x="194" y="235">08</text><text x="194" y="256">09</text><text x="194" y="277">10</text>
      <text x="194" y="298">11</text>
    </g>

    <!-- Syntax highlighted code -->
    <g font-family="ui-monospace,Consolas,monospace" font-size="10.2">
      <text x="212" y="88" fill="{syn["comment"]}">// Cyclorama Dawn v2.1.0 — Steel &amp; Beacon Orange</text>
      <text x="212" y="109"><tspan fill="{syn["keyword"]}" font-weight="700">pub struct </tspan><tspan fill="{syn["type"]}" font-weight="700">StageCue </tspan><tspan fill="{syn["punctuation"]}">&#123; </tspan><tspan fill="{syn["property"]}">lx</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["type"]}">u16</tspan><tspan fill="{syn["punctuation"]}">, </tspan><tspan fill="{syn["property"]}">name</tspan><tspan fill="{syn["punctuation"]}">: &amp;'static </tspan><tspan fill="{syn["type"]}">str </tspan><tspan fill="{syn["punctuation"]}">&#125;</tspan></text>
      <text x="212" y="130"><tspan fill="{syn["keyword"]}" font-weight="700">pub const </tspan><tspan fill="{syn["constant"]}" font-weight="700">DEFAULT_CUE</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["type"]}">StageCue </tspan><tspan fill="{syn["operator"]}">= </tspan><tspan fill="{syn["type"]}">StageCue </tspan><tspan fill="{syn["punctuation"]}">&#123;</tspan></text>
      <text x="212" y="151"><tspan fill="{syn["property"]}">    lx</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["number"]}" font-weight="700">263</tspan><tspan fill="{syn["punctuation"]}">, </tspan><tspan fill="{syn["property"]}">name</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["string"]}">"Beacon Horizon"</tspan><tspan fill="{syn["punctuation"]}">,</tspan></text>
      <text x="212" y="172"><tspan fill="{syn["punctuation"]}">&#125;; </tspan><tspan fill="{syn["keyword"]}" font-weight="700">pub fn </tspan><tspan fill="{syn["function"]}" font-weight="700">verify_wcag</tspan><tspan fill="{syn["punctuation"]}">(</tspan><tspan fill="{syn["parameter"]}">fg</tspan><tspan fill="{syn["punctuation"]}">: &amp;</tspan><tspan fill="{syn["type"]}">str</tspan><tspan fill="{syn["punctuation"]}">, </tspan><tspan fill="{syn["parameter"]}">bg</tspan><tspan fill="{syn["punctuation"]}">: &amp;</tspan><tspan fill="{syn["type"]}">str</tspan><tspan fill="{syn["punctuation"]}">) -&gt; </tspan><tspan fill="{syn["type"]}">f64 </tspan><tspan fill="{syn["punctuation"]}">&#123;</tspan></text>
      <text x="212" y="193"><tspan fill="{syn["keyword"]}" font-weight="700">    let </tspan><tspan fill="{ui["text"]}">ratio </tspan><tspan fill="{syn["operator"]}">= </tspan><tspan fill="{syn["function"]}">contrast_ratio</tspan><tspan fill="{syn["punctuation"]}">(</tspan><tspan fill="{syn["parameter"]}">fg</tspan><tspan fill="{syn["punctuation"]}">, </tspan><tspan fill="{syn["parameter"]}">bg</tspan><tspan fill="{syn["punctuation"]}">);</tspan></text>
      <text x="212" y="214"><tspan fill="{syn["keyword"]}" font-weight="700">    assert!</tspan><tspan fill="{syn["punctuation"]}">(</tspan><tspan fill="{ui["text"]}">ratio </tspan><tspan fill="{syn["operator"]}">&gt;= </tspan><tspan fill="{syn["number"]}" font-weight="700">4.5</tspan><tspan fill="{syn["punctuation"]}">, </tspan><tspan fill="{syn["string"]}">"[x] AA contrast failed"</tspan><tspan fill="{syn["punctuation"]}">);</tspan></text>
      <text x="212" y="235"><tspan fill="{syn["keyword"]}" font-weight="700">    println!</tspan><tspan fill="{syn["punctuation"]}">(</tspan><tspan fill="{syn["string"]}">"[ok] &#123;ratio:.2&#125;:1 calibrated"</tspan><tspan fill="{syn["punctuation"]}">);</tspan></text>
      <text x="212" y="256"><tspan fill="{ui["text"]}">    ratio</tspan></text>
      <text x="212" y="277"><tspan fill="{syn["punctuation"]}">&#125;</tspan></text>
      <text x="212" y="298" fill="{syn["comment"]}">// Built local-first · Real-Fruit-Snacks</text>
    </g>

    <!-- Status bar (y=324..346) -->
    <rect x="0" y="324" width="660" height="22" fill="{ui["accent_fill"]}"/>
    <text x="14" y="338.5" fill="#FFFFFF" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">{escape(footer_left)}</text>
    <text x="646" y="338.5" text-anchor="end" fill="#FFFFFF" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="600">{escape(app_name)} · AA PASS</text>
    '''
    return _frame_shell(variant, f"[{slug}]", app_name, "AA PASS", body, _standard_swatches(variant))


def render_terminal_preview(app_name: str, slug: str, variant: dict, shell_cmd: str = "rfs-themes verify --all") -> str:
    ui = variant["ui"]
    a = variant["ansi"]
    ansi16 = ansi_list(variant)
    from rfs_palette import contrast as cr
    ansi_bars = []
    for idx, hx in enumerate(ansi16):
        row = idx // 8
        col = idx % 8
        bx = 24 + col * 76
        by = 266 + row * 32
        txt_col = "#050507" if cr("#050507", hx) >= cr("#F4F5F8", hx) else "#F4F5F8"
        ansi_bars.append(
            f'<rect x="{bx}" y="{by}" width="68" height="22" rx="3" fill="{hx}" stroke="{ui["border"]}" stroke-width="0.8"/>'
            f'<text x="{bx + 34}" y="{by + 14}" text-anchor="middle" fill="{txt_col}" '
            f'font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">C{idx:02d}</text>'
        )

    body = f'''
    <!-- Terminal session tab bar -->
    <rect x="0" y="36" width="660" height="26" fill="{ui["rail"]}"/>
    <line x1="0" y1="62" x2="660" y2="62" stroke="{ui["border"]}" stroke-width="1"/>
    <rect x="12" y="39" width="166" height="23" rx="4" fill="{ui["bg"]}"/>
    <rect x="12" y="39" width="166" height="2" fill="{ui["accent"]}"/>
    <text x="24" y="54" fill="{ui["text"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.2" font-weight="700">1: pwsh  ~/rfs-themes</text>
    <text x="196" y="54" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.2">2: git log</text>

    <!-- Terminal body -->
    <rect x="0" y="62" width="660" height="284" fill="{ui["bg"]}"/>
    <g font-family="ui-monospace,Consolas,monospace" font-size="10.5">
      <text x="24" y="90"><tspan fill="{a["blue"]}" font-weight="700">matt@rfs</tspan><tspan fill="{ui["mute"]}">:</tspan><tspan fill="{a["cyan"]}">~/rfs-themes</tspan><tspan fill="{ui["mute"]}"> (</tspan><tspan fill="{a["magenta"]}">main</tspan><tspan fill="{ui["mute"]}">) </tspan><tspan fill="{a["brightRed"]}" font-weight="700">$</tspan><tspan fill="{ui["text"]}"> {escape(shell_cmd)}</tspan></text>
      <text x="24" y="114"><tspan fill="{a["green"]}" font-weight="700">[ok]</tspan><tspan fill="{ui["text"]}"> loaded brand/rfs.tokens.json </tspan><tspan fill="{a["yellow"]}">v2.1.0</tspan><tspan fill="{ui["mute"]}"> (Cyclorama Dawn)</tspan></text>
      <text x="24" y="136"><tspan fill="{a["cyan"]}" font-weight="700">[i] </tspan><tspan fill="{ui["text_soft"]}"> ANSI 0-15 calibrated · cursor </tspan><tspan fill="{ui["cursor"]}" font-weight="700">{ui["cursor"]}</tspan><tspan fill="{ui["mute"]}"> · selection </tspan><tspan fill="{a["blue"]}">{ui["selection_active"]}</tspan></text>
      <text x="24" y="158"><tspan fill="{a["yellow"]}" font-weight="700">[!] </tspan><tspan fill="{ui["text_soft"]}"> warning token: </tspan><tspan fill="{a["yellow"]}">{a["yellow"]}</tspan><tspan fill="{ui["mute"]}"> · diff-add </tspan><tspan fill="{a["green"]}">+142</tspan><tspan fill="{ui["mute"]}"> / </tspan><tspan fill="{a["red"]}">-18</tspan></text>
      <text x="24" y="180"><tspan fill="{a["red"]}" font-weight="700">[x] </tspan><tspan fill="{ui["text_soft"]}"> fault token: </tspan><tspan fill="{a["red"]}">{a["red"]}</tspan><tspan fill="{ui["mute"]}"> (Signal Crimson · AA verified)</tspan></text>
      <text x="24" y="206"><tspan fill="{a["blue"]}" font-weight="700">matt@rfs</tspan><tspan fill="{ui["mute"]}">:</tspan><tspan fill="{a["cyan"]}">~/rfs-themes</tspan><tspan fill="{ui["mute"]}"> </tspan><tspan fill="{a["brightRed"]}" font-weight="700">$</tspan><tspan fill="{ui["text"]}"> </tspan></text>
      <rect x="200" y="194" width="8" height="15" fill="{ui["cursor"]}"/>
    </g>

    <!-- ANSI 16 palette grid -->
    <text x="24" y="256" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700" letter-spacing="0.8">ANSI 16 PALETTE (00-07 NORMAL · 08-15 BRIGHT)</text>
    {''.join(ansi_bars)}
    '''
    swatches = [
        ("BG", ui["bg"]), ("TEXT", ui["text"]), ("CURSOR", ui["cursor"]), ("SEL", ui["selection_active"]),
        ("RED", a["red"]), ("GRN", a["green"]), ("YLW", a["yellow"]), ("BLU", a["blue"]),
        ("MAG", a["magenta"]), ("CYN", a["cyan"]),
    ]
    return _frame_shell(variant, f"[{slug}]", app_name, "ANSI 16 AA", body, swatches)


def render_cli_preview(app_name: str, slug: str, variant: dict, kind: str) -> str:
    ui, syn, a = variant["ui"], variant["syntax"], variant["ansi"]
    if kind == "prompt":
        body = f'''
        <rect x="0" y="36" width="660" height="310" fill="{ui["bg"]}"/>
        <!-- Prompt card 1: Segment pills -->
        <rect x="22" y="56" width="616" height="118" rx="8" fill="{ui["surface"]}" stroke="{ui["border"]}" stroke-width="1"/>
        <text x="36" y="78" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700" letter-spacing="0.8">PROMPT SEGMENTS · {escape(app_name.upper())}</text>

        <rect x="36" y="92" width="118" height="24" rx="4" fill="{ui["secondary_fill"]}"/>
        <text x="95" y="107.5" text-anchor="middle" fill="#FFFFFF" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">~/rfs-themes</text>
        <rect x="160" y="92" width="84" height="24" rx="4" fill="{ui["accent_fill"]}"/>
        <text x="202" y="107.5" text-anchor="middle" fill="#FFFFFF" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">git:main</text>
        <rect x="250" y="92" width="76" height="24" rx="4" fill="{ui["raised"]}" stroke="{ui["signal"]}" stroke-width="1"/>
        <text x="288" y="107.5" text-anchor="middle" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">py 3.13</text>
        <rect x="332" y="92" width="76" height="24" rx="4" fill="{ui["raised"]}" stroke="{ui["warning"]}" stroke-width="1"/>
        <text x="370" y="107.5" text-anchor="middle" fill="{ui["warning"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">rs 1.88</text>
        <rect x="540" y="92" width="82" height="24" rx="4" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
        <text x="581" y="107.5" text-anchor="middle" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">142ms · ok</text>

        <text x="36" y="146" font-family="ui-monospace,Consolas,monospace" font-size="11"><tspan fill="{ui["accent"]}" font-weight="700">&gt; </tspan><tspan fill="{ui["text"]}">python tools/verify-themes.py --strict</tspan></text>

        <!-- Prompt card 2: Error state + output -->
        <rect x="22" y="192" width="616" height="134" rx="8" fill="{ui["code_bg"]}" stroke="{ui["border"]}" stroke-width="1"/>
        <g font-family="ui-monospace,Consolas,monospace" font-size="10">
          <text x="36" y="218"><tspan fill="{ui["signal"]}" font-weight="700">[ok]</tspan><tspan fill="{ui["text"]}"> 20 app ports · 60 variants verified</tspan></text>
          <text x="36" y="242"><tspan fill="{ui["secondary"]}" font-weight="700">[i] </tspan><tspan fill="{ui["text_soft"]}"> palette = "{escape(variant["id"])}" ({escape(variant["lx"])})</tspan></text>
          <text x="36" y="266"><tspan fill="{ui["warning"]}" font-weight="700">[!] </tspan><tspan fill="{ui["text_soft"]}"> git dirty indicator: </tspan><tspan fill="{ui["warning"]}">+3 ~1</tspan><tspan fill="{ui["mute"]}"> · duration threshold 2s</tspan></text>
          <text x="36" y="294"><tspan fill="{ui["fault"]}" font-weight="700">[x] </tspan><tspan fill="{ui["fault"]}">exit 1</tspan><tspan fill="{ui["mute"]}"> prompt glyph turns Signal Crimson ({ui["fault"]})</tspan></text>
        </g>
        '''
    elif kind == "diff":
        body = f'''
        <rect x="0" y="36" width="660" height="310" fill="{ui["bg"]}"/>
        <rect x="18" y="52" width="624" height="28" rx="5" fill="{ui["surface"]}" stroke="{ui["border"]}" stroke-width="1"/>
        <text x="30" y="70" fill="{ui["accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="10" font-weight="700">src/theme.rs</text>
        <text x="630" y="70" text-anchor="end" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">@@ -42,6 +42,7 @@ fn palette()</text>

        <rect x="18" y="88" width="624" height="240" rx="6" fill="{ui["code_bg"]}" stroke="{ui["border"]}" stroke-width="1"/>
        <rect x="19" y="138" width="622" height="24" fill="{ui["diff_del_bg"]}"/>
        <rect x="19" y="162" width="622" height="24" fill="{ui["diff_del_bg"]}"/>
        <rect x="19" y="186" width="622" height="24" fill="{ui["diff_add_bg"]}"/>
        <rect x="19" y="210" width="622" height="24" fill="{ui["diff_add_bg"]}"/>
        <rect x="19" y="234" width="622" height="24" fill="{ui["diff_add_bg"]}"/>

        <g font-family="ui-monospace,Consolas,monospace" font-size="10">
          <text x="32" y="108" fill="{ui["subtle"]}"> 42   <tspan fill="{syn["keyword"]}">pub fn </tspan><tspan fill="{syn["function"]}">cyclorama_tokens</tspan><tspan fill="{syn["punctuation"]}">() -&gt; </tspan><tspan fill="{syn["type"]}">Palette </tspan><tspan fill="{syn["punctuation"]}">&#123;</tspan></text>
          <text x="32" y="130" fill="{ui["subtle"]}"> 43       <tspan fill="{syn["type"]}">Palette </tspan><tspan fill="{syn["punctuation"]}">&#123;</tspan></text>
          <text x="32" y="154"><tspan fill="{ui["fault"]}" font-weight="700">-44</tspan><tspan fill="{ui["text"]}">       danger: </tspan><tspan fill="{syn["string"]}">"#E04E39"</tspan><tspan fill="{syn["punctuation"]}">,</tspan></text>
          <text x="32" y="178"><tspan fill="{ui["fault"]}" font-weight="700">-45</tspan><tspan fill="{ui["text"]}">       border: </tspan><tspan fill="{syn["string"]}">"#1E1E24"</tspan><tspan fill="{syn["punctuation"]}">,</tspan></text>
          <text x="32" y="202"><tspan fill="{ui["signal"]}" font-weight="700">+44</tspan><tspan fill="{ui["text"]}">       danger: </tspan><tspan fill="{syn["string"]}">"{ui["fault"]}"</tspan><tspan fill="{syn["punctuation"]}">,  </tspan><tspan fill="{syn["comment"]}">// Signal Crimson</tspan></text>
          <text x="32" y="226"><tspan fill="{ui["signal"]}" font-weight="700">+45</tspan><tspan fill="{ui["text"]}">       border: </tspan><tspan fill="{syn["string"]}">"{ui["border"]}"</tspan><tspan fill="{syn["punctuation"]}">,  </tspan><tspan fill="{syn["comment"]}">// Calibrated hairline</tspan></text>
          <text x="32" y="250"><tspan fill="{ui["signal"]}" font-weight="700">+46</tspan><tspan fill="{ui["text"]}">       accent: </tspan><tspan fill="{syn["string"]}">"{ui["accent"]}"</tspan><tspan fill="{syn["punctuation"]}">,  </tspan><tspan fill="{syn["comment"]}">// {escape(variant["accentRole"])}</tspan></text>
          <text x="32" y="278" fill="{ui["subtle"]}"> 47       <tspan fill="{syn["punctuation"]}">&#125;</tspan></text>
          <text x="32" y="302" fill="{ui["subtle"]}"> 48   <tspan fill="{syn["punctuation"]}">&#125;</tspan></text>
        </g>
        '''
    else:  # fzf / bat
        body = f'''
        <rect x="0" y="36" width="660" height="310" fill="{ui["bg"]}"/>
        <!-- Search bar -->
        <rect x="20" y="52" width="620" height="32" rx="6" fill="{ui["raised"]}" stroke="{ui["accent"]}" stroke-width="1.2"/>
        <text x="34" y="72" font-family="ui-monospace,Consolas,monospace" font-size="11"><tspan fill="{ui["accent"]}" font-weight="700">&gt; </tspan><tspan fill="{ui["text"]}">cyclorama </tspan><tspan fill="{ui["mute"]}">20/60</tspan></text>

        <!-- Left match list -->
        <rect x="20" y="94" width="286" height="236" rx="6" fill="{ui["surface"]}" stroke="{ui["border"]}" stroke-width="1"/>
        <rect x="26" y="102" width="274" height="26" rx="4" fill="{ui["selection_active"]}"/>
        <rect x="26" y="104" width="3" height="22" rx="1" fill="{ui["accent"]}"/>
        <text x="38" y="119" font-family="ui-monospace,Consolas,monospace" font-size="10" font-weight="700"><tspan fill="{ui["accent"]}">&gt; </tspan><tspan fill="{ui["text"]}">apps/vscode/</tspan><tspan fill="{ui["secondary"]}">cyclorama</tspan></text>
        <text x="38" y="148" fill="{ui["text_soft"]}" font-family="ui-monospace,Consolas,monospace" font-size="10">  apps/neovim/<tspan fill="{ui["accent"]}">cyclorama</tspan>.lua</text>
        <text x="38" y="174" fill="{ui["text_soft"]}" font-family="ui-monospace,Consolas,monospace" font-size="10">  apps/ghostty/<tspan fill="{ui["accent"]}">cyclorama</tspan></text>
        <text x="38" y="200" fill="{ui["text_soft"]}" font-family="ui-monospace,Consolas,monospace" font-size="10">  apps/wezterm/<tspan fill="{ui["accent"]}">cyclorama</tspan>.toml</text>
        <text x="38" y="226" fill="{ui["text_soft"]}" font-family="ui-monospace,Consolas,monospace" font-size="10">  apps/obsidian/theme.css</text>
        <text x="38" y="252" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="10">  apps/starship/<tspan fill="{ui["accent"]}">cyclorama</tspan>.toml</text>
        <text x="38" y="278" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="10">  apps/delta/<tspan fill="{ui["accent"]}">cyclorama</tspan>.gitconfig</text>
        <text x="38" y="308" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">20 matches · 0.4ms</text>

        <!-- Right preview pane -->
        <rect x="316" y="94" width="324" height="236" rx="6" fill="{ui["code_bg"]}" stroke="{ui["border"]}" stroke-width="1"/>
        <text x="330" y="116" fill="{ui["secondary"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">PREVIEW · {escape(app_name)}</text>
        <line x1="316" y1="126" x2="640" y2="126" stroke="{ui["border"]}" stroke-width="1"/>
        <g font-family="ui-monospace,Consolas,monospace" font-size="9.5">
          <text x="330" y="148"><tspan fill="{syn["comment"]}"># Cyclorama Dawn v2.1.0</tspan></text>
          <text x="330" y="170"><tspan fill="{syn["keyword"]}">variant </tspan><tspan fill="{syn["operator"]}">= </tspan><tspan fill="{syn["string"]}">"{escape(variant["id"])}"</tspan></text>
          <text x="330" y="192"><tspan fill="{syn["keyword"]}">accent  </tspan><tspan fill="{syn["operator"]}">= </tspan><tspan fill="{syn["function"]}">"{ui["accent"]}"</tspan></text>
          <text x="330" y="214"><tspan fill="{syn["keyword"]}">steel   </tspan><tspan fill="{syn["operator"]}">= </tspan><tspan fill="{syn["type"]}">"{ui["secondary"]}"</tspan></text>
          <text x="330" y="236"><tspan fill="{syn["keyword"]}">signal  </tspan><tspan fill="{syn["operator"]}">= </tspan><tspan fill="{syn["number"]}">"{ui["signal"]}"</tspan></text>
          <text x="330" y="258"><tspan fill="{syn["keyword"]}">fault   </tspan><tspan fill="{syn["operator"]}">= </tspan><tspan fill="{syn["tag"]}">"{ui["fault"]}"</tspan></text>
          <text x="330" y="294"><tspan fill="{ui["signal"]}" font-weight="700">[ok]</tspan><tspan fill="{ui["mute"]}"> WCAG AA calibrated</tspan></text>
        </g>
        '''
    return _frame_shell(variant, f"[{slug}]", app_name, "AA PASS", body, _standard_swatches(variant))


def render_notes_preview(app_name: str, slug: str, variant: dict) -> str:
    ui, syn = variant["ui"], variant["syntax"]
    sel = mix(ui["surface"], ui["accent"], 0.16 if variant["mode"] == "dark" else 0.12)
    body = f'''
    <!-- Left vault sidebar (x=0..168) -->
    <rect x="0" y="36" width="168" height="310" fill="{ui["surface"]}"/>
    <line x1="168" y1="36" x2="168" y2="346" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="14" y="58" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700" letter-spacing="0.8">VAULT · LOCAL-FIRST</text>
    <rect x="10" y="68" width="148" height="26" rx="5" fill="{sel}"/>
    <rect x="10" y="72" width="3" height="18" rx="1" fill="{ui["accent"]}"/>
    <text x="22" y="85" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11" font-weight="700">Cyclorama Dawn.md</text>
    <text x="22" y="114" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Architecture.md</text>
    <text x="22" y="138" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Daily Notes / 2026</text>
    <text x="22" y="162" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Release Checklist</text>

    <!-- Mini Graph box inside sidebar -->
    <rect x="12" y="194" width="144" height="136" rx="6" fill="{ui["code_bg"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="22" y="212" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">LOCAL GRAPH</text>
    <line x1="84" y1="264" x2="46" y2="236" stroke="{ui["border_strong"]}" stroke-width="1.2"/>
    <line x1="84" y1="264" x2="128" y2="240" stroke="{ui["border_strong"]}" stroke-width="1.2"/>
    <line x1="84" y1="264" x2="54" y2="302" stroke="{ui["border_strong"]}" stroke-width="1.2"/>
    <line x1="84" y1="264" x2="124" y2="298" stroke="{ui["border_strong"]}" stroke-width="1.2"/>
    <circle cx="84" cy="264" r="7" fill="{ui["accent"]}"/>
    <circle cx="46" cy="236" r="4.5" fill="{ui["secondary"]}"/>
    <circle cx="128" cy="240" r="4.5" fill="{ui["signal"]}"/>
    <circle cx="54" cy="302" r="4.5" fill="{ui["warning"]}"/>
    <circle cx="124" cy="298" r="4.5" fill="{ui["secondary"]}"/>

    <!-- Markdown Note pane (x=168..660) -->
    <rect x="168" y="36" width="492" height="310" fill="{ui["bg"]}"/>
    <text x="194" y="72" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="20" font-weight="800">Cyclorama Dawn Knowledge Base</text>
    <rect x="194" y="84" width="66" height="19" rx="4" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="227" y="96.5" text-anchor="middle" fill="{ui["secondary"]}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">#brand</text>
    <rect x="268" y="84" width="76" height="19" rx="4" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="306" y="96.5" text-anchor="middle" fill="{ui["accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">#obsidian</text>

    <text x="194" y="128" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11.5">Linked to <tspan fill="{ui["accent"]}" font-weight="700" text-decoration="underline">[[rfs-brand v2.1.0]]</tspan> and <tspan fill="{ui["secondary"]}" font-weight="700" text-decoration="underline">[[LX 263 Lighting Cues]]</tspan>.</text>
    <text x="194" y="148" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11.5">Every heading, callout, code fence, and graph node stays AA crisp.</text>

    <!-- Callout block -->
    <rect x="194" y="166" width="440" height="58" rx="6" fill="{ui["surface"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <rect x="194" y="166" width="3.5" height="58" rx="1.5" fill="{ui["secondary"]}"/>
    <text x="208" y="186" fill="{ui["secondary"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">[!note] Zero External Dependencies</text>
    <text x="208" y="206" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Drop theme.css + manifest.json into .obsidian/themes/Cyclorama Dawn/</text>

    <!-- Inline markdown code block -->
    <rect x="194" y="240" width="440" height="84" rx="6" fill="{ui["code_bg"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <g font-family="ui-monospace,Consolas,monospace" font-size="9.5">
      <text x="208" y="262"><tspan fill="{syn["comment"]}">```css</tspan></text>
      <text x="208" y="282"><tspan fill="{syn["keyword"]}">--background-primary</tspan><tspan fill="{syn["punctuation"]}">: </tspan><tspan fill="{syn["string"]}">{ui["bg"]}</tspan><tspan fill="{syn["punctuation"]}">;</tspan></text>
      <text x="208" y="302"><tspan fill="{syn["keyword"]}">--text-accent</tspan><tspan fill="{syn["punctuation"]}">:        </tspan><tspan fill="{syn["function"]}">{ui["accent"]}</tspan><tspan fill="{syn["punctuation"]}">;</tspan></text>
    </g>
    '''
    return _frame_shell(variant, f"[{slug}]", app_name, "AA PASS", body, _standard_swatches(variant))


def render_browser_preview(app_name: str, slug: str, variant: dict) -> str:
    ui = variant["ui"]
    body = f'''
    <!-- Browser tab strip -->
    <rect x="0" y="36" width="660" height="32" fill="{ui["rail"]}"/>
    <path d="M 14 68 L 14 45 Q 14 40 19 40 L 182 40 Q 187 40 187 45 L 187 68 Z" fill="{ui["surface"]}"/>
    <rect x="14" y="40" width="173" height="2" fill="{ui["accent"]}"/>
    <text x="28" y="57" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="700">rfs-themes · Gallery</text>
    <text x="204" y="57" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10">Real-Fruit-Snacks / GitHub</text>
    <text x="380" y="57" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10">rfs.tools</text>

    <!-- Omnibox toolbar -->
    <rect x="0" y="68" width="660" height="38" fill="{ui["surface"]}"/>
    <line x1="0" y1="106" x2="660" y2="106" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="18" y="91" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="11">&lt;  &gt;  @</text>
    <rect x="86" y="75" width="470" height="24" rx="12" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="102" y="90.5" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">https://</text>
    <text x="152" y="90.5" fill="{ui["text"]}" font-family="ui-monospace,Consolas,monospace" font-size="9.5">real-fruit-snacks.github.io/rfs-themes/</text>
    <rect x="570" y="77" width="72" height="20" rx="4" fill="{ui["accent_fill"]}"/>
    <text x="606" y="90" text-anchor="middle" fill="#FFFFFF" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">RFS MV3</text>

    <!-- Bookmarks bar -->
    <rect x="0" y="106" width="660" height="26" fill="{ui["surface"]}"/>
    <line x1="0" y1="132" x2="660" y2="132" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="18" y="122" fill="{ui["secondary"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5" font-weight="600">Brand Kit</text>
    <text x="86" y="122" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">GitHub</text>
    <text x="140" y="122" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">rfs.tools</text>
    <text x="200" y="122" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">PrivacyNotes</text>

    <!-- New Tab Page canvas -->
    <rect x="0" y="132" width="660" height="214" fill="{ui["bg"]}"/>
    <text x="330" y="190" text-anchor="middle" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="24" font-weight="800" letter-spacing="2">CYCLORAMA DAWN</text>
    <rect x="235" y="200" width="190" height="3" rx="1.5" fill="url(#hbeam)"/>
    <text x="330" y="224" text-anchor="middle" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="10">Chromium MV3 Theme · Brave · Chrome · Edge</text>

    <rect x="134" y="248" width="116" height="58" rx="8" fill="{ui["surface"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="192" y="274" text-anchor="middle" fill="{ui["accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="10" font-weight="700">frame</text>
    <text x="192" y="292" text-anchor="middle" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">{ui["rail"]}</text>

    <rect x="272" y="248" width="116" height="58" rx="8" fill="{ui["surface"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="330" y="274" text-anchor="middle" fill="{ui["secondary"]}" font-family="ui-monospace,Consolas,monospace" font-size="10" font-weight="700">toolbar</text>
    <text x="330" y="292" text-anchor="middle" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">{ui["surface"]}</text>

    <rect x="410" y="248" width="116" height="58" rx="8" fill="{ui["surface"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="468" y="274" text-anchor="middle" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="10" font-weight="700">ntp_bg</text>
    <text x="468" y="292" text-anchor="middle" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">{ui["bg"]}</text>
    '''
    return _frame_shell(variant, f"[{slug}]", app_name, "MV3 THEME", body, _standard_swatches(variant))


def render_chat_preview(app_name: str, slug: str, variant: dict) -> str:
    ui = variant["ui"]
    sel = mix(ui["surface"], ui["accent"], 0.16 if variant["mode"] == "dark" else 0.12)
    body = f'''
    <!-- Server rail (x=0..46) -->
    <rect x="0" y="36" width="46" height="310" fill="{ui["rail"]}"/>
    <line x1="46" y1="36" x2="46" y2="346" stroke="{ui["border"]}" stroke-width="1"/>
    <rect x="0" y="54" width="3" height="24" rx="1.5" fill="{ui["accent"]}"/>
    <rect x="11" y="52" width="24" height="24" rx="6" fill="{ui["accent_fill"]}"/>
    <text x="23" y="67.5" text-anchor="middle" fill="#FFFFFF" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">RFS</text>
    <circle cx="23" cy="98" r="12" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <circle cx="23" cy="130" r="12" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>

    <!-- Channel list (x=46..190) -->
    <rect x="46" y="36" width="144" height="310" fill="{ui["surface"]}"/>
    <line x1="190" y1="36" x2="190" y2="346" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="58" y="56" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11" font-weight="700">Real-Fruit-Snacks</text>
    <line x1="46" y1="66" x2="190" y2="66" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="58" y="84" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">CHANNELS</text>
    <rect x="52" y="92" width="132" height="24" rx="4" fill="{sel}"/>
    <text x="62" y="108" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5" font-weight="700"><tspan fill="{ui["accent"]}"># </tspan>themes-lab</text>
    <text x="62" y="132" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5"># releases</text>
    <text x="62" y="154" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5"># brand-tokens</text>
    <text x="62" y="176" fill="{ui["secondary"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5"># build-status</text>

    <!-- User status footer in channel rail -->
    <rect x="46" y="308" width="144" height="38" fill="{ui["rail"]}"/>
    <line x1="46" y1="308" x2="190" y2="308" stroke="{ui["border"]}" stroke-width="1"/>
    <circle cx="64" cy="327" r="9" fill="{ui["secondary_fill"]}"/>
    <circle cx="71" cy="334" r="3.5" fill="{ui["signal"]}"/>
    <text x="80" y="325" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5" font-weight="700">matt</text>
    <text x="80" y="337" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8">Online · LX 263</text>

    <!-- Chat area (x=190..660) -->
    <rect x="190" y="36" width="470" height="310" fill="{ui["bg"]}"/>
    <rect x="190" y="36" width="470" height="30" fill="{ui["surface"]}"/>
    <line x1="190" y1="66" x2="660" y2="66" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="206" y="55" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11" font-weight="700"><tspan fill="{ui["accent"]}"># </tspan>themes-lab</text>

    <!-- Message 1 -->
    <circle cx="216" cy="96" r="13" fill="{ui["accent_fill"]}"/>
    <text x="238" y="92" font-family="system-ui,-apple-system,sans-serif" font-size="10.5"><tspan fill="{ui["accent"]}" font-weight="700">RFS-Bot</tspan><tspan fill="{ui["mute"]}" font-size="8.5">  Today at 20:55</tspan></text>
    <text x="238" y="109" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Shipped <tspan fill="{ui["secondary"]}" font-weight="600">Cyclorama Dawn v2.1.0</tspan> for Vencord &amp; BetterDiscord.</text>

    <!-- Embed card -->
    <rect x="238" y="122" width="390" height="72" rx="6" fill="{ui["surface"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <rect x="238" y="122" width="3.5" height="72" rx="1.5" fill="{ui["accent"]}"/>
    <text x="252" y="142" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11" font-weight="700">rfs-themes · {escape(variant["name"])}</text>
    <text x="252" y="160" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">bg: {ui["bg"]}  ·  accent: {ui["accent"]}  ·  status: AA PASS</text>
    <rect x="252" y="170" width="76" height="16" rx="3" fill="{ui["raised"]}" stroke="{ui["signal"]}" stroke-width="0.9"/>
    <text x="290" y="181" text-anchor="middle" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">[ok] verified</text>

    <!-- Message 2 -->
    <circle cx="216" cy="226" r="13" fill="{ui["secondary_fill"]}"/>
    <text x="238" y="222" font-family="system-ui,-apple-system,sans-serif" font-size="10.5"><tspan fill="{ui["secondary"]}" font-weight="700">matt</tspan><tspan fill="{ui["mute"]}" font-size="8.5">  Today at 20:56</tspan></text>
    <text x="238" y="239" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Clean contrast on every panel — zero washed-out grays.</text>

    <!-- Chat composer -->
    <rect x="206" y="294" width="434" height="34" rx="7" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
    <text x="222" y="315" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Message #themes-lab</text>
    '''
    return _frame_shell(variant, f"[{slug}]", app_name, "CSS THEME", body, _standard_swatches(variant))


def render_utility_preview(app_name: str, slug: str, variant: dict, kind: str) -> str:
    ui = variant["ui"]
    sel = mix(ui["surface"], ui["accent"], 0.16 if variant["mode"] == "dark" else 0.12)
    if kind == "launcher":
        body = f'''
        <!-- Desktop stage backdrop -->
        <rect x="0" y="36" width="660" height="310" fill="{ui["rail"]}"/>
        <!-- Centered Flow Launcher spotlight window -->
        <rect x="70" y="64" width="520" height="252" rx="10" fill="{ui["bg"]}" stroke="{ui["border_strong"]}" stroke-width="1.2"/>
        <rect x="70" y="64" width="520" height="3" rx="1" fill="url(#hbeam)"/>
        <!-- Query input -->
        <rect x="86" y="80" width="488" height="38" rx="6" fill="{ui["raised"]}" stroke="{ui["accent"]}" stroke-width="1.2"/>
        <text x="104" y="104" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="15" font-weight="600">rfs-themes</text>
        <rect x="190" y="90" width="2" height="18" fill="{ui["accent"]}"/>
        <text x="560" y="103" text-anchor="end" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">Alt+Space</text>

        <!-- Selected result -->
        <rect x="86" y="130" width="488" height="44" rx="6" fill="{sel}"/>
        <rect x="86" y="135" width="3.5" height="34" rx="1.5" fill="{ui["accent"]}"/>
        <rect x="102" y="140" width="24" height="24" rx="5" fill="{ui["accent_fill"]}"/>
        <text x="114" y="155.5" text-anchor="middle" fill="#FFFFFF" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">RFS</text>
        <text x="138" y="149" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11.5" font-weight="700">Cyclorama Dawn Theme Gallery</text>
        <text x="138" y="165" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">https://real-fruit-snacks.github.io/rfs-themes/</text>
        <text x="562" y="156" text-anchor="end" fill="{ui["accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">Enter</text>

        <!-- Result 2 -->
        <rect x="102" y="188" width="24" height="24" rx="5" fill="{ui["secondary_fill"]}"/>
        <text x="138" y="198" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11" font-weight="600">Windows Terminal — settings.json</text>
        <text x="138" y="213" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">apps/windows-terminal/schemes.json</text>

        <!-- Result 3 -->
        <rect x="102" y="236" width="24" height="24" rx="5" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="1"/>
        <text x="138" y="246" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="11" font-weight="600">Screen Mark — Capture Region</text>
        <text x="138" y="261" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">Local app · Cyclorama Dawn v2.1.0</text>

        <!-- Footer hint -->
        <line x1="70" y1="286" x2="590" y2="286" stroke="{ui["border"]}" stroke-width="1"/>
        <text x="86" y="304" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5">WPF XAML · {escape(variant["name"])}</text>
        <text x="574" y="304" text-anchor="end" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">[ok] AA PASS</text>
        '''
    else:  # qbittorrent
        body = f'''
        <!-- Sidebar filters (x=0..150) -->
        <rect x="0" y="36" width="150" height="286" fill="{ui["surface"]}"/>
        <line x1="150" y1="36" x2="150" y2="322" stroke="{ui["border"]}" stroke-width="1"/>
        <text x="14" y="56" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">STATUS</text>
        <rect x="10" y="64" width="130" height="24" rx="4" fill="{sel}"/>
        <text x="20" y="80" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5" font-weight="700">All (4)</text>
        <text x="20" y="106" fill="{ui["signal"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Seeding (2)</text>
        <text x="20" y="128" fill="{ui["secondary"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Downloading (1)</text>
        <text x="20" y="150" fill="{ui["warning"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">Paused (1)</text>
        <text x="14" y="184" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">PORT SYNC</text>
        <rect x="12" y="194" width="126" height="22" rx="4" fill="{ui["raised"]}" stroke="{ui["signal"]}" stroke-width="1"/>
        <text x="75" y="208.5" text-anchor="middle" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">Port 51037 OK</text>

        <!-- Transfer table (x=150..660) -->
        <rect x="150" y="36" width="510" height="286" fill="{ui["bg"]}"/>
        <rect x="150" y="36" width="510" height="26" fill="{ui["rail"]}"/>
        <line x1="150" y1="62" x2="660" y2="62" stroke="{ui["border"]}" stroke-width="1"/>
        <text x="164" y="53" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">NAME</text>
        <text x="410" y="53" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">PROGRESS</text>
        <text x="560" y="53" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">STATUS</text>

        <!-- Row 1 selected -->
        <rect x="150" y="62" width="510" height="34" fill="{sel}"/>
        <text x="164" y="83" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5" font-weight="600">ubuntu-24.04.2-desktop-amd64.iso</text>
        <rect x="410" y="74" width="126" height="10" rx="3" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.8"/>
        <rect x="410" y="74" width="126" height="10" rx="3" fill="{ui["signal"]}"/>
        <text x="560" y="83" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">Seeding</text>

        <!-- Row 2 -->
        <rect x="150" y="96" width="510" height="34" fill="{ui["bg"]}"/>
        <text x="164" y="117" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">debian-12.9.0-amd64-netinst.iso</text>
        <rect x="410" y="108" width="126" height="10" rx="3" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.8"/>
        <rect x="410" y="108" width="84" height="10" rx="3" fill="{ui["accent"]}"/>
        <text x="560" y="117" fill="{ui["secondary"]}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">66.7%</text>

        <!-- Row 3 -->
        <rect x="150" y="130" width="510" height="34" fill="{ui["surface"]}"/>
        <text x="164" y="151" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">archlinux-2026.11.01-x86_64.iso</text>
        <rect x="410" y="142" width="126" height="10" rx="3" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.8"/>
        <rect x="410" y="142" width="126" height="10" rx="3" fill="{ui["signal"]}"/>
        <text x="560" y="151" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">Seeding</text>

        <!-- Row 4 -->
        <rect x="150" y="164" width="510" height="34" fill="{ui["bg"]}"/>
        <text x="164" y="185" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5">fedora-workstation-live-43.iso</text>
        <rect x="410" y="176" width="126" height="10" rx="3" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.8"/>
        <rect x="410" y="176" width="42" height="10" rx="3" fill="{ui["warning"]}"/>
        <text x="560" y="185" fill="{ui["warning"]}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">Paused</text>

        <!-- Bottom transfer status bar -->
        <rect x="0" y="322" width="660" height="24" fill="{ui["rail"]}"/>
        <line x1="0" y1="322" x2="660" y2="322" stroke="{ui["border"]}" stroke-width="1"/>
        <text x="14" y="337" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">DHT: 312 nodes</text>
        <text x="646" y="337" text-anchor="end" fill="{ui["text_soft"]}" font-family="ui-monospace,Consolas,monospace" font-size="9">DL 18.4 MiB/s  ·  UL 6.2 MiB/s</text>
        '''
    return _frame_shell(variant, f"[{slug}]", app_name, "AA PASS", body, _standard_swatches(variant))


def render_windows_preview(
    app_name: str,
    slug: str,
    variant: dict,
    accent_palette: list[str] | None = None,
    colorization_hex: str | None = None,
) -> str:
    ui = variant["ui"]
    vid = variant["id"]
    is_dark = variant["mode"] == "dark"
    mode_text = "Dark" if is_dark else "Light"
    sel = mix(ui["surface"], ui["accent"], 0.16 if is_dark else 0.12)

    if accent_palette is None:
        accent_palette = [
            ui["accent_hover"], ui["accent"], ui["accent_vivid"], ui["accent_fill"],
            ui["accent_fill_hover"], ui["secondary"], ui["secondary_vivid"], ui["secondary_fill"],
        ]
    active_hex = (colorization_hex or ui["accent_vivid"]).upper()

    if vid == "cyclorama-dawn":
        floor_stops = (
            f'<stop offset="0%" stop-color="{ui["secondary_vivid"]}"/>'
            f'<stop offset="24%" stop-color="{ui["steel_wash"]}"/>'
            f'<stop offset="50%" stop-color="{ui["bg"]}"/>'
            f'<stop offset="76%" stop-color="{ui["beacon_wash"]}"/>'
            f'<stop offset="100%" stop-color="{ui["accent_vivid"]}"/>'
        )
        floor_opacity = "0.52"
    elif vid == "cyclorama-steel":
        floor_stops = (
            f'<stop offset="0%" stop-color="{ui["steel_wash"]}"/>'
            f'<stop offset="50%" stop-color="{ui["accent_vivid"]}"/>'
            f'<stop offset="100%" stop-color="{ui["accent_fill"]}"/>'
        )
        floor_opacity = "0.52"
    else:
        floor_stops = (
            f'<stop offset="0%" stop-color="{ui["steel_wash"]}"/>'
            f'<stop offset="50%" stop-color="{ui["bg"]}"/>'
            f'<stop offset="100%" stop-color="{ui["beacon_wash"]}"/>'
        )
        floor_opacity = "0.92"

    slot_labels = ("L3", "L2", "L1", "ACC", "D1", "D2", "D3", "CMP")
    pal_cells = []
    for idx, hx in enumerate(accent_palette[:8]):
        px = 216 + idx * 42
        pal_cells.append(
            f'<rect x="{px}" y="226" width="36" height="18" rx="3" fill="{hx}" stroke="{ui["border"]}" stroke-width="0.8"/>'
            f'<text x="{px + 18}" y="256" text-anchor="middle" fill="{ui["mute"]}" '
            f'font-family="ui-monospace,Consolas,monospace" font-size="7.5" font-weight="700">{slot_labels[idx]}</text>'
        )

    toggle_x = 516 if is_dark else 532
    taskbar_bg = ui["rail"]
    taskbar_icon_bg = ui["surface"] if is_dark else ui["raised"]

    body = f'''
    <defs>
      <linearGradient id="win-floor-h" x1="0%" y1="0%" x2="100%" y2="0%">
        {floor_stops}
      </linearGradient>
      <linearGradient id="win-floor-v" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0"/>
        <stop offset="45%" stop-color="#FFFFFF" stop-opacity="0.18"/>
        <stop offset="100%" stop-color="#FFFFFF" stop-opacity="1"/>
      </linearGradient>
      <mask id="win-floor-mask">
        <rect x="0" y="178" width="660" height="134" fill="url(#win-floor-v)"/>
      </mask>
      <clipPath id="win-settings-clip">
        <rect x="84" y="52" width="492" height="244" rx="8"/>
      </clipPath>
    </defs>

    <!-- Desktop Cyclorama wallpaper stage (y=36..312) -->
    <rect x="0" y="36" width="660" height="276" fill="{ui["bg"]}"/>
    <rect x="0" y="178" width="660" height="134" fill="url(#win-floor-h)" fill-opacity="{floor_opacity}" mask="url(#win-floor-mask)"/>
    <rect x="0" y="310" width="660" height="2" fill="url(#hbeam)" fill-opacity="0.45"/>

    <!-- Windows 11 Settings: Personalization > Colors window (clipped to rx=8) -->
    <g clip-path="url(#win-settings-clip)">
      <rect x="84" y="52" width="492" height="244" fill="{ui["surface"]}"/>
      <!-- Settings title bar -->
      <rect x="84" y="52" width="492" height="26" fill="{ui["rail"]}"/>
      <line x1="84" y1="78" x2="576" y2="78" stroke="{ui["border"]}" stroke-width="1"/>
      <text x="98" y="69" fill="{ui["text_soft"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5" font-weight="600">Settings  &gt;  Personalization  &gt;  Colors</text>
      <!-- Win11 window controls (minimize, maximize, close) -->
      <line x1="518" y1="65" x2="526" y2="65" stroke="{ui["mute"]}" stroke-width="1.2"/>
      <rect x="537" y="61" width="7" height="7" fill="none" stroke="{ui["mute"]}" stroke-width="1.1"/>
      <path d="M 556 61 L 563 68 M 563 61 L 556 68" stroke="{ui["mute"]}" stroke-width="1.2"/>

      <!-- Settings left navigation rail -->
      <rect x="84" y="78" width="117" height="218" fill="{ui["rail"]}"/>
      <line x1="201" y1="78" x2="201" y2="296" stroke="{ui["border"]}" stroke-width="1"/>
      <text x="98" y="100" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">Background</text>
      <rect x="92" y="109" width="102" height="24" rx="4" fill="{sel}"/>
      <rect x="92" y="114" width="3" height="14" rx="1.5" fill="{ui["accent"]}"/>
      <text x="103" y="124.5" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5" font-weight="700">Colors</text>
      <text x="98" y="149" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">Themes</text>
      <text x="98" y="171" fill="{ui["mute"]}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">Taskbar</text>
      <rect x="94" y="256" width="96" height="24" rx="4" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.9"/>
      <text x="142" y="271.5" text-anchor="middle" fill="{ui["signal"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">backup.reg OK</text>

      <!-- Settings right pane: Mode & Active Accent -->
      <rect x="216" y="90" width="346" height="44" rx="6" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.9"/>
      <text x="228" y="108" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="700">Choose your mode</text>
      <text x="228" y="123" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5">{escape(variant["name"])} · {mode_text} · Transparency ON</text>
      <rect x="512" y="103" width="36" height="18" rx="9" fill="{ui["accent_fill"]}"/>
      <circle cx="{toggle_x + 5}" cy="112" r="6" fill="#FFFFFF"/>

      <!-- Active Accent Color pill card -->
      <rect x="216" y="142" width="346" height="54" rx="6" fill="{ui["raised"]}" stroke="{ui["border"]}" stroke-width="0.9"/>
      <rect x="228" y="153" width="32" height="32" rx="6" fill="{active_hex}" stroke="{ui["border_strong"]}" stroke-width="0.9"/>
      <text x="270" y="166" fill="{ui["text"]}" font-family="system-ui,-apple-system,sans-serif" font-size="10" font-weight="700">Accent color  ·  {escape(variant["accentRole"])}</text>
      <text x="270" y="182" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5">Colorization {active_hex} · Oklab 1080p + 4K</text>
      <rect x="488" y="158" width="62" height="22" rx="4" fill="{ui["accent_fill"]}"/>
      <text x="519" y="172.5" text-anchor="middle" fill="#FFFFFF" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">ACTIVE</text>

      <!-- 8-slot Windows 11 AccentPalette strip -->
      <text x="216" y="216" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700" letter-spacing="0.6">EXPLORER ACCENTPALETTE (8 SLOTS · 32 BYTES)</text>
      {''.join(pal_cells)}
      <text x="216" y="278" fill="{ui["text_soft"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5">Theme: {escape(variant["name"])}.theme  ·  Taskbar: Matte {mode_text}</text>
    </g>
    <rect x="84" y="52" width="492" height="244" rx="8" fill="none" stroke="{ui["border_strong"]}" stroke-width="1"/>

    <!-- Matte Windows 11 Centered Taskbar (y=312..346) -->
    <rect x="0" y="312" width="660" height="34" fill="{taskbar_bg}"/>
    <line x1="0" y1="312" x2="660" y2="312" stroke="{ui["border"]}" stroke-width="1"/>

    <!-- Centered Taskbar App Icons -->
    <!-- Start 4-pane logo -->
    <rect x="242" y="318" width="22" height="22" rx="4" fill="{taskbar_icon_bg}" stroke="{ui["border"]}" stroke-width="0.8"/>
    <rect x="248" y="324" width="4.5" height="4.5" rx="0.6" fill="{ui["secondary"]}"/>
    <rect x="253.5" y="324" width="4.5" height="4.5" rx="0.6" fill="{ui["secondary"]}"/>
    <rect x="248" y="329.5" width="4.5" height="4.5" rx="0.6" fill="{ui["secondary"]}"/>
    <rect x="253.5" y="329.5" width="4.5" height="4.5" rx="0.6" fill="{ui["secondary"]}"/>

    <!-- Terminal icon (running dot) -->
    <rect x="272" y="318" width="22" height="22" rx="4" fill="{taskbar_icon_bg}" stroke="{ui["border"]}" stroke-width="0.8"/>
    <text x="283" y="332" text-anchor="middle" fill="{ui["text_soft"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">&gt;_</text>
    <rect x="280" y="341.5" width="6" height="2" rx="1" fill="{ui["secondary"]}"/>

    <!-- Code editor icon (running dot) -->
    <rect x="302" y="318" width="22" height="22" rx="4" fill="{taskbar_icon_bg}" stroke="{ui["border"]}" stroke-width="0.8"/>
    <text x="313" y="332" text-anchor="middle" fill="{ui["secondary"]}" font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="700">&#123;&#125;</text>
    <rect x="310" y="341.5" width="6" height="2" rx="1" fill="{ui["secondary"]}"/>

    <!-- Settings icon (ACTIVE with wide Accent underline pill!) -->
    <rect x="332" y="317" width="24" height="24" rx="4" fill="{ui["raised"]}" stroke="{ui["border_strong"]}" stroke-width="0.9"/>
    <circle cx="344" cy="329" r="5" fill="none" stroke="{ui["accent"]}" stroke-width="1.8"/>
    <circle cx="344" cy="329" r="1.8" fill="{ui["accent"]}"/>
    <rect x="337" y="341.5" width="14" height="2.4" rx="1.2" fill="{ui["accent"]}"/>

    <!-- Browser icon -->
    <rect x="364" y="318" width="22" height="22" rx="4" fill="{taskbar_icon_bg}" stroke="{ui["border"]}" stroke-width="0.8"/>
    <circle cx="375" cy="329" r="5" fill="none" stroke="{ui["mute"]}" stroke-width="1.3"/>
    <rect x="372" y="341.5" width="6" height="2" rx="1" fill="{ui["mute"]}"/>

    <!-- Explorer icon -->
    <rect x="394" y="318" width="22" height="22" rx="4" fill="{taskbar_icon_bg}" stroke="{ui["border"]}" stroke-width="0.8"/>
    <rect x="399" y="325" width="12" height="8" rx="1.5" fill="none" stroke="{ui["warning"]}" stroke-width="1.3"/>

    <!-- System tray right -->
    <text x="646" y="328" text-anchor="end" fill="{ui["text_soft"]}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700">21:00</text>
    <text x="646" y="339" text-anchor="end" fill="{ui["mute"]}" font-family="ui-monospace,Consolas,monospace" font-size="7.5">{escape(variant["lx"])} · WIN11</text>
    '''
    return _frame_shell(variant, f"[{slug}]", app_name, "WIN11 26H2", body, _standard_swatches(variant))
