#!/usr/bin/env python3
"""Generate Cyclorama Dawn v2.1.0 editor & IDE theme ports for rfs-themes.

Generates deterministic, WCAG AA calibrated ports (UTF-8, LF line endings) for:
  1. apps/vscode/     — VS Code / Cursor / Antigravity JSON theme extension
  2. apps/neovim/     — Neovim Lua colorscheme + Treesitter + LSP + Lualine plugin
  3. apps/zed/        — Zed Editor v0.2.0 unified + standalone JSON themes
  4. apps/jetbrains/  — JetBrains IDEs .icls editor schemes + .theme.json UI themes + plugin.xml

Zero external dependencies (Python 3.11+ standard library only).
"""
from __future__ import annotations

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
    ansi_list,
    mix,
    with_alpha,
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


def _icls_hex(hx: str) -> str:
    """Convert #RRGGBB to 6-char uppercase RRGGBB without '#' for JetBrains .icls."""
    clean = hx.lstrip("#").upper()
    if len(clean) != 6:
        raise ValueError(f"Expected 6-char hex color for .icls, got {hx!r}")
    return clean


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
        f"with WCAG AA calibrated surfaces, syntax tokens, and ANSI 0-15 terminal colors.",
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
            "python tools/build_editors.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


# =============================================================================
# 1. VS Code / Cursor / Antigravity
# =============================================================================


def _vscode_theme_payload(v: dict) -> dict:
    ui = v["ui"]
    syn = v["syntax"]
    ansi = v["ansi"]
    is_dark = v["mode"] == "dark"

    transparent = with_alpha(ui["bg"], "00")
    shadow = with_alpha(ui["bg"], "99") if is_dark else with_alpha(ui["text"], "24")
    hover_bg = mix(ui["surface"], ui["accent"], 0.10 if is_dark else 0.08)
    list_sel = mix(ui["surface"], ui["accent"], 0.18 if is_dark else 0.14)
    list_inactive = mix(ui["surface"], ui["secondary"], 0.12 if is_dark else 0.10)
    bracket_bg = with_alpha(ui["accent"], "26")
    find_hl = with_alpha(ui["warning"], "38" if is_dark else "45")
    word_hl = with_alpha(ui["secondary"], "2A" if is_dark else "33")
    word_strong = with_alpha(ui["accent"], "33" if is_dark else "3D")
    diff_add_txt = with_alpha(ui["signal"], "2B" if is_dark else "38")
    diff_del_txt = with_alpha(ui["fault"], "2B" if is_dark else "38")
    diff_add_line = with_alpha(ui["diff_add_bg"], "CC")
    diff_del_line = with_alpha(ui["diff_del_bg"], "CC")
    scroll_bg = with_alpha(ui["border_strong"], "55")
    scroll_hover = with_alpha(ui["border_strong"], "88")
    scroll_active = with_alpha(ui["accent"], "AA")

    colors = {
        # Base & focus
        "focusBorder": ui["accent"],
        "foreground": ui["text"],
        "disabledForeground": ui["subtle"],
        "widget.border": ui["border"],
        "widget.shadow": shadow,
        "selection.background": ui["selection_active"],
        "descriptionForeground": ui["mute"],
        "errorForeground": ui["fault"],
        "icon.foreground": ui["mute"],
        "sash.hoverBorder": ui["accent"],
        # Text & links
        "textLink.foreground": ui["accent"],
        "textLink.activeForeground": ui["accent_hover"],
        "textBlockQuote.background": ui["surface"],
        "textBlockQuote.border": ui["secondary"],
        "textCodeBlock.background": ui["code_bg"],
        "textPreformat.foreground": ui["accent"],
        "textSeparator.foreground": ui["border"],
        # Buttons, badges & progress
        "button.background": ui["accent_fill"],
        "button.foreground": ui["on_accent"],
        "button.hoverBackground": ui["accent_fill_hover"],
        "button.secondaryBackground": ui["raised"],
        "button.secondaryForeground": ui["text"],
        "button.secondaryHoverBackground": ui["overlay"],
        "badge.background": ui["accent_fill"],
        "badge.foreground": ui["on_accent"],
        "progressBar.background": ui["accent"],
        # Inputs & dropdowns
        "input.background": ui["code_bg"],
        "input.foreground": ui["text"],
        "input.border": ui["border"],
        "input.placeholderForeground": ui["subtle"],
        "inputOption.activeBorder": ui["accent"],
        "inputOption.activeBackground": with_alpha(ui["accent"], "26"),
        "inputOption.activeForeground": ui["text"],
        "inputValidation.errorBackground": ui["diff_del_bg"],
        "inputValidation.errorBorder": ui["fault"],
        "inputValidation.warningBackground": ui["find_match"],
        "inputValidation.warningBorder": ui["warning"],
        "inputValidation.infoBackground": ui["diff_chg_bg"],
        "inputValidation.infoBorder": ui["secondary"],
        "dropdown.background": ui["surface"],
        "dropdown.border": ui["border"],
        "dropdown.foreground": ui["text"],
        "dropdown.listBackground": ui["surface"],
        # Scrollbar & minimap
        "scrollbar.shadow": shadow,
        "scrollbarSlider.background": scroll_bg,
        "scrollbarSlider.hoverBackground": scroll_hover,
        "scrollbarSlider.activeBackground": scroll_active,
        "minimap.selectionHighlight": ui["selection_active"],
        "minimap.findMatchHighlight": ui["warning"],
        "minimap.errorHighlight": ui["fault"],
        "minimap.warningHighlight": ui["warning"],
        "minimapGutter.addedBackground": ui["signal"],
        "minimapGutter.modifiedBackground": ui["secondary"],
        "minimapGutter.deletedBackground": ui["fault"],
        # Lists & trees
        "list.activeSelectionBackground": list_sel,
        "list.activeSelectionForeground": ui["text"],
        "list.inactiveSelectionBackground": list_inactive,
        "list.inactiveSelectionForeground": ui["text"],
        "list.hoverBackground": hover_bg,
        "list.hoverForeground": ui["text"],
        "list.focusBackground": list_sel,
        "list.focusOutline": ui["accent"],
        "list.highlightForeground": ui["accent"],
        "list.errorForeground": ui["fault"],
        "list.warningForeground": ui["warning"],
        "tree.indentGuidesStroke": ui["border_subtle"],
        # Activity bar
        "activityBar.background": ui["rail"],
        "activityBar.foreground": ui["accent"],
        "activityBar.inactiveForeground": ui["subtle"],
        "activityBar.border": ui["border"],
        "activityBar.activeBorder": ui["accent"],
        "activityBar.activeBackground": ui["surface"],
        "activityBarBadge.background": ui["accent_fill"],
        "activityBarBadge.foreground": ui["on_accent"],
        # Side bar
        "sideBar.background": ui["surface"],
        "sideBar.foreground": ui["text_soft"],
        "sideBar.border": ui["border"],
        "sideBarTitle.foreground": ui["text"],
        "sideBarSectionHeader.background": ui["rail"],
        "sideBarSectionHeader.foreground": ui["mute"],
        "sideBarSectionHeader.border": ui["border"],
        # Editor groups & tabs
        "editorGroup.border": ui["border"],
        "editorGroupHeader.tabsBackground": ui["rail"],
        "editorGroupHeader.tabsBorder": ui["border"],
        "tab.activeBackground": ui["bg"],
        "tab.activeForeground": ui["text"],
        "tab.activeBorderTop": ui["accent"],
        "tab.border": ui["border_subtle"],
        "tab.inactiveBackground": ui["rail"],
        "tab.inactiveForeground": ui["mute"],
        "tab.hoverBackground": ui["surface"],
        "tab.unfocusedActiveBorderTop": ui["secondary"],
        "tab.activeModifiedBorder": ui["secondary"],
        # Editor core
        "editor.background": ui["bg"],
        "editor.foreground": ui["text"],
        "editorCursor.foreground": ui["cursor"],
        "editorCursor.background": ui["cursor_text"],
        "editorLineNumber.foreground": ui["subtle"],
        "editorLineNumber.activeForeground": ui["text"],
        "editor.lineHighlightBackground": ui["raised"],
        "editor.lineHighlightBorder": transparent,
        "editor.selectionBackground": ui["selection_active"],
        "editor.inactiveSelectionBackground": ui["selection_bg"],
        "editor.selectionHighlightBackground": word_hl,
        "editor.wordHighlightBackground": word_hl,
        "editor.wordHighlightStrongBackground": word_strong,
        "editor.findMatchBackground": ui["find_match"],
        "editor.findMatchHighlightBackground": find_hl,
        "editor.findMatchBorder": ui["warning"],
        "editor.hoverHighlightBackground": hover_bg,
        "editorIndentGuide.background1": ui["border_subtle"],
        "editorIndentGuide.activeBackground1": ui["border_strong"],
        "editorRuler.foreground": ui["border_subtle"],
        "editorWhitespace.foreground": ui["border"],
        "editorLink.activeForeground": ui["accent"],
        "editorCodeLens.foreground": ui["subtle"],
        "editorBracketMatch.background": bracket_bg,
        "editorBracketMatch.border": ui["accent"],
        # Bracket pair colorization
        "editorBracketHighlight.foreground1": ui["accent"],
        "editorBracketHighlight.foreground2": ui["secondary"],
        "editorBracketHighlight.foreground3": ui["signal"],
        "editorBracketHighlight.foreground4": ui["warning"],
        "editorBracketHighlight.foreground5": ui["magenta"],
        "editorBracketHighlight.foreground6": ui["cyan"],
        "editorBracketHighlight.unexpectedBracket.foreground": ui["fault"],
        # Editor gutter
        "editorGutter.background": ui["bg"],
        "editorGutter.addedBackground": ui["signal"],
        "editorGutter.modifiedBackground": ui["secondary"],
        "editorGutter.deletedBackground": ui["fault"],
        "editorGutter.foldingControlForeground": ui["mute"],
        # Editor widgets & diagnostics
        "editorWidget.background": ui["surface"],
        "editorWidget.border": ui["border"],
        "editorWidget.foreground": ui["text"],
        "editorSuggestWidget.background": ui["surface"],
        "editorSuggestWidget.border": ui["border"],
        "editorSuggestWidget.foreground": ui["text"],
        "editorSuggestWidget.highlightForeground": ui["accent"],
        "editorSuggestWidget.selectedBackground": list_sel,
        "editorHoverWidget.background": ui["surface"],
        "editorHoverWidget.border": ui["border"],
        "editorError.foreground": ui["fault"],
        "editorWarning.foreground": ui["warning"],
        "editorInfo.foreground": ui["secondary"],
        "editorHint.foreground": ui["cyan"],
        "problemsErrorIcon.foreground": ui["fault"],
        "problemsWarningIcon.foreground": ui["warning"],
        "problemsInfoIcon.foreground": ui["secondary"],
        # Diff editor
        "diffEditor.insertedTextBackground": diff_add_txt,
        "diffEditor.removedTextBackground": diff_del_txt,
        "diffEditor.insertedLineBackground": diff_add_line,
        "diffEditor.removedLineBackground": diff_del_line,
        "diffEditor.diagonalFill": ui["border_subtle"],
        "diffEditor.border": ui["border"],
        # Peek view & quick input
        "peekView.border": ui["accent"],
        "peekViewEditor.background": ui["code_bg"],
        "peekViewResult.background": ui["surface"],
        "peekViewTitle.background": ui["rail"],
        "quickInput.background": ui["surface"],
        "quickInput.foreground": ui["text"],
        "quickInputList.focusBackground": list_sel,
        "quickInputList.focusForeground": ui["text"],
        # Panel
        "panel.background": ui["surface"],
        "panel.border": ui["border"],
        "panelTitle.activeBorder": ui["accent"],
        "panelTitle.activeForeground": ui["text"],
        "panelTitle.inactiveForeground": ui["mute"],
        # Status bar
        "statusBar.background": ui["accent_fill"],
        "statusBar.foreground": ui["on_accent"],
        "statusBar.border": ui["border"],
        "statusBar.debuggingBackground": ui["secondary_fill"],
        "statusBar.debuggingForeground": ui["on_accent"],
        "statusBar.noFolderBackground": ui["rail"],
        "statusBar.noFolderForeground": ui["text"],
        "statusBarItem.hoverBackground": ui["accent_fill_hover"],
        "statusBarItem.remoteBackground": ui["secondary_fill"],
        "statusBarItem.remoteForeground": ui["on_accent"],
        # Title bar & menus
        "titleBar.activeBackground": ui["rail"],
        "titleBar.activeForeground": ui["text"],
        "titleBar.inactiveBackground": ui["rail"],
        "titleBar.inactiveForeground": ui["mute"],
        "titleBar.border": ui["border"],
        "menu.background": ui["surface"],
        "menu.foreground": ui["text"],
        "menu.selectionBackground": list_sel,
        "menu.selectionForeground": ui["text"],
        "menu.separatorBackground": ui["border"],
        "menu.border": ui["border"],
        # Notifications & breadcrumbs
        "notifications.background": ui["surface"],
        "notifications.foreground": ui["text"],
        "notifications.border": ui["border"],
        "notificationCenterHeader.background": ui["rail"],
        "notificationsErrorIcon.foreground": ui["fault"],
        "notificationsWarningIcon.foreground": ui["warning"],
        "notificationsInfoIcon.foreground": ui["secondary"],
        "breadcrumb.background": ui["bg"],
        "breadcrumb.foreground": ui["mute"],
        "breadcrumb.focusForeground": ui["text"],
        "breadcrumb.activeSelectionForeground": ui["accent"],
        # Git decorations
        "gitDecoration.addedResourceForeground": ui["signal"],
        "gitDecoration.modifiedResourceForeground": ui["secondary"],
        "gitDecoration.deletedResourceForeground": ui["fault"],
        "gitDecoration.untrackedResourceForeground": ui["signal"],
        "gitDecoration.ignoredResourceForeground": ui["subtle"],
        "gitDecoration.conflictingResourceForeground": ui["warning"],
        "gitDecoration.submoduleResourceForeground": ui["cyan"],
        # Terminal ANSI 0-15
        "terminal.background": ui["bg"],
        "terminal.foreground": ui["text"],
        "terminal.border": ui["border"],
        "terminalCursor.foreground": ui["cursor"],
        "terminalCursor.background": ui["cursor_text"],
        "terminal.selectionBackground": ui["selection_active"],
        "terminal.ansiBlack": ansi["black"],
        "terminal.ansiRed": ansi["red"],
        "terminal.ansiGreen": ansi["green"],
        "terminal.ansiYellow": ansi["yellow"],
        "terminal.ansiBlue": ansi["blue"],
        "terminal.ansiMagenta": ansi["magenta"],
        "terminal.ansiCyan": ansi["cyan"],
        "terminal.ansiWhite": ansi["white"],
        "terminal.ansiBrightBlack": ansi["brightBlack"],
        "terminal.ansiBrightRed": ansi["brightRed"],
        "terminal.ansiBrightGreen": ansi["brightGreen"],
        "terminal.ansiBrightYellow": ansi["brightYellow"],
        "terminal.ansiBrightBlue": ansi["brightBlue"],
        "terminal.ansiBrightMagenta": ansi["brightMagenta"],
        "terminal.ansiBrightCyan": ansi["brightCyan"],
        "terminal.ansiBrightWhite": ansi["brightWhite"],
    }

    semantic_tokens = {
        "namespace": syn["type"],
        "type": syn["type"],
        "class": {"foreground": syn["type"], "bold": True},
        "struct": {"foreground": syn["type"], "bold": True},
        "enum": syn["type"],
        "interface": {"foreground": syn["type"], "italic": True},
        "typeParameter": syn["property"],
        "function": syn["function"],
        "method": syn["function"],
        "macro": {"foreground": syn["keyword"], "bold": True},
        "variable": ui["text"],
        "variable.readonly": syn["constant"],
        "variable.defaultLibrary": syn["type"],
        "parameter": syn["parameter"],
        "property": syn["property"],
        "enumMember": syn["constant"],
        "keyword": syn["keyword"],
        "comment": {"foreground": syn["comment"], "italic": True},
        "string": syn["string"],
        "number": syn["number"],
        "regexp": syn["constant"],
        "operator": syn["operator"],
        "decorator": syn["constant"],
    }

    token_colors = [
        {
            "name": "Comments",
            "scope": [
                "comment",
                "punctuation.definition.comment",
                "comment.line",
                "comment.block",
            ],
            "settings": {"foreground": syn["comment"], "fontStyle": "italic"},
        },
        {
            "name": "Keywords & Storage",
            "scope": [
                "keyword",
                "keyword.control",
                "keyword.other",
                "storage",
                "storage.type",
                "storage.modifier",
            ],
            "settings": {"foreground": syn["keyword"]},
        },
        {
            "name": "Operators & Punctuation",
            "scope": [
                "keyword.operator",
                "punctuation.separator",
                "punctuation.terminator",
                "punctuation.accessor",
            ],
            "settings": {"foreground": syn["operator"]},
        },
        {
            "name": "Brackets & Delimiters",
            "scope": [
                "punctuation.section",
                "meta.brace",
                "punctuation.definition.block",
                "punctuation.definition.parameters",
            ],
            "settings": {"foreground": syn["punctuation"]},
        },
        {
            "name": "Functions & Methods",
            "scope": [
                "entity.name.function",
                "meta.function-call entity.name.function",
                "support.function",
                "variable.function",
            ],
            "settings": {"foreground": syn["function"]},
        },
        {
            "name": "Strings",
            "scope": [
                "string",
                "string.quoted",
                "string.template",
                "punctuation.definition.string",
            ],
            "settings": {"foreground": syn["string"]},
        },
        {
            "name": "String Escapes & Regex",
            "scope": [
                "constant.character.escape",
                "string.regexp",
                "punctuation.definition.template-expression",
            ],
            "settings": {"foreground": syn["constant"]},
        },
        {
            "name": "Numbers & Booleans",
            "scope": [
                "constant.numeric",
                "constant.language.boolean",
                "constant.language.null",
                "constant.language.undefined",
            ],
            "settings": {"foreground": syn["number"]},
        },
        {
            "name": "Types, Classes & Namespaces",
            "scope": [
                "entity.name.type",
                "entity.name.class",
                "entity.name.struct",
                "entity.name.enum",
                "entity.name.interface",
                "entity.name.namespace",
                "entity.other.inherited-class",
                "support.type",
                "support.class",
            ],
            "settings": {"foreground": syn["type"]},
        },
        {
            "name": "Constants & Symbols",
            "scope": [
                "constant.language",
                "constant.other",
                "constant.other.symbol",
                "variable.other.constant",
                "entity.name.constant",
            ],
            "settings": {"foreground": syn["constant"]},
        },
        {
            "name": "Variables",
            "scope": ["variable", "variable.other.readwrite"],
            "settings": {"foreground": ui["text"]},
        },
        {
            "name": "Parameters",
            "scope": ["variable.parameter", "meta.function.parameters variable"],
            "settings": {"foreground": syn["parameter"]},
        },
        {
            "name": "Self / This Language Variables",
            "scope": ["variable.language"],
            "settings": {"foreground": syn["keyword"], "fontStyle": "italic"},
        },
        {
            "name": "Properties & Object Keys",
            "scope": [
                "variable.other.property",
                "variable.other.object.property",
                "meta.object-literal.key",
                "entity.other.attribute-name",
            ],
            "settings": {"foreground": syn["property"]},
        },
        {
            "name": "HTML & XML Tags",
            "scope": ["entity.name.tag", "support.class.component"],
            "settings": {"foreground": syn["tag"]},
        },
        {
            "name": "HTML & XML Tag Punctuation",
            "scope": ["punctuation.definition.tag"],
            "settings": {"foreground": syn["punctuation"]},
        },
        {
            "name": "CSS Selectors & Properties",
            "scope": [
                "support.type.property-name.css",
                "entity.other.attribute-name.class.css",
                "entity.other.attribute-name.id.css",
            ],
            "settings": {"foreground": syn["property"]},
        },
        {
            "name": "CSS Units",
            "scope": ["keyword.other.unit"],
            "settings": {"foreground": syn["number"]},
        },
        {
            "name": "JSON Keys",
            "scope": ["support.type.property-name.json"],
            "settings": {"foreground": syn["property"]},
        },
        {
            "name": "Decorators & Annotations",
            "scope": [
                "meta.decorator",
                "punctuation.definition.decorator",
                "storage.type.annotation",
            ],
            "settings": {"foreground": syn["constant"]},
        },
        {
            "name": "Markdown Headings",
            "scope": [
                "markup.heading",
                "entity.name.section.markdown",
                "punctuation.definition.heading.markdown",
            ],
            "settings": {"foreground": syn["function"], "fontStyle": "bold"},
        },
        {
            "name": "Markdown Bold",
            "scope": ["markup.bold"],
            "settings": {"foreground": ui["text"], "fontStyle": "bold"},
        },
        {
            "name": "Markdown Italic",
            "scope": ["markup.italic"],
            "settings": {"foreground": ui["text_soft"], "fontStyle": "italic"},
        },
        {
            "name": "Markdown Links",
            "scope": [
                "markup.underline.link",
                "string.other.link.title.markdown",
                "string.other.link.description.markdown",
            ],
            "settings": {"foreground": syn["keyword"]},
        },
        {
            "name": "Markdown Inline & Fenced Code",
            "scope": [
                "markup.inline.raw",
                "markup.fenced_code.block.markdown",
                "markup.raw.block.markdown",
            ],
            "settings": {"foreground": syn["string"]},
        },
        {
            "name": "Markdown Blockquote",
            "scope": ["markup.quote"],
            "settings": {"foreground": syn["comment"], "fontStyle": "italic"},
        },
        {
            "name": "Diff Inserted",
            "scope": ["markup.inserted", "punctuation.definition.inserted"],
            "settings": {"foreground": syn["diff_add"]},
        },
        {
            "name": "Diff Deleted",
            "scope": ["markup.deleted", "punctuation.definition.deleted"],
            "settings": {"foreground": syn["diff_del"]},
        },
        {
            "name": "Diff Changed & Headers",
            "scope": ["markup.changed", "meta.diff.header", "meta.diff.range"],
            "settings": {"foreground": syn["diff_change"]},
        },
        {
            "name": "Invalid & Deprecated",
            "scope": ["invalid", "invalid.illegal"],
            "settings": {"foreground": ui["fault"], "fontStyle": "underline"},
        },
        {
            "name": "Deprecated",
            "scope": ["invalid.deprecated"],
            "settings": {"foreground": ui["warning"], "fontStyle": "strikethrough"},
        },
    ]

    return {
        "$schema": "vscode://schemas/color-theme",
        "name": v["name"],
        "type": v["mode"],
        "semanticHighlighting": True,
        "colors": colors,
        "semanticTokenColors": semantic_tokens,
        "tokenColors": token_colors,
    }


def _vscode_copy_snippet(v: dict) -> str:
    ui = v["ui"]
    snippet = {
        "workbench.colorTheme": v["name"],
        "editor.semanticHighlighting.enabled": True,
        "workbench.colorCustomizations": {
            f"[{v['name']}]": {
                "editor.background": ui["bg"],
                "sideBar.background": ui["surface"],
                "statusBar.background": ui["accent_fill"],
                "statusBar.foreground": ui["on_accent"],
                "focusBorder": ui["accent"],
            }
        },
    }
    return json.dumps(snippet, indent=2)


def build_vscode() -> dict:
    slug = "vscode"
    app_name = "VS Code"
    homepage = "https://code.visualstudio.com/"
    fmt = "VS Code JSON Theme Extension"
    install = "Copy apps/vscode/ into ~/.vscode/extensions/rfs-cyclorama-dawn and pick Color Theme"
    install_steps = [
        "Copy `apps/vscode/` to `~/.vscode/extensions/rfs-cyclorama-dawn` (or `~/.cursor/extensions/rfs-cyclorama-dawn`).",
        "Reload the window (`Ctrl+Shift+P` -> **Developer: Reload Window**).",
        "Open **Preferences: Color Theme** (`Ctrl+K Ctrl+T`) and select **Cyclorama Dawn**, **Cyclorama Steel**, or **Cyclorama Day**.",
    ]

    ver = VARIANTS["cyclorama-dawn"]["version"]
    pkg = {
        "name": "cyclorama-dawn-theme",
        "displayName": "Cyclorama Dawn — Real-Fruit-Snacks",
        "description": "Cyclorama Dawn (Steel & Beacon Orange) WCAG AA color themes for VS Code, Cursor, and Antigravity.",
        "version": ver,
        "publisher": AUTHOR,
        "license": "MIT",
        "homepage": GALLERY_URL,
        "repository": {"type": "git", "url": REPO_URL},
        "engines": {"vscode": "^1.75.0"},
        "categories": ["Themes"],
        "keywords": [
            "theme",
            "color-theme",
            "dark",
            "light",
            "cyclorama-dawn",
            "real-fruit-snacks",
            "wcag-aa",
        ],
        "contributes": {
            "themes": [
                {
                    "label": VARIANTS[vid]["name"],
                    "uiTheme": "vs-dark" if VARIANTS[vid]["mode"] == "dark" else "vs",
                    "path": f"./themes/{vid}.json",
                }
                for vid in VARIANT_ORDER
            ]
        },
    }
    _write_json(f"apps/{slug}/package.json", pkg)

    theme_entries = []
    files = [{"label": "Extension manifest (package.json)", "path": f"apps/{slug}/package.json"}]
    variant_files: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        rel_in_app = f"themes/{vid}.json"
        rel_repo = f"apps/{slug}/{rel_in_app}"
        variant_files[vid] = rel_in_app
        _write_json(rel_repo, _vscode_theme_payload(v))

        svg = render_editor_preview(
            app_name,
            slug,
            v,
            active_file="palette.rs",
            footer_left="main  ·  Rust  ·  UTF-8",
        )
        write_preview_pair(slug, vid, svg)

        files.append({"label": f"{v['name']} ({vid}.json)", "path": rel_repo})
        theme_entries.append(
            {
                "id": vid,
                "name": v["name"],
                "lx": v["lx"],
                "mode": v["mode"],
                "accentRole": v["accentRole"],
                "tagline": v["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": rel_repo,
                "copyLang": "json",
                "copyLabel": "settings.json snippet",
                "copySnippet": _vscode_copy_snippet(v),
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
        "primaryFile": f"apps/{slug}/themes/cyclorama-dawn.json",
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
            extra_notes="Works identically in **VS Code**, **Cursor**, and **Antigravity** (full workbench colors, semantic tokens, and TextMate scopes).",
        ),
    )
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# =============================================================================
# 2. Neovim
# =============================================================================


LUA_KEYWORDS = frozenset({
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "goto", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "until", "while",
})


def _lua_dict(d: dict[str, str], indent: int = 6) -> str:
    pad = " " * indent
    rows = []
    for k, val in d.items():
        lhs = f'["{k}"]' if (k in LUA_KEYWORDS or not k.isidentifier()) else k
        rows.append(f'{pad}{lhs} = "{val}",')
    return "\n".join(rows)


def _neovim_palette_lua() -> str:
    blocks = [
        "-- Cyclorama Dawn v2.1.0 canonical Neovim palette tables",
        "-- Generated by tools/build_editors.py from brand/rfs.tokens.json",
        "local M = {}",
        "",
    ]
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        blocks.extend(
            [
                f'M["{vid}"] = {{',
                "  meta = {",
                f'    id = "{v["id"]}",',
                f'    name = "{v["name"]}",',
                f'    lx = "{v["lx"]}",',
                f'    mode = "{v["mode"]}",',
                f'    version = "{v["version"]}",',
                "  },",
                "  ui = {",
                _lua_dict(v["ui"], indent=4),
                "  },",
                "  syntax = {",
                _lua_dict(v["syntax"], indent=4),
                "  },",
                "  ansi = {",
                _lua_dict(v["ansi"], indent=4),
                "  },",
                "  terminal = {",
                "    " + ", ".join(f'"{hx}"' for hx in ansi_list(v)),
                "  },",
                "}",
                "",
            ]
        )
    blocks.append("return M\n")
    return "\n".join(blocks)


def _neovim_init_lua() -> str:
    return """-- Cyclorama Dawn v2.1.0 colorscheme plugin for Neovim (0.9+)
-- Generated by tools/build_editors.py — Real-Fruit-Snacks
local palette = require("cyclorama.palette")

local M = {}

M.config = {
  variant = "cyclorama-dawn",
  transparent = false,
  italic_comments = true,
  terminal_colors = true,
}

M.current = "cyclorama-dawn"

function M.setup(opts)
  M.config = vim.tbl_deep_extend("force", M.config, opts or {})
end

function M.get_palette(variant)
  local key = variant or M.current or M.config.variant
  return palette[key] or palette["cyclorama-dawn"]
end

local function set_terminal_colors(ordered)
  for i, hex in ipairs(ordered) do
    vim.g["terminal_color_" .. (i - 1)] = hex
  end
end

function M.load(variant)
  local key = variant or M.config.variant or "cyclorama-dawn"
  local p = palette[key] or palette["cyclorama-dawn"]
  local ui, syn = p.ui, p.syntax

  if vim.g.colors_name then
    vim.cmd("highlight clear")
  end
  if vim.fn.exists("syntax_on") == 1 then
    vim.cmd("syntax reset")
  end

  vim.o.termguicolors = true
  vim.o.background = p.meta.mode
  vim.g.colors_name = p.meta.id
  M.current = p.meta.id

  local bg = M.config.transparent and "NONE" or ui.bg
  local float_bg = M.config.transparent and "NONE" or ui.surface
  local italic_cmt = M.config.italic_comments

  local groups = {
    -- Core UI
    Normal = { fg = ui.text, bg = bg },
    NormalNC = { fg = ui.text_soft, bg = bg },
    NormalFloat = { fg = ui.text, bg = float_bg },
    FloatBorder = { fg = ui.border_strong, bg = float_bg },
    FloatTitle = { fg = ui.accent, bg = float_bg, bold = true },
    Cursor = { fg = ui.cursor_text, bg = ui.cursor },
    lCursor = { fg = ui.cursor_text, bg = ui.cursor },
    CursorIM = { fg = ui.cursor_text, bg = ui.cursor },
    TermCursor = { fg = ui.cursor_text, bg = ui.cursor },
    CursorLine = { bg = ui.raised },
    CursorColumn = { bg = ui.raised },
    ColorColumn = { bg = ui.surface },
    LineNr = { fg = ui.subtle },
    CursorLineNr = { fg = ui.accent, bold = true },
    SignColumn = { fg = ui.subtle, bg = bg },
    FoldColumn = { fg = ui.subtle, bg = bg },
    Folded = { fg = ui.mute, bg = ui.surface },
    Visual = { bg = ui.selection_active },
    VisualNOS = { bg = ui.selection_bg },
    Search = { fg = ui.text, bg = ui.find_match },
    IncSearch = { fg = ui.on_accent, bg = ui.accent_fill, bold = true },
    CurSearch = { fg = ui.on_accent, bg = ui.accent_fill, bold = true },
    Substitute = { fg = ui.on_accent, bg = ui.fault_fill, bold = true },
    MatchParen = { fg = ui.accent, bg = ui.overlay, bold = true },
    Pmenu = { fg = ui.text, bg = ui.surface },
    PmenuSel = { fg = ui.on_accent, bg = ui.accent_fill, bold = true },
    PmenuSbar = { bg = ui.raised },
    PmenuThumb = { bg = ui.border_strong },
    StatusLine = { fg = ui.on_accent, bg = ui.accent_fill, bold = true },
    StatusLineNC = { fg = ui.mute, bg = ui.rail },
    TabLine = { fg = ui.mute, bg = ui.rail },
    TabLineFill = { bg = ui.rail },
    TabLineSel = { fg = ui.text, bg = ui.bg, bold = true },
    WinBar = { fg = ui.text, bg = ui.surface, bold = true },
    WinBarNC = { fg = ui.mute, bg = ui.surface },
    VertSplit = { fg = ui.border },
    WinSeparator = { fg = ui.border },
    Title = { fg = ui.accent, bold = true },
    Directory = { fg = ui.secondary, bold = true },
    NonText = { fg = ui.border_strong },
    SpecialKey = { fg = ui.border_strong },
    Whitespace = { fg = ui.border },
    EndOfBuffer = { fg = ui.border_subtle },
    Conceal = { fg = ui.subtle },
    ErrorMsg = { fg = ui.fault, bold = true },
    WarningMsg = { fg = ui.warning, bold = true },
    ModeMsg = { fg = ui.accent, bold = true },
    MoreMsg = { fg = ui.signal, bold = true },
    Question = { fg = ui.secondary, bold = true },
    QuickFixLine = { bg = ui.selection_active, bold = true },
    DiffAdd = { bg = ui.diff_add_bg },
    DiffChange = { bg = ui.diff_chg_bg },
    DiffDelete = { fg = ui.fault, bg = ui.diff_del_bg },
    DiffText = { fg = ui.text, bg = ui.selection_active, bold = true },
    SpellBad = { undercurl = true, sp = ui.fault },
    SpellCap = { undercurl = true, sp = ui.warning },
    SpellLocal = { undercurl = true, sp = ui.secondary },
    SpellRare = { undercurl = true, sp = ui.cyan },

    -- Classic syntax
    Comment = { fg = syn.comment, italic = italic_cmt },
    Constant = { fg = syn.constant },
    String = { fg = syn.string },
    Character = { fg = syn.string },
    Number = { fg = syn.number },
    Boolean = { fg = syn.number, bold = true },
    Float = { fg = syn.number },
    Identifier = { fg = ui.text },
    Function = { fg = syn["function"] },
    Statement = { fg = syn.keyword },
    Conditional = { fg = syn.keyword },
    Repeat = { fg = syn.keyword },
    Label = { fg = syn.property },
    Operator = { fg = syn.operator },
    Keyword = { fg = syn.keyword },
    Exception = { fg = ui.fault },
    PreProc = { fg = syn.keyword },
    Include = { fg = syn.keyword },
    Define = { fg = syn.keyword },
    Macro = { fg = syn["function"] },
    PreCondit = { fg = syn.keyword },
    Type = { fg = syn.type },
    StorageClass = { fg = syn.keyword },
    Structure = { fg = syn.type },
    Typedef = { fg = syn.type },
    Special = { fg = syn.constant },
    SpecialChar = { fg = syn.constant },
    Tag = { fg = syn.tag },
    Delimiter = { fg = syn.punctuation },
    SpecialComment = { fg = syn.comment, italic = italic_cmt, bold = true },
    Debug = { fg = ui.warning },
    Underlined = { fg = ui.accent, underline = true },
    Error = { fg = ui.fault, bold = true },
    Todo = { fg = ui.on_accent, bg = ui.accent_fill, bold = true },

    -- Treesitter captures
    ["@comment"] = { fg = syn.comment, italic = italic_cmt },
    ["@comment.documentation"] = { fg = syn.comment, italic = italic_cmt },
    ["@comment.todo"] = { fg = ui.on_accent, bg = ui.accent_fill, bold = true },
    ["@comment.warning"] = { fg = ui.warning, bold = true },
    ["@comment.error"] = { fg = ui.fault, bold = true },
    ["@keyword"] = { fg = syn.keyword },
    ["@keyword.function"] = { fg = syn.keyword },
    ["@keyword.return"] = { fg = syn.keyword },
    ["@keyword.operator"] = { fg = syn.keyword },
    ["@keyword.import"] = { fg = syn.keyword },
    ["@keyword.conditional"] = { fg = syn.keyword },
    ["@keyword.repeat"] = { fg = syn.keyword },
    ["@function"] = { fg = syn["function"] },
    ["@function.builtin"] = { fg = syn["function"], bold = true },
    ["@function.call"] = { fg = syn["function"] },
    ["@function.method"] = { fg = syn["function"] },
    ["@function.macro"] = { fg = syn.keyword, bold = true },
    ["@constructor"] = { fg = syn.type },
    ["@string"] = { fg = syn.string },
    ["@string.escape"] = { fg = syn.constant },
    ["@string.regexp"] = { fg = syn.constant },
    ["@string.special.url"] = { fg = ui.accent, underline = true },
    ["@character"] = { fg = syn.string },
    ["@number"] = { fg = syn.number },
    ["@number.float"] = { fg = syn.number },
    ["@boolean"] = { fg = syn.number, bold = true },
    ["@constant"] = { fg = syn.constant },
    ["@constant.builtin"] = { fg = syn.constant, bold = true },
    ["@constant.macro"] = { fg = syn.constant },
    ["@type"] = { fg = syn.type },
    ["@type.builtin"] = { fg = syn.type },
    ["@type.definition"] = { fg = syn.type, bold = true },
    ["@module"] = { fg = syn.type },
    ["@variable"] = { fg = ui.text },
    ["@variable.builtin"] = { fg = syn.keyword, italic = true },
    ["@variable.parameter"] = { fg = syn.parameter },
    ["@variable.member"] = { fg = syn.property },
    ["@property"] = { fg = syn.property },
    ["@attribute"] = { fg = syn.constant },
    ["@operator"] = { fg = syn.operator },
    ["@punctuation.delimiter"] = { fg = syn.punctuation },
    ["@punctuation.bracket"] = { fg = syn.punctuation },
    ["@punctuation.special"] = { fg = syn.constant },
    ["@tag"] = { fg = syn.tag },
    ["@tag.attribute"] = { fg = syn.property },
    ["@tag.delimiter"] = { fg = syn.punctuation },
    ["@markup.heading"] = { fg = syn["function"], bold = true },
    ["@markup.heading.1"] = { fg = ui.accent, bold = true },
    ["@markup.heading.2"] = { fg = ui.secondary, bold = true },
    ["@markup.heading.3"] = { fg = syn.type, bold = true },
    ["@markup.strong"] = { fg = ui.text, bold = true },
    ["@markup.italic"] = { fg = ui.text_soft, italic = true },
    ["@markup.strikethrough"] = { fg = ui.subtle, strikethrough = true },
    ["@markup.link"] = { fg = ui.secondary },
    ["@markup.link.url"] = { fg = ui.accent, underline = true },
    ["@markup.raw"] = { fg = syn.string },
    ["@markup.list"] = { fg = ui.accent },
    ["@markup.quote"] = { fg = syn.comment, italic = true },
    ["@diff.plus"] = { fg = syn.diff_add },
    ["@diff.minus"] = { fg = syn.diff_del },
    ["@diff.delta"] = { fg = syn.diff_change },

    -- LSP semantic tokens
    ["@lsp.type.class"] = { fg = syn.type, bold = true },
    ["@lsp.type.comment"] = { fg = syn.comment, italic = italic_cmt },
    ["@lsp.type.decorator"] = { fg = syn.constant },
    ["@lsp.type.enum"] = { fg = syn.type },
    ["@lsp.type.enumMember"] = { fg = syn.constant },
    ["@lsp.type.function"] = { fg = syn["function"] },
    ["@lsp.type.interface"] = { fg = syn.type, italic = true },
    ["@lsp.type.macro"] = { fg = syn.keyword, bold = true },
    ["@lsp.type.method"] = { fg = syn["function"] },
    ["@lsp.type.namespace"] = { fg = syn.type },
    ["@lsp.type.parameter"] = { fg = syn.parameter },
    ["@lsp.type.property"] = { fg = syn.property },
    ["@lsp.type.struct"] = { fg = syn.type, bold = true },
    ["@lsp.type.type"] = { fg = syn.type },
    ["@lsp.type.typeParameter"] = { fg = syn.property },
    ["@lsp.type.variable"] = { fg = ui.text },
    ["@lsp.mod.readonly"] = { fg = syn.constant },
    ["@lsp.mod.deprecated"] = { strikethrough = true },

    -- Diagnostics & LSP UI
    DiagnosticError = { fg = ui.fault },
    DiagnosticWarn = { fg = ui.warning },
    DiagnosticInfo = { fg = ui.secondary },
    DiagnosticHint = { fg = ui.cyan },
    DiagnosticOk = { fg = ui.signal },
    DiagnosticVirtualTextError = { fg = ui.fault, bg = ui.diff_del_bg },
    DiagnosticVirtualTextWarn = { fg = ui.warning, bg = ui.find_match },
    DiagnosticVirtualTextInfo = { fg = ui.secondary, bg = ui.diff_chg_bg },
    DiagnosticVirtualTextHint = { fg = ui.cyan, bg = ui.surface },
    DiagnosticUnderlineError = { undercurl = true, sp = ui.fault },
    DiagnosticUnderlineWarn = { undercurl = true, sp = ui.warning },
    DiagnosticUnderlineInfo = { undercurl = true, sp = ui.secondary },
    DiagnosticUnderlineHint = { undercurl = true, sp = ui.cyan },
    DiagnosticSignError = { fg = ui.fault },
    DiagnosticSignWarn = { fg = ui.warning },
    DiagnosticSignInfo = { fg = ui.secondary },
    DiagnosticSignHint = { fg = ui.cyan },
    LspReferenceText = { bg = ui.selection_bg },
    LspReferenceRead = { bg = ui.selection_bg },
    LspReferenceWrite = { bg = ui.selection_active },
    LspInlayHint = { fg = ui.subtle, bg = ui.surface, italic = true },

    -- Telescope
    TelescopeNormal = { fg = ui.text, bg = ui.surface },
    TelescopeBorder = { fg = ui.border_strong, bg = ui.surface },
    TelescopeTitle = { fg = ui.accent, bold = true },
    TelescopePromptNormal = { fg = ui.text, bg = ui.raised },
    TelescopePromptBorder = { fg = ui.accent, bg = ui.raised },
    TelescopePromptTitle = { fg = ui.on_accent, bg = ui.accent_fill, bold = true },
    TelescopePromptPrefix = { fg = ui.accent, bold = true },
    TelescopeSelection = { fg = ui.text, bg = ui.selection_active, bold = true },
    TelescopeSelectionCaret = { fg = ui.accent, bg = ui.selection_active },
    TelescopeMatching = { fg = ui.accent, bold = true },

    -- Gitsigns
    GitSignsAdd = { fg = ui.signal },
    GitSignsChange = { fg = ui.secondary },
    GitSignsDelete = { fg = ui.fault },
    GitSignsCurrentLineBlame = { fg = ui.subtle, italic = true },

    -- Neo-tree
    NeoTreeNormal = { fg = ui.text_soft, bg = ui.surface },
    NeoTreeNormalNC = { fg = ui.text_soft, bg = ui.surface },
    NeoTreeWinSeparator = { fg = ui.border, bg = ui.surface },
    NeoTreeDirectoryName = { fg = ui.secondary },
    NeoTreeDirectoryIcon = { fg = ui.secondary },
    NeoTreeRootName = { fg = ui.accent, bold = true },
    NeoTreeGitAdded = { fg = ui.signal },
    NeoTreeGitModified = { fg = ui.secondary },
    NeoTreeGitDeleted = { fg = ui.fault },
    NeoTreeGitUntracked = { fg = ui.warning },
    NeoTreeIndentMarker = { fg = ui.border },

    -- WhichKey
    WhichKey = { fg = ui.accent, bold = true },
    WhichKeyGroup = { fg = ui.secondary },
    WhichKeyDesc = { fg = ui.text },
    WhichKeySeparator = { fg = ui.subtle },
    WhichKeyFloat = { bg = ui.surface },
    WhichKeyBorder = { fg = ui.border_strong, bg = ui.surface },
  }

  for group, spec in pairs(groups) do
    vim.api.nvim_set_hl(0, group, spec)
  end

  if M.config.terminal_colors then
    set_terminal_colors(p.terminal)
  end
end

return M
"""


def _neovim_lualine_lua() -> str:
    return """-- Cyclorama Dawn v2.1.0 Lualine theme helper
-- Usage: require("lualine").setup({ options = { theme = require("cyclorama.lualine") } })
local cyclorama = require("cyclorama")
local p = cyclorama.get_palette(vim.g.colors_name)
local ui = p.ui

return {
  normal = {
    a = { fg = ui.on_accent, bg = ui.accent_fill, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  insert = {
    a = { fg = ui.bg, bg = ui.signal, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  visual = {
    a = { fg = ui.on_accent, bg = ui.secondary_fill, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  replace = {
    a = { fg = ui.on_accent, bg = ui.fault_fill, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  command = {
    a = { fg = ui.bg, bg = ui.warning, gui = "bold" },
    b = { fg = ui.text, bg = ui.raised },
    c = { fg = ui.mute, bg = ui.surface },
  },
  inactive = {
    a = { fg = ui.mute, bg = ui.rail },
    b = { fg = ui.subtle, bg = ui.rail },
    c = { fg = ui.subtle, bg = ui.rail },
  },
}
"""


def _neovim_copy_snippet(v: dict) -> str:
    vid = v["id"]
    return (
        "-- lazy.nvim specification (point `dir` to your local clone of apps/neovim)\n"
        "{\n"
        '  "Real-Fruit-Snacks/rfs-themes",\n'
        f'  name = "{vid}",\n'
        "  priority = 1000,\n"
        "  config = function(plugin)\n"
        '    vim.opt.rtp:append(plugin.dir .. "/apps/neovim")\n'
        '    require("cyclorama").setup({\n'
        f'      variant = "{vid}",\n'
        "      transparent = false,\n"
        "      italic_comments = true,\n"
        "      terminal_colors = true,\n"
        "    })\n"
        f'    vim.cmd.colorscheme("{vid}")\n'
        "  end,\n"
        "}"
    )


def build_neovim() -> dict:
    slug = "neovim"
    app_name = "Neovim"
    homepage = "https://neovim.io/"
    fmt = "Lua Colorscheme Plugin"
    install = "Add apps/neovim to runtimepath (lazy.nvim/packer) and run :colorscheme cyclorama-dawn"
    install_steps = [
        "Clone `rfs-themes` or copy `apps/neovim/` into your Neovim plugin directory (or add via `lazy.nvim` using `rtp:append`).",
        "Run `:colorscheme cyclorama-dawn`, `:colorscheme cyclorama-steel`, or `:colorscheme cyclorama-day`.",
        "Optional: pass `theme = require(\"cyclorama.lualine\")` to `lualine.nvim` for a matched statusline.",
    ]

    ver = VARIANTS["cyclorama-dawn"]["version"]
    _write_text(f"apps/{slug}/lua/cyclorama/palette.lua", _neovim_palette_lua())
    _write_text(f"apps/{slug}/lua/cyclorama/init.lua", _neovim_init_lua())
    _write_text(f"apps/{slug}/lua/cyclorama/lualine.lua", _neovim_lualine_lua())

    files = [
        {"label": "Core colorscheme (lua/cyclorama/init.lua)", "path": f"apps/{slug}/lua/cyclorama/init.lua"},
        {"label": "Palette tables (lua/cyclorama/palette.lua)", "path": f"apps/{slug}/lua/cyclorama/palette.lua"},
        {"label": "Lualine helper (lua/cyclorama/lualine.lua)", "path": f"apps/{slug}/lua/cyclorama/lualine.lua"},
    ]
    theme_entries = []
    variant_files: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        rel_in_app = f"colors/{vid}.lua"
        rel_repo = f"apps/{slug}/{rel_in_app}"
        variant_files[vid] = rel_in_app
        _write_text(rel_repo, f'require("cyclorama").load("{vid}")\n')

        svg = render_editor_preview(
            app_name,
            slug,
            v,
            active_file="init.lua",
            footer_left="NORMAL  ·  init.lua  ·  UTF-8",
        )
        write_preview_pair(slug, vid, svg)

        files.append({"label": f"{v['name']} ({rel_in_app})", "path": rel_repo})
        theme_entries.append(
            {
                "id": vid,
                "name": v["name"],
                "lx": v["lx"],
                "mode": v["mode"],
                "accentRole": v["accentRole"],
                "tagline": v["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": rel_repo,
                "copyLang": "lua",
                "copyLabel": "lazy.nvim spec",
                "copySnippet": _neovim_copy_snippet(v),
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
        "primaryFile": f"apps/{slug}/lua/cyclorama/init.lua",
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
            extra_notes="Includes Treesitter (`@...`), LSP semantic tokens (`@lsp.type.*`), Diagnostics, Telescope, Gitsigns, Neo-tree, WhichKey, Lualine (`require(\"cyclorama.lualine\")`), and ANSI 0-15 terminal colors.",
        ),
    )
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# =============================================================================
# 3. Zed Editor (v0.2.0)
# =============================================================================


def _zed_syntax_style(color: str, font_style: str | None = None, font_weight: int | None = None) -> dict:
    return {
        "color": color,
        "font_style": font_style,
        "font_weight": font_weight,
    }


def _zed_variant_obj(v: dict) -> dict:
    ui = v["ui"]
    syn = v["syntax"]
    ansi = v["ansi"]
    is_dark = v["mode"] == "dark"

    transparent = with_alpha(ui["bg"], "00")
    hover_el = mix(ui["surface"], ui["accent"], 0.12 if is_dark else 0.09)
    active_el = mix(ui["surface"], ui["accent"], 0.20 if is_dark else 0.16)
    drop_bg = with_alpha(ui["accent"], "28")
    doc_read = with_alpha(ui["secondary"], "26" if is_dark else "33")
    doc_write = with_alpha(ui["accent"], "33" if is_dark else "3D")
    search_match = with_alpha(ui["warning"], "44" if is_dark else "55")
    dim_factor = 0.25 if is_dark else 0.20
    dim_base = ui["bg"]

    style = {
        "border": ui["border"],
        "border.variant": ui["border_subtle"],
        "border.focused": ui["accent"],
        "border.selected": ui["secondary"],
        "border.transparent": transparent,
        "border.disabled": ui["border_subtle"],
        "elevated_surface.background": ui["raised"],
        "surface.background": ui["surface"],
        "background": ui["rail"],
        "element.background": ui["raised"],
        "element.hover": hover_el,
        "element.active": active_el,
        "element.selected": ui["selection_active"],
        "element.disabled": ui["surface"],
        "drop_target.background": drop_bg,
        "ghost_element.background": transparent,
        "ghost_element.hover": hover_el,
        "ghost_element.active": active_el,
        "ghost_element.selected": ui["selection_bg"],
        "ghost_element.disabled": transparent,
        "text": ui["text"],
        "text.muted": ui["mute"],
        "text.placeholder": ui["subtle"],
        "text.disabled": ui["subtle"],
        "text.accent": ui["accent"],
        "icon": ui["text_soft"],
        "icon.muted": ui["mute"],
        "icon.disabled": ui["subtle"],
        "icon.placeholder": ui["subtle"],
        "icon.accent": ui["accent"],
        "status_bar.background": ui["rail"],
        "title_bar.background": ui["rail"],
        "title_bar.inactive_background": ui["rail"],
        "toolbar.background": ui["bg"],
        "tab_bar.background": ui["rail"],
        "tab.inactive_background": ui["rail"],
        "tab.active_background": ui["bg"],
        "search.match_background": search_match,
        "panel.background": ui["surface"],
        "panel.focused_border": ui["accent"],
        "pane.focused_border": ui["accent"],
        "scrollbar.thumb.background": with_alpha(ui["border_strong"], "66"),
        "scrollbar.thumb.hover_background": with_alpha(ui["border_strong"], "99"),
        "scrollbar.thumb.border": ui["border"],
        "scrollbar.track.background": transparent,
        "scrollbar.track.border": ui["border_subtle"],
        "editor.foreground": ui["text"],
        "editor.background": ui["bg"],
        "editor.gutter.background": ui["bg"],
        "editor.subheader.background": ui["surface"],
        "editor.active_line.background": ui["raised"],
        "editor.highlighted_line.background": ui["raised"],
        "editor.line_number": ui["subtle"],
        "editor.active_line_number": ui["text"],
        "editor.invisible": ui["border"],
        "editor.wrap_guide": ui["border_subtle"],
        "editor.active_wrap_guide": ui["border_strong"],
        "editor.document_highlight.read_background": doc_read,
        "editor.document_highlight.write_background": doc_write,
        "terminal.background": ui["bg"],
        "terminal.foreground": ui["text"],
        "terminal.bright_foreground": ui["text"],
        "terminal.dim_foreground": ui["mute"],
        "terminal.ansi.black": ansi["black"],
        "terminal.ansi.bright_black": ansi["brightBlack"],
        "terminal.ansi.dim_black": mix(ansi["black"], dim_base, dim_factor),
        "terminal.ansi.red": ansi["red"],
        "terminal.ansi.bright_red": ansi["brightRed"],
        "terminal.ansi.dim_red": mix(ansi["red"], dim_base, dim_factor),
        "terminal.ansi.green": ansi["green"],
        "terminal.ansi.bright_green": ansi["brightGreen"],
        "terminal.ansi.dim_green": mix(ansi["green"], dim_base, dim_factor),
        "terminal.ansi.yellow": ansi["yellow"],
        "terminal.ansi.bright_yellow": ansi["brightYellow"],
        "terminal.ansi.dim_yellow": mix(ansi["yellow"], dim_base, dim_factor),
        "terminal.ansi.blue": ansi["blue"],
        "terminal.ansi.bright_blue": ansi["brightBlue"],
        "terminal.ansi.dim_blue": mix(ansi["blue"], dim_base, dim_factor),
        "terminal.ansi.magenta": ansi["magenta"],
        "terminal.ansi.bright_magenta": ansi["brightMagenta"],
        "terminal.ansi.dim_magenta": mix(ansi["magenta"], dim_base, dim_factor),
        "terminal.ansi.cyan": ansi["cyan"],
        "terminal.ansi.bright_cyan": ansi["brightCyan"],
        "terminal.ansi.dim_cyan": mix(ansi["cyan"], dim_base, dim_factor),
        "terminal.ansi.white": ansi["white"],
        "terminal.ansi.bright_white": ansi["brightWhite"],
        "terminal.ansi.dim_white": mix(ansi["white"], dim_base, dim_factor),
        "link_text.hover": ui["accent_hover"],
        "conflict": ui["warning"],
        "conflict.background": ui["find_match"],
        "conflict.border": ui["warning"],
        "created": ui["signal"],
        "created.background": ui["diff_add_bg"],
        "created.border": ui["signal"],
        "deleted": ui["fault"],
        "deleted.background": ui["diff_del_bg"],
        "deleted.border": ui["fault"],
        "error": ui["fault"],
        "error.background": ui["diff_del_bg"],
        "error.border": ui["fault"],
        "hidden": ui["subtle"],
        "hidden.background": ui["surface"],
        "hidden.border": ui["border_subtle"],
        "hint": ui["cyan"],
        "hint.background": ui["surface"],
        "hint.border": ui["cyan"],
        "ignored": ui["subtle"],
        "ignored.background": ui["surface"],
        "ignored.border": ui["border_subtle"],
        "info": ui["secondary"],
        "info.background": ui["diff_chg_bg"],
        "info.border": ui["secondary"],
        "modified": ui["secondary"],
        "modified.background": ui["diff_chg_bg"],
        "modified.border": ui["secondary"],
        "predictive": ui["subtle"],
        "predictive.background": ui["surface"],
        "predictive.border": ui["border"],
        "renamed": ui["cyan"],
        "renamed.background": ui["diff_chg_bg"],
        "renamed.border": ui["cyan"],
        "success": ui["signal"],
        "success.background": ui["diff_add_bg"],
        "success.border": ui["signal"],
        "unreachable": ui["mute"],
        "unreachable.background": ui["surface"],
        "unreachable.border": ui["border"],
        "warning": ui["warning"],
        "warning.background": ui["find_match"],
        "warning.border": ui["warning"],
        "players": [
            {
                "cursor": ui["cursor"],
                "background": ui["cursor"],
                "selection": with_alpha(ui["accent"], "3D"),
            },
            {
                "cursor": ui["secondary"],
                "background": ui["secondary"],
                "selection": with_alpha(ui["secondary"], "3D"),
            },
            {
                "cursor": ui["signal"],
                "background": ui["signal"],
                "selection": with_alpha(ui["signal"], "3D"),
            },
            {
                "cursor": ui["warning"],
                "background": ui["warning"],
                "selection": with_alpha(ui["warning"], "3D"),
            },
            {
                "cursor": ui["magenta"],
                "background": ui["magenta"],
                "selection": with_alpha(ui["magenta"], "3D"),
            },
            {
                "cursor": ui["cyan"],
                "background": ui["cyan"],
                "selection": with_alpha(ui["cyan"], "3D"),
            },
        ],
        "syntax": {
            "attribute": _zed_syntax_style(syn["property"]),
            "boolean": _zed_syntax_style(syn["number"], font_weight=700),
            "comment": _zed_syntax_style(syn["comment"], font_style="italic"),
            "comment.doc": _zed_syntax_style(syn["comment"], font_style="italic"),
            "constant": _zed_syntax_style(syn["constant"]),
            "constructor": _zed_syntax_style(syn["type"]),
            "embedded": _zed_syntax_style(ui["text"]),
            "emphasis": _zed_syntax_style(ui["text_soft"], font_style="italic"),
            "emphasis.strong": _zed_syntax_style(ui["text"], font_weight=700),
            "enum": _zed_syntax_style(syn["type"]),
            "function": _zed_syntax_style(syn["function"]),
            "hint": _zed_syntax_style(ui["subtle"], font_style="italic"),
            "keyword": _zed_syntax_style(syn["keyword"]),
            "label": _zed_syntax_style(syn["property"]),
            "link_text": _zed_syntax_style(syn["keyword"]),
            "link_uri": _zed_syntax_style(ui["accent"]),
            "number": _zed_syntax_style(syn["number"]),
            "operator": _zed_syntax_style(syn["operator"]),
            "predictive": _zed_syntax_style(ui["subtle"], font_style="italic"),
            "preproc": _zed_syntax_style(syn["keyword"]),
            "primary": _zed_syntax_style(ui["text"]),
            "property": _zed_syntax_style(syn["property"]),
            "punctuation": _zed_syntax_style(syn["punctuation"]),
            "punctuation.bracket": _zed_syntax_style(syn["punctuation"]),
            "punctuation.delimiter": _zed_syntax_style(syn["punctuation"]),
            "punctuation.list_marker": _zed_syntax_style(ui["accent"]),
            "punctuation.special": _zed_syntax_style(syn["constant"]),
            "string": _zed_syntax_style(syn["string"]),
            "string.escape": _zed_syntax_style(syn["constant"]),
            "string.regex": _zed_syntax_style(syn["constant"]),
            "string.special": _zed_syntax_style(syn["constant"]),
            "string.special.symbol": _zed_syntax_style(syn["constant"]),
            "tag": _zed_syntax_style(syn["tag"]),
            "text.literal": _zed_syntax_style(syn["string"]),
            "title": _zed_syntax_style(syn["function"], font_weight=700),
            "type": _zed_syntax_style(syn["type"]),
            "variable": _zed_syntax_style(ui["text"]),
            "variable.special": _zed_syntax_style(syn["parameter"]),
            "variant": _zed_syntax_style(syn["constant"]),
        },
    }

    return {
        "name": v["name"],
        "appearance": v["mode"],
        "style": style,
    }


def _zed_copy_snippet(v: dict) -> str:
    dark_name = v["name"] if v["mode"] == "dark" else "Cyclorama Dawn"
    light_name = v["name"] if v["mode"] == "light" else "Cyclorama Day"
    snippet = {
        "theme": {
            "mode": "dark" if v["mode"] == "dark" else "light",
            "dark": dark_name,
            "light": light_name,
        }
    }
    return json.dumps(snippet, indent=2)


def build_zed() -> dict:
    slug = "zed"
    app_name = "Zed"
    homepage = "https://zed.dev/"
    fmt = "Zed JSON Theme (v0.2.0)"
    install = "Copy apps/zed/themes/cyclorama.json into ~/.config/zed/themes/ and select theme"
    install_steps = [
        "Copy `apps/zed/themes/cyclorama.json` into `~/.config/zed/themes/` (or `%APPDATA%\\Zed\\themes\\` on Windows) for all three variants in one pack, or copy an individual `cyclorama-*.json` file.",
        "Open Zed's theme selector (`Ctrl+K Ctrl+T` / `Cmd+K Cmd+T`) and pick **Cyclorama Dawn**, **Cyclorama Steel**, or **Cyclorama Day**.",
        "Optional: set `theme.dark` and `theme.light` in `~/.config/zed/settings.json` to follow your OS dark/light mode.",
    ]

    ver = VARIANTS["cyclorama-dawn"]["version"]
    schema = "https://zed.dev/schema/themes/v0.2.0.json"

    all_theme_objs = [_zed_variant_obj(VARIANTS[vid]) for vid in VARIANT_ORDER]
    unified_pack = {
        "$schema": schema,
        "name": BRAND_NAME,
        "author": AUTHOR,
        "themes": all_theme_objs,
    }
    _write_json(f"apps/{slug}/themes/cyclorama.json", unified_pack)

    files = [{"label": "Unified 3-theme pack (cyclorama.json)", "path": f"apps/{slug}/themes/cyclorama.json"}]
    theme_entries = []
    variant_files: dict[str, str] = {}

    for idx, vid in enumerate(VARIANT_ORDER):
        v = VARIANTS[vid]
        rel_in_app = f"themes/{vid}.json"
        rel_repo = f"apps/{slug}/{rel_in_app}"
        variant_files[vid] = rel_in_app
        single_pack = {
            "$schema": schema,
            "name": v["name"],
            "author": AUTHOR,
            "themes": [all_theme_objs[idx]],
        }
        _write_json(rel_repo, single_pack)

        svg = render_editor_preview(
            app_name,
            slug,
            v,
            active_file="theme.rs",
            footer_left="main  ·  Rust  ·  Zed",
        )
        write_preview_pair(slug, vid, svg)

        files.append({"label": f"{v['name']} ({vid}.json)", "path": rel_repo})
        theme_entries.append(
            {
                "id": vid,
                "name": v["name"],
                "lx": v["lx"],
                "mode": v["mode"],
                "accentRole": v["accentRole"],
                "tagline": v["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": rel_repo,
                "copyLang": "json",
                "copyLabel": "Zed settings.json",
                "copySnippet": _zed_copy_snippet(v),
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
        "primaryFile": f"apps/{slug}/themes/cyclorama.json",
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
            extra_notes="Drop [`themes/cyclorama.json`](themes/cyclorama.json) into `~/.config/zed/themes/` to install all three variants at once, or use the individual variant files below.",
        ),
    )
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# =============================================================================
# 4. JetBrains IDEs (.icls + .theme.json + META-INF/plugin.xml)
# =============================================================================


def _icls_option(name: str, fg: str | None = None, bg: str | None = None, font_type: int | None = None, effect_color: str | None = None, effect_type: int | None = None) -> str:
    inner = []
    if fg is not None:
        inner.append(f'        <option name="FOREGROUND" value="{_icls_hex(fg)}" />')
    if bg is not None:
        inner.append(f'        <option name="BACKGROUND" value="{_icls_hex(bg)}" />')
    if font_type is not None:
        inner.append(f'        <option name="FONT_TYPE" value="{font_type}" />')
    if effect_color is not None:
        inner.append(f'        <option name="EFFECT_COLOR" value="{_icls_hex(effect_color)}" />')
    if effect_type is not None:
        inner.append(f'        <option name="EFFECT_TYPE" value="{effect_type}" />')
    body = "\n".join(inner)
    return f'    <option name="{name}">\n      <value>\n{body}\n      </value>\n    </option>'


def _jetbrains_icls_xml(v: dict) -> str:
    ui = v["ui"]
    syn = v["syntax"]
    ansi = v["ansi"]
    parent = "Darcula" if v["mode"] == "dark" else "Default"

    colors_map = [
        ("ADDED_LINES_COLOR", ui["signal"]),
        ("ANNOTATIONS_COLOR", ui["mute"]),
        ("BORDER_LINES_COLOR", ui["border"]),
        ("CARET_COLOR", ui["cursor"]),
        ("CARET_ROW_COLOR", ui["raised"]),
        ("CONSOLE_BACKGROUND_KEY", ui["code_bg"]),
        ("DELETED_LINES_COLOR", ui["fault"]),
        ("DOC_COMMENT_LINK", ui["accent"]),
        ("FILESTATUS_ADDED", ui["signal"]),
        ("FILESTATUS_DELETED", ui["fault"]),
        ("FILESTATUS_IDEA_FILESTATUS_IGNORED", ui["subtle"]),
        ("FILESTATUS_MERGED_WITH_CONFLICTS", ui["warning"]),
        ("FILESTATUS_MODIFIED", ui["secondary"]),
        ("FILESTATUS_UNKNOWN", ui["warning"]),
        ("GUTTER_BACKGROUND", ui["bg"]),
        ("INDENT_GUIDE", ui["border_subtle"]),
        ("LINE_NUMBERS_COLOR", ui["subtle"]),
        ("LINE_NUMBER_ON_CARET_ROW_COLOR", ui["text"]),
        ("METHOD_SEPARATORS_COLOR", ui["border"]),
        ("MODIFIED_LINES_COLOR", ui["secondary"]),
        ("RIGHT_MARGIN_COLOR", ui["border_subtle"]),
        ("SELECTED_INDENT_GUIDE", ui["border_strong"]),
        ("SELECTED_TEARLINE_COLOR", ui["accent"]),
        ("SELECTION_BACKGROUND", ui["selection_active"]),
        ("SELECTION_FOREGROUND", ui["text"]),
        ("TEARLINE_COLOR", ui["border"]),
        ("VISUAL_INDENT_GUIDE", ui["border_subtle"]),
        ("WHITESPACES", ui["border"]),
        ("WHITESPACES_MODIFIED_LINES_COLOR", ui["secondary"]),
    ]

    color_lines = [
        f'    <option name="{k}" value="{_icls_hex(val)}" />'
        for k, val in colors_map
    ]

    attrs = [
        _icls_option("TEXT", fg=ui["text"], bg=ui["bg"]),
        # Syntax
        _icls_option("DEFAULT_KEYWORD", fg=syn["keyword"], font_type=1),
        _icls_option("DEFAULT_FUNCTION_DECLARATION", fg=syn["function"]),
        _icls_option("DEFAULT_FUNCTION_CALL", fg=syn["function"]),
        _icls_option("DEFAULT_INSTANCE_METHOD", fg=syn["function"]),
        _icls_option("DEFAULT_STATIC_METHOD", fg=syn["function"], font_type=2),
        _icls_option("DEFAULT_STRING", fg=syn["string"]),
        _icls_option("DEFAULT_VALID_STRING_ESCAPE", fg=syn["constant"]),
        _icls_option("DEFAULT_INVALID_STRING_ESCAPE", fg=ui["fault"], effect_color=ui["fault"], effect_type=2),
        _icls_option("DEFAULT_NUMBER", fg=syn["number"]),
        _icls_option("DEFAULT_LINE_COMMENT", fg=syn["comment"], font_type=2),
        _icls_option("DEFAULT_BLOCK_COMMENT", fg=syn["comment"], font_type=2),
        _icls_option("DEFAULT_DOC_COMMENT", fg=syn["comment"], font_type=2),
        _icls_option("DEFAULT_DOC_COMMENT_TAG", fg=syn["keyword"], font_type=3),
        _icls_option("DEFAULT_CLASS_NAME", fg=syn["type"], font_type=1),
        _icls_option("DEFAULT_INTERFACE_NAME", fg=syn["type"], font_type=2),
        _icls_option("DEFAULT_CLASS_REFERENCE", fg=syn["type"]),
        _icls_option("DEFAULT_CONSTANT", fg=syn["constant"]),
        _icls_option("DEFAULT_STATIC_FIELD", fg=syn["constant"], font_type=2),
        _icls_option("DEFAULT_PARAMETER", fg=syn["parameter"]),
        _icls_option("DEFAULT_LOCAL_VARIABLE", fg=ui["text"]),
        _icls_option("DEFAULT_IDENTIFIER", fg=ui["text"]),
        _icls_option("DEFAULT_INSTANCE_FIELD", fg=syn["property"]),
        _icls_option("DEFAULT_METADATA", fg=syn["constant"]),
        _icls_option("DEFAULT_OPERATION_SIGN", fg=syn["operator"]),
        _icls_option("DEFAULT_BRACES", fg=syn["punctuation"]),
        _icls_option("DEFAULT_BRACKETS", fg=syn["punctuation"]),
        _icls_option("DEFAULT_PARENTHS", fg=syn["punctuation"]),
        _icls_option("DEFAULT_COMMA", fg=syn["punctuation"]),
        _icls_option("DEFAULT_SEMICOLON", fg=syn["punctuation"]),
        _icls_option("DEFAULT_DOT", fg=syn["punctuation"]),
        _icls_option("DEFAULT_TAG", fg=syn["tag"]),
        _icls_option("DEFAULT_ATTRIBUTE", fg=syn["property"]),
        _icls_option("HTML_TAG_NAME", fg=syn["tag"]),
        _icls_option("XML_TAG_NAME", fg=syn["tag"]),
        _icls_option("JSON.PROPERTY_KEY", fg=syn["property"]),
        _icls_option("YAML_SCALAR_KEY", fg=syn["property"]),
        _icls_option("KOTLIN_NAMED_ARGUMENT", fg=syn["parameter"]),
        _icls_option("KOTLIN_FUNCTION_LITERAL_BRACES_AND_ARROW", fg=syn["keyword"], font_type=1),
        _icls_option("MARKDOWN_HEADER_LEVEL_1", fg=ui["accent"], font_type=1),
        _icls_option("MARKDOWN_HEADER_LEVEL_2", fg=ui["secondary"], font_type=1),
        _icls_option("MARKDOWN_CODE_SPAN", fg=syn["string"], bg=ui["code_bg"]),
        _icls_option("MARKDOWN_LINK_DESTINATION", fg=ui["accent"]),
        # Editor states & diagnostics
        _icls_option("ERRORS_ATTRIBUTES", effect_color=ui["fault"], effect_type=2),
        _icls_option("WARNING_ATTRIBUTES", effect_color=ui["warning"], effect_type=2),
        _icls_option("INFO_ATTRIBUTES", effect_color=ui["secondary"], effect_type=2),
        _icls_option("DEPRECATED_ATTRIBUTES", effect_color=ui["subtle"], effect_type=3),
        _icls_option("TODO_DEFAULT_ATTRIBUTES", fg=ui["accent"], font_type=3),
        _icls_option("HYPERLINK_ATTRIBUTES", fg=ui["accent"], effect_color=ui["accent"], effect_type=1),
        _icls_option("FOLLOWED_HYPERLINK_ATTRIBUTES", fg=ui["secondary"], effect_color=ui["secondary"], effect_type=1),
        _icls_option("MATCHED_BRACE_ATTRIBUTES", fg=ui["accent"], bg=ui["overlay"], font_type=1),
        _icls_option("SEARCH_RESULT_ATTRIBUTES", bg=ui["find_match"]),
        _icls_option("WRITE_SEARCH_RESULT_ATTRIBUTES", bg=ui["selection_active"]),
        _icls_option("TEXT_SEARCH_RESULT_ATTRIBUTES", bg=ui["find_match"], effect_color=ui["warning"], effect_type=4),
        _icls_option("IDENTIFIER_UNDER_CARET_ATTRIBUTES", bg=ui["selection_bg"]),
        _icls_option("WRITE_IDENTIFIER_UNDER_CARET_ATTRIBUTES", bg=ui["selection_active"]),
        _icls_option("INLAY_DEFAULT", fg=ui["subtle"], bg=ui["surface"]),
        _icls_option("FOLDED_TEXT_ATTRIBUTES", fg=ui["mute"], bg=ui["surface"]),
        # Diff
        _icls_option("DIFF_INSERTED", bg=ui["diff_add_bg"]),
        _icls_option("DIFF_DELETED", bg=ui["diff_del_bg"]),
        _icls_option("DIFF_MODIFIED", bg=ui["diff_chg_bg"]),
        _icls_option("DIFF_CONFLICT", bg=ui["find_match"]),
        # Console ANSI 0-15
        _icls_option("CONSOLE_NORMAL_OUTPUT", fg=ui["text"]),
        _icls_option("CONSOLE_SYSTEM_OUTPUT", fg=ui["mute"]),
        _icls_option("CONSOLE_USER_INPUT", fg=ui["signal"], font_type=2),
        _icls_option("CONSOLE_ERROR_OUTPUT", fg=ui["fault"]),
        _icls_option("CONSOLE_BLACK_OUTPUT", fg=ansi["black"]),
        _icls_option("CONSOLE_RED_OUTPUT", fg=ansi["red"]),
        _icls_option("CONSOLE_GREEN_OUTPUT", fg=ansi["green"]),
        _icls_option("CONSOLE_YELLOW_OUTPUT", fg=ansi["yellow"]),
        _icls_option("CONSOLE_BLUE_OUTPUT", fg=ansi["blue"]),
        _icls_option("CONSOLE_MAGENTA_OUTPUT", fg=ansi["magenta"]),
        _icls_option("CONSOLE_CYAN_OUTPUT", fg=ansi["cyan"]),
        _icls_option("CONSOLE_GRAY_OUTPUT", fg=ansi["white"]),
        _icls_option("CONSOLE_DARKGRAY_OUTPUT", fg=ansi["brightBlack"]),
        _icls_option("CONSOLE_RED_BRIGHT_OUTPUT", fg=ansi["brightRed"]),
        _icls_option("CONSOLE_GREEN_BRIGHT_OUTPUT", fg=ansi["brightGreen"]),
        _icls_option("CONSOLE_YELLOW_BRIGHT_OUTPUT", fg=ansi["brightYellow"]),
        _icls_option("CONSOLE_BLUE_BRIGHT_OUTPUT", fg=ansi["brightBlue"]),
        _icls_option("CONSOLE_MAGENTA_BRIGHT_OUTPUT", fg=ansi["brightMagenta"]),
        _icls_option("CONSOLE_CYAN_BRIGHT_OUTPUT", fg=ansi["brightCyan"]),
        _icls_option("CONSOLE_WHITE_OUTPUT", fg=ansi["brightWhite"]),
    ]

    return (
        f'<scheme name="{v["name"]}" version="142" parent_scheme="{parent}">\n'
        "  <metaInfo>\n"
        f'    <property name="author">{AUTHOR}</property>\n'
        f'    <property name="brandVersion">{v["version"]}</property>\n'
        '    <property name="ide">idea</property>\n'
        f'    <property name="originalScheme">{v["name"]}</property>\n'
        "  </metaInfo>\n"
        "  <colors>\n"
        + "\n".join(color_lines)
        + "\n  </colors>\n"
        "  <attributes>\n"
        + "\n".join(attrs)
        + "\n  </attributes>\n"
        "</scheme>\n"
    )


def _jetbrains_theme_json(v: dict) -> dict:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    hover_bg = mix(ui["surface"], ui["accent"], 0.12 if is_dark else 0.09)

    return {
        "name": v["name"],
        "dark": is_dark,
        "author": AUTHOR,
        "editorScheme": f"/schemes/{v['name']}.icls",
        "colors": {
            "bg": ui["bg"],
            "rail": ui["rail"],
            "surface": ui["surface"],
            "raised": ui["raised"],
            "overlay": ui["overlay"],
            "border": ui["border"],
            "borderSubtle": ui["border_subtle"],
            "borderStrong": ui["border_strong"],
            "text": ui["text"],
            "textSoft": ui["text_soft"],
            "mute": ui["mute"],
            "subtle": ui["subtle"],
            "accent": ui["accent"],
            "accentHover": ui["accent_hover"],
            "accentFill": ui["accent_fill"],
            "accentFillHover": ui["accent_fill_hover"],
            "onAccent": ui["on_accent"],
            "secondary": ui["secondary"],
            "secondaryFill": ui["secondary_fill"],
            "signal": ui["signal"],
            "warning": ui["warning"],
            "fault": ui["fault"],
            "selectionBg": ui["selection_bg"],
            "selectionActive": ui["selection_active"],
            "hoverBg": hover_bg,
        },
        "ui": {
            "*": {
                "background": "surface",
                "foreground": "text",
                "infoForeground": "mute",
                "selectionBackground": "selectionActive",
                "selectionForeground": "text",
                "selectionInactiveBackground": "selectionBg",
                "selectionInactiveForeground": "textSoft",
                "disabledBackground": "rail",
                "disabledForeground": "subtle",
                "disabledText": "subtle",
                "borderColor": "border",
                "separatorColor": "border",
                "focusColor": "accent",
                "focusedBorderColor": "accent",
                "hoverBackground": "hoverBg",
            },
            "Panel": {
                "background": "surface",
                "foreground": "text",
            },
            "Button": {
                "startBackground": "raised",
                "endBackground": "raised",
                "startBorderColor": "border",
                "endBorderColor": "border",
                "foreground": "text",
                "focusedBorderColor": "accent",
                "default": {
                    "startBackground": "accentFill",
                    "endBackground": "accentFill",
                    "startBorderColor": "accentFill",
                    "endBorderColor": "accentFill",
                    "foreground": "onAccent",
                    "focusColor": "accent",
                    "focusedBorderColor": "accent",
                },
            },
            "EditorTabs": {
                "background": "rail",
                "underlineColor": "accent",
                "inactiveUnderlineColor": "secondary",
                "underlinedTabBackground": "bg",
                "underlinedTabForeground": "text",
                "hoverBackground": "surface",
                "borderColor": "border",
            },
            "DefaultTabs": {
                "background": "rail",
                "underlineColor": "accent",
                "underlinedTabBackground": "surface",
                "underlinedTabForeground": "text",
                "hoverBackground": "hoverBg",
            },
            "ToolWindow": {
                "Header.background": "rail",
                "Header.inactiveBackground": "rail",
                "Header.borderColor": "border",
                "HeaderTab.selectedBackground": "surface",
                "HeaderTab.selectedInactiveBackground": "surface",
                "HeaderTab.hoverBackground": "hoverBg",
                "HeaderTab.underlineColor": "accent",
                "Button.hoverBackground": "hoverBg",
                "Button.selectedBackground": "selectionActive",
                "Button.selectedForeground": "accent",
            },
            "Tree": {
                "background": "surface",
                "foreground": "textSoft",
                "selectionBackground": "selectionActive",
                "selectionForeground": "text",
                "selectionInactiveBackground": "selectionBg",
                "hoverBackground": "hoverBg",
                "modifiedItemForeground": "secondary",
            },
            "List": {
                "background": "surface",
                "foreground": "text",
                "selectionBackground": "selectionActive",
                "selectionForeground": "text",
                "selectionInactiveBackground": "selectionBg",
                "hoverBackground": "hoverBg",
            },
            "Table": {
                "background": "surface",
                "foreground": "text",
                "selectionBackground": "selectionActive",
                "selectionForeground": "text",
                "gridColor": "borderSubtle",
                "hoverBackground": "hoverBg",
            },
            "StatusBar": {
                "background": "rail",
                "foreground": "mute",
                "borderColor": "border",
                "hoverBackground": "hoverBg",
            },
            "TitlePane": {
                "background": "rail",
                "inactiveBackground": "rail",
                "infoForeground": "mute",
            },
            "MainToolbar": {
                "background": "rail",
                "inactiveBackground": "rail",
            },
            "Popup": {
                "background": "surface",
                "borderColor": "borderStrong",
                "Header.activeBackground": "rail",
                "Header.inactiveBackground": "rail",
            },
            "SearchEverywhere": {
                "Tab.selectedBackground": "accentFill",
                "Tab.selectedForeground": "onAccent",
                "SearchField.background": "bg",
                "SearchField.borderColor": "accent",
            },
            "TextField": {
                "background": "bg",
                "foreground": "text",
                "caretForeground": "accent",
                "selectionBackground": "selectionActive",
                "selectionForeground": "text",
            },
            "Link": {
                "activeForeground": "accent",
                "hoverForeground": "accentHover",
                "pressedForeground": "accentHover",
                "visitedForeground": "secondary",
            },
            "Notification": {
                "background": "raised",
                "borderColor": "borderStrong",
                "errorBackground": "raised",
                "errorBorderColor": "fault",
            },
            "ProgressBar": {
                "progressColor": "accent",
                "indeterminateStartColor": "secondary",
                "indeterminateEndColor": "accent",
                "trackColor": "raised",
                "passedColor": "signal",
                "failedColor": "fault",
            },
            "Component": {
                "borderColor": "border",
                "focusedBorderColor": "accent",
                "focusColor": "accent",
                "errorFocusColor": "fault",
                "warningFocusColor": "warning",
            },
            "Focus": {
                "borderColor": "accent",
            },
        },
        "icons": {
            "ColorPalette": {
                "Actions.Grey": ui["mute"],
                "Actions.Red": ui["fault"],
                "Actions.Yellow": ui["warning"],
                "Actions.Green": ui["signal"],
                "Actions.Blue": ui["secondary"],
                "Actions.GreyInline": ui["subtle"],
                "Objects.Grey": ui["mute"],
                "Objects.Blue": ui["secondary"],
                "Objects.Green": ui["signal"],
                "Objects.Yellow": ui["warning"],
                "Objects.Red": ui["fault"],
                "Objects.Purple": ui["magenta"],
                "Checkbox.Background.Default": ui["bg"],
                "Checkbox.Border.Default": ui["border_strong"],
                "Checkbox.Focus.Thin.Default": ui["accent"],
                "Checkbox.Background.Selected": ui["accent_fill"],
                "Checkbox.Border.Selected": ui["accent_fill"],
            }
        },
    }


def _jetbrains_plugin_xml(ver: str) -> str:
    providers = "\n".join(
        f'    <themeProvider id="rfs-{vid}" path="/themes/{vid}.theme.json"/>'
        for vid in VARIANT_ORDER
    )
    return (
        "<idea-plugin>\n"
        "  <id>dev.realfruitsnacks.themes.cyclorama-dawn</id>\n"
        f"  <name>{BRAND_NAME} Theme</name>\n"
        f"  <version>{ver}</version>\n"
        f'  <vendor url="{REPO_URL}">{AUTHOR}</vendor>\n'
        "  <description><![CDATA[\n"
        "    Cyclorama Dawn (Steel &amp; Beacon Orange) WCAG AA color themes for JetBrains IDEs:\n"
        "    Cyclorama Dawn (LX 263 Dark), Cyclorama Steel (LX 263 Dark), and Cyclorama Day (LX 512 Light).\n"
        "  ]]></description>\n"
        '  <idea-version since-build="232"/>\n'
        "  <depends>com.intellij.modules.platform</depends>\n"
        '  <extensions defaultExtensionNs="com.intellij">\n'
        f"{providers}\n"
        "  </extensions>\n"
        "</idea-plugin>\n"
    )


def _jetbrains_copy_snippet(v: dict) -> str:
    ui = v["ui"]
    snippet = {
        "name": v["name"],
        "dark": v["mode"] == "dark",
        "author": AUTHOR,
        "editorScheme": f"/schemes/{v['name']}.icls",
        "colors": {
            "bg": ui["bg"],
            "surface": ui["surface"],
            "border": ui["border"],
            "text": ui["text"],
            "accent": ui["accent"],
            "accentFill": ui["accent_fill"],
            "secondary": ui["secondary"],
        },
        "ui": {
            "Panel.background": "surface",
            "EditorTabs.underlineColor": "accent",
            "Button.default.startBackground": "accentFill",
            "StatusBar.background": "bg",
            "Focus.borderColor": "accent",
        },
    }
    return json.dumps(snippet, indent=2)


def build_jetbrains() -> dict:
    slug = "jetbrains"
    app_name = "JetBrains IDEs"
    homepage = "https://www.jetbrains.com/"
    fmt = "IntelliJ .icls + .theme.json"
    install = "Import .icls in Settings -> Editor -> Color Scheme, or zip apps/jetbrains/ as a theme plugin"
    install_steps = [
        "**Editor colors only:** open **Settings -> Editor -> Color Scheme**, click the gear icon -> **Import Scheme -> IntelliJ IDEA color scheme (.icls)**, and select `schemes/Cyclorama Dawn.icls` (or Steel / Day).",
        "**Full UI + Editor plugin:** zip `apps/jetbrains/` (`META-INF/`, `themes/`, `schemes/`) into `cyclorama-dawn-jetbrains.jar` and install via **Settings -> Plugins -> Install Plugin from Disk...**.",
        "Switch themes anytime from **Settings -> Appearance & Behavior -> Appearance -> Theme**.",
    ]

    ver = VARIANTS["cyclorama-dawn"]["version"]
    _write_text(f"apps/{slug}/META-INF/plugin.xml", _jetbrains_plugin_xml(ver))

    files = [{"label": "Plugin descriptor (META-INF/plugin.xml)", "path": f"apps/{slug}/META-INF/plugin.xml"}]
    theme_entries = []
    variant_files: dict[str, str] = {}

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        icls_in_app = f"schemes/{v['name']}.icls"
        icls_repo = f"apps/{slug}/{icls_in_app}"
        theme_in_app = f"themes/{vid}.theme.json"
        theme_repo = f"apps/{slug}/{theme_in_app}"

        variant_files[vid] = icls_in_app
        _write_text(icls_repo, _jetbrains_icls_xml(v))
        _write_json(theme_repo, _jetbrains_theme_json(v))

        svg = render_editor_preview(
            app_name,
            slug,
            v,
            active_file="StageCue.kt",
            footer_left="main  ·  Kotlin  ·  UTF-8",
        )
        write_preview_pair(slug, vid, svg)

        files.append({"label": f"{v['name']} Editor Scheme (.icls)", "path": icls_repo})
        files.append({"label": f"{v['name']} UI Theme (.theme.json)", "path": theme_repo})
        theme_entries.append(
            {
                "id": vid,
                "name": v["name"],
                "lx": v["lx"],
                "mode": v["mode"],
                "accentRole": v["accentRole"],
                "tagline": v["summary"],
                "preview": f"apps/{slug}/previews/{vid}.svg",
                "file": icls_repo,
                "copyLang": "json",
                "copyLabel": "JetBrains .theme.json snippet",
                "copySnippet": _jetbrains_copy_snippet(v),
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
        "primaryFile": f"apps/{slug}/schemes/Cyclorama Dawn.icls",
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
            extra_notes="Works across **IntelliJ IDEA**, **PyCharm**, **WebStorm**, **RustRover**, **Rider**, **GoLand**, **CLion**, and **Android Studio**. UI theme JSON files: [`cyclorama-dawn.theme.json`](themes/cyclorama-dawn.theme.json), [`cyclorama-steel.theme.json`](themes/cyclorama-steel.theme.json), [`cyclorama-day.theme.json`](themes/cyclorama-day.theme.json). Plugin descriptor: [`META-INF/plugin.xml`](META-INF/plugin.xml).",
        ),
    )
    return _manifest_entry(slug, app_name, homepage, fmt, install)


# =============================================================================
# Public entrypoint & self-verification
# =============================================================================


def build() -> list[dict]:
    """Generate all 4 editor & IDE ports and return their apps/manifest.json entries."""
    return [
        build_vscode(),
        build_neovim(),
        build_zed(),
        build_jetbrains(),
    ]


def _verify_generated(entries: list[dict]) -> None:
    json_count = 0
    xml_count = 0
    svg_count = 0
    for entry in entries:
        app_dir = os.path.join(ROOT, *entry["path"].split("/"))
        for r, _, fns in os.walk(app_dir):
            for fn in sorted(fns):
                fp = os.path.join(r, fn)
                raw = open(fp, encoding="utf-8").read()
                if fn.endswith(".json"):
                    json.loads(raw)
                    json_count += 1
                elif fn.endswith((".xml", ".icls")):
                    ET.fromstring(raw)
                    xml_count += 1
                elif fn.endswith(".svg"):
                    ET.fromstring(raw)
                    svg_count += 1
        # Verify docs/assets/previews/<slug> parity
        slug = entry["slug"]
        for vid in VARIANT_ORDER:
            p1 = os.path.join(ROOT, "apps", slug, "previews", f"{vid}.svg")
            p2 = os.path.join(ROOT, "docs", "assets", "previews", slug, f"{vid}.svg")
            if open(p1, "rb").read() != open(p2, "rb").read():
                raise AssertionError(f"Preview mismatch: {p1} != {p2}")
        # Verify themes.json referenced files exist and copySnippet <= 45 lines
        tj = json.loads(open(os.path.join(ROOT, *entry["data"].split("/")), encoding="utf-8").read())
        for fobj in tj["files"]:
            fp = os.path.join(ROOT, *fobj["path"].split("/"))
            if not os.path.exists(fp):
                raise AssertionError(f"Missing file listed in themes.json: {fobj['path']}")
        for t in tj["themes"]:
            lines = t["copySnippet"].splitlines()
            if len(lines) > 45:
                raise AssertionError(f"{slug}/{t['id']} copySnippet too long: {len(lines)} lines")
    print(f"[ok] built {len(entries)} editor ports ({json_count} JSON, {xml_count} XML/ICLS, {svg_count} SVG verified)")


if __name__ == "__main__":
    manifest_entries = build()
    _verify_generated(manifest_entries)
