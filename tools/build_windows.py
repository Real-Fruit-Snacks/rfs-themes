#!/usr/bin/env python3
"""Generate Cyclorama Dawn v2.1.0 Windows 11 theme pack, Oklab wallpapers,
backup-first PowerShell installers, and SVG previews for apps/windows/.

Generates:
  - apps/windows/wallpapers/cyclorama-{dawn,steel,day}-{1080p,4k}.png
  - apps/windows/Cyclorama {Dawn,Steel,Day}.theme
  - apps/windows/install-cyclorama-{dawn,steel,day}.ps1
  - apps/windows/previews/cyclorama-{dawn,steel,day}.svg (+ docs/assets/previews/windows/)
  - apps/windows/themes.json & apps/windows/README.md

Zero external dependencies (Python 3.11+ standard library only).
Deterministic UTF-8 LF output and byte-identical PNGs across runs.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import uuid
import zlib
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
    hex_to_rgb,
    mix,
)
from svg_previews import render_windows_preview, write_preview_pair  # noqa: E402

# ---------------------------------------------------------------------------
# Variant-specific Windows 11 DWM & Explorer AccentPalette specification
# 8 slots (Light3, Light2, Light1, Accent, Dark1, Dark2, Dark3, Complementary)
# ---------------------------------------------------------------------------

WINDOWS_ACCENT_SPECS: dict[str, dict] = {
    "cyclorama-dawn": {
        "colorization": "#F06E2B",  # ui["accent_vivid"]
        "palette": [
            "#FFD2B3",  # Light3
            "#FFB07A",  # Light2 (ui["accent_hover"])
            "#FF9254",  # Light1 (ui["accent"])
            "#F06E2B",  # Accent (ui["accent_vivid"])
            "#CC5016",  # Dark1  (ui["beacon_wash"])
            "#9E3B0C",  # Dark2  (ui["accent_fill_hover"])
            "#5C2006",  # Dark3
            "#74B8E8",  # Complementary (ui["secondary"])
        ],
    },
    "cyclorama-steel": {
        "colorization": "#1F547A",  # ui["accent_vivid"]
        "palette": [
            "#CDE7FA",  # Light3
            "#99CDF2",  # Light2 (ui["accent_hover"])
            "#74B8E8",  # Light1 (ui["accent"])
            "#1F547A",  # Accent (ui["accent_vivid"])
            "#18496B",  # Dark1  (ui["accent_fill"])
            "#123955",  # Dark2  (ui["accent_fill_hover"])
            "#0B2436",  # Dark3
            "#FF9254",  # Complementary (ui["secondary"])
        ],
    },
    "cyclorama-day": {
        "colorization": "#AD3D0A",  # ui["accent"]
        "palette": [
            "#F8C9B0",  # Light3
            "#F09B6E",  # Light2
            "#D45B24",  # Light1
            "#AD3D0A",  # Accent (ui["accent"])
            "#8B2F06",  # Dark1  (ui["accent_hover"])
            "#6A2304",  # Dark2
            "#471602",  # Dark3
            "#18496B",  # Complementary (ui["accent_fill"])
        ],
    },
}

# Symmetric 4x4 Bayer ordered dithering offsets in (0, 1) -> +-0.5/255 step
_BAYER4_OFFSETS: tuple[tuple[float, float, float, float], ...] = (
    (0.5 / 16.0, 8.5 / 16.0, 2.5 / 16.0, 10.5 / 16.0),
    (12.5 / 16.0, 4.5 / 16.0, 14.5 / 16.0, 6.5 / 16.0),
    (3.5 / 16.0, 11.5 / 16.0, 1.5 / 16.0, 9.5 / 16.0),
    (15.5 / 16.0, 7.5 / 16.0, 13.5 / 16.0, 5.5 / 16.0),
)


# ---------------------------------------------------------------------------
# Pure-Python sRGB <-> Linear <-> Oklab + Deterministic PNG Encoder
# ---------------------------------------------------------------------------

def _srgb_to_linear(v: float) -> float:
    c = v / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    if c <= 0.0:
        return 0.0
    if c >= 1.0:
        return 255.0
    v = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055
    return v * 255.0


def _rgb_to_oklab(r: int, g: int, b: int) -> tuple[float, float, float]:
    rl, gl, bl = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)
    l = (0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl) ** (1.0 / 3.0)
    m = (0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl) ** (1.0 / 3.0)
    s = (0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl) ** (1.0 / 3.0)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def _oklab_to_srgb(L: float, a: float, b: float) -> tuple[float, float, float]:
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ * l_ * l_, m_ * m_ * m_, s_ * s_ * s_
    return (
        _linear_to_srgb(+4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
        _linear_to_srgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
        _linear_to_srgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s),
    )


def _sample_oklab_stops(
    stops: list[tuple[float, tuple[float, float, float]]],
    t: float,
) -> tuple[float, float, float]:
    for idx in range(len(stops) - 1):
        p0, c0 = stops[idx]
        p1, c1 = stops[idx + 1]
        if t <= p1 or idx == len(stops) - 2:
            u = 0.0 if p1 <= p0 else max(0.0, min(1.0, (t - p0) / (p1 - p0)))
            return _oklab_to_srgb(
                c0[0] + (c1[0] - c0[0]) * u,
                c0[1] + (c1[1] - c0[1]) * u,
                c0[2] + (c1[2] - c0[2]) * u,
            )
    return _oklab_to_srgb(*stops[-1][1])


def _precompute_horizontal_phases(
    width: int,
    hex_stops: list[tuple[float, str]],
) -> tuple[list[bytes], list[bytes], list[bytes]]:
    stops = [(pos, _rgb_to_oklab(*hex_to_rgb(hx))) for pos, hx in hex_stops]
    qr = bytearray(width)
    qg = bytearray(width)
    qb = bytearray(width)
    inv_w = 1.0 / (width - 1)
    for x in range(width):
        r, g, b = _sample_oklab_stops(stops, x * inv_w)
        qr[x] = min(255, max(0, int(r + 0.5)))
        qg[x] = min(255, max(0, int(g + 0.5)))
        qb[x] = min(255, max(0, int(b + 0.5)))
    return (
        [bytes(qr[p::4]) for p in range(4)],
        [bytes(qg[p::4]) for p in range(4)],
        [bytes(qb[p::4]) for p in range(4)],
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _encode_png_rgb(width: int, height: int, raw_scanlines: bytes) -> bytes:
    """Write a deterministic 8-bit Truecolor RGB PNG (no tIME chunk)."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw_scanlines, level=6)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"sRGB", b"\x00")
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def _apply_horizon_strip(
    base_row: bytearray,
    width: int,
    rim_stops: list[tuple[float, str]],
    rim_alpha: float,
    bayer_row: tuple[float, float, float, float],
) -> bytes:
    """Blend a crisp, subtle Oklab horizon rim into the bottom scanlines."""
    stops = [(pos, _rgb_to_oklab(*hex_to_rgb(hx))) for pos, hx in rim_stops]
    out = bytearray(base_row)
    inv_w = 1.0 / (width - 1)
    one_m = 1.0 - rim_alpha
    pos = 1
    for x in range(width):
        rr, rg, rb = _sample_oklab_stops(stops, x * inv_w)
        off = bayer_row[x & 3]
        out[pos] = min(255, max(0, int(out[pos] * one_m + rr * rim_alpha + off)))
        out[pos + 1] = min(255, max(0, int(out[pos + 1] * one_m + rg * rim_alpha + off)))
        out[pos + 2] = min(255, max(0, int(out[pos + 2] * one_m + rb * rim_alpha + off)))
        pos += 3
    return bytes(out)


def _generate_wallpaper_pair(vid: str, wp_dir: str) -> tuple[str, str]:
    """Generate both 1920x1080 and 3840x2160 Oklab wallpapers in one dual-res pass."""
    v = VARIANTS[vid]
    ui = v["ui"]
    bg_rgb = hex_to_rgb(ui["bg"])

    if vid == "cyclorama-dawn":
        floor_stops = [
            (0.00, ui["secondary_vivid"]),  # #1F547A Glacial Steel
            (0.24, ui["steel_wash"]),       # #133954 Deep Steel wash
            (0.50, ui["bg"]),               # #050507 Matte dark center
            (0.76, ui["beacon_wash"]),      # #CC5016 Warm Beacon wash
            (1.00, ui["accent_vivid"]),     # #F06E2B Beacon Orange
        ]
        max_alpha = 0.34
        cool_whisper = None
        rim_stops = [
            (0.00, ui["beam_start"]),       # #74B8E8
            (0.32, ui["secondary_vivid"]),  # #1F547A
            (0.50, ui["bg"]),               # #050507
            (0.68, ui["beacon_wash"]),      # #CC5016
            (1.00, ui["beam_end"]),         # #F06E2B
        ]
        rim_alpha = 0.22
    elif vid == "cyclorama-steel":
        floor_stops = [
            (0.00, ui["steel_wash"]),       # #133954
            (0.50, ui["accent_vivid"]),     # #1F547A
            (1.00, ui["accent_fill"]),      # #18496B
        ]
        max_alpha = 0.34
        cool_whisper = hex_to_rgb(ui["accent"])  # #74B8E8 coolness along the base
        rim_stops = [
            (0.00, ui["accent_fill"]),      # #18496B
            (0.50, ui["accent"]),           # #74B8E8
            (1.00, ui["accent_vivid"]),     # #1F547A
        ]
        rim_alpha = 0.18
    else:  # cyclorama-day
        floor_stops = [
            (0.00, ui["steel_wash"]),       # #DCE7F0 cool frost Steel
            (0.50, ui["bg"]),               # #F5F7F9 Alabaster center
            (1.00, ui["beacon_wash"]),      # #F8E3D6 warm Dawn frost
        ]
        max_alpha = 0.85
        cool_whisper = None
        rim_stops = [
            (0.00, ui["beam_start"]),       # #18496B
            (0.50, ui["bg"]),               # #F5F7F9
            (1.00, ui["beam_end"]),         # #AD3D0A
        ]
        rim_alpha = 0.10

    w1, h1 = 1920, 1080
    w4, h4 = 3840, 2160
    start1 = int(h1 * 0.52)  # 561 rows matte top; 519 rows lower 48% floor wash

    qr1, qg1, qb1 = _precompute_horizontal_phases(w1, floor_stops)
    qr4, qg4, qb4 = _precompute_horizontal_phases(w4, floor_stops)

    flat1 = b"\x00" + bytes(bg_rgb) * w1
    flat4 = b"\x00" + bytes(bg_rgb) * w4
    rows1: list[bytes] = [flat1] * start1
    rows4: list[bytes] = [flat4] * (start1 * 2)

    br0, bg0, bb0 = bg_rgb
    span1 = h1 - start1  # 519
    inv_span = 1.0 / (span1 - 1)
    row1 = bytearray(1 + w1 * 3)
    row1[0] = 0
    row4 = bytearray(1 + w4 * 3)
    row4[0] = 0
    rng256 = range(256)
    same_rg = (br0 == bg0) and (cool_whisper is None)

    for k in range(span1):
        ty = k * inv_span
        al = max_alpha * ty * ty * ty
        one_m = 1.0 - al
        bayer_row = _BAYER4_OFFSETS[k & 3]
        o0, o1, o2, o3 = bayer_row

        cr = br0 * one_m
        cg = bg0 * one_m
        cb = bb0 * one_m

        if cool_whisper is not None and ty > 0.78:
            tw = (ty - 0.78) / 0.22
            wa = 0.08 * tw * tw
            wm = 1.0 - wa
            wr, wg, wb = cool_whisper
            cr = cr * wm + wr * wa
            cg = cg * wm + wg * wa
            cb = cb * wm + wb * wa
            al_eff = al * wm
        else:
            al_eff = al

        tr0 = bytes(min(255, int(cr + o0 + i * al_eff)) for i in rng256)
        tr1 = bytes(min(255, int(cr + o1 + i * al_eff)) for i in rng256)
        tr2 = bytes(min(255, int(cr + o2 + i * al_eff)) for i in rng256)
        tr3 = bytes(min(255, int(cr + o3 + i * al_eff)) for i in rng256)
        if same_rg:
            tg0, tg1, tg2, tg3 = tr0, tr1, tr2, tr3
        else:
            tg0 = bytes(min(255, int(cg + o0 + i * al_eff)) for i in rng256)
            tg1 = bytes(min(255, int(cg + o1 + i * al_eff)) for i in rng256)
            tg2 = bytes(min(255, int(cg + o2 + i * al_eff)) for i in rng256)
            tg3 = bytes(min(255, int(cg + o3 + i * al_eff)) for i in rng256)
        tb0 = bytes(min(255, int(cb + o0 + i * al_eff)) for i in rng256)
        tb1 = bytes(min(255, int(cb + o1 + i * al_eff)) for i in rng256)
        tb2 = bytes(min(255, int(cb + o2 + i * al_eff)) for i in rng256)
        tb3 = bytes(min(255, int(cb + o3 + i * al_eff)) for i in rng256)

        row1[1::12] = qr1[0].translate(tr0)
        row1[2::12] = qg1[0].translate(tg0)
        row1[3::12] = qb1[0].translate(tb0)
        row1[4::12] = qr1[1].translate(tr1)
        row1[5::12] = qg1[1].translate(tg1)
        row1[6::12] = qb1[1].translate(tb1)
        row1[7::12] = qr1[2].translate(tr2)
        row1[8::12] = qg1[2].translate(tg2)
        row1[9::12] = qb1[2].translate(tb2)
        row1[10::12] = qr1[3].translate(tr3)
        row1[11::12] = qg1[3].translate(tg3)
        row1[12::12] = qb1[3].translate(tb3)

        row4[1::12] = qr4[0].translate(tr0)
        row4[2::12] = qg4[0].translate(tg0)
        row4[3::12] = qb4[0].translate(tb0)
        row4[4::12] = qr4[1].translate(tr1)
        row4[5::12] = qg4[1].translate(tg1)
        row4[6::12] = qb4[1].translate(tb1)
        row4[7::12] = qr4[2].translate(tr2)
        row4[8::12] = qg4[2].translate(tg2)
        row4[9::12] = qb4[2].translate(tb2)
        row4[10::12] = qr4[3].translate(tr3)
        row4[11::12] = qg4[3].translate(tg3)
        row4[12::12] = qb4[3].translate(tb3)

        # Subtle 2px (1080p) / 4px (4K) horizon rim along the bottom edge
        if k >= span1 - 2:
            weight = rim_alpha * (0.55 if k == span1 - 2 else 1.0)
            b1 = _apply_horizon_strip(row1, w1, rim_stops, weight, bayer_row)
            b4 = _apply_horizon_strip(row4, w4, rim_stops, weight, bayer_row)
            rows1.append(b1)
            rows4.append(b4)
            rows4.append(b4)
        else:
            rows1.append(bytes(row1))
            b4 = bytes(row4)
            rows4.append(b4)
            rows4.append(b4)

    os.makedirs(wp_dir, exist_ok=True)
    p_1080 = os.path.join(wp_dir, f"{vid}-1080p.png")
    p_4k = os.path.join(wp_dir, f"{vid}-4k.png")
    with open(p_1080, "wb") as fh:
        fh.write(_encode_png_rgb(w1, h1, b"".join(rows1)))
    with open(p_4k, "wb") as fh:
        fh.write(_encode_png_rgb(w4, h4, b"".join(rows4)))
    return p_1080, p_4k


# ---------------------------------------------------------------------------
# Helpers for Windows .theme INI & PowerShell Installers
# ---------------------------------------------------------------------------

def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _write_json(path: str, payload: dict) -> None:
    _write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _theme_guid(vid: str) -> str:
    return "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"{REPO_URL}/apps/windows/{vid}")).upper() + "}"


def _abgr_dword_hex(hx: str) -> str:
    r, g, b = hex_to_rgb(hx)
    return f"0xFF{b:02X}{g:02X}{r:02X}"


def _argb_dword_hex(hx: str, alpha: int = 0xC4) -> str:
    r, g, b = hex_to_rgb(hx)
    return f"0x{alpha:02X}{r:02X}{g:02X}{b:02X}"


def _accent_palette_ps_bytes(hex_slots: list[str]) -> str:
    """Format 8 hex colors as 32-byte Explorer AccentPalette (RR GG BB 00 x8)."""
    chunks = []
    for hx in hex_slots:
        r, g, b = hex_to_rgb(hx)
        chunks.append(f"0x{r:02X},0x{g:02X},0x{b:02X},0x00")
    return ", ".join(chunks)


def _build_theme_ini(v: dict) -> str:
    vid = v["id"]
    ui = v["ui"]
    spec = WINDOWS_ACCENT_SPECS[vid]
    r, g, b = hex_to_rgb(ui["bg"])
    mode_win = "Dark" if v["mode"] == "dark" else "Light"
    colorization = _argb_dword_hex(spec["colorization"], alpha=0xC4)
    guid = _theme_guid(vid)

    return (
        f"; {v['name']} ({v['lx']} {mode_win} · {v['accentRole']}) — Windows 11 Theme\n"
        f"; Brand: {BRAND_NAME} v{v['version']} | Author: {AUTHOR}\n"
        f"; Source: {REPO_URL}\n\n"
        f"[Theme]\n"
        f"DisplayName={v['name']}\n"
        f"ThemeId={guid}\n\n"
        f"[Control Panel\\Desktop]\n"
        f"Wallpaper=%LOCALAPPDATA%\\rfs-themes\\windows\\wallpapers\\{vid}-1080p.png\n"
        f"Pattern=\n"
        f"MultimonBackgrounds=0\n"
        f"PicturePosition=4\n\n"
        f"[Control Panel\\Colors]\n"
        f"Background={r} {g} {b}\n\n"
        f"[VisualStyles]\n"
        f"Path=%SystemRoot%\\resources\\themes\\Aero\\Aero.msstyles\n"
        f"ColorStyle=NormalColor\n"
        f"Size=NormalSize\n"
        f"AutoColorization=0\n"
        f"ColorizationColor={colorization}\n"
        f"VisualStyleVersion=10\n"
        f"SystemMode={mode_win}\n"
        f"AppMode={mode_win}\n\n"
        f"[MasterThemeSelector]\n"
        f"MTSM=RJSPBS\n\n"
        f"[boot]\n"
        f"SCRNSAVE.EXE=\n"
    )


def _build_installer_ps1(v: dict) -> str:
    vid = v["id"]
    ui = v["ui"]
    spec = WINDOWS_ACCENT_SPECS[vid]
    palette = spec["palette"]
    is_light = v["mode"] == "light"
    mode_win = "Light" if is_light else "Dark"
    light_val = 1 if is_light else 0
    bg_r, bg_g, bg_b = hex_to_rgb(ui["bg"])

    accent_hex = spec["colorization"]
    dark1_hex = palette[4]
    dwm_accent_abgr = _abgr_dword_hex(accent_hex)
    dwm_colorization = _argb_dword_hex(accent_hex, alpha=0xC4)
    start_color_abgr = _abgr_dword_hex(dark1_hex)
    palette_bytes = _accent_palette_ps_bytes(palette)
    theme_filename = f"{v['name']}.theme"

    return f"""#Requires -Version 5.1
<#
.SYNOPSIS
    Installs {v['name']} ({v['lx']} {mode_win} · {v['accentRole']}) on Windows 11.
.DESCRIPTION
    Backup-first installer for {BRAND_NAME} v{v['version']} ({AUTHOR}).
    Copies Oklab-calibrated 1080p & 4K wallpapers and native .theme files into
    %LOCALAPPDATA%\\rfs-themes\\windows and %LOCALAPPDATA%\\Microsoft\\Windows\\Themes,
    exports a one-time registry backup (backup-pre-rfs.reg), configures Personalize,
    DWM, Explorer AccentPalette (32 bytes), and applies the wallpaper and accents live.
.PARAMETER Resolution
    Wallpaper resolution: 'auto' (4k when any connected display exceeds 1920x1080 —
    such as 1440p, ultrawide, or 4K — else 1080p), '1080p', or '4k'.
.PARAMETER TintTaskbar
    When specified, enables accent tinting on Start and Taskbar (ColorPrevalence = 1).
    Defaults to off so the taskbar stays matte {mode_win.lower()}.
.EXAMPLE
    .\\install-{vid}.ps1
.EXAMPLE
    .\\install-{vid}.ps1 -Resolution 4k -TintTaskbar
#>
[CmdletBinding()]
param(
    [ValidateSet('auto', '1080p', '4k')]
    [string]$Resolution = 'auto',
    [switch]$TintTaskbar
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$VariantId      = '{vid}'
$ThemeName      = '{v["name"]}'
$ThemeFileName  = '{theme_filename}'
$ScriptDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot    = Join-Path $env:LOCALAPPDATA 'rfs-themes\\windows'
$WallpaperDest  = Join-Path $InstallRoot 'wallpapers'
$WinThemesDir   = Join-Path $env:LOCALAPPDATA 'Microsoft\\Windows\\Themes'
$BackupRegPath  = Join-Path $InstallRoot 'backup-pre-rfs.reg'

if (-not ([System.Management.Automation.PSTypeName]'RfsThemes.NativeWin32').Type) {{
    Add-Type -Namespace 'RfsThemes' -Name 'NativeWin32' -MemberDefinition @'
        [System.Runtime.InteropServices.DllImport("user32.dll", SetLastError = true)]
        public static extern bool SetProcessDpiAwarenessContext(System.IntPtr value);

        [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
        public static extern bool SystemParametersInfoW(uint uiAction, uint uiParam, string pvParam, uint fWinIni);

        [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
        public static extern System.IntPtr SendMessageTimeoutW(
            System.IntPtr hWnd,
            uint Msg,
            System.UIntPtr wParam,
            string lParam,
            uint fuFlags,
            uint uTimeout,
            out System.UIntPtr lpdwResult
        );
'@
}}

# 1. Resolve target display resolution ('auto' -> 4k if any connected monitor exceeds 1920x1080)
if ($Resolution -eq 'auto') {{
    $screenWidth  = 0
    $screenHeight = 0
    # Query physical pixels via WMI video controllers (unaffected by DPI scaling)
    try {{
        $controllers = Get-CimInstance -ClassName Win32_VideoController -ErrorAction Stop |
            Where-Object {{ $_.CurrentHorizontalResolution -and $_.CurrentVerticalResolution }}
        foreach ($vc in $controllers) {{
            $screenWidth  = [Math]::Max($screenWidth,  [int]$vc.CurrentHorizontalResolution)
            $screenHeight = [Math]::Max($screenHeight, [int]$vc.CurrentVerticalResolution)
        }}
    }} catch {{}}
    # Enable Per-Monitor V2 DPI awareness (-4) and inspect ALL connected screens
    try {{
        $null = [RfsThemes.NativeWin32]::SetProcessDpiAwarenessContext([System.IntPtr](-4))
    }} catch {{}}
    try {{
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        foreach ($scr in [System.Windows.Forms.Screen]::AllScreens) {{
            $screenWidth  = [Math]::Max($screenWidth,  [int]$scr.Bounds.Width)
            $screenHeight = [Math]::Max($screenHeight, [int]$scr.Bounds.Height)
        }}
    }} catch {{}}
    if ($screenWidth -le 0) {{
        $screenWidth = 1920
    }}
    $Resolution = if ($screenWidth -gt 1920 -or $screenHeight -gt 1080) {{ '4k' }} else {{ '1080p' }}
}}

# 2. Copy wallpapers and native Windows 11 .theme files to permanent directories
New-Item -ItemType Directory -Path $WallpaperDest -Force | Out-Null
New-Item -ItemType Directory -Path $WinThemesDir -Force | Out-Null

$SourceWallpapers = Join-Path $ScriptDir 'wallpapers'
if (Test-Path -LiteralPath $SourceWallpapers) {{
    Get-ChildItem -LiteralPath $SourceWallpapers -Filter 'cyclorama-*.png' | ForEach-Object {{
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $WallpaperDest $_.Name) -Force
    }}
}}

$wpPath = Join-Path $WallpaperDest "$VariantId-$Resolution.png"
if (-not (Test-Path -LiteralPath $wpPath)) {{
    throw "Wallpaper not found at $wpPath. Run this script from apps/windows/."
}}

Get-ChildItem -LiteralPath $ScriptDir -Filter 'Cyclorama *.theme' | ForEach-Object {{
    $themeContent = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
    $themeContent = $themeContent -replace '-1080p\\.png', "-$Resolution.png"
    $destLocal = Join-Path $InstallRoot $_.Name
    $destWin   = Join-Path $WinThemesDir $_.Name
    [System.IO.File]::WriteAllText($destLocal, $themeContent, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($destWin, $themeContent, [System.Text.UTF8Encoding]::new($false))
}}

# 3. Export one-time registry backup before modifying any Windows personalization keys
if (-not (Test-Path -LiteralPath $BackupRegPath)) {{
    $keysToBackup = @(
        'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize',
        'HKCU\\Software\\Microsoft\\Windows\\DWM',
        'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent',
        'HKCU\\Control Panel\\Desktop',
        'HKCU\\Control Panel\\Colors'
    )
    $mergedLines = New-Object System.Collections.Generic.List[string]
    $mergedLines.Add('Windows Registry Editor Version 5.00')
    $mergedLines.Add('')
    foreach ($regKey in $keysToBackup) {{
        $psRegPath = $regKey -replace '^HKCU\\\\', 'HKCU:\\'
        if (-not (Test-Path -LiteralPath $psRegPath)) {{
            continue
        }}
        $tmpFile = Join-Path $env:TEMP ("rfs-backup-" + [System.Guid]::NewGuid().ToString('N') + '.reg')
        $prevEap = $ErrorActionPreference
        try {{
            $ErrorActionPreference = 'Continue'
            & reg.exe export $regKey $tmpFile /y 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $tmpFile)) {{
                $exported = Get-Content -LiteralPath $tmpFile -Encoding Unicode
                foreach ($line in ($exported | Select-Object -Skip 1)) {{
                    $mergedLines.Add($line)
                }}
                $mergedLines.Add('')
            }}
        }} finally {{
            $ErrorActionPreference = $prevEap
            if (Test-Path -LiteralPath $tmpFile) {{
                Remove-Item -LiteralPath $tmpFile -Force -ErrorAction SilentlyContinue
            }}
        }}
    }}
    Set-Content -LiteralPath $BackupRegPath -Value $mergedLines -Encoding Unicode
    Write-Host "[ok] Saved one-time pre-RFS registry backup to $BackupRegPath"
}}

function Set-RegistryValue {{
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string]$Type
    )
    if (-not (Test-Path -LiteralPath $Path)) {{
        New-Item -Path $Path -Force | Out-Null
    }}
    New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
}}

# 4. Personalize (Dark/Light mode, transparency, taskbar color prevalence)
$PersonalizeKey = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize'
$TaskbarTintVal = if ($TintTaskbar.IsPresent) {{ 1 }} else {{ 0 }}
Set-RegistryValue -Path $PersonalizeKey -Name 'AppsUseLightTheme'    -Value {light_val} -Type DWord
Set-RegistryValue -Path $PersonalizeKey -Name 'SystemUsesLightTheme' -Value {light_val} -Type DWord
Set-RegistryValue -Path $PersonalizeKey -Name 'ColorPrevalence'      -Value $TaskbarTintVal -Type DWord
Set-RegistryValue -Path $PersonalizeKey -Name 'EnableTransparency'   -Value 1 -Type DWord

# 5. DWM Accent & Colorization ({accent_hex}: ABGR={dwm_accent_abgr}, ARGB={dwm_colorization})
$DwmKey = 'HKCU:\\Software\\Microsoft\\Windows\\DWM'
Set-RegistryValue -Path $DwmKey -Name 'AccentColor'           -Value {dwm_accent_abgr} -Type DWord
Set-RegistryValue -Path $DwmKey -Name 'ColorizationColor'     -Value {dwm_colorization} -Type DWord
Set-RegistryValue -Path $DwmKey -Name 'ColorizationAfterglow' -Value {dwm_colorization} -Type DWord
Set-RegistryValue -Path $DwmKey -Name 'ColorPrevalence'       -Value 0 -Type DWord

# 6. Explorer Accent Menu & 32-byte AccentPalette (8 slots x RR GG BB 00)
$AccentKey = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent'
[byte[]]$AccentPalette = @(
    {palette_bytes}
)
Set-RegistryValue -Path $AccentKey -Name 'AccentColorMenu' -Value {dwm_accent_abgr} -Type DWord
Set-RegistryValue -Path $AccentKey -Name 'StartColorMenu'  -Value {start_color_abgr} -Type DWord
Set-RegistryValue -Path $AccentKey -Name 'AccentPalette'   -Value $AccentPalette -Type Binary

# 7. Desktop solid fallback background + wallpaper fit mode
$ColorsKey  = 'HKCU:\\Control Panel\\Colors'
$DesktopKey = 'HKCU:\\Control Panel\\Desktop'
Set-RegistryValue -Path $ColorsKey  -Name 'Background'     -Value '{bg_r} {bg_g} {bg_b}' -Type String
Set-RegistryValue -Path $DesktopKey -Name 'WallpaperStyle' -Value '10' -Type String
Set-RegistryValue -Path $DesktopKey -Name 'TileWallpaper'  -Value '0'  -Type String

# 8. Apply wallpaper live and broadcast WM_SETTINGCHANGE ("ImmersiveColorSet")
$null = [RfsThemes.NativeWin32]::SystemParametersInfoW(0x0014, 0, $wpPath, 3)
$broadcastResult = [System.UIntPtr]::Zero
$null = [RfsThemes.NativeWin32]::SendMessageTimeoutW(
    [System.IntPtr]0xFFFF,
    0x001A,
    [System.UIntPtr]::Zero,
    'ImmersiveColorSet',
    0x0002,
    5000,
    [ref]$broadcastResult
)

Write-Host "[ok] Installed $ThemeName ($Resolution, {mode_win} mode, TintTaskbar=$($TintTaskbar.IsPresent))"
Write-Host "[i]  Theme registered in Settings -> Personalization -> Themes ($ThemeFileName)"
Write-Host "[i]  To revert original Windows colors later, merge: $BackupRegPath"
"""


def _six_swatches(v: dict) -> list[dict[str, str]]:
    ui = v["ui"]
    spec = WINDOWS_ACCENT_SPECS[v["id"]]
    return [
        {"label": "Background", "hex": ui["bg"]},
        {"label": "Surface", "hex": ui["surface"]},
        {"label": "Accent", "hex": ui["accent"]},
        {"label": "Colorize", "hex": spec["colorization"]},
        {"label": "Dark1", "hex": spec["palette"][4]},
        {"label": "Secondary", "hex": ui["secondary"]},
    ]


def _render_readme(
    *,
    app_name: str,
    homepage: str,
    fmt: str,
    install_steps: list[str],
    files: list[dict[str, str]],
    summaries: dict[str, str],
) -> str:
    ver = VARIANTS["cyclorama-dawn"]["version"]
    lines = [
        f"# {BRAND_NAME} for {app_name}",
        "",
        f"Native Windows 11 `.theme` packs, pure-Oklab 1080p & 4K wallpapers (zero 8-bit banding via 4×4 Bayer dithering), "
        f"and backup-first PowerShell installers calibrated from [`brand/rfs.tokens.json`](../../brand/rfs.tokens.json) "
        f"(**{BRAND_NAME} v{ver}**) for **[{app_name}]({homepage})** (`{fmt}`).",
        "",
        "## Install",
        "",
    ]
    for idx, step in enumerate(install_steps, 1):
        lines.append(f"{idx}. {step}")

    lines += [
        "",
        "### Quick PowerShell Install",
        "",
        "```powershell",
        "# Auto-detects 4K (>1920x1080 across all monitors: 1440p/ultrawide/4K) vs 1080p and backs up current settings to backup-pre-rfs.reg",
        ".\\install-cyclorama-dawn.ps1",
        "",
        "# Optional: force 4K or enable taskbar accent tinting",
        ".\\install-cyclorama-steel.ps1 -Resolution 4k -TintTaskbar",
        "```",
        "",
        "### Reverting",
        "",
        "Double-click `%LOCALAPPDATA%\\rfs-themes\\windows\\backup-pre-rfs.reg` (created automatically on first run) "
        "or choose any prior theme under **Settings -> Personalization -> Themes**.",
        "",
        "## Included Files",
        "",
        "| Artifact | Path |",
        "|---|---|",
    ]
    prefix = "apps/windows/"
    for item in files:
        rel = item["path"][len(prefix):] if item["path"].startswith(prefix) else item["path"]
        href = quote(rel, safe="/")
        lines.append(f"| {item['label']} | [`{rel}`]({href}) |")

    lines += [
        "",
        "## Variants",
        "",
        "| Variant | Lighting Cue | Mode | Colorization (`ARGB`) | DWM Accent (`ABGR`) | Background | Wallpapers |",
        "|---|---|---|---|---|---|---|",
    ]
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        ui = v["ui"]
        spec = WINDOWS_ACCENT_SPECS[vid]
        c_argb = _argb_dword_hex(spec["colorization"], 0xC4)
        a_abgr = _abgr_dword_hex(spec["colorization"])
        wp_links = (
            f"[1080p](wallpapers/{vid}-1080p.png) · "
            f"[4K](wallpapers/{vid}-4k.png)"
        )
        lines.append(
            f"| **{v['name']}** | `{v['lx']}` | `{v['mode']}` | `{c_argb}` | `{a_abgr}` | `{ui['bg']}` | {wp_links} |"
        )

    lines += [
        "",
        "## 8-Slot Windows 11 `AccentPalette`",
        "",
        "| Variant | Light3 | Light2 | Light1 | Accent | Dark1 | Dark2 | Dark3 | Complementary |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        slots = " | ".join(f"`{hx}`" for hx in WINDOWS_ACCENT_SPECS[vid]["palette"])
        lines.append(f"| **{v['name']}** | {slots} |")

    lines += ["", "## Previews", ""]
    for idx, vid in enumerate(VARIANT_ORDER, 1):
        v = VARIANTS[vid]
        lines += [
            f"### {idx}. {v['name']} (`{v['lx']} · {v['accentRole']}`)",
            "",
            summaries[vid],
            "",
            f"![{v['name']} Windows 11 desktop preview](previews/{vid}.svg)",
            "",
        ]

    lines += [
        "## Regenerating",
        "",
        "```sh",
        "python tools/build_windows.py",
        "```",
        "",
        f"Browse all ports in the [{BRAND_NAME} Theme Gallery]({GALLERY_URL}) or on [GitHub]({REPO_URL}).",
        "",
    ]
    return "\n".join(lines)


def build() -> dict:
    slug = "windows"
    app_name = "Windows 11"
    category = "Browsers & Desktop"
    homepage = "https://www.microsoft.com/windows/"
    fmt = "Windows 11 .theme + Wallpapers + .ps1"
    install = "Run install-cyclorama-dawn.ps1 or double-click .theme"
    install_steps = [
        "Run `.\\install-cyclorama-dawn.ps1` (or `steel` / `day`) from `apps/windows/` — it auto-detects `1080p` vs `4k` (`-Resolution auto|1080p|4k`), saves a one-time registry backup to `%LOCALAPPDATA%\\rfs-themes\\windows\\backup-pre-rfs.reg`, installs wallpapers & `.theme` files, sets the 32-byte `AccentPalette`, and refreshes Windows live.",
        "Pass `-TintTaskbar` if you want Start/Taskbar tinted with the accent color (off by default so the taskbar stays matte `#050507` or Alabaster `#F5F7F9`).",
        "Switch between **Cyclorama Dawn**, **Cyclorama Steel**, and **Cyclorama Day** anytime from **Settings -> Personalization -> Themes**, or double-click `backup-pre-rfs.reg` to revert.",
    ]

    app_dir = os.path.join(ROOT, "apps", slug)
    wp_dir = os.path.join(app_dir, "wallpapers")
    ver = VARIANTS["cyclorama-dawn"]["version"]

    theme_texts: dict[str, str] = {}
    files: list[dict[str, str]] = []

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        spec = WINDOWS_ACCENT_SPECS[vid]

        # A. Oklab 1080p + 4K wallpapers
        _generate_wallpaper_pair(vid, wp_dir)

        # B. Native Windows 11 .theme file
        ini_text = _build_theme_ini(v)
        theme_texts[vid] = ini_text
        _write_text(os.path.join(app_dir, f"{v['name']}.theme"), ini_text)

        # C. Backup-first PowerShell installer
        ps1_text = _build_installer_ps1(v)
        _write_text(os.path.join(app_dir, f"install-{vid}.ps1"), ps1_text)

        # D. Desktop SVG preview pair (apps/ + docs/)
        svg = render_windows_preview(
            app_name,
            slug,
            v,
            accent_palette=spec["palette"],
            colorization_hex=spec["colorization"],
        )
        write_preview_pair(slug, vid, svg)

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        files.append({"label": f"{v['name']} Theme ({v['name']}.theme)", "path": f"apps/{slug}/{v['name']}.theme"})
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        files.append({"label": f"{v['name']} Installer (install-{vid}.ps1)", "path": f"apps/{slug}/install-{vid}.ps1"})
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        files.append({"label": f"{v['name']} Wallpaper 1080p", "path": f"apps/{slug}/wallpapers/{vid}-1080p.png"})
        files.append({"label": f"{v['name']} Wallpaper 4K", "path": f"apps/{slug}/wallpapers/{vid}-4k.png"})

    summaries = {
        "cyclorama-dawn": "Matte #050507 Windows 11 dark stage with Oklab Steel-to-Beacon floor wash, Beacon Orange (#F06E2B) DWM accent, and 8-slot Explorer AccentPalette.",
        "cyclorama-steel": "Deep Glacial Steel Windows 11 dark desktop with Oklab Steel wash, #1F547A DWM colorization, and luminous #74B8E8 accent highlights.",
        "cyclorama-day": "Crisp #F5F7F9 Alabaster Day Windows 11 light desktop with subtle frost Steel-to-Dawn floor wash and burnt Beacon (#AD3D0A) accents.",
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
        "primaryFile": "apps/windows/Cyclorama Dawn.theme",
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
                "file": f"apps/{slug}/{VARIANTS[vid]['name']}.theme",
                "copyLang": "ini",
                "copyLabel": f"Copy {VARIANTS[vid]['name']} Windows 11 .theme",
                "copySnippet": theme_texts[vid].rstrip("\n"),
                "swatches": _six_swatches(VARIANTS[vid]),
            }
            for vid in VARIANT_ORDER
        ],
    }
    _write_json(os.path.join(app_dir, "themes.json"), themes_json)

    readme = _render_readme(
        app_name=app_name,
        homepage=homepage,
        fmt=fmt,
        install_steps=install_steps,
        files=files,
        summaries=summaries,
    )
    _write_text(os.path.join(app_dir, "README.md"), readme)

    print(f"[ok] built apps/windows/ (3 .theme, 3 .ps1, 6 Oklab PNG wallpapers, 3 SVG preview pairs)")
    return {
        "slug": slug,
        "name": app_name,
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


if __name__ == "__main__":
    build()
