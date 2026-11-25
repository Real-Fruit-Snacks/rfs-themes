#!/usr/bin/env python3
"""Generate Cyclorama Dawn v2.1.0 extra Editor & IDE theme ports for rfs-themes.

Generates deterministic, WCAG AA calibrated ports (UTF-8, LF line endings) for:
  1. apps/notepad-plus-plus/  — Notepad++ 8.x XML themes + backup-first Dark Mode .ps1 appliers
  2. apps/python-idle/        — Python IDLE config-highlight.cfg + config-main-*.cfg
  3. apps/powershell-ise/     — Windows PowerShell ISE .StorableColorTheme.ps1xml + .ps1 installers

Zero external dependencies (Python 3.11+ standard library only).
All colors are derived from tools/rfs_palette.py (zero hardcoded hex literals).
"""
from __future__ import annotations

import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

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
    contrast,
    hex_to_rgb,
    mix,
)
from svg_previews import render_editor_preview, write_preview_pair  # noqa: E402

CATEGORY = "Editors & IDEs"
BRAND_REPO_URL = "https://github.com/Real-Fruit-Snacks/rfs-brand"


def _write_text(rel_path: str, content: str) -> str:
    """Write UTF-8 text with deterministic LF line endings."""
    abs_path = os.path.join(ROOT, *rel_path.split("/"))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    return abs_path


def _write_json(rel_path: str, data: object) -> str:
    return _write_text(rel_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _npp_hex(hx: str) -> str:
    """Convert #RRGGBB to 6-char uppercase RRGGBB without '#' for Notepad++ XML."""
    clean = hx.lstrip("#").upper()
    if len(clean) != 6 or any(ch not in "0123456789ABCDEF" for ch in clean):
        raise ValueError(f"Expected 6-char hex color, got {hx!r}")
    return clean


def _colorref(hx: str) -> int:
    """Return Win32 COLORREF integer: R + (G * 256) + (B * 65536)."""
    r, g, b = hex_to_rgb(hx)
    return r + (g << 8) + (b << 16)


def _srgb_to_linear_str(channel: int) -> str:
    """Convert 0..255 sRGB byte to WPF ScRGB linear float string."""
    if channel <= 0:
        return "0"
    if channel >= 255:
        return "1"
    s = channel / 255.0
    val = s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    if val < 1e-4:
        return f"{val:.7g}"
    return f"{val:.7f}".rstrip("0").rstrip(".")


def _swatches(v: dict) -> list[dict]:
    ui = v["ui"]
    return [
        {"label": "Background", "hex": ui["bg"]},
        {"label": "Surface", "hex": ui["surface"]},
        {"label": "Text", "hex": ui["text"]},
        {"label": "Accent", "hex": ui["accent"]},
        {"label": "Secondary", "hex": ui["secondary"]},
        {"label": "Signal", "hex": ui["signal"]},
    ]


def _manifest_entry(
    slug: str,
    name: str,
    homepage: str,
    fmt: str,
    install: str,
) -> dict:
    return {
        "slug": slug,
        "name": name,
        "category": CATEGORY,
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
                "summary": VARIANTS[vid]["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
            }
            for vid in VARIANT_ORDER
        ],
        "path": f"apps/{slug}",
        "data": f"apps/{slug}/themes.json",
    }


def _render_readme(
    app_name: str,
    slug: str,
    homepage: str,
    fmt: str,
    install_steps: list[str],
    variant_files: dict[str, str],
    extra_notes: str = "",
) -> str:
    brand_ver = VARIANTS["cyclorama-dawn"]["version"]
    lines = [
        f"# {BRAND_NAME} for {app_name}",
        "",
        f"Three **{BRAND_NAME} v{brand_ver} (Steel & Beacon Orange)** themes for "
        f"**[{app_name}]({homepage})**, built from [`Real-Fruit-Snacks/rfs-brand`]({BRAND_REPO_URL}) "
        f"with WCAG AA calibrated surfaces, syntax tokens, and editor chrome.",
        "",
        f"- **Category:** {CATEGORY}",
        f"- **Format:** `{fmt}`",
        f"- **Gallery:** [{GALLERY_URL}]({GALLERY_URL})",
        "",
        "## Install",
        "",
    ]
    for idx, step in enumerate(install_steps, 1):
        lines.append(f"{idx}. {step}")

    if extra_notes:
        lines.extend(["", extra_notes.strip()])

    lines.extend(
        [
            "",
            "## Variants",
            "",
            "| Variant | LX | Mode | Accent Role | Background | Accent | Secondary | File |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        ui = v["ui"]
        rel_in_app = variant_files[vid]
        href = quote(rel_in_app, safe="/")
        lines.append(
            f"| **{v['name']}** | `{v['lx']}` | `{v['mode']}` | {v['accentRole']} "
            f"| `{ui['bg']}` | `{ui['accent']}` | `{ui['secondary']}` "
            f"| [`{rel_in_app}`]({href}) |"
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
                f"![{v['name']} {app_name} preview](previews/{vid}.svg)",
                "",
            ]
        )

    lines.extend(
        [
            "## Regenerating",
            "",
            "```sh",
            "python tools/build_extras_editors.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


# =============================================================================
# 1. Notepad++ (XML Themes + Custom Dark Mode PowerShell Appliers)
# =============================================================================


def _npp_words_style(
    name: str,
    style_id: int,
    fg: str,
    bg: str,
    font_style: int = 0,
    keyword_class: str | None = None,
    font_name: str = "",
    font_size: str = "",
) -> str:
    attrs = [
        f'name="{xml_escape(name)}"',
        f'styleID="{style_id}"',
        f'fgColor="{_npp_hex(fg)}"',
        f'bgColor="{_npp_hex(bg)}"',
        f'fontName="{xml_escape(font_name)}"',
        f'fontStyle="{font_style}"',
        f'fontSize="{xml_escape(font_size)}"',
    ]
    if keyword_class:
        attrs.append(f'keywordClass="{xml_escape(keyword_class)}"')
    return f"            <WordsStyle {' '.join(attrs)} />"


def _npp_widget_style(
    name: str,
    style_id: int,
    fg: str | None = None,
    bg: str | None = None,
    font_name: str | None = None,
    font_style: int | None = None,
    font_size: str | None = None,
) -> str:
    attrs = [f'name="{xml_escape(name)}"', f'styleID="{style_id}"']
    if fg is not None:
        attrs.append(f'fgColor="{_npp_hex(fg)}"')
    if bg is not None:
        attrs.append(f'bgColor="{_npp_hex(bg)}"')
    if font_name is not None:
        attrs.append(f'fontName="{xml_escape(font_name)}"')
    if font_style is not None:
        attrs.append(f'fontStyle="{font_style}"')
    if font_size is not None:
        attrs.append(f'fontSize="{xml_escape(font_size)}"')
    return f"        <WidgetStyle {' '.join(attrs)} />"


def _npp_c_like_styles(
    ui: dict,
    syn: dict,
    *,
    include_raw: bool = False,
    include_window_inst: bool = False,
    window_kc: str | None = None,
    include_preprocessor: bool = True,
) -> list[tuple[str, int, str, str, int, str | None]]:
    bg = ui["bg"]
    rows: list[tuple[str, int, str, str, int, str | None]] = []
    if include_preprocessor:
        rows.append(("PREPROCESSOR", 9, syn["constant"], bg, 0, None))
    rows.extend([
        ("DEFAULT", 11, ui["text"], bg, 0, None),
        ("INSTRUCTION WORD", 5, syn["keyword"], bg, 1, "instre1"),
        ("TYPE WORD", 16, syn["type"], bg, 0, "type1"),
    ])
    if include_window_inst:
        rows.append(("WINDOW INSTRUCTION", 19, syn["function"], bg, 1, window_kc))
    rows.extend([
        ("NUMBER", 4, syn["number"], bg, 0, None),
        ("STRING", 6, syn["string"], bg, 0, None),
    ])
    if include_raw:
        raw_name = "STRING RAW" if include_window_inst else "STRINGRAW"
        rows.append((raw_name, 20, syn["string"], bg, 0, None))
    rows.extend([
        ("CHARACTER", 7, syn["string"], bg, 0, None),
        ("OPERATOR", 10, syn["operator"], bg, 1, None),
        ("VERBATIM", 13, syn["string"], bg, 0, None),
        ("REGEX", 14, syn["constant"], bg, 1, None),
        ("COMMENT", 1, syn["comment"], bg, 2, None),
        ("COMMENT LINE", 2, syn["comment"], bg, 2, None),
        ("COMMENT DOC", 3, syn["comment"], bg, 2, None),
        ("COMMENT LINE DOC", 15, syn["comment"], bg, 2, None),
        ("COMMENT DOC KEYWORD", 17, syn["property"], bg, 3, None),
        ("COMMENT DOC KEYWORD ERROR", 18, ui["fault"], bg, 2, None),
    ])
    if include_preprocessor:
        rows.extend([
            ("PREPROCESSOR COMMENT", 23, syn["comment"], bg, 2, None),
            ("PREPROCESSOR COMMENT DOC", 24, syn["comment"], bg, 2, None),
        ])
    for idx in range(1, 9):
        color = syn["function"] if idx % 2 == 1 else syn["type"]
        rows.append((f"USER KEYWORDS {idx}", 127 + idx, color, bg, 1, f"substyle{idx}"))
    return rows


def _npp_theme_xml(v: dict) -> str:
    ui = v["ui"]
    syn = v["syntax"]
    bg = ui["bg"]

    mark_1 = mix(ui["surface"], ui["signal"], 0.34)
    mark_2 = mix(ui["surface"], ui["warning"], 0.34)
    mark_3 = mix(ui["surface"], ui["fault"], 0.34)
    mark_4 = mix(ui["surface"], ui["secondary"], 0.34)
    mark_5 = mix(ui["surface"], ui["magenta"], 0.34)

    # 19 authentic Notepad++ 8.x LexerTypes matching Scintilla styleIDs & keywordClasses
    lexers: list[tuple[str, str, str, list[tuple[str, int, str, str, int, str | None]]]] = [
        ("c", "C", "", _npp_c_like_styles(ui, syn)),
        ("cpp", "C++", "", _npp_c_like_styles(ui, syn, include_raw=True)),
        ("cs", "C#", "", _npp_c_like_styles(ui, syn)),
        (
            "rust",
            "Rust",
            "",
            [
                ("DEFAULT", 32, ui["text"], bg, 0, None),
                ("WHITESPACE", 0, ui["subtle"], bg, 0, None),
                ("BLOCK COMMENT", 1, syn["comment"], bg, 2, None),
                ("LINE COMMENT", 2, syn["comment"], bg, 2, None),
                ("BLOCK DOC COMMENT", 3, syn["comment"], bg, 2, None),
                ("LINE DOC COMMENT", 4, syn["comment"], bg, 2, None),
                ("NUMBER", 5, syn["number"], bg, 0, None),
                ("KEYWORDS 1", 6, syn["keyword"], bg, 1, "instre1"),
                ("KEYWORDS 2", 7, syn["type"], bg, 1, "instre2"),
                ("KEYWORDS 3", 8, syn["function"], bg, 0, "type1"),
                ("KEYWORDS 4", 9, syn["type"], bg, 0, "type2"),
                ("KEYWORDS 5", 10, syn["constant"], bg, 0, "type3"),
                ("KEYWORDS 6", 11, syn["property"], bg, 2, "type4"),
                ("KEYWORDS 7", 12, syn["parameter"], bg, 2, "type5"),
                ("REGULAR STRING", 13, syn["string"], bg, 0, None),
                ("RAW STRING", 14, syn["string"], bg, 0, None),
                ("CHARACTER", 15, syn["string"], bg, 0, None),
                ("OPERATOR", 16, syn["operator"], bg, 1, None),
                ("IDENTIFIER", 17, ui["text"], bg, 0, None),
                ("LIFETIME", 18, syn["parameter"], bg, 2, None),
                ("MACRO", 19, syn["function"], bg, 1, None),
                ("LEXICAL ERROR", 20, ui["fault"], ui["diff_del_bg"], 1, None),
                ("BYTE STRING", 21, syn["string"], bg, 2, None),
                ("RAW BYTE STRING", 22, syn["string"], bg, 2, None),
                ("BYTE CHARACTER", 23, syn["string"], bg, 0, None),
                ("C STRING", 24, syn["string"], bg, 0, None),
                ("RAW C STRING", 25, syn["string"], bg, 0, None),
            ],
        ),
        (
            "python",
            "Python",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("COMMENT LINE", 1, syn["comment"], bg, 2, None),
                ("NUMBER", 2, syn["number"], bg, 0, None),
                ("STRING", 3, syn["string"], bg, 0, None),
                ("CHARACTER", 4, syn["string"], bg, 0, None),
                ("KEYWORDS", 5, syn["keyword"], bg, 1, "instre1"),
                ("TRIPLE", 6, syn["string"], bg, 0, None),
                ("TRIPLE DOUBLE", 7, syn["string"], bg, 0, None),
                ("CLASS NAME", 8, syn["type"], bg, 1, None),
                ("DEF NAME", 9, syn["function"], bg, 1, None),
                ("OPERATOR", 10, syn["operator"], bg, 1, None),
                ("IDENTIFIER", 11, ui["text"], bg, 0, None),
                ("COMMENT BLOCK", 12, syn["comment"], bg, 2, None),
                ("BUILTINS", 14, syn["type"], bg, 0, "instre2"),
                ("DECORATOR", 15, syn["constant"], bg, 2, None),
                ("ATTRIBUTE", 20, syn["property"], bg, 0, None),
                ("F STRING", 16, syn["string"], bg, 0, None),
                ("F CHARACTER", 17, syn["string"], bg, 0, None),
                ("F TRIPLE", 18, syn["string"], bg, 0, None),
                ("F TRIPLEDOUBLE", 19, syn["string"], bg, 0, None),
                *[
                    (f"USER KEYWORDS {i}", 127 + i, syn["function"] if i % 2 else syn["property"], bg, 1, f"substyle{i}")
                    for i in range(1, 9)
                ],
            ],
        ),
        (
            "powershell",
            "PowerShell",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("COMMENT", 1, syn["comment"], bg, 2, None),
                ("STRING", 2, syn["string"], bg, 0, None),
                ("CHARACTER", 3, syn["string"], bg, 0, None),
                ("NUMBER", 4, syn["number"], bg, 0, None),
                ("VARIABLE", 5, syn["parameter"], bg, 1, None),
                ("OPERATOR", 6, syn["operator"], bg, 1, None),
                ("IDENTIFIER", 7, ui["text"], bg, 0, None),
                ("INSTRUCTION WORD", 8, syn["keyword"], bg, 1, "instre1"),
                ("CMDLET", 9, syn["function"], bg, 0, "instre2"),
                ("ALIAS", 10, syn["type"], bg, 0, "type1"),
                ("FUNCTION", 11, syn["function"], bg, 0, "type2"),
                ("USER KEYWORDS", 12, syn["constant"], bg, 0, "type3"),
                ("COMMENT STREAM", 13, syn["comment"], bg, 2, None),
                ("HERE STRING", 14, syn["string"], bg, 0, None),
                ("HERE CHARACTER", 15, syn["string"], bg, 0, None),
                ("COMMENT DOC KEYWORD", 16, syn["property"], bg, 1, "type4"),
            ],
        ),
        (
            "bash",
            "bash",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("ERROR", 1, ui["fault"], ui["diff_del_bg"], 1, None),
                ("INSTRUCTION WORD", 4, syn["keyword"], bg, 1, "instre1"),
                ("NUMBER", 3, syn["number"], bg, 0, None),
                ("STRING", 5, syn["string"], bg, 0, None),
                ("CHARACTER", 6, syn["string"], bg, 0, None),
                ("OPERATOR", 7, syn["operator"], bg, 1, None),
                ("IDENTIFIER", 8, ui["text"], bg, 0, None),
                ("SCALAR", 9, syn["parameter"], bg, 1, None),
                ("COMMENT LINE", 2, syn["comment"], bg, 2, None),
                ("PARAM", 10, syn["property"], bg, 0, None),
                ("BACKTICKS", 11, syn["function"], bg, 1, None),
                ("HERE DELIM", 12, syn["constant"], bg, 1, None),
                ("HERE Q", 13, syn["string"], bg, 2, None),
                *[
                    (f"USER KEYWORDS {i}", 127 + i, syn["keyword"], bg, 1, f"substyle{i}")
                    for i in range(1, 5)
                ],
                *[
                    (f"USER SCALAR {i}", 131 + i, syn["parameter"], bg, 1, f"substyle{i + 4}")
                    for i in range(1, 5)
                ],
            ],
        ),
        (
            "javascript.js",
            "JavaScript",
            "",
            _npp_c_like_styles(
                ui,
                syn,
                include_raw=True,
                include_window_inst=True,
                window_kc="instre2",
                include_preprocessor=False,
            ),
        ),
        (
            "typescript",
            "TypeScript",
            "",
            _npp_c_like_styles(
                ui,
                syn,
                include_raw=True,
                include_window_inst=True,
                window_kc=None,
                include_preprocessor=False,
            ),
        ),
        (
            "json",
            "JSON",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("NUMBER", 1, syn["number"], bg, 0, None),
                ("STRING", 2, syn["string"], bg, 0, None),
                ("STRING EOL", 3, ui["fault"], ui["diff_del_bg"], 0, None),
                ("PROPERTY NAME", 4, syn["property"], bg, 0, None),
                ("ESCAPE SEQUENCE", 5, syn["constant"], bg, 1, None),
                ("LINE COMMENT", 6, syn["comment"], bg, 2, None),
                ("BLOCK COMMENT", 7, syn["comment"], bg, 2, None),
                ("OPERATOR", 8, syn["punctuation"], bg, 0, None),
                ("URI", 9, ui["accent"], bg, 0, None),
                ("COMPACT IRI", 10, syn["type"], bg, 1, None),
                ("KEYWORD", 11, syn["keyword"], bg, 1, "instre1"),
                ("LD KEYWORD", 12, syn["constant"], bg, 0, "instre2"),
                ("ERROR", 13, ui["fault"], ui["diff_del_bg"], 1, None),
            ],
        ),
        (
            "yaml",
            "YAML",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("IDENTIFIER", 2, syn["property"], bg, 1, None),
                ("COMMENT", 1, syn["comment"], bg, 2, None),
                ("INSTRUCTION WORD", 3, syn["keyword"], bg, 1, "instre1"),
                ("NUMBER", 4, syn["number"], bg, 0, None),
                ("REFERENCE", 5, syn["constant"], bg, 0, None),
                ("DOCUMENT", 6, syn["function"], bg, 1, None),
                ("TEXT", 7, syn["string"], bg, 0, None),
                ("ERROR", 8, ui["fault"], ui["diff_del_bg"], 2, None),
            ],
        ),
        (
            "html",
            "HTML",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("COMMENT", 9, syn["comment"], bg, 2, None),
                ("NUMBER", 5, syn["number"], bg, 0, None),
                ("DOUBLE STRING", 6, syn["string"], bg, 0, None),
                ("SINGLE STRING", 7, syn["string"], bg, 0, None),
                ("TAG", 1, syn["tag"], bg, 0, "instre1"),
                ("TAG END", 11, syn["tag"], bg, 0, None),
                ("TAG UNKNOWN", 2, ui["warning"], bg, 0, None),
                ("ATTRIBUTE", 3, syn["property"], bg, 0, None),
                ("ATTRIBUTE UNKNOWN", 4, syn["parameter"], bg, 2, None),
                ("SGML DEFAULT", 21, ui["text_soft"], bg, 0, None),
                ("SGML COMMAND", 22, syn["keyword"], bg, 1, "instre2"),
                ("SGML 1ST PARAM", 23, syn["type"], bg, 0, None),
                ("SGML DOUBLESTRING", 24, syn["string"], bg, 0, None),
                ("SGML SIMPLESTRING", 25, syn["string"], bg, 0, None),
                ("SGML BLOCK DEFAULT", 31, ui["mute"], bg, 0, None),
                ("CDATA", 17, syn["string"], bg, 0, None),
                ("VALUE", 19, syn["string"], bg, 0, None),
                ("ENTITY", 10, syn["constant"], bg, 2, None),
                *[
                    (f"USER TAGS {i}", 191 + i, syn["tag"], bg, 0, f"substyle{i}")
                    for i in range(1, 5)
                ],
                *[
                    (f"USER ATTRIBUTES {i}", 195 + i, syn["property"], bg, 1, f"substyle{i + 4}")
                    for i in range(1, 5)
                ],
            ],
        ),
        (
            "css",
            "CSS",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("TAG", 1, syn["tag"], bg, 0, None),
                ("CLASS", 2, syn["function"], bg, 0, None),
                ("PSEUDOCLASS", 3, syn["constant"], bg, 1, "instre2"),
                ("UNKNOWN PSEUDOCLASS", 4, ui["warning"], bg, 0, None),
                ("OPERATOR", 5, syn["punctuation"], bg, 1, None),
                ("IDENTIFIER", 6, syn["property"], bg, 0, "instre1"),
                ("UNKNOWN IDENTIFIER", 7, syn["parameter"], bg, 0, None),
                ("VALUE", 8, syn["string"], bg, 0, None),
                ("COMMENT", 9, syn["comment"], bg, 2, None),
                ("ID", 10, syn["type"], bg, 1, None),
                ("IMPORTANT", 11, ui["fault"], bg, 1, None),
                ("DIRECTIVE", 12, syn["keyword"], bg, 1, None),
                ("DOUBLE STRING", 13, syn["string"], bg, 0, None),
                ("SINGLE STRING", 14, syn["string"], bg, 0, None),
                ("ATTRIBUTE", 16, syn["property"], bg, 0, None),
                ("PSEUDOELEMENT", 18, syn["constant"], bg, 0, "type3"),
                ("LEGACY PSEUDOELEMENT", 20, syn["constant"], bg, 0, "type5"),
                ("MEDIA", 22, syn["keyword"], bg, 1, None),
                ("VARIABLE", 23, syn["parameter"], bg, 0, None),
            ],
        ),
        (
            "xml",
            "XML",
            "",
            [
                ("XMLSTART", 12, syn["keyword"], bg, 1, None),
                ("XMLEND", 13, syn["keyword"], bg, 1, None),
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("COMMENT", 9, syn["comment"], bg, 2, None),
                ("NUMBER", 5, syn["number"], bg, 0, None),
                ("DOUBLE STRING", 6, syn["string"], bg, 0, None),
                ("SINGLE STRING", 7, syn["string"], bg, 0, None),
                ("TAG", 1, syn["tag"], bg, 0, None),
                ("TAG END", 11, syn["tag"], bg, 0, None),
                ("TAG UNKNOWN", 2, ui["warning"], bg, 0, None),
                ("ATTRIBUTE", 3, syn["property"], bg, 0, None),
                ("ATTRIBUTE UNKNOWN", 4, syn["parameter"], bg, 2, None),
                ("SGML DEFAULT", 21, ui["text_soft"], bg, 0, None),
                ("SGML COMMAND", 22, syn["keyword"], bg, 1, "instre1"),
                ("SGML 1ST PARAM", 23, syn["type"], bg, 0, None),
                ("SGML DOUBLESTRING", 24, syn["string"], bg, 0, None),
                ("SGML SIMPLESTRING", 25, syn["string"], bg, 0, None),
                ("SGML BLOCK DEFAULT", 31, ui["mute"], bg, 0, None),
                ("CDATA", 17, syn["string"], bg, 0, None),
                ("ENTITY", 10, syn["constant"], bg, 2, None),
                *[
                    (f"USER ATTRIBUTES {i}", 191 + i, syn["property"], bg, 1, f"substyle{i}")
                    for i in range(1, 9)
                ],
            ],
        ),
        (
            "markdown",
            "Markdown",
            "md markdown",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("LINE BEGIN", 1, ui["text"], bg, 0, None),
                ("STRONG 1", 2, ui["text"], bg, 1, None),
                ("STRONG 2", 3, ui["text"], bg, 1, None),
                ("EM 1", 4, ui["text_soft"], bg, 2, None),
                ("EM 2", 5, ui["text_soft"], bg, 2, None),
                ("HEADER 1", 6, syn["function"], bg, 1, None),
                ("HEADER 2", 7, syn["function"], bg, 1, None),
                ("HEADER 3", 8, syn["keyword"], bg, 1, None),
                ("HEADER 4", 9, syn["keyword"], bg, 1, None),
                ("HEADER 5", 10, syn["type"], bg, 1, None),
                ("HEADER 6", 11, syn["property"], bg, 1, None),
                ("PRECHAR", 12, syn["punctuation"], bg, 0, None),
                ("ULIST ITEM", 13, syn["function"], bg, 1, None),
                ("OLIST ITEM", 14, syn["number"], bg, 1, None),
                ("BLOCKQUOTE", 15, syn["comment"], bg, 2, None),
                ("STRIKEOUT", 16, ui["mute"], bg, 0, None),
                ("HRULE", 17, ui["subtle"], bg, 1, None),
                ("LINK", 18, syn["keyword"], bg, 0, None),
                ("CODE", 19, syn["string"], ui["code_bg"], 0, None),
                ("CODE 2", 20, syn["string"], ui["code_bg"], 0, None),
                ("CODE BLOCK", 21, syn["string"], ui["code_bg"], 0, None),
            ],
        ),
        (
            "sql",
            "SQL",
            "",
            [
                ("KEYWORD", 5, syn["keyword"], bg, 1, "instre1"),
                ("USER1", 16, syn["type"], bg, 1, "instre2"),
                ("KEYWORD2", 19, syn["function"], bg, 1, "type3"),
                ("NUMBER", 4, syn["number"], bg, 0, None),
                ("STRING", 6, syn["string"], bg, 0, None),
                ("STRING2", 7, syn["string"], bg, 0, None),
                ("OPERATOR", 10, syn["operator"], bg, 1, None),
                ("COMMENT", 1, syn["comment"], bg, 2, None),
                ("COMMENT LINE", 2, syn["comment"], bg, 2, None),
                ("COMMENT DOC", 3, syn["comment"], bg, 2, None),
                ("Q OPERATOR", 24, syn["constant"], bg, 0, None),
            ],
        ),
        (
            "ini",
            "ini file",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("COMMENT", 1, syn["comment"], bg, 2, None),
                ("SECTION", 2, syn["function"], bg, 1, None),
                ("ASSIGNMENT", 3, syn["operator"], bg, 1, None),
                ("DEFVAL", 4, syn["string"], bg, 0, None),
                ("KEY", 5, syn["property"], bg, 0, None),
            ],
        ),
        (
            "diff",
            "DIFF",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("COMMENT", 1, syn["comment"], bg, 2, None),
                ("COMMAND", 2, syn["keyword"], bg, 1, None),
                ("HEADER", 3, syn["function"], ui["surface"], 1, None),
                ("POSITION", 4, syn["diff_change"], ui["diff_chg_bg"], 1, None),
                ("DELETED", 5, syn["diff_del"], ui["diff_del_bg"], 0, None),
                ("ADDED", 6, syn["diff_add"], ui["diff_add_bg"], 0, None),
            ],
        ),
        (
            "batch",
            "Batch",
            "",
            [
                ("DEFAULT", 0, ui["text"], bg, 0, None),
                ("COMMENT", 1, syn["comment"], bg, 2, None),
                ("KEYWORDS", 2, syn["keyword"], bg, 1, "instre1"),
                ("LABEL", 3, syn["function"], bg, 1, None),
                ("HIDE SYMBOL", 4, syn["punctuation"], bg, 0, None),
                ("COMMAND", 5, syn["type"], bg, 0, None),
                ("VARIABLE", 6, syn["parameter"], bg, 1, None),
                ("OPERATOR", 7, syn["operator"], bg, 1, None),
                ("AFTER LABEL", 8, syn["comment"], bg, 2, None),
            ],
        ),
    ]

    lines = [
        '<?xml version="1.0" encoding="UTF-8" ?>',
        f"<!-- {v['name']} ({v['lx']} {v['mode'].upper()}) for Notepad++ 8.x · {BRAND_NAME} v{v['version']} -->",
        "<NotepadPlus>",
        "    <LexerStyles>",
    ]
    for lname, ldesc, lext, styles in lexers:
        lines.append(
            f'        <LexerType name="{xml_escape(lname)}" desc="{xml_escape(ldesc)}" ext="{xml_escape(lext)}">'
        )
        for sname, sid, fg, sbg, fstyle, kc in styles:
            lines.append(_npp_words_style(sname, sid, fg, sbg, fstyle, kc))
        lines.append("        </LexerType>")
    lines.append("    </LexerStyles>")

    global_widgets = [
        _npp_widget_style("Global override", 0, fg=ui["text"], bg=bg, font_name="Consolas", font_style=0, font_size=""),
        _npp_widget_style("Default Style", 32, fg=ui["text"], bg=bg, font_name="Consolas", font_style=0, font_size="10"),
        _npp_widget_style("Indent guideline style", 37, fg=ui["border"], bg=bg, font_name="", font_style=0, font_size=""),
        _npp_widget_style("Brace highlight style", 34, fg=ui["accent"], bg=ui["raised"], font_name="", font_style=1, font_size=""),
        _npp_widget_style("Bad brace colour", 35, fg=ui["fault"], bg=ui["diff_del_bg"], font_name="", font_style=1, font_size=""),
        _npp_widget_style("Current line background colour", 0, bg=ui["raised"]),
        _npp_widget_style("Selected text colour", 0, fg=ui["text"], bg=ui["selection_active"]),
        _npp_widget_style("Multi-selected text color", 0, bg=ui["selection_bg"]),
        _npp_widget_style("Caret colour", 2069, fg=ui["cursor"]),
        _npp_widget_style("Multi-edit carets color", 0, fg=ui["secondary"]),
        _npp_widget_style("Edge colour", 0, fg=ui["border_subtle"]),
        _npp_widget_style("Line number margin", 33, fg=ui["subtle"], bg=ui["surface"], font_name="", font_style=0, font_size=""),
        _npp_widget_style("Bookmark margin", 0, bg=ui["surface"]),
        _npp_widget_style("Change History margin", 0, bg=ui["surface"]),
        _npp_widget_style("Change History modified", 0, fg=ui["accent"], bg=ui["accent"]),
        _npp_widget_style("Change History revert modified", 0, fg=ui["warning"], bg=ui["warning"]),
        _npp_widget_style("Change History revert origin", 0, fg=ui["secondary"], bg=ui["secondary"]),
        _npp_widget_style("Change History saved", 0, fg=ui["signal"], bg=ui["signal"]),
        _npp_widget_style("Fold", 0, fg=ui["mute"], bg=ui["surface"]),
        _npp_widget_style("Fold active", 0, fg=ui["accent"]),
        _npp_widget_style("Fold margin", 0, fg=ui["surface"], bg=ui["rail"]),
        _npp_widget_style("White space symbol", 0, fg=ui["border_strong"]),
        _npp_widget_style("Smart Highlighting", 29, bg=ui["steel_wash"]),
        _npp_widget_style("Find Mark Style", 31, bg=ui["find_match"]),
        _npp_widget_style("Find status: Not found", 0, fg=ui["fault"]),
        _npp_widget_style("Find status: Message", 0, fg=ui["secondary"]),
        _npp_widget_style("Find status: Search end reached", 0, fg=ui["signal"]),
        _npp_widget_style("Mark Style 1", 25, bg=mark_1),
        _npp_widget_style("Mark Style 2", 24, bg=mark_2),
        _npp_widget_style("Mark Style 3", 23, bg=mark_3),
        _npp_widget_style("Mark Style 4", 22, bg=mark_4),
        _npp_widget_style("Mark Style 5", 21, bg=mark_5),
        _npp_widget_style("Incremental highlight all", 28, bg=ui["find_match"]),
        _npp_widget_style("Tags match highlighting", 27, bg=ui["selection_bg"]),
        _npp_widget_style("Tags attribute", 26, bg=ui["raised"]),
        _npp_widget_style("Active tab focused indicator", 0, fg=ui["accent"]),
        _npp_widget_style("Active tab unfocused indicator", 0, fg=ui["secondary"]),
        _npp_widget_style("Active tab text", 0, fg=ui["text"]),
        _npp_widget_style("Inactive tabs", 0, fg=ui["mute"], bg=ui["rail"]),
        _npp_widget_style("URL hovered", 0, fg=ui["accent"]),
        _npp_widget_style("Document map", 0, fg=ui["text"], bg=ui["surface"]),
        _npp_widget_style("EOL custom color", 0, fg=ui["subtle"]),
        _npp_widget_style("Non-printing characters custom color", 0, fg=ui["border_strong"]),
    ]

    lines.append("    <GlobalStyles>")
    lines.extend(global_widgets)
    lines.append("    </GlobalStyles>")
    lines.append("</NotepadPlus>")
    return "\n".join(lines) + "\n"


def _npp_copy_snippet(v: dict) -> str:
    ui = v["ui"]
    bg = ui["bg"]
    snippet_lines = [
        '<?xml version="1.0" encoding="UTF-8" ?>',
        "<NotepadPlus>",
        "    <GlobalStyles>",
        _npp_widget_style("Default Style", 32, fg=ui["text"], bg=bg, font_name="Consolas", font_style=0, font_size="10"),
        _npp_widget_style("Current line background colour", 0, bg=ui["raised"]),
        _npp_widget_style("Selected text colour", 0, fg=ui["text"], bg=ui["selection_active"]),
        _npp_widget_style("Caret colour", 2069, fg=ui["cursor"]),
        _npp_widget_style("Line number margin", 33, fg=ui["subtle"], bg=ui["surface"]),
        _npp_widget_style("Brace highlight style", 34, fg=ui["accent"], bg=ui["raised"], font_style=1),
        _npp_widget_style("Smart Highlighting", 29, bg=ui["steel_wash"]),
        _npp_widget_style("Find Mark Style", 31, bg=ui["find_match"]),
        _npp_widget_style("Active tab focused indicator", 0, fg=ui["accent"]),
        _npp_widget_style("URL hovered", 0, fg=ui["accent"]),
        "    </GlobalStyles>",
        "</NotepadPlus>",
    ]
    return "\n".join(snippet_lines)


def _npp_apply_ps1(v: dict) -> str:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    theme_xml = f"{v['name']}.xml"

    dark_attrs = {
        "enable": "yes",
        "enableWindowsMode": "no",
        "colorTone": "32",
        "customColorTop": str(_colorref(ui["rail"])),
        "customColorMenuHotTrack": str(_colorref(ui["raised"])),
        "customColorActive": str(_colorref(ui["surface"])),
        "customColorMain": str(_colorref(ui["bg"])),
        "customColorError": str(_colorref(ui["fault_fill"])),
        "customColorText": str(_colorref(ui["text"])),
        "customColorDarkText": str(_colorref(ui["mute"])),
        "customColorDisabledText": str(_colorref(ui["subtle"])),
        "customColorLinkText": str(_colorref(ui["accent"])),
        "customColorEdge": str(_colorref(ui["border"])),
        "customColorHotEdge": str(_colorref(ui["accent"])),
        "customColorDisabledEdge": str(_colorref(ui["border_subtle"])),
        "darkThemeName": theme_xml,
        "darkTbFluentColor": "9",
        "darkTbFluentCustomColor": str(_colorref(ui["accent"])),
    }

    light_attrs = {
        "enable": "no",
        "enableWindowsMode": "no",
        "lightThemeName": theme_xml,
        "lightTbFluentColor": "9",
        "lightTbFluentCustomColor": str(_colorref(ui["accent"])),
    }

    attrs = dark_attrs if is_dark else light_attrs
    attr_lines = "\n".join(
        f"    '{k}' = '{val}'" for k, val in attrs.items()
    )

    styler_block = ""
    if not is_dark:
        styler_block = """
$StylerNode = $GuiConfigs.SelectSingleNode("GUIConfig[@name='stylerTheme']")
if ($null -eq $StylerNode) {
    $StylerNode = $Doc.CreateElement('GUIConfig')
    [void]$StylerNode.SetAttribute('name', 'stylerTheme')
    [void]$GuiConfigs.AppendChild($StylerNode)
}
$ActiveThemePath = Join-Path $ThemesDir $ThemeFileName
[void]$StylerNode.SetAttribute('path', $ActiveThemePath)
"""

    return f"""<#
.SYNOPSIS
    Apply {v['name']} ({v['lx']} {v['mode'].upper()}) to Notepad++ 8.x.
.DESCRIPTION
    Copies all three Cyclorama Dawn XML themes into %APPDATA%\\Notepad++\\themes\\,
    creates a one-time backup of config.xml (config.xml.pre-rfs.bak), and configures
    Notepad++ DarkMode{' Custom Tone (colorTone="32")' if is_dark else ' (Light mode + stylerTheme)'}.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ThemeName = '{v['name']}'
$ThemeFileName = '{theme_xml}'
$AllThemes = @('Cyclorama Dawn.xml', 'Cyclorama Steel.xml', 'Cyclorama Day.xml')

$NppDir = Join-Path $env:APPDATA 'Notepad++'
$ThemesDir = Join-Path $NppDir 'themes'
$ConfigPath = Join-Path $NppDir 'config.xml'
$BackupPath = Join-Path $NppDir 'config.xml.pre-rfs.bak'

$Running = Get-Process -Name 'notepad++' -ErrorAction SilentlyContinue
if ($null -ne $Running) {{
    Write-Warning '[!] Notepad++ is currently running. Close Notepad++ before applying so it does not overwrite config.xml on exit, or re-run this script after closing Notepad++.'
}}

if (-not (Test-Path -LiteralPath $ThemesDir)) {{
    New-Item -ItemType Directory -Path $ThemesDir -Force | Out-Null
}}

$Copied = 0
foreach ($File in $AllThemes) {{
    $Src = Join-Path $PSScriptRoot $File
    if (Test-Path -LiteralPath $Src) {{
        Copy-Item -LiteralPath $Src -Destination (Join-Path $ThemesDir $File) -Force
        $Copied++
    }}
}}
Write-Host "[ok] Copied $Copied Cyclorama XML theme(s) into $ThemesDir"

if (-not (Test-Path -LiteralPath $ConfigPath)) {{
    Write-Warning "[!] $ConfigPath not found. Launch Notepad++ once to initialize config.xml, then select '$ThemeName' in Settings -> Style Configurator."
    return
}}

if (-not (Test-Path -LiteralPath $BackupPath)) {{
    Copy-Item -LiteralPath $ConfigPath -Destination $BackupPath -Force
    Write-Host "[ok] Created one-time backup: $BackupPath"
}} else {{
    Write-Host "[i]  Preserving existing backup: $BackupPath"
}}

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$RawXml = [System.IO.File]::ReadAllText($ConfigPath, $Utf8NoBom)
$Doc = New-Object System.Xml.XmlDocument
$Doc.PreserveWhitespace = $true
$Doc.LoadXml($RawXml)

$GuiConfigs = $Doc.SelectSingleNode('/NotepadPlus/GUIConfigs')
if ($null -eq $GuiConfigs) {{
    throw "Could not find <GUIConfigs> in $ConfigPath"
}}

$DarkModeNode = $GuiConfigs.SelectSingleNode("GUIConfig[@name='DarkMode']")
if ($null -eq $DarkModeNode) {{
    $DarkModeNode = $Doc.CreateElement('GUIConfig')
    [void]$DarkModeNode.SetAttribute('name', 'DarkMode')
    [void]$GuiConfigs.AppendChild($DarkModeNode)
}}

$DarkModeAttrs = [ordered]@{{
{attr_lines}
}}

foreach ($Key in $DarkModeAttrs.Keys) {{
    [void]$DarkModeNode.SetAttribute($Key, $DarkModeAttrs[$Key])
}}
{styler_block}
$Settings = New-Object System.Xml.XmlWriterSettings
$Settings.Encoding = $Utf8NoBom
$Settings.Indent = $true
$Settings.OmitXmlDeclaration = $false

$Writer = [System.Xml.XmlWriter]::Create($ConfigPath, $Settings)
try {{
    $Doc.Save($Writer)
}} finally {{
    $Writer.Dispose()
}}

Write-Host "[ok] Applied '$ThemeName' to $ConfigPath"
Write-Host "[i]  Launch (or restart) Notepad++ to see $ThemeName in full effect."
"""


def build_notepad_plus_plus() -> dict:
    slug = "notepad-plus-plus"
    app_name = "Notepad++"
    homepage = "https://notepad-plus-plus.org/"
    fmt = "Notepad++ XML + Dark Mode .ps1"
    install = "Run apply-cyclorama-dawn.ps1 (copies XMLs + sets Custom Dark Mode) or copy *.xml to %APPDATA%\\Notepad++\\themes\\"
    install_steps = [
        "Close Notepad++ so it does not overwrite `config.xml` on exit.",
        "Run `powershell -ExecutionPolicy Bypass -File apps/notepad-plus-plus/apply-cyclorama-dawn.ps1` (or `steel` / `day`). The script copies all three `.xml` files into `%APPDATA%\\Notepad++\\themes\\`, writes a one-time `config.xml.pre-rfs.bak` backup, and configures Notepad++ 8.x Custom Dark Mode (`colorTone=\"32\"`) or Day light mode.",
        "Alternatively, copy `Cyclorama Dawn.xml`, `Cyclorama Steel.xml`, and `Cyclorama Day.xml` into `%APPDATA%\\Notepad++\\themes\\` and select the theme in **Settings -> Style Configurator**.",
    ]

    ver = VARIANTS["cyclorama-dawn"]["version"]
    files: list[dict[str, str]] = []
    theme_entries: list[dict] = []
    variant_files: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        xml_in_app = f"{v['name']}.xml"
        xml_repo = f"apps/{slug}/{xml_in_app}"
        ps1_in_app = f"apply-{vid}.ps1"
        ps1_repo = f"apps/{slug}/{ps1_in_app}"

        variant_files[vid] = xml_in_app
        _write_text(xml_repo, _npp_theme_xml(v))
        _write_text(ps1_repo, _npp_apply_ps1(v))

        svg = render_editor_preview(
            app_name,
            slug,
            v,
            active_file="config.xml",
            footer_left="XML  ·  UTF-8  ·  CRLF",
        )
        write_preview_pair(slug, vid, svg)

        files.append({"label": f"{v['name']} Theme XML ({xml_in_app})", "path": xml_repo})
        files.append({"label": f"{v['name']} PowerShell Applier ({ps1_in_app})", "path": ps1_repo})
        theme_entries.append(
            {
                "id": vid,
                "name": v["name"],
                "lx": v["lx"],
                "mode": v["mode"],
                "accentRole": v["accentRole"],
                "tagline": v["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": xml_repo,
                "copyLang": "xml",
                "copyLabel": "Notepad++ GlobalStyles XML snippet",
                "copySnippet": _npp_copy_snippet(v),
                "swatches": _swatches(v),
            }
        )

    themes_json = {
        "app": app_name,
        "slug": slug,
        "category": CATEGORY,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": f"apps/{slug}/Cyclorama Dawn.xml",
        "files": files,
        "themes": theme_entries,
    }
    _write_json(f"apps/{slug}/themes.json", themes_json)
    _write_text(
        f"apps/{slug}/README.md",
        _render_readme(
            app_name,
            slug,
            homepage,
            fmt,
            install_steps,
            variant_files,
            extra_notes=(
                "Includes 19 authentic Notepad++ 8.x `<LexerType>` syntax definitions "
                "(`c`, `cpp`, `cs`, `rust`, `python`, `powershell`, `bash`, `javascript.js`, `typescript`, "
                "`json`, `yaml`, `html`, `css`, `xml`, `markdown`, `sql`, `ini`, `diff`, `batch`) plus "
                "backup-first PowerShell appliers: [`apply-cyclorama-dawn.ps1`](apply-cyclorama-dawn.ps1), "
                "[`apply-cyclorama-steel.ps1`](apply-cyclorama-steel.ps1), and "
                "[`apply-cyclorama-day.ps1`](apply-cyclorama-day.ps1)."
            ),
        ),
    )
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# =============================================================================
# 2. Python IDLE (config-highlight.cfg + config-main-*.cfg)
# =============================================================================

IDLE_KEYS: tuple[str, ...] = (
    "normal-foreground",
    "normal-background",
    "keyword-foreground",
    "keyword-background",
    "builtin-foreground",
    "builtin-background",
    "comment-foreground",
    "comment-background",
    "string-foreground",
    "string-background",
    "definition-foreground",
    "definition-background",
    "hilite-foreground",
    "hilite-background",
    "break-foreground",
    "break-background",
    "hit-foreground",
    "hit-background",
    "error-foreground",
    "error-background",
    "context-foreground",
    "context-background",
    "linenumber-foreground",
    "linenumber-background",
    "cursor-foreground",
    "stdout-foreground",
    "stdout-background",
    "stderr-foreground",
    "stderr-background",
    "console-foreground",
    "console-background",
)


def _idle_theme_map(v: dict) -> dict[str, str]:
    ui = v["ui"]
    syn = v["syntax"]
    bg = ui["bg"]

    return {
        "normal-foreground": ui["text"],
        "normal-background": bg,
        "keyword-foreground": syn["keyword"],
        "keyword-background": bg,
        "builtin-foreground": syn["type"],
        "builtin-background": bg,
        "comment-foreground": syn["comment"],
        "comment-background": bg,
        "string-foreground": syn["string"],
        "string-background": bg,
        "definition-foreground": syn["function"],
        "definition-background": bg,
        "hilite-foreground": ui["text"],
        "hilite-background": ui["selection_active"],
        "break-foreground": ui["text"],
        "break-background": ui["find_match"],
        "hit-foreground": ui["on_accent"],
        "hit-background": ui["accent_fill"],
        "error-foreground": ui["on_accent"],
        "error-background": ui["fault_fill"],
        "context-foreground": ui["text"],
        "context-background": ui["raised"],
        "linenumber-foreground": ui["subtle"],
        "linenumber-background": ui["surface"],
        "cursor-foreground": ui["cursor"],
        "stdout-foreground": ui["secondary"],
        "stdout-background": bg,
        "stderr-foreground": ui["fault"],
        "stderr-background": bg,
        "console-foreground": ui["accent"],
        "console-background": bg,
    }


def _idle_section_text(v: dict) -> str:
    mapping = _idle_theme_map(v)
    lines = [f"[{v['name']}]"]
    for key in IDLE_KEYS:
        lines.append(f"{key} = {mapping[key]}")
    return "\n".join(lines)


def _idle_config_main(v: dict) -> str:
    return "\n".join([
        f"# Python IDLE active theme selector for {v['name']} ({v['lx']} {v['mode'].upper()})",
        "[Theme]",
        "default = False",
        f"name = {v['name']}",
        "name2 =",
        "",
    ])


def build_python_idle() -> dict:
    slug = "python-idle"
    app_name = "Python IDLE"
    homepage = "https://docs.python.org/3/library/idle.html"
    fmt = "IDLE config-highlight.cfg"
    install = "Append apps/python-idle/config-highlight.cfg to ~/.idlerc/config-highlight.cfg and pick in Options -> Configure IDLE -> Highlights"
    install_steps = [
        "Copy or append `apps/python-idle/config-highlight.cfg` into `~/.idlerc/config-highlight.cfg` (on Windows: `%USERPROFILE%\\.idlerc\\config-highlight.cfg`).",
        "Open Python IDLE -> **Options -> Configure IDLE -> Highlights**, select **a Custom Theme**, and pick **Cyclorama Dawn**, **Cyclorama Steel**, or **Cyclorama Day**.",
        "Optional: copy the matching `config-main-dawn.cfg`, `config-main-steel.cfg`, or `config-main-day.cfg` `[Theme]` block into `~/.idlerc/config-main.cfg` to activate immediately.",
    ]

    ver = VARIANTS["cyclorama-dawn"]["version"]
    unified_header = [
        f"# {BRAND_NAME} v{ver} (Steel & Beacon Orange) for Python IDLE",
        "# Append or copy to ~/.idlerc/config-highlight.cfg (Windows: %USERPROFILE%\\.idlerc\\config-highlight.cfg)",
        "",
    ]
    unified_sections = [_idle_section_text(VARIANTS[vid]) for vid in VARIANT_ORDER]
    unified_rel = f"apps/{slug}/config-highlight.cfg"
    _write_text(unified_rel, "\n".join(unified_header) + "\n\n".join(unified_sections) + "\n")

    files: list[dict[str, str]] = [
        {"label": "All 3 Variants Unified (config-highlight.cfg)", "path": unified_rel},
    ]
    theme_entries: list[dict] = []
    variant_files: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        short_slug = v["short"].lower()
        cfg_in_app = f"{vid}.cfg"
        cfg_repo = f"apps/{slug}/{cfg_in_app}"
        main_in_app = f"config-main-{short_slug}.cfg"
        main_repo = f"apps/{slug}/{main_in_app}"

        variant_files[vid] = cfg_in_app
        section = _idle_section_text(v)
        _write_text(
            cfg_repo,
            f"# {v['name']} ({v['lx']} {v['mode'].upper()}) for Python IDLE\n{section}\n",
        )
        _write_text(main_repo, _idle_config_main(v))

        svg = render_editor_preview(
            app_name,
            slug,
            v,
            active_file="palette.py",
            footer_left="Python 3.13  ·  UTF-8",
        )
        write_preview_pair(slug, vid, svg)

        files.append({"label": f"{v['name']} Highlight Theme ({cfg_in_app})", "path": cfg_repo})
        files.append({"label": f"{v['name']} Active Theme Config ({main_in_app})", "path": main_repo})
        theme_entries.append(
            {
                "id": vid,
                "name": v["name"],
                "lx": v["lx"],
                "mode": v["mode"],
                "accentRole": v["accentRole"],
                "tagline": v["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": cfg_repo,
                "copyLang": "ini",
                "copyLabel": "IDLE config-highlight.cfg section",
                "copySnippet": section,
                "swatches": _swatches(v),
            }
        )

    themes_json = {
        "app": app_name,
        "slug": slug,
        "category": CATEGORY,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": unified_rel,
        "files": files,
        "themes": theme_entries,
    }
    _write_json(f"apps/{slug}/themes.json", themes_json)
    _write_text(
        f"apps/{slug}/README.md",
        _render_readme(
            app_name,
            slug,
            homepage,
            fmt,
            install_steps,
            variant_files,
            extra_notes=(
                "Unified 3-variant highlight file: [`config-highlight.cfg`](config-highlight.cfg). "
                "Drop-in `config-main.cfg` selectors: [`config-main-dawn.cfg`](config-main-dawn.cfg), "
                "[`config-main-steel.cfg`](config-main-steel.cfg), and "
                "[`config-main-day.cfg`](config-main-day.cfg). "
                "Every one of the 31 official Python 3.13/3.14 `idlelib/config-highlight.def` slots "
                "is verified to meet `>= 4.5:1` WCAG AA contrast."
            ),
        ),
    )
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# =============================================================================
# 3. Windows PowerShell ISE (.StorableColorTheme.ps1xml + .ps1 Installers)
# =============================================================================

ISE_PANE_KEYS: tuple[str, ...] = (
    "ErrorForegroundColor",
    "ErrorBackgroundColor",
    "WarningForegroundColor",
    "WarningBackgroundColor",
    "VerboseForegroundColor",
    "VerboseBackgroundColor",
    "DebugForegroundColor",
    "DebugBackgroundColor",
    "ConsolePaneBackgroundColor",
    "ConsolePaneTextBackgroundColor",
    "ConsolePaneForegroundColor",
    "ScriptPaneBackgroundColor",
    "ScriptPaneForegroundColor",
)

ISE_TOKEN_NAMES: tuple[str, ...] = (
    "Attribute",
    "Command",
    "CommandArgument",
    "CommandParameter",
    "Comment",
    "GroupEnd",
    "GroupStart",
    "Keyword",
    "LineContinuation",
    "LoopLabel",
    "Member",
    "NewLine",
    "Number",
    "Operator",
    "Position",
    "StatementSeparator",
    "String",
    "Type",
    "Unknown",
    "Variable",
)

ISE_XML_TOKEN_NAMES: tuple[str, ...] = (
    "CharacterData",
    "QuotedString",
    "Comment",
    "CommentDelimiter",
    "15",
    "13",
    "12",
    "14",
    "18",
    "MarkupExtension",
    "Quote",
    "17",
    "ElementName",
    "11",
    "19",
    "16",
    "Attribute",
    "10",
    "Tag",
    "Text",
)

ISE_ALL_73_KEYS: tuple[str, ...] = (
    *ISE_PANE_KEYS,
    *(f"TokenColors\\{k}" for k in ISE_TOKEN_NAMES),
    *(f"ConsoleTokenColors\\{k}" for k in ISE_TOKEN_NAMES),
    *(f"XmlTokenColors\\{k}" for k in ISE_XML_TOKEN_NAMES),
)


def _ise_color_block(hx: str, alpha: int = 255) -> list[str]:
    r, g, b = hex_to_rgb(hx)
    sca = "0" if alpha == 0 else ("1" if alpha == 255 else f"{alpha / 255.0:.7f}".rstrip("0").rstrip("."))
    return [
        "    <Color>",
        f"      <A>{alpha}</A>",
        f"      <R>{r}</R>",
        f"      <G>{g}</G>",
        f"      <B>{b}</B>",
        f"      <ScA>{sca}</ScA>",
        f"      <ScR>{_srgb_to_linear_str(r)}</ScR>",
        f"      <ScG>{_srgb_to_linear_str(g)}</ScG>",
        f"      <ScB>{_srgb_to_linear_str(b)}</ScB>",
        "    </Color>",
    ]


def _ise_color_entries(v: dict) -> list[tuple[str, str, int]]:
    ui = v["ui"]
    syn = v["syntax"]
    bg = ui["bg"]
    console_bg = ui["code_bg"]

    pane: dict[str, tuple[str, int]] = {
        "ErrorForegroundColor": (ui["fault"], 255),
        "ErrorBackgroundColor": (console_bg, 0),
        "WarningForegroundColor": (ui["warning"], 255),
        "WarningBackgroundColor": (console_bg, 0),
        "VerboseForegroundColor": (ui["cyan"], 255),
        "VerboseBackgroundColor": (console_bg, 0),
        "DebugForegroundColor": (ui["secondary"], 255),
        "DebugBackgroundColor": (console_bg, 0),
        "ConsolePaneBackgroundColor": (console_bg, 255),
        "ConsolePaneTextBackgroundColor": (console_bg, 255),
        "ConsolePaneForegroundColor": (ui["text"], 255),
        "ScriptPaneBackgroundColor": (bg, 255),
        "ScriptPaneForegroundColor": (ui["text"], 255),
    }

    ps_tokens: dict[str, str] = {
        "Attribute": syn["constant"],
        "Command": syn["function"],
        "CommandArgument": ui["text_soft"],
        "CommandParameter": syn["property"],
        "Comment": syn["comment"],
        "GroupEnd": syn["punctuation"],
        "GroupStart": syn["punctuation"],
        "Keyword": syn["keyword"],
        "LineContinuation": syn["punctuation"],
        "LoopLabel": syn["constant"],
        "Member": syn["property"],
        "NewLine": ui["text"],
        "Number": syn["number"],
        "Operator": syn["operator"],
        "Position": ui["text"],
        "StatementSeparator": syn["punctuation"],
        "String": syn["string"],
        "Type": syn["type"],
        "Unknown": ui["fault"],
        "Variable": syn["parameter"],
    }

    xml_tokens: dict[str, str] = {
        "CharacterData": syn["comment"],
        "QuotedString": syn["string"],
        "Comment": syn["comment"],
        "CommentDelimiter": syn["comment"],
        "15": ui["text"],
        "13": ui["text"],
        "12": ui["text"],
        "14": ui["text"],
        "18": ui["text"],
        "MarkupExtension": ui["accent"],
        "Quote": syn["punctuation"],
        "17": ui["text"],
        "ElementName": syn["tag"],
        "11": ui["text"],
        "19": ui["text"],
        "16": ui["text"],
        "Attribute": syn["property"],
        "10": ui["text"],
        "Tag": syn["punctuation"],
        "Text": ui["text"],
    }

    entries: list[tuple[str, str, int]] = []
    for k in ISE_PANE_KEYS:
        hx, alpha = pane[k]
        entries.append((k, hx, alpha))
    for k in ISE_TOKEN_NAMES:
        entries.append((f"TokenColors\\{k}", ps_tokens[k], 255))
    for k in ISE_TOKEN_NAMES:
        entries.append((f"ConsoleTokenColors\\{k}", ps_tokens[k], 255))
    for k in ISE_XML_TOKEN_NAMES:
        entries.append((f"XmlTokenColors\\{k}", xml_tokens[k], 255))
    return entries


def _ise_theme_xml(v: dict) -> str:
    entries = _ise_color_entries(v)
    assert len(entries) == 73, f"Expected 73 ISE theme entries, got {len(entries)}"
    assert tuple(k for k, _, _ in entries) == ISE_ALL_73_KEYS

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<StorableColorTheme xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        "  <Keys>",
    ]
    for key, _, _ in entries:
        lines.append(f"    <string>{xml_escape(key)}</string>")
    lines.append("  </Keys>")
    lines.append("  <Values>")
    for _, hx, alpha in entries:
        lines.extend(_ise_color_block(hx, alpha))
    lines.extend([
        "  </Values>",
        f"  <Name>{xml_escape(v['name'])}</Name>",
        "  <FontFamily>Consolas</FontFamily>",
        "  <FontSize>10</FontSize>",
        "</StorableColorTheme>",
    ])
    return "\n".join(lines) + "\n"


def _ise_copy_snippet(v: dict) -> str:
    ui = v["ui"]
    syn = v["syntax"]
    sample_pairs = [
        ("ConsolePaneBackgroundColor", ui["code_bg"]),
        ("ConsolePaneForegroundColor", ui["text"]),
        ("ScriptPaneBackgroundColor", ui["bg"]),
        ("TokenColors\\Keyword", syn["keyword"]),
        ("TokenColors\\Command", syn["function"]),
    ]
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<StorableColorTheme xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        "  <Keys>",
        *[f"    <string>{xml_escape(k)}</string>" for k, _ in sample_pairs],
        "  </Keys>",
        "  <Values>",
    ]
    for _, hx in sample_pairs:
        r, g, b = hex_to_rgb(hx)
        lines.append(
            f"    <Color><A>255</A><R>{r}</R><G>{g}</G><B>{b}</B>"
            f"<ScA>1</ScA><ScR>{_srgb_to_linear_str(r)}</ScR>"
            f"<ScG>{_srgb_to_linear_str(g)}</ScG><ScB>{_srgb_to_linear_str(b)}</ScB></Color>"
        )
    lines.extend([
        "  </Values>",
        f"  <Name>{xml_escape(v['name'])}</Name>",
        "  <FontFamily>Consolas</FontFamily>",
        "  <FontSize>10</FontSize>",
        "</StorableColorTheme>",
    ])
    return "\n".join(lines)


def _ise_install_ps1(v: dict) -> str:
    theme_file = f"{v['name']}.StorableColorTheme.ps1xml"
    preset_key = "Dark Console, Dark Editor" if v["mode"] == "dark" else "Light Console, Light Editor"
    return f"""<#
.SYNOPSIS
    Validate and register {v['name']} ({v['lx']} {v['mode'].upper()}) in Windows PowerShell ISE.
.DESCRIPTION
    Loads Microsoft.PowerShell.GPowerShell, deserializes {theme_file} via
    StorableColorTheme::FromFile(), validates all 73 keys (0 errors required),
    and stores the theme in PowerShell ISE via StoreTheme(). If executed inside
    PowerShell ISE ($psISE present), also applies the theme immediately.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSEdition -eq 'Core') {{
    throw 'Windows PowerShell ISE requires Windows PowerShell 5.1 (powershell.exe), not PowerShell 7 (pwsh).'
}}

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName Microsoft.PowerShell.GPowerShell

if ($null -eq [System.Windows.Application]::Current) {{
    $null = New-Object System.Windows.Application
}}

$ThemeFileName = '{theme_file}'
$ThemePath = Join-Path $PSScriptRoot $ThemeFileName
if (-not (Test-Path -LiteralPath $ThemePath)) {{
    throw "Theme file not found: $ThemePath"
}}

$Asm = [System.Reflection.Assembly]::LoadWithPartialName('Microsoft.PowerShell.GPowerShell')
$Flags = [System.Reflection.BindingFlags]'Public,NonPublic,Static,Instance'
$ThemeType = $Asm.GetType('Microsoft.Windows.PowerShell.Gui.Internal.StorableColorTheme')
$PresetType = $Asm.GetType('Microsoft.Windows.PowerShell.Gui.Internal.PresetThemes')

$FromFileMethod = $ThemeType.GetMethod('FromFile', $Flags)
$ValidateMethod = $ThemeType.GetMethod('Validate', $Flags)
$StoreMethod = $ThemeType.GetMethod('StoreTheme', $Flags)
$ApplyMethod = $ThemeType.GetMethod('ApplyToISEOptions', $Flags)

function Invoke-ClrMethod {{
    param([System.Reflection.MethodInfo]$Method, $Target, $Arg)
    $Unwrapped = if ($Arg -is [psobject]) {{ $Arg.BaseObject }} else {{ $Arg }}
    $ArgArray = [object[]]::new(1)
    $ArgArray[0] = $Unwrapped
    $TargetObj = if ($Target -is [psobject]) {{ $Target.BaseObject }} else {{ $Target }}
    return $Method.Invoke($TargetObj, $ArgArray)
}}

$Theme = Invoke-ClrMethod $FromFileMethod $null ([string]$ThemePath)
if ($null -eq $Theme) {{
    throw "StorableColorTheme::FromFile returned null for $ThemePath"
}}

$Presets = $PresetType.GetProperty('Themes', $Flags).GetValue($null)
$KnownGood = $Presets['{preset_key}']
$ValidationErrors = @(Invoke-ClrMethod $ValidateMethod $Theme $KnownGood)
if ($ValidationErrors.Count -ne 0) {{
    $Joined = ($ValidationErrors -join '; ')
    throw "Theme validation failed with $($ValidationErrors.Count) error(s): $Joined"
}}

[void](Invoke-ClrMethod $StoreMethod $null $Theme)
Write-Host "[ok] Validated (0 errors) and registered '$($Theme.Name)' in Windows PowerShell ISE."

$IseVar = Get-Variable -Name 'psISE' -ErrorAction SilentlyContinue
if ($null -ne $IseVar -and $null -ne $IseVar.Value) {{
    [void](Invoke-ClrMethod $ApplyMethod $Theme $IseVar.Value.Options)
    Write-Host "[ok] Applied '$($Theme.Name)' to the active PowerShell ISE session."
}} else {{
    Write-Host "[i]  Open PowerShell ISE -> Tools -> Options -> Colors and Fonts -> Manage Themes -> select '$($Theme.Name)'."
}}
"""


def build_powershell_ise() -> dict:
    slug = "powershell-ise"
    app_name = "Windows PowerShell ISE"
    homepage = "https://learn.microsoft.com/en-us/powershell/scripting/windows-powershell/ise/introducing-the-windows-powershell-ise"
    fmt = ".StorableColorTheme.ps1xml"
    install = "Run install-cyclorama-dawn.ps1 in Windows PowerShell 5.1 or import .StorableColorTheme.ps1xml via Tools -> Options -> Manage Themes"
    install_steps = [
        "Run `powershell.exe -ExecutionPolicy Bypass -File apps/powershell-ise/install-cyclorama-dawn.ps1` (or `steel` / `day`) in Windows PowerShell 5.1 to validate and register the theme via `StorableColorTheme::StoreTheme()`.",
        "Open **Windows PowerShell ISE** -> **Tools -> Options -> Colors and Fonts -> Manage Themes** and select **Cyclorama Dawn**, **Cyclorama Steel**, or **Cyclorama Day**.",
        "Alternatively, click **Import...** inside **Manage Themes** and choose any `.StorableColorTheme.ps1xml` file directly.",
    ]

    ver = VARIANTS["cyclorama-dawn"]["version"]
    files: list[dict[str, str]] = []
    theme_entries: list[dict] = []
    variant_files: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        xml_in_app = f"{v['name']}.StorableColorTheme.ps1xml"
        xml_repo = f"apps/{slug}/{xml_in_app}"
        ps1_in_app = f"install-{vid}.ps1"
        ps1_repo = f"apps/{slug}/{ps1_in_app}"

        variant_files[vid] = xml_in_app
        _write_text(xml_repo, _ise_theme_xml(v))
        _write_text(ps1_repo, _ise_install_ps1(v))

        svg = render_editor_preview(
            "PowerShell ISE",
            slug,
            v,
            active_file="profile.ps1",
            footer_left="PS 5.1  ·  UTF-8",
        )
        write_preview_pair(slug, vid, svg)

        files.append({"label": f"{v['name']} ISE Theme ({xml_in_app})", "path": xml_repo})
        files.append({"label": f"{v['name']} ISE Installer ({ps1_in_app})", "path": ps1_repo})
        theme_entries.append(
            {
                "id": vid,
                "name": v["name"],
                "lx": v["lx"],
                "mode": v["mode"],
                "accentRole": v["accentRole"],
                "tagline": v["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": xml_repo,
                "copyLang": "xml",
                "copyLabel": "PowerShell ISE StorableColorTheme XML excerpt",
                "copySnippet": _ise_copy_snippet(v),
                "swatches": _swatches(v),
            }
        )

    themes_json = {
        "app": app_name,
        "slug": slug,
        "category": CATEGORY,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": f"apps/{slug}/Cyclorama Dawn.StorableColorTheme.ps1xml",
        "files": files,
        "themes": theme_entries,
    }
    _write_json(f"apps/{slug}/themes.json", themes_json)
    _write_text(
        f"apps/{slug}/README.md",
        _render_readme(
            app_name,
            slug,
            homepage,
            fmt,
            install_steps,
            variant_files,
            extra_notes=(
                "Each `.StorableColorTheme.ps1xml` defines all 73 `StorableColorTheme` keys "
                "(13 pane/stream colors, 20 `TokenColors\\*`, 20 `ConsoleTokenColors\\*`, and "
                "20 `XmlTokenColors\\*`) with exact sRGB-to-linear `ScA`/`ScR`/`ScG`/`ScB` floats. "
                "Installers: [`install-cyclorama-dawn.ps1`](install-cyclorama-dawn.ps1), "
                "[`install-cyclorama-steel.ps1`](install-cyclorama-steel.ps1), and "
                "[`install-cyclorama-day.ps1`](install-cyclorama-day.ps1)."
            ),
        ),
    )
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# =============================================================================
# Public entrypoint & self-verification
# =============================================================================


def build() -> list[dict]:
    """Generate all 3 extra editor & IDE ports and return their manifest entries."""
    return [
        build_notepad_plus_plus(),
        build_python_idle(),
        build_powershell_ise(),
    ]


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _verify_generated(entries: list[dict]) -> None:
    hex6_plain = re.compile(r"^[0-9A-F]{6}$")
    hex6_hash = re.compile(r"^#[0-9A-F]{6}$")
    ps1_files: list[str] = []
    ise_xml_files: list[str] = []

    for entry in entries:
        slug = entry["slug"]
        app_dir = os.path.join(ROOT, *entry["path"].split("/"))

        # Check all files for LF endings & valid syntax
        for r, _, fns in os.walk(app_dir):
            for fn in sorted(fns):
                fp = os.path.join(r, fn)
                raw_b = _read_bytes(fp)
                if b"\r\n" in raw_b:
                    raise AssertionError(f"CRLF detected in {fp}")
                raw = raw_b.decode("utf-8")
                if fn.endswith(".json"):
                    json.loads(raw)
                elif fn.endswith((".xml", ".ps1xml", ".svg")):
                    ET.fromstring(raw)
                    if fn.endswith(".StorableColorTheme.ps1xml"):
                        ise_xml_files.append(fp)
                elif fn.endswith(".cfg"):
                    cp = configparser.RawConfigParser(interpolation=None, strict=True)
                    cp.optionxform = lambda s: s
                    cp.read_string(raw)
                elif fn.endswith(".ps1"):
                    ps1_files.append(fp)

        # Verify mirrored SVG preview parity
        for vid in VARIANT_ORDER:
            p1 = os.path.join(ROOT, "apps", slug, "previews", f"{vid}.svg")
            p2 = os.path.join(ROOT, "docs", "assets", "previews", slug, f"{vid}.svg")
            if _read_bytes(p1) != _read_bytes(p2):
                raise AssertionError(f"Preview mismatch: {p1} != {p2}")

        # Verify themes.json contract & copySnippet validity
        tj = json.loads(_read_text(os.path.join(ROOT, *entry["data"].split("/"))))
        for fobj in tj["files"]:
            fp = os.path.join(ROOT, *fobj["path"].split("/"))
            if not os.path.isfile(fp):
                raise AssertionError(f"Missing file listed in themes.json: {fobj['path']}")
        for t in tj["themes"]:
            snip = t["copySnippet"]
            if len(snip.splitlines()) > 45:
                raise AssertionError(f"{slug}/{t['id']} copySnippet exceeds 45 lines")
            if t["copyLang"] == "xml":
                ET.fromstring(snip)
            elif t["copyLang"] == "ini":
                cp = configparser.RawConfigParser(interpolation=None, strict=True)
                cp.optionxform = lambda s: s
                cp.read_string(snip)

    # 1. Deep check Notepad++ XML structure & 6-char uppercase hex
    expected_lexers = {
        "c", "cpp", "cs", "rust", "python", "powershell", "bash",
        "javascript.js", "typescript", "json", "yaml", "html", "css",
        "xml", "markdown", "sql", "ini", "diff", "batch",
    }
    expected_globals = {
        "Global override", "Default Style", "Indent guideline style",
        "Brace highlight style", "Bad brace colour", "Current line background colour",
        "Selected text colour", "Caret colour", "Multi-selected text color",
        "Line number margin", "Bookmark margin", "Change History margin",
        "Fold", "Fold active", "Fold margin", "White space symbol",
        "Smart Highlighting", "Find Mark Style", "Active tab focused indicator",
        "Active tab unfocused indicator", "Active tab text", "Inactive tabs",
        "URL hovered", "EOL custom color", "Non-printing characters custom color",
    }
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        xp = os.path.join(ROOT, "apps", "notepad-plus-plus", f"{v['name']}.xml")
        root = ET.fromstring(_read_text(xp))
        found_lexers = {el.attrib["name"] for el in root.findall("./LexerStyles/LexerType")}
        if not expected_lexers.issubset(found_lexers):
            raise AssertionError(f"Notepad++ {v['name']}.xml missing lexers: {expected_lexers - found_lexers}")
        found_globals = {el.attrib["name"] for el in root.findall("./GlobalStyles/WidgetStyle")}
        if not expected_globals.issubset(found_globals):
            raise AssertionError(f"Notepad++ {v['name']}.xml missing GlobalStyles: {expected_globals - found_globals}")
        for el in root.iter():
            for attr in ("fgColor", "bgColor"):
                val = el.attrib.get(attr)
                if val is not None and not hex6_plain.match(val):
                    raise AssertionError(f"Notepad++ invalid {attr}={val!r} in {v['name']}.xml")

    # 2. Deep check Python IDLE 31 keys + strict WCAG AA (>= 4.5:1) on EVERY fg/bg pair
    idle_unified = os.path.join(ROOT, "apps", "python-idle", "config-highlight.cfg")
    cp = configparser.RawConfigParser(interpolation=None, strict=True)
    cp.optionxform = lambda s: s
    cp.read_string(_read_text(idle_unified))
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        sec = v["name"]
        if not cp.has_section(sec):
            raise AssertionError(f"IDLE config-highlight.cfg missing section [{sec}]")
        keys = set(cp.options(sec))
        if keys != set(IDLE_KEYS):
            raise AssertionError(f"IDLE [{sec}] key mismatch: {keys ^ set(IDLE_KEYS)}")
        for k in IDLE_KEYS:
            val = cp.get(sec, k).strip()
            if not hex6_hash.match(val):
                raise AssertionError(f"IDLE [{sec}] invalid hex {k}={val!r}")
        for role in (
            "normal", "keyword", "builtin", "comment", "string", "definition",
            "hilite", "break", "hit", "error", "context", "linenumber",
            "stdout", "stderr", "console",
        ):
            fg = cp.get(sec, f"{role}-foreground").strip()
            bg = cp.get(sec, f"{role}-background").strip()
            ratio = contrast(fg, bg)
            if ratio < 4.5:
                raise AssertionError(f"IDLE [{sec}] {role} contrast {ratio:.2f}:1 < 4.5:1 ({fg} on {bg})")
        cur_ratio = contrast(cp.get(sec, "cursor-foreground").strip(), cp.get(sec, "normal-background").strip())
        if cur_ratio < 4.5:
            raise AssertionError(f"IDLE [{sec}] cursor contrast {cur_ratio:.2f}:1 < 4.5:1")

    # 3. Deep check PowerShell ISE 73 keys + WCAG AA foreground readability
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        xp = os.path.join(ROOT, "apps", "powershell-ise", f"{v['name']}.StorableColorTheme.ps1xml")
        root = ET.fromstring(_read_text(xp))
        keys = tuple(el.text or "" for el in root.findall("./Keys/string"))
        vals = root.findall("./Values/Color")
        if keys != ISE_ALL_73_KEYS or len(vals) != 73:
            raise AssertionError(f"ISE {v['name']} expected exact 73 keys/values, got {len(keys)}/{len(vals)}")
        for k, hx, alpha in _ise_color_entries(v):
            if alpha == 255 and k not in ("ConsolePaneBackgroundColor", "ConsolePaneTextBackgroundColor", "ScriptPaneBackgroundColor"):
                bg_ref = v["ui"]["code_bg"] if k.startswith(("Console", "Error", "Warning", "Verbose", "Debug")) else v["ui"]["bg"]
                ratio = contrast(hx, bg_ref)
                if ratio < 4.5:
                    raise AssertionError(f"ISE {v['name']} {k} contrast {ratio:.2f}:1 < 4.5:1 ({hx} on {bg_ref})")

    # 4. Windows PowerShell 5.1 AST parse for ALL 6 .ps1 scripts + live ISE FromFile().Validate()
    ps_exe = shutil.which("powershell.exe")
    if ps_exe:
        ps_list = ", ".join("'" + p.replace("'", "''") + "'" for p in ps1_files)
        ast_cmd = (
            f"$files = @({ps_list}); $bad = 0; "
            "foreach ($f in $files) { $t = $null; $e = $null; "
            "[void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$t, [ref]$e); "
            "if ($e.Count -gt 0) { Write-Error ($f + ': ' + $e[0].Message); $bad++ } }; "
            "if ($bad -gt 0) { exit 2 }"
        )
        res = subprocess.run([ps_exe, "-NoProfile", "-Command", ast_cmd], capture_output=True, text=True)
        if res.returncode != 0:
            raise AssertionError(f"PowerShell 5.1 AST parse failed:\n{res.stderr.strip()}")

        ise_list = ", ".join("'" + p.replace("'", "''") + "'" for p in ise_xml_files)
        ise_cmd = (
            "Add-Type -AssemblyName PresentationFramework; "
            "Add-Type -AssemblyName Microsoft.PowerShell.GPowerShell; "
            "if ($null -eq [System.Windows.Application]::Current) { $null = New-Object System.Windows.Application }; "
            "$asm = [System.Reflection.Assembly]::LoadWithPartialName('Microsoft.PowerShell.GPowerShell'); "
            "$flags = [System.Reflection.BindingFlags]'Public,NonPublic,Static,Instance'; "
            "$t = $asm.GetType('Microsoft.Windows.PowerShell.Gui.Internal.StorableColorTheme'); "
            "$pt = $asm.GetType('Microsoft.Windows.PowerShell.Gui.Internal.PresetThemes'); "
            "$presets = $pt.GetProperty('Themes', $flags).GetValue($null); "
            "$known = $presets['Dark Console, Dark Editor']; "
            "$fromFile = $t.GetMethod('FromFile', $flags); "
            "$validate = $t.GetMethod('Validate', $flags); "
            f"$paths = @({ise_list}); "
            "foreach ($p in $paths) { "
            "  $obj = $fromFile.Invoke($null, [object[]]@($p)); "
            "  $errs = $validate.Invoke($obj, [object[]]@($known)); "
            "  if ($errs.Count -ne 0) { Write-Error ($p + ': ' + ($errs -join '; ')); exit 3 } "
            "  Write-Output ('[ok] ISE Validate 0 errors: ' + $obj.Name + ' (' + $obj.Keys.Count + ' keys)') "
            "}"
        )
        res2 = subprocess.run([ps_exe, "-NoProfile", "-STA", "-Command", ise_cmd], capture_output=True, text=True)
        if res2.returncode != 0:
            raise AssertionError(f"ISE StorableColorTheme::FromFile().Validate() failed:\n{res2.stdout}\n{res2.stderr}")
        for line in res2.stdout.strip().splitlines():
            if line.strip():
                print(line)

    print(
        f"[ok] built & verified {len(entries)} extra editor ports "
        f"(Notepad++, Python IDLE, Windows PowerShell ISE; {len(ps1_files)} PS1 ASTs, "
        f"{len(ise_xml_files)} ISE themes, 48 IDLE AA pairs, 9 SVG pairs)"
    )


if __name__ == "__main__":
    manifest_entries = build()
    _verify_generated(manifest_entries)
