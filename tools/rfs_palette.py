#!/usr/bin/env python3
"""Canonical Cyclorama Dawn v2.1.0 palette engine for all rfs-themes ports.

Single source of truth derived from brand/rfs.tokens.json so every app port
(editors, terminals, CLI/TUI, notes, browsers, desktop utilities) shares
identical, WCAG AA verified colors across all three standard variants:

  - cyclorama-dawn  (LX 263 Dark  · Beacon Orange accent, Steel Blue secondary)
  - cyclorama-steel (LX 263 Dark  · Steel Blue accent, Beacon Orange secondary)
  - cyclorama-day   (LX 512 Light · Alabaster Day light mode)

Zero external dependencies (Python 3.11+ standard library only).
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOKENS_PATH = os.path.join(ROOT, "brand", "rfs.tokens.json")

AUTHOR = "Real-Fruit-Snacks"
BRAND_NAME = "Cyclorama Dawn"
REPO_URL = "https://github.com/Real-Fruit-Snacks/rfs-themes"
GALLERY_URL = "https://real-fruit-snacks.github.io/rfs-themes/"


def load_brand_tokens() -> dict:
    with open(TOKENS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, int(v + 0.5))):02X}" for v in rgb)


def mix(a: str, b: str, t: float) -> str:
    x, y = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex((
        x[0] * (1.0 - t) + y[0] * t,
        x[1] * (1.0 - t) + y[1] * t,
        x[2] * (1.0 - t) + y[2] * t,
    ))


def with_alpha(h: str, alpha_hex: str) -> str:
    """Return #RRGGBBAA (alpha_hex is two hex chars like '33' or 'CC')."""
    return f"#{h.lstrip('#').upper()}{alpha_hex.upper()}"


def argb_hex(h: str, alpha_hex: str = "FF") -> str:
    """Return #AARRGGBB (for WPF/XAML and JetBrains/Qt)."""
    return f"#{alpha_hex.upper()}{h.lstrip('#').upper()}"


def _channel(v: int) -> float:
    s = v / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def luminance(h: str) -> float:
    r, g, b = hex_to_rgb(h)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def min_contrast(fg: str, bgs: list[str]) -> float:
    return min(contrast(fg, bg) for bg in bgs)


def _build_variants() -> dict[str, dict]:
    tok = load_brand_tokens()
    d = tok["color"]["dark"]
    l = tok["color"]["light"]
    ver = tok["meta"]["version"]

    # Extended syntax & ANSI-16 gel accents calibrated to Cyclorama Dawn stagecraft.
    # Every dark foreground >= 4.5:1 against bg/surface/raised; every light foreground
    # >= 4.5:1 against bg/surface/raised.
    dawn_ui = {
        "bg": d["bg"].upper(),                  # #050507
        "rail": d["rail"].upper(),              # #070709
        "code_bg": d["code-bg"].upper(),        # #08080B
        "surface": d["surface"].upper(),        # #0C0C10
        "list": "#0F1016",
        "raised": d["raised"].upper(),          # #14141A
        "overlay": "#1C1D26",
        "border_subtle": d["line"].upper(),     # #27272E
        "border": "#2A2C35",
        "border_strong": d["line-strong"].upper(),  # #62646D
        "text": d["text"].upper(),              # #F4F5F8
        "text_soft": "#D6D8E0",
        "mute": d["mute"].upper(),              # #B3B5C0
        "subtle": "#8C8F9D",                    # >= 5.5:1 on #14141A
        "accent": d["beacon-ink"].upper(),      # #FF9254
        "accent_vivid": d["beacon"].upper(),    # #F06E2B
        "accent_hover": "#FFB07A",
        "accent_fill": "#BD4811",               # white-on-fill >= 5.1:1
        "accent_fill_hover": "#9E3B0C",
        "on_accent": "#FFFFFF",
        "on_vivid": d["on-primary"].upper(),    # #050507
        "secondary": d["steel-ink"].upper(),    # #74B8E8
        "secondary_vivid": d["steel"].upper(),  # #1F547A
        "secondary_fill": d["steel-fill"].upper(),  # #18496B
        "secondary_hover": "#99CDF2",
        "signal": d["signal"].upper(),          # #3DDC97
        "warning": d["accent"].upper(),         # #FFC247
        "fault": d["fault"].upper(),            # #FF5C6C
        "fault_fill": d["fault-fill"].upper(),  # #C92438
        "fault_hover": d["fault-fill-hover"].upper(),  # #E02E44
        "cyan": "#56D4E0",
        "magenta": "#C996F5",
        "steel_wash": "#133954",
        "beacon_wash": d["beacon-wash"].upper(),  # #CC5016
        "selection_bg": "#2B2220",
        "selection_active": "#3D2B24",
        "find_match": "#4A3619",
        "diff_add_bg": "#0D291E",
        "diff_del_bg": "#301218",
        "diff_chg_bg": "#112436",
        "cursor": d["beacon"].upper(),          # #F06E2B
        "cursor_text": d["bg"].upper(),         # #050507
        "beam_start": d["steel-ink"].upper(),   # #74B8E8
        "beam_end": d["beacon"].upper(),        # #F06E2B
    }

    steel_ui = {
        "bg": d["bg"].upper(),                  # #050507
        "rail": "#07080B",
        "code_bg": "#080A0E",
        "surface": d["surface"].upper(),        # #0C0C10
        "list": "#0E1117",
        "raised": "#131820",
        "overlay": "#1A222E",
        "border_subtle": "#222B36",
        "border": "#27313D",
        "border_strong": "#637284",
        "text": d["text"].upper(),              # #F4F5F8
        "text_soft": "#D6DCE4",
        "mute": d["mute"].upper(),              # #B3B5C0
        "subtle": "#8C96A6",                    # >= 5.5:1 on #131820
        "accent": d["steel-ink"].upper(),       # #74B8E8
        "accent_vivid": d["steel"].upper(),     # #1F547A
        "accent_hover": "#99CDF2",
        "accent_fill": d["steel-fill"].upper(), # #18496B
        "accent_fill_hover": "#123955",
        "on_accent": "#FFFFFF",
        "on_vivid": "#FFFFFF",
        "secondary": d["beacon-ink"].upper(),   # #FF9254
        "secondary_vivid": d["beacon"].upper(), # #F06E2B
        "secondary_fill": "#BD4811",
        "secondary_hover": "#FFB07A",
        "signal": d["signal"].upper(),          # #3DDC97
        "warning": d["accent"].upper(),         # #FFC247
        "fault": d["fault"].upper(),            # #FF5C6C
        "fault_fill": d["fault-fill"].upper(),  # #C92438
        "fault_hover": d["fault-fill-hover"].upper(),  # #E02E44
        "cyan": "#56D4E0",
        "magenta": "#C996F5",
        "steel_wash": "#133954",
        "beacon_wash": d["beacon-wash"].upper(),
        "selection_bg": "#15293D",
        "selection_active": "#1D3B57",
        "find_match": "#3B3117",
        "diff_add_bg": "#0D291E",
        "diff_del_bg": "#301218",
        "diff_chg_bg": "#13293D",
        "cursor": d["steel-ink"].upper(),       # #74B8E8
        "cursor_text": d["bg"].upper(),         # #050507
        "beam_start": d["steel-ink"].upper(),   # #74B8E8
        "beam_end": d["beacon"].upper(),        # #F06E2B
    }

    day_ui = {
        "bg": l["bg"].upper(),                  # #F5F7F9
        "rail": l["rail"].upper(),              # #EAEEF2
        "code_bg": l["code-bg"].upper(),        # #EEF2F5
        "surface": l["surface"].upper(),        # #FFFFFF
        "list": "#F0F3F7",
        "raised": l["raised"].upper(),          # #E3E8EE
        "overlay": "#D7DFE8",
        "border_subtle": l["line"].upper(),     # #CFD5DC
        "border": "#C8D0DA",
        "border_strong": l["line-strong"].upper(),  # #6E7682
        "text": l["text"].upper(),              # #0D1016
        "text_soft": "#252A34",
        "mute": l["mute"].upper(),              # #474D59
        "subtle": "#58606E",                    # >= 5.0:1 on #E3E8EE
        "accent": l["beacon-ink"].upper(),      # #AD3D0A
        "accent_vivid": l["beacon-wash"].upper(),  # #CC5016
        "accent_hover": "#8B2F06",
        "accent_fill": l["steel-fill"].upper(), # #18496B
        "accent_fill_hover": "#113752",
        "on_accent": "#FFFFFF",
        "on_vivid": "#FFFFFF",
        "secondary": l["steel-ink"].upper(),    # #164669
        "secondary_vivid": l["steel"].upper(),  # #1F547A
        "secondary_fill": l["beacon-ink"].upper(),  # #AD3D0A
        "secondary_hover": "#0F334E",
        "signal": l["signal"].upper(),          # #127247
        "warning": l["accent"].upper(),         # #885800
        "fault": l["fault"].upper(),            # #B91C2E
        "fault_fill": l["fault-fill"].upper(),  # #B91C2E
        "fault_hover": l["fault-fill-hover"].upper(),  # #991525
        "cyan": "#0E6674",                      # >= 5.1:1 on #E3E8EE
        "magenta": "#6B38B8",                   # >= 5.8:1 on #E3E8EE
        "steel_wash": "#DCE7F0",
        "beacon_wash": "#F8E3D6",
        "selection_bg": "#DCE7F0",
        "selection_active": "#C6DAEB",
        "find_match": "#F5DFB0",
        "diff_add_bg": "#D9F0E4",
        "diff_del_bg": "#F8DADF",
        "diff_chg_bg": "#DCE8F3",
        "cursor": l["beacon-ink"].upper(),      # #AD3D0A
        "cursor_text": "#FFFFFF",
        "beam_start": l["steel-fill"].upper(),  # #18496B
        "beam_end": l["beacon-ink"].upper(),    # #AD3D0A
    }

    def dark_syntax(ui: dict) -> dict:
        return {
            "keyword": "#74B8E8",       # steel-ink (rfs.tokens.json syntax.keyword)
            "function": "#FF9254",      # beacon-ink (rfs.tokens.json syntax.function)
            "string": "#FFC247",        # accent/amber (rfs.tokens.json syntax.string)
            "number": "#3DDC97",        # signal/green (rfs.tokens.json syntax.number)
            "comment": ui["subtle"],    # muted comment >= 5.5:1
            "type": "#56D4E0",          # stage cyan
            "constant": "#C996F5",      # iris/lavender gel
            "operator": "#D6D8E0",      # soft ink
            "property": "#99CDF2",      # light steel
            "parameter": "#FFB07A",     # warm beacon highlight
            "tag": "#FF5C6C",           # crimson / HTML tag
            "punctuation": "#B3B5C0",   # mute ink
            "diff_add": "#3DDC97",
            "diff_del": "#FF5C6C",
            "diff_change": "#74B8E8",
        }

    def light_syntax(ui: dict) -> dict:
        return {
            "keyword": "#164669",       # steel-ink (rfs.tokens.json syntax.keyword)
            "function": "#AD3D0A",      # beacon-ink (rfs.tokens.json syntax.function)
            "string": "#885800",        # accent/amber (rfs.tokens.json syntax.string)
            "number": "#127247",        # signal/green (rfs.tokens.json syntax.number)
            "comment": ui["subtle"],    # >= 5.0:1 on #E3E8EE
            "type": "#0E6674",          # deep stage teal
            "constant": "#6B38B8",      # deep iris
            "operator": "#252A34",      # soft ink
            "property": "#1F547A",      # steel
            "parameter": "#943207",     # deep beacon
            "tag": "#B91C2E",           # crimson / HTML tag
            "punctuation": "#474D59",   # mute ink
            "diff_add": "#127247",
            "diff_del": "#B91C2E",
            "diff_change": "#164669",
        }

    def dark_ansi(ui: dict) -> dict:
        # ANSI 0..15 mapped from rfs.tokens.json cli + stagecraft gels
        return {
            "black": ui["surface"],         # 0  #0C0C10
            "red": "#FF5C6C",               # 1  fault
            "green": "#3DDC97",             # 2  signal
            "yellow": "#FFC247",            # 3  warning/amber
            "blue": "#74B8E8",              # 4  steel-ink
            "magenta": "#C996F5",           # 5  iris
            "cyan": "#56D4E0",              # 6  stage cyan
            "white": "#D6D8E0",             # 7  text-soft
            "brightBlack": ui["subtle"],    # 8  comment/bright-black (>= 5.5:1)
            "brightRed": "#FF9254",         # 9  beacon-ink (cli.prompt bright-red!)
            "brightGreen": "#6CE8B2",       # 10 luminous signal
            "brightYellow": "#FFD475",      # 11 warm gold
            "brightBlue": "#99CDF2",        # 12 pale glacial steel
            "brightMagenta": "#DCB8FA",     # 13 pale iris
            "brightCyan": "#85E3EC",        # 14 bright cyan
            "brightWhite": "#F4F5F8",       # 15 text
        }

    def light_ansi(ui: dict) -> dict:
        return {
            "black": "#0D1016",             # 0  text
            "red": "#B91C2E",               # 1  fault
            "green": "#127247",             # 2  signal
            "yellow": "#885800",            # 3  warning/amber
            "blue": "#164669",              # 4  steel-ink
            "magenta": "#6B38B8",           # 5  deep iris
            "cyan": "#0E6674",              # 6  deep cyan
            "white": "#E3E8EE",             # 7  raised surface
            "brightBlack": "#58606E",       # 8  subtle (>= 5.0:1)
            "brightRed": "#AD3D0A",         # 9  beacon-ink (cli.prompt!)
            "brightGreen": "#0D5A37",       # 10 deep signal
            "brightYellow": "#704700",      # 11 deep amber
            "brightBlue": "#1F547A",        # 12 steel
            "brightMagenta": "#572A9E",     # 13 royal iris
            "brightCyan": "#0A525E",        # 14 dark teal
            "brightWhite": "#FFFFFF",       # 15 white surface
        }

    return {
        "cyclorama-dawn": {
            "id": "cyclorama-dawn",
            "name": "Cyclorama Dawn",
            "short": "Dawn",
            "lx": "LX 263",
            "mode": "dark",
            "accentRole": "Beacon Orange",
            "version": ver,
            "summary": "Matte #050507 dark stage with Beacon Orange focus and Steel Blue secondary accents.",
            "ui": dawn_ui,
            "syntax": dark_syntax(dawn_ui),
            "ansi": dark_ansi(dawn_ui),
        },
        "cyclorama-steel": {
            "id": "cyclorama-steel",
            "name": "Cyclorama Steel",
            "short": "Steel",
            "lx": "LX 263",
            "mode": "dark",
            "accentRole": "Steel Blue",
            "version": ver,
            "summary": "Cool steel-charcoal dark stage with Steel Blue controls and Beacon Orange highlights.",
            "ui": steel_ui,
            "syntax": dark_syntax(steel_ui),
            "ansi": dark_ansi(steel_ui),
        },
        "cyclorama-day": {
            "id": "cyclorama-day",
            "name": "Cyclorama Day",
            "short": "Day",
            "lx": "LX 512",
            "mode": "light",
            "accentRole": "Alabaster Day",
            "version": ver,
            "summary": "Crisp #F5F7F9 Alabaster Day light workspace with white panels, burnt Beacon links, and Steel buttons.",
            "ui": day_ui,
            "syntax": light_syntax(day_ui),
            "ansi": light_ansi(day_ui),
        },
    }


VARIANTS: dict[str, dict] = _build_variants()
VARIANT_ORDER: tuple[str, ...] = ("cyclorama-dawn", "cyclorama-steel", "cyclorama-day")


def ansi_list(variant: dict) -> list[str]:
    """Return 16 ANSI colors in standard order 0..15."""
    a = variant["ansi"]
    return [
        a["black"], a["red"], a["green"], a["yellow"],
        a["blue"], a["magenta"], a["cyan"], a["white"],
        a["brightBlack"], a["brightRed"], a["brightGreen"], a["brightYellow"],
        a["brightBlue"], a["brightMagenta"], a["brightCyan"], a["brightWhite"],
    ]


def verify_palette_contrast() -> list[tuple[str, str, float, float, bool]]:
    """Run WCAG AA checks on every variant's UI, syntax, and ANSI tokens."""
    results = []
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        ui = v["ui"]
        syn = v["syntax"]
        ansi = v["ansi"]
        grounds = [ui["bg"], ui["surface"], ui["raised"], ui["code_bg"]]

        for key in ("text", "text_soft", "mute", "subtle", "accent", "accent_hover",
                    "secondary", "signal", "warning", "fault", "cyan", "magenta"):
            ratio = min_contrast(ui[key], grounds)
            results.append((vid, f"ui.{key}", ratio, 4.5, ratio >= 4.5))

        for btn_bg in ("accent_fill", "accent_fill_hover", "secondary_fill", "fault_fill"):
            ratio = contrast("#FFFFFF", ui[btn_bg])
            results.append((vid, f"white-on-{btn_bg}", ratio, 4.5, ratio >= 4.5))

        syn_grounds = [ui["bg"], ui["code_bg"], ui["surface"]]
        for key, hx in syn.items():
            ratio = min_contrast(hx, syn_grounds)
            results.append((vid, f"syntax.{key}", ratio, 4.5, ratio >= 4.5))

        # Terminal ANSI foreground readability on terminal bg (skip color 0/7 bg-matching swatches)
        term_bg = [ui["bg"], ui["code_bg"]]
        skip_ansi = ("black",) if v["mode"] == "dark" else ("white", "brightWhite")
        for key, hx in ansi.items():
            if key in skip_ansi:
                continue
            ratio = min_contrast(hx, term_bg)
            results.append((vid, f"ansi.{key}", ratio, 4.5, ratio >= 4.5))
    return results


if __name__ == "__main__":
    checks = verify_palette_contrast()
    fails = [c for c in checks if not c[4]]
    for vid in VARIANT_ORDER:
        v_checks = [c for c in checks if c[0] == vid]
        worst = min(v_checks, key=lambda c: c[2])
        v_fails = [c for c in v_checks if not c[4]]
        status = "[ok]" if not v_fails else "[x] "
        print(f"{status} {vid:<16} {len(v_checks) - len(v_fails)}/{len(v_checks)} AA checks pass (min {worst[1]} = {worst[2]:.2f}:1)")
    if fails:
        for vid, role, ratio, need, _ in fails:
            print(f"[x]  FAIL {vid} {role}: {ratio:.2f}:1 < {need:.1f}:1")
        sys.exit(1)
    print(f"[ok] all {len(checks)} Cyclorama Dawn palette contrast checks passed")
