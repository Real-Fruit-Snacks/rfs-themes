#!/usr/bin/env python3
"""Generate and validate PrivacyNotes pn1: theme codes, SVG workspace previews and logo icons.

Implements PrivacyNotes' exact themeCode.ts resolution and 17-check WCAG contrast
validator using only the Python standard library (zero external dependencies).
Also copies the RFS brand mark into apps/privacynotes/icons/ for the theme
editor's "Upload or drop a custom icon" slot.

Usage:
    python tools/build-privacynotes.py
"""
from html import escape
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
APP_DIR = os.path.join(ROOT, "apps", "privacynotes")
THEMES_JSON = os.path.join(APP_DIR, "themes.json")
CODES_TXT = os.path.join(APP_DIR, "codes.txt")
PREVIEW_DIR = os.path.join(APP_DIR, "previews")
DOCS_PREVIEW_DIR = os.path.join(ROOT, "docs", "assets", "previews", "privacynotes")
ICON_DIR = os.path.join(APP_DIR, "icons")
# Byte-exact copies of rfs-brand brand/mark/rfs-mark-small-{dark,light}.svg. The brand
# uses its small-size optical variant at 16-48 px, and PrivacyNotes shows the icon at 40 px.
BRAND_MARKS = {
    "dark": os.path.join(ROOT, "brand", "rfs-mark-small-dark.svg"),
    "light": os.path.join(ROOT, "brand", "rfs-mark-small-light.svg"),
}

SEED_KEYS = ("background", "sidebar", "border", "text", "muted", "accent")
MORE_KEYS = (
    "list", "paper", "well", "soft", "hover",
    "fill", "fillhover", "danger", "warning", "success", "label",
)

BLACK = "#000000"
WHITE = "#FFFFFF"
AIM = 4.6

STATUS = {
    "light": {"danger": "#C10007", "warning": "#973C00", "success": "#006045"},
    "dark": {"danger": "#FF6467", "warning": "#FFB900", "success": "#00D492"},
}
PRO = {"light": "#B45309", "dark": "#F5C518"}
LABEL_INKS = {
    "light": ["#5A6168", "#BA1C1C", "#A43F08", "#8D5200", "#206D2F", "#096878", "#1661A7", "#653AE6", "#B52356"],
    "dark": ["#8E969D", "#EA7171", "#F46D24", "#F08C00", "#33AA49", "#0FA4BC", "#469AE7", "#A085F0", "#E36F98"],
}
TINT_RGB = ["#868E96", "#FF6B6B", "#FF922B", "#FACC15", "#40C057", "#12B886", "#339AF0", "#9775FA", "#F06595"]
TINT_ALPHA = {
    "light": [0.12] * 9,
    "dark": [0.1, 0.1, 0.1, 0.08, 0.1, 0.1, 0.1, 0.1, 0.1],
}


def rgb_of(h: str):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


def hex_of(rgb):
    return "#" + "".join(f"{max(0, min(255, int(v + 0.5))):02X}" for v in rgb)


def mix(a: str, b: str, t: float) -> str:
    x, y = rgb_of(a), rgb_of(b)
    return hex_of([x[i] * (1.0 - t) + y[i] * t for i in range(3)])


def channel(v: int) -> float:
    s = v / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def luminance(h: str) -> float:
    r, g, b = rgb_of(h)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def worst_on(fg: str, bgs) -> float:
    return min(contrast(fg, bg) for bg in bgs)


def walk(start: str, toward: str, ok) -> str:
    for i in range(101):
        c = mix(start, toward, i / 100.0)
        if ok(c):
            return c
    return toward


def serialize_pn1(theme: dict, author: str) -> str:
    seeds = ",".join(theme["seeds"][k][1:].upper() for k in SEED_KEYS)
    ov = theme.get("overrides", {})
    pairs = [f"{k}={ov[k][1:].upper()}" for k in MORE_KEYS if k in ov]
    if author:
        pairs.append(f"by={author}")
    more = ",".join(pairs)
    return f"pn1:{theme['name']}:{seeds}" + (f":{more}" if more else "")


def grounds(theme: dict, mode: str, lst: str, well: str) -> dict:
    s = theme["seeds"]
    paper = theme.get("overrides", {}).get("paper", s["background"])
    tinted = [s["background"]] if paper == s["background"] else [s["background"], paper]
    level = 0.2 if mode == "dark" else 0.15
    surfaces = [s["sidebar"], lst, s["background"], well] + ([] if paper == s["background"] else [paper])
    return {
        "surfaces": surfaces,
        "selectedRow": mix(s["sidebar"], s["accent"], level),
        "accentTints": [mix(p, s["accent"], level) for p in [s["sidebar"], lst] + tinted],
        "tints": [
            mix(ground, TINT_RGB[i], TINT_ALPHA[mode][i])
            for ground in tinted
            for i in range(len(TINT_RGB))
        ],
    }


def resolve_theme(theme: dict) -> dict:
    s = theme["seeds"]
    o = theme.get("overrides", {})
    mode = "dark" if luminance(s["background"]) < luminance(s["text"]) else "light"
    dark = mode == "dark"
    away = WHITE if dark else BLACK

    sug_list = mix(s["sidebar"], s["background"], 0.5)
    apart = lambda c: contrast(c, s["background"]) >= 1.15
    if dark:
        sug_well = walk(s["background"], BLACK, apart) if contrast(BLACK, s["background"]) >= 1.15 else walk(s["background"], s["text"], apart)
    else:
        sug_well = walk(s["background"], s["text"], apart)
    lst = o.get("list", sug_list)
    well = o.get("well", sug_well)
    g = grounds(theme, mode, lst, well)
    passes = lambda c: worst_on(c, g["surfaces"]) >= AIM

    sug_soft = walk(
        mix(s["text"], s["muted"], 0.5),
        s["text"],
        lambda c: passes(c) and contrast(c, g["selectedRow"]) >= AIM and (dark or worst_on(c, g["tints"]) >= AIM),
    )
    sug_hover = walk(
        mix(s["accent"], s["text"], 0.25),
        s["text"],
        lambda c: passes(c) and worst_on(c, g["accentTints"]) >= AIM,
    )
    sug_fill = walk(s["accent"], BLACK, lambda c: contrast(WHITE, c) >= AIM)
    fill = o.get("fill", sug_fill)
    sug_fillhover = mix(fill, BLACK, 0.14)
    sug_label = walk(s["accent"], s["text"], lambda c: worst_on(c, g["surfaces"]) >= 3.2)

    status = lambda k: walk(STATUS[mode][k], away, passes)
    suggested = {
        "list": sug_list, "paper": s["background"], "well": sug_well,
        "soft": sug_soft, "hover": sug_hover, "fill": sug_fill,
        "fillhover": sug_fillhover,
        "danger": status("danger"), "warning": status("warning"), "success": status("success"),
        "label": sug_label,
    }
    val = lambda k: o.get(k, suggested[k])
    return {
        "mode": mode,
        "label": o.get("label", sug_label),
        "paper": o.get("paper", s["background"]),
        "colors": {
            "surface-0": s["sidebar"], "surface-1": lst, "surface-2": s["background"],
            "track": well, "divider": s["border"],
            "text": s["text"], "text-soft": val("soft"), "text-muted": s["muted"],
            "accent": s["accent"], "accent-hover": val("hover"),
            "accent-fill": fill, "accent-fill-hover": val("fillhover"),
            "danger": val("danger"), "warning": val("warning"), "success": val("success"),
        },
    }


def check_theme(theme: dict) -> list:
    r = resolve_theme(theme)
    c = r["colors"]
    dark = r["mode"] == "dark"
    g = grounds(theme, r["mode"], c["surface-1"], c["track"])
    side = lambda h: luminance(h) < luminance(c["text"])
    same_side = side(theme["seeds"]["sidebar"]) == side(theme["seeds"]["background"])

    def txt(cid, fg, bgs=None):
        ratio = worst_on(fg, g["surfaces"] if bgs is None else bgs)
        return (cid, ratio, 4.5, ratio >= 4.5)

    def on_white(cid, bg):
        ratio = contrast(WHITE, bg)
        return (cid, ratio, 4.5, ratio >= 4.5)

    body = c["text"] if dark else c["text-soft"]
    note_ratio = worst_on(body, g["tints"])
    dates_pass = worst_on(c["text-muted"], g["tints"]) >= 3.0
    ink_ratio = min(worst_on(ink, g["surfaces"]) for ink in LABEL_INKS[r["mode"]])
    pro_ratio = worst_on(PRO[r["mode"]], g["surfaces"])
    label_ratio = min(worst_on(r["label"], g["surfaces"]), contrast(c["accent"], g["selectedRow"]))

    return [
        ("sides", None, 0.0, same_side),
        txt("text", c["text"]),
        txt("soft", c["text-soft"]),
        txt("muted", c["text-muted"]),
        txt("accent", c["accent"]),
        txt("hover", c["accent-hover"]),
        txt("accent-tint", c["accent-hover"], g["accentTints"]),
        txt("selected", c["text-soft"], [g["selectedRow"]]),
        on_white("fill", c["accent-fill"]),
        on_white("fill-hover", c["accent-fill-hover"]),
        txt("danger", c["danger"]),
        txt("warning", c["warning"]),
        txt("success", c["success"]),
        ("tinted-notes", note_ratio, 4.5, note_ratio >= 4.5 and dates_pass),
        ("labels", ink_ratio, 3.0, ink_ratio >= 3.0),
        ("label", label_ratio, 3.0, label_ratio >= 3.0),
        ("pro", pro_ratio, 3.0, pro_ratio >= 3.0),
    ]


def render_preview_svg(theme: dict, resolved: dict) -> str:
    """Render a crisp 3-pane PrivacyNotes workspace preview SVG (zero traffic lights)."""
    c = resolved["colors"]
    dark = resolved["mode"] == "dark"
    sidebar = c["surface-0"]
    note_list = c["surface-1"]
    bg = c["surface-2"]
    paper = resolved["paper"]
    well = c["track"]
    border = c["divider"]
    ink = c["text"]
    soft = c["text-soft"]
    mute = c["text-muted"]
    accent = c["accent"]
    fill = c["accent-fill"]
    label = resolved["label"]
    danger = c["danger"]
    warning = c["warning"]
    success = c["success"]
    level = 0.20 if dark else 0.15
    sel_side = mix(sidebar, accent, level)
    sel_list = mix(note_list, accent, level)
    beam_start = "#74B8E8" if dark else "#18496B"
    beam_end = "#F06E2B" if dark else "#AD3D0A"
    name = escape(theme["name"])
    lx = escape(theme["lx"])
    mode_lbl = "DARK" if dark else "LIGHT"
    swatches = [
        ("BG", bg), ("SIDE", sidebar), ("LIST", note_list), ("WELL", well),
        ("ACCENT", accent), ("FILL", fill), ("LABEL", label),
        ("OK", success), ("WARN", warning), ("ERR", danger),
    ]
    sw_svg = []
    sw_w = 56
    for idx, (lbl, hx) in enumerate(swatches):
        sx = 18 + idx * (sw_w + 6.4)
        sw_svg.append(
            f'<rect x="{sx:.1f}" y="357" width="{sw_w}" height="10" rx="2.5" fill="{hx}" stroke="{border}" stroke-width="0.8"/>'
            f'<text x="{sx + sw_w / 2:.1f}" y="378" text-anchor="middle" fill="{mute}" '
            f'font-family="ui-monospace,Consolas,monospace" font-size="8" font-weight="600">{lbl}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 390" width="660" height="390" role="img" aria-label="PrivacyNotes {name} ({lx} {mode_lbl}) workspace preview">
  <defs>
    <linearGradient id="hbeam" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{beam_start}"/>
      <stop offset="100%" stop-color="{beam_end}"/>
    </linearGradient>
    <clipPath id="frame-clip"><rect x="1" y="1" width="658" height="388" rx="11"/></clipPath>
  </defs>
  <g clip-path="url(#frame-clip)">
    <rect width="660" height="390" fill="{bg}"/>
    <rect width="660" height="3" fill="url(#hbeam)"/>

    <!-- Top workspace bar -->
    <rect x="0" y="3" width="660" height="33" fill="{sidebar}"/>
    <line x1="0" y1="36" x2="660" y2="36" stroke="{border}" stroke-width="1"/>
    <rect x="14" y="10" width="96" height="19" rx="4" fill="{well}" stroke="{border}" stroke-width="1"/>
    <text x="23" y="23" fill="{accent}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">[privacynotes]</text>
    <text x="122" y="23" fill="{ink}" font-family="system-ui,-apple-system,sans-serif" font-size="11.5" font-weight="700">{name}</text>
    <text x="646" y="23" text-anchor="end" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="600">{lx} · {mode_lbl} · 17/17 PASS</text>

    <!-- Pane 1: Sidebar (x=0..154) -->
    <rect x="0" y="36" width="154" height="310" fill="{sidebar}"/>
    <line x1="154" y1="36" x2="154" y2="346" stroke="{border}" stroke-width="1"/>

    <!-- Sidebar search well -->
    <rect x="12" y="48" width="130" height="24" rx="5" fill="{well}" stroke="{border}" stroke-width="1"/>
    <text x="22" y="63.5" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="9.5">Ninja...  Ctrl+K</text>

    <!-- Sidebar folders -->
    <text x="14" y="92" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700" letter-spacing="0.8">FOLDERS</text>
    <rect x="10" y="100" width="134" height="26" rx="5" fill="{sel_side}"/>
    <rect x="10" y="104" width="3" height="18" rx="1.5" fill="{accent}"/>
    <rect x="20" y="109" width="8" height="8" rx="1.5" fill="none" stroke="{accent}" stroke-width="1.5"/>
    <text x="35" y="116.5" fill="{soft}" font-family="system-ui,-apple-system,sans-serif" font-size="11" font-weight="600">Local Tools</text>
    <text x="135" y="116.5" text-anchor="end" fill="{accent}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">12</text>

    <rect x="20" y="135" width="8" height="8" rx="1.5" fill="none" stroke="{label}" stroke-width="1.5"/>
    <text x="35" y="142.5" fill="{soft}" font-family="system-ui,-apple-system,sans-serif" font-size="11">Brand Notes</text>
    <text x="135" y="142.5" text-anchor="end" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="9.5">04</text>

    <rect x="20" y="160" width="8" height="8" rx="1.5" fill="none" stroke="{label}" stroke-width="1.5"/>
    <text x="35" y="167.5" fill="{soft}" font-family="system-ui,-apple-system,sans-serif" font-size="11">Runbooks</text>
    <text x="135" y="167.5" text-anchor="end" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="9.5">09</text>

    <text x="14" y="198" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="700" letter-spacing="0.8">TAGS</text>
    <rect x="14" y="206" width="54" height="18" rx="4" fill="{well}" stroke="{border}" stroke-width="1"/>
    <text x="22" y="218" fill="{label}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="600">#local</text>
    <rect x="74" y="206" width="60" height="18" rx="4" fill="{well}" stroke="{border}" stroke-width="1"/>
    <text x="82" y="218" fill="{label}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="600">#e2ee</text>

    <!-- Primary New Note fill button -->
    <rect x="12" y="308" width="130" height="26" rx="5" fill="{fill}"/>
    <text x="77" y="324.5" text-anchor="middle" fill="#FFFFFF" font-family="system-ui,-apple-system,sans-serif" font-size="10.5" font-weight="700">+ New Note</text>

    <!-- Pane 2: Note List (x=154..332) -->
    <rect x="154" y="36" width="178" height="310" fill="{note_list}"/>
    <line x1="332" y1="36" x2="332" y2="346" stroke="{border}" stroke-width="1"/>
    <text x="166" y="57" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="9" font-weight="700">LOCAL TOOLS  ·  3 NOTES</text>
    <line x1="154" y1="67" x2="332" y2="67" stroke="{border}" stroke-width="1"/>

    <!-- Active note card -->
    <rect x="162" y="75" width="162" height="68" rx="6" fill="{sel_list}" stroke="{accent}" stroke-width="1"/>
    <text x="172" y="94" fill="{ink}" font-family="system-ui,-apple-system,sans-serif" font-size="11.5" font-weight="700">Cyclorama Dawn v2.1</text>
    <text x="172" y="110" fill="{soft}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">Zero-knowledge notes synced</text>
    <text x="172" y="123" fill="{soft}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">with calibrated AA tokens.</text>
    <text x="172" y="136" fill="{accent}" font-family="ui-monospace,Consolas,monospace" font-size="8.5" font-weight="600">Updated 2m ago</text>

    <!-- Second note card -->
    <rect x="162" y="152" width="162" height="58" rx="6" fill="{paper}" stroke="{border}" stroke-width="1"/>
    <text x="172" y="170" fill="{ink}" font-family="system-ui,-apple-system,sans-serif" font-size="11" font-weight="600">port-sync Checklist</text>
    <text x="172" y="185" fill="{mute}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">Forwarded port 51037 check</text>
    <text x="172" y="199" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="8.5">Yesterday · #local</text>

    <!-- Third note card -->
    <rect x="162" y="219" width="162" height="58" rx="6" fill="{paper}" stroke="{border}" stroke-width="1"/>
    <text x="172" y="237" fill="{ink}" font-family="system-ui,-apple-system,sans-serif" font-size="11" font-weight="600">mTLS Cert Store Guide</text>
    <text x="172" y="252" fill="{mute}" font-family="system-ui,-apple-system,sans-serif" font-size="9.5">CurrentUser\\My client cert</text>
    <text x="172" y="266" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="8.5">Nov 21 · #e2ee</text>

    <!-- Pane 3: Writing Paper (x=332..660) -->
    <rect x="332" y="36" width="328" height="310" fill="{paper}"/>
    <text x="352" y="66" fill="{ink}" font-family="system-ui,-apple-system,sans-serif" font-size="17" font-weight="800">Cyclorama Dawn v2.1</text>
    <text x="352" y="84" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="9">Encrypted locally  ·  #local  ·  by Real-Fruit-Snacks</text>
    <line x1="352" y1="95" x2="640" y2="95" stroke="{border}" stroke-width="1"/>

    <text x="352" y="116" fill="{soft}" font-family="system-ui,-apple-system,sans-serif" font-size="11">Calibrated directly from rfs-brand v2.1.0 tokens.</text>
    <text x="352" y="133" fill="{soft}" font-family="system-ui,-apple-system,sans-serif" font-size="11">Every surface, tint, and status role passes all 17</text>
    <text x="352" y="150" fill="{soft}" font-family="system-ui,-apple-system,sans-serif" font-size="11">built-in PrivacyNotes contrast checks with zero edits.</text>

    <!-- Code well inside editor -->
    <rect x="352" y="166" width="288" height="58" rx="6" fill="{well}" stroke="{border}" stroke-width="1"/>
    <rect x="352" y="166" width="3" height="58" rx="1.5" fill="{accent}"/>
    <text x="364" y="185" fill="{mute}" font-family="ui-monospace,Consolas,monospace" font-size="9"># Settings -&gt; Design -&gt; Paste theme code</text>
    <text x="364" y="202" fill="{accent}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">pn1:{name}</text>
    <text x="364" y="216" fill="{ink}" font-family="ui-monospace,Consolas,monospace" font-size="8.5">by=Real-Fruit-Snacks</text>

    <!-- Semantic status pills -->
    <rect x="352" y="242" width="84" height="22" rx="4" fill="{well}" stroke="{success}" stroke-width="1"/>
    <text x="394" y="256.5" text-anchor="middle" fill="{success}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">[ok] synced</text>
    <rect x="444" y="242" width="90" height="22" rx="4" fill="{well}" stroke="{warning}" stroke-width="1"/>
    <text x="489" y="256.5" text-anchor="middle" fill="{warning}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">[warn] draft</text>
    <rect x="542" y="242" width="98" height="22" rx="4" fill="{well}" stroke="{danger}" stroke-width="1"/>
    <text x="591" y="256.5" text-anchor="middle" fill="{danger}" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="700">[err] locked</text>

    <!-- Editor footer action row -->
    <text x="352" y="308" fill="{accent}" font-family="system-ui,-apple-system,sans-serif" font-size="10.5" font-weight="600" text-decoration="underline">Open theme repository -&gt;</text>
    <rect x="540" y="292" width="100" height="26" rx="5" fill="{fill}"/>
    <text x="590" y="308.5" text-anchor="middle" fill="#FFFFFF" font-family="system-ui,-apple-system,sans-serif" font-size="10.5" font-weight="700">Apply Theme</text>

    <!-- Bottom palette telemetry ribbon -->
    <rect x="0" y="346" width="660" height="44" fill="{sidebar}"/>
    <line x1="0" y1="346" x2="660" y2="346" stroke="{border}" stroke-width="1"/>
    {''.join(sw_svg)}
  </g>
  <rect x="0.5" y="0.5" width="659" height="389" rx="11.5" fill="none" stroke="{border}" stroke-width="1"/>
</svg>
'''


def icon_svg(theme: dict) -> str:
    """The RFS brand mark for this theme's PrivacyNotes logo slot, unchanged.

    The brand has two colourways: the dark mark for dark themes (Dawn, Steel) and
    the light mark for light themes (Day).
    """
    with open(BRAND_MARKS[theme["mode"]], encoding="utf-8") as fh:
        return fh.read()


def main() -> int:
    data = json.load(open(THEMES_JSON, encoding="utf-8"))
    author = data.get("author", "Real-Fruit-Snacks")
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    os.makedirs(DOCS_PREVIEW_DIR, exist_ok=True)
    os.makedirs(ICON_DIR, exist_ok=True)

    code_lines = [
        "# Real-Fruit-Snacks — Cyclorama Dawn themes for PrivacyNotes (https://privacynotes.app/)",
        "# Paste any pn1: line into Settings -> Design -> Paste theme code",
        "",
    ]

    for t in data["themes"]:
        canonical = serialize_pn1(t, author)
        if t.get("code") != canonical:
            print(f"[x] {t['id']}: code mismatch\n  json: {t.get('code')}\n  calc: {canonical}")
            return 1
        checks = check_theme(t)
        fails = [ch for ch in checks if not ch[3]]
        if fails:
            print(f"[x] {t['id']}: failed contrast checks: {fails}")
            return 1
        res = resolve_theme(t)
        svg = render_preview_svg(t, res)
        for out_dir in (PREVIEW_DIR, DOCS_PREVIEW_DIR):
            p = os.path.join(out_dir, f"{t['id']}.svg")
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(svg)
        with open(os.path.join(ICON_DIR, f"{t['id']}.svg"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(icon_svg(t))
        code_lines.append(f"# {t['name']} ({t['lx']} {res['mode'].title()}) — {t['tagline']}")
        code_lines.append(canonical)
        code_lines.append("")
        print(f"[ok] {t['name']:<16} ({res['mode']:<5}, 17/17 checks pass, {len(canonical)} chars)")

    with open(CODES_TXT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(code_lines))
    print(f"[ok] wrote {os.path.relpath(CODES_TXT, ROOT)}, {len(data['themes'])} SVG previews and {len(data['themes'])} logo icons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
