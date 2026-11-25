#!/usr/bin/env python3
"""Generate Cyclorama Dawn v2.1.0 CLI & TUI app theme ports and SVG previews.

Builds 5 CLI & TUI ports from the canonical palette in tools/rfs_palette.py:
  1. apps/starship/    — Starship Prompt (.toml drop-ins + palettes.toml)
  2. apps/oh-my-posh/  — Oh My Posh v3 (.omp.json)
  3. apps/bat/         — bat Syntax Highlighter (TextMate .tmTheme XML plist)
  4. apps/delta/       — git-delta (.gitconfig feature pack + standalone configs)
  5. apps/fzf/         — fzf Fuzzy Finder (.sh and PowerShell .ps1)

Zero external dependencies (Python 3.11+ standard library only).
All generated files use UTF-8 encoding with Unix LF line endings for deterministic CI.
"""
from __future__ import annotations

import json
import os
import plistlib
import sys
import tomllib
import uuid
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from rfs_palette import AUTHOR, BRAND_NAME, REPO_URL, VARIANT_ORDER, VARIANTS, mix
from svg_previews import render_cli_preview, write_preview_pair


def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _write_json(path: str, data: object) -> None:
    _write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _swatches(v: dict) -> list[dict[str, str]]:
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
    *,
    slug: str,
    app_name: str,
    category: str,
    homepage: str,
    fmt: str,
    install: str,
    taglines: dict[str, str],
) -> dict:
    variants = []
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        variants.append({
            "id": vid,
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "summary": taglines[vid],
            "preview": f"apps/{slug}/previews/{vid}.svg",
        })
    return {
        "slug": slug,
        "name": app_name,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "variants": variants,
        "path": f"apps/{slug}",
        "data": f"apps/{slug}/themes.json",
    }


def _render_previews(app_name: str, slug: str, kind: str) -> None:
    for vid in VARIANT_ORDER:
        svg = render_cli_preview(app_name, slug, VARIANTS[vid], kind=kind)
        write_preview_pair(slug, vid, svg)


def _md_link_path(filename: str) -> str:
    return filename.replace(" ", "%20")


def _build_readme(
    *,
    app_name: str,
    homepage: str,
    intro: str,
    install_steps: list[str],
    files_by_variant: dict[str, list[str]],
    extra_files: list[tuple[str, str]],
    taglines: dict[str, str],
    usage_block: str,
) -> str:
    ver = VARIANTS["cyclorama-dawn"]["version"]
    lines = [
        f"# {BRAND_NAME} for {app_name}",
        "",
        f"Three **{BRAND_NAME} v{ver} (Steel & Beacon Orange)** themes for **[{app_name}]({homepage})**, "
        f"built from [`{AUTHOR}/rfs-brand`](https://github.com/{AUTHOR}/rfs-brand) tokens in [`{AUTHOR}/rfs-themes`]({REPO_URL}). {intro}",
        "",
        "## Install",
        "",
    ]
    for idx, step in enumerate(install_steps, start=1):
        lines.append(f"{idx}. {step}")

    if usage_block:
        lines.extend(["", usage_block.rstrip()])

    if extra_files:
        lines.extend(["", "## Included Pack Files", ""])
        for label, fname in extra_files:
            lines.append(f"- [{label}]({_md_link_path(fname)})")

    lines.extend([
        "",
        "## Variants",
        "",
        "| Variant | Lighting Cue | Mode | Accent Role | Background | Accent | Secondary | Files |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        ui = v["ui"]
        flinks = ", ".join(f"[`{fn}`]({_md_link_path(fn)})" for fn in files_by_variant[vid])
        lines.append(
            f"| **{v['name']}** | `{v['lx']}` | {v['mode'].title()} | {v['accentRole']} "
            f"| `{ui['bg']}` | `{ui['accent']}` | `{ui['secondary']}` | {flinks} |"
        )

    lines.append("")
    for idx, vid in enumerate(VARIANT_ORDER, start=1):
        v = VARIANTS[vid]
        lines.extend([
            f"### {idx}. {v['name']} (`{v['lx']} {v['mode'].title()} · {v['accentRole']}`)",
            "",
            taglines[vid],
            "",
            f"![{v['name']} {app_name} preview](previews/{vid}.svg)",
            "",
        ])

    lines.extend([
        "## Regenerating",
        "",
        "```sh",
        "python tools/build_cli.py",
        "```",
        "",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1. Starship Prompt (apps/starship/)
# ---------------------------------------------------------------------------

def _starship_palette_table(v: dict) -> str:
    pal_key = v["id"].replace("-", "_")
    ui, syn, ansi = v["ui"], v["syntax"], v["ansi"]
    rows = [f"[palettes.{pal_key}]"]
    for k, hx in ui.items():
        rows.append(f'{k} = "{hx}"')
    for k, hx in syn.items():
        rows.append(f'syntax_{k} = "{hx}"')
    for k, hx in ansi.items():
        # Convert camelCase bright keys to snake_case for clean TOML naming
        snake = "".join(f"_{c.lower()}" if c.isupper() else c for c in k)
        rows.append(f'ansi_{snake} = "{hx}"')
    return "\n".join(rows) + "\n"


def _starship_config(v: dict) -> str:
    pal_key = v["id"].replace("-", "_")
    ver = v["version"]
    mode_lbl = v["mode"].title()
    header = (
        f"# {BRAND_NAME} v{ver} — Starship Prompt Configuration\n"
        f"# Variant: {v['name']} ({v['lx']} · {mode_lbl} · {v['accentRole']})\n"
        f"# Author:  {AUTHOR}\n"
        f"# Source:  {REPO_URL}\n\n"
        '"$schema" = "https://starship.rs/config-schema.json"\n\n'
        f'palette = "{pal_key}"\n'
        "add_newline = true\n\n"
        'format = """\n'
        "$directory\\\n"
        "$git_branch\\\n"
        "$git_status\\\n"
        "$rust\\\n"
        "$python\\\n"
        "$nodejs\\\n"
        "$cmd_duration\\\n"
        "$line_break\\\n"
        '$character"""\n\n'
        "[directory]\n"
        'style = "bold fg:on_accent bg:secondary_fill"\n'
        'read_only = " [ro]"\n'
        'read_only_style = "bold fault"\n'
        'format = "[ $path ]($style)[$read_only]($read_only_style) "\n'
        "truncation_length = 3\n"
        "truncate_to_repo = true\n\n"
        "[git_branch]\n"
        'symbol = "git:"\n'
        'style = "bold fg:on_accent bg:accent_fill"\n'
        'format = "[ $symbol$branch ]($style) "\n\n'
        "[git_status]\n"
        'style = "bold warning"\n'
        'format = "([$all_status$ahead_behind]($style) )"\n'
        'conflicted = "!"\n'
        'ahead = "^${count}"\n'
        'behind = "v${count}"\n'
        'diverged = "^${ahead_count}v${behind_count}"\n'
        'untracked = "?${count}"\n'
        'stashed = "*${count}"\n'
        'modified = "~${count}"\n'
        'staged = "+${count}"\n'
        'deleted = "-${count}"\n\n'
        "[rust]\n"
        'symbol = "rs "\n'
        'style = "bold warning"\n'
        'format = "[$symbol($version)]($style) "\n\n'
        "[python]\n"
        'symbol = "py "\n'
        'style = "bold signal"\n'
        'format = "[$symbol$pyenv_prefix($version )(\\\\($virtualenv\\\\) )]($style)"\n\n'
        "[nodejs]\n"
        'symbol = "node "\n'
        'style = "bold cyan"\n'
        'format = "[$symbol($version)]($style) "\n\n'
        "[cmd_duration]\n"
        "min_time = 2000\n"
        'style = "mute"\n'
        'format = "[$duration]($style) "\n\n'
        "[character]\n"
        'success_symbol = "[>](bold accent)"\n'
        'error_symbol = "[x](bold fault)"\n'
        'vimcmd_symbol = "[<](bold secondary)"\n\n'
    )
    return header + _starship_palette_table(v)


def build_starship() -> dict:
    slug = "starship"
    app_name = "Starship"
    category = "CLI & TUI"
    homepage = "https://starship.rs/"
    fmt = "Starship .toml Palette"
    install = "Copy cyclorama-dawn.toml to ~/.config/starship.toml"
    install_steps = [
        "Copy `cyclorama-dawn.toml` (or `steel` / `day`) to `~/.config/starship.toml`.",
        "Or append `palettes.toml` to your existing `~/.config/starship.toml` and set `palette = \"cyclorama_dawn\"` at the top.",
        "Start a new shell session to load the updated Starship prompt.",
    ]
    taglines = {
        "cyclorama-dawn": "Matte dark Starship prompt with Steel Blue path pills, Beacon Orange git segments, and Signal Emerald status.",
        "cyclorama-steel": "Cool steel-charcoal Starship prompt with Steel Blue primary focus and Beacon Orange secondary highlights.",
        "cyclorama-day": "Alabaster Day light Starship prompt with high-contrast Steel pills, burnt Beacon accents, and deep Signal badges.",
    }
    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    files = []
    themes = []
    palette_sections = [
        f"# {BRAND_NAME} v{ver} — Combined Starship Palettes\n"
        f"# Author: {AUTHOR}\n"
        f"# Source: {REPO_URL}\n"
        "# Paste into ~/.config/starship.toml and set:\n"
        '#   palette = "cyclorama_dawn"  # or "cyclorama_steel" / "cyclorama_day"\n'
    ]

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        fname = f"{vid}.toml"
        cfg = _starship_config(v)
        _write_text(os.path.join(app_dir, fname), cfg)
        pal_tbl = _starship_palette_table(v)
        palette_sections.append(pal_tbl)
        files.append({"label": f"{v['name']} Config", "path": f"apps/{slug}/{fname}"})

        pal_key = vid.replace("-", "_")
        themes.append({
            "id": vid,
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": taglines[vid],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{fname}",
            "copyLang": "toml",
            "copyLabel": f"Copy {v['name']} Starship palette",
            "copySnippet": f'palette = "{pal_key}"\n\n{pal_tbl.rstrip()}',
            "swatches": _swatches(v),
        })

    _write_text(os.path.join(app_dir, "palettes.toml"), "\n".join(palette_sections))
    files.append({"label": "All 3 Palettes Pack", "path": f"apps/{slug}/palettes.toml"})

    _render_previews(app_name, slug, kind="prompt")

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": f"apps/{slug}/cyclorama-dawn.toml",
        "files": files,
        "themes": themes,
    })

    usage_block = (
        "```sh\n"
        "mkdir -p ~/.config\n"
        "cp apps/starship/cyclorama-dawn.toml ~/.config/starship.toml\n"
        "```"
    )
    readme = _build_readme(
        app_name=app_name,
        homepage=homepage,
        intro="Each drop-in file configures directory, git, Rust, Python, Node.js, duration, and prompt character segments using named `[palettes.cyclorama_*]` tables.",
        install_steps=install_steps,
        files_by_variant={vid: [f"{vid}.toml"] for vid in VARIANT_ORDER},
        extra_files=[("palettes.toml — All 3 `[palettes.cyclorama_*]` tables", "palettes.toml")],
        taglines=taglines,
        usage_block=usage_block,
    )
    _write_text(os.path.join(app_dir, "README.md"), readme)

    return _manifest_entry(
        slug=slug,
        app_name=app_name,
        category=category,
        homepage=homepage,
        fmt=fmt,
        install=install,
        taglines=taglines,
    )


# ---------------------------------------------------------------------------
# 2. Oh My Posh v3 (apps/oh-my-posh/)
# ---------------------------------------------------------------------------

def _omp_palette(v: dict) -> dict[str, str]:
    ui = v["ui"]
    return {
        "bg": ui["bg"],
        "surface": ui["surface"],
        "raised": ui["raised"],
        "border": ui["border"],
        "text": ui["text"],
        "text_soft": ui["text_soft"],
        "mute": ui["mute"],
        "subtle": ui["subtle"],
        "accent": ui["accent"],
        "accent_vivid": ui["accent_vivid"],
        "accent_fill": ui["accent_fill"],
        "on_accent": ui["on_accent"],
        "secondary": ui["secondary"],
        "secondary_fill": ui["secondary_fill"],
        "signal": ui["signal"],
        "warning": ui["warning"],
        "fault": ui["fault"],
        "fault_fill": ui["fault_fill"],
        "cyan": ui["cyan"],
        "magenta": ui["magenta"],
    }


def _omp_config(v: dict) -> dict:
    return {
        "$schema": "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json",
        "version": 3,
        "final_space": True,
        "console_title_template": "{{ .Shell }} in {{ .Folder }}",
        "palette": _omp_palette(v),
        "blocks": [
            {
                "type": "prompt",
                "alignment": "left",
                "newline": True,
                "segments": [
                    {
                        "type": "path",
                        "style": "plain",
                        "foreground": "p:on_accent",
                        "background": "p:secondary_fill",
                        "template": " {{ .Path }} ",
                        "properties": {
                            "style": "folder",
                            "max_depth": 3,
                        },
                    },
                    {
                        "type": "git",
                        "style": "plain",
                        "foreground": "p:on_accent",
                        "background": "p:accent_fill",
                        "template": (
                            " git:{{ .HEAD }}"
                            "{{ if .BranchStatus }} {{ .BranchStatus }}{{ end }}"
                            "{{ if .Working.Changed }} ~{{ .Working.String }}{{ end }}"
                            "{{ if .Staging.Changed }} +{{ .Staging.String }}{{ end }} "
                        ),
                        "properties": {
                            "fetch_status": True,
                            "fetch_upstream_icon": False,
                        },
                    },
                    {
                        "type": "python",
                        "style": "plain",
                        "foreground": "p:signal",
                        "background": "p:raised",
                        "template": " py {{ if .Venv }}({{ .Venv }}) {{ end }}{{ .Full }} ",
                        "properties": {
                            "display_mode": "files",
                            "fetch_virtual_env": True,
                        },
                    },
                    {
                        "type": "rust",
                        "style": "plain",
                        "foreground": "p:warning",
                        "background": "p:raised",
                        "template": " rs {{ .Full }} ",
                        "properties": {
                            "display_mode": "files",
                        },
                    },
                    {
                        "type": "node",
                        "style": "plain",
                        "foreground": "p:cyan",
                        "background": "p:raised",
                        "template": " node {{ .Full }} ",
                        "properties": {
                            "display_mode": "files",
                        },
                    },
                ],
            },
            {
                "type": "prompt",
                "alignment": "right",
                "segments": [
                    {
                        "type": "executiontime",
                        "style": "plain",
                        "foreground": "p:mute",
                        "background": "p:raised",
                        "template": " {{ .FormattedMs }} ",
                        "properties": {
                            "threshold": 500,
                            "style": "roundrock",
                        },
                    },
                    {
                        "type": "status",
                        "style": "plain",
                        "foreground": "p:signal",
                        "foreground_templates": [
                            "{{ if gt .Code 0 }}p:fault{{ end }}",
                        ],
                        "background": "p:raised",
                        "template": " {{ if gt .Code 0 }}exit {{ .Code }}{{ else }}ok{{ end }} ",
                        "properties": {
                            "always_enabled": True,
                        },
                    },
                ],
            },
            {
                "type": "prompt",
                "alignment": "left",
                "newline": True,
                "segments": [
                    {
                        "type": "text",
                        "style": "plain",
                        "foreground": "p:accent",
                        "foreground_templates": [
                            "{{ if gt .Code 0 }}p:fault{{ end }}",
                        ],
                        "template": ">",
                    },
                ],
            },
        ],
    }


def build_oh_my_posh() -> dict:
    slug = "oh-my-posh"
    app_name = "Oh My Posh"
    category = "CLI & TUI"
    homepage = "https://ohmyposh.dev/"
    fmt = "Oh My Posh v3 .omp.json"
    install = "oh-my-posh init <shell> --config apps/oh-my-posh/cyclorama-dawn.omp.json"
    install_steps = [
        "Copy `cyclorama-dawn.omp.json` (or `steel` / `day`) into your Oh My Posh themes folder.",
        "Initialize Oh My Posh in your shell profile (`~/.zshrc`, `~/.bashrc`, or PowerShell `$PROFILE`) with `--config` pointing to the `.omp.json` file.",
        "Reload your shell profile to activate the prompt.",
    ]
    taglines = {
        "cyclorama-dawn": "Oh My Posh v3 dark prompt using p:<token> palette references with Beacon Orange git badges and Steel Blue paths.",
        "cyclorama-steel": "Oh My Posh v3 steel-charcoal dark prompt with Steel Blue primary pills and Beacon Orange highlights.",
        "cyclorama-day": "Oh My Posh v3 Alabaster Day light prompt with crisp Steel and burnt Beacon contrast across every segment.",
    }
    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    files = []
    themes = []
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        fname = f"{vid}.omp.json"
        cfg = _omp_config(v)
        _write_json(os.path.join(app_dir, fname), cfg)
        files.append({"label": f"{v['name']} Theme", "path": f"apps/{slug}/{fname}"})

        pal_snippet = json.dumps({"palette": cfg["palette"]}, indent=2)
        themes.append({
            "id": vid,
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": taglines[vid],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{fname}",
            "copyLang": "json",
            "copyLabel": f"Copy {v['name']} Oh My Posh palette",
            "copySnippet": pal_snippet,
            "swatches": _swatches(v),
        })

    _render_previews(app_name, slug, kind="prompt")

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": f"apps/{slug}/cyclorama-dawn.omp.json",
        "files": files,
        "themes": themes,
    })

    usage_block = (
        "```powershell\n"
        "# PowerShell ($PROFILE)\n"
        "oh-my-posh init pwsh --config \"$HOME/.config/oh-my-posh/cyclorama-dawn.omp.json\" | Invoke-Expression\n"
        "```\n\n"
        "```sh\n"
        "# Bash / Zsh\n"
        'eval "$(oh-my-posh init zsh --config ~/.config/oh-my-posh/cyclorama-dawn.omp.json)"\n'
        "```"
    )
    readme = _build_readme(
        app_name=app_name,
        homepage=homepage,
        intro="Every `.omp.json` uses the Oh My Posh v3 schema and `p:<key>` palette lookups for path, git, Python, Rust, Node.js, execution time, status, and prompt glyph blocks.",
        install_steps=install_steps,
        files_by_variant={vid: [f"{vid}.omp.json"] for vid in VARIANT_ORDER},
        extra_files=[],
        taglines=taglines,
        usage_block=usage_block,
    )
    _write_text(os.path.join(app_dir, "README.md"), readme)

    return _manifest_entry(
        slug=slug,
        app_name=app_name,
        category=category,
        homepage=homepage,
        fmt=fmt,
        install=install,
        taglines=taglines,
    )


# ---------------------------------------------------------------------------
# 3. bat Syntax Highlighter (apps/bat/)
# ---------------------------------------------------------------------------

def _tmtheme_bytes(v: dict) -> bytes:
    ui, syn = v["ui"], v["syntax"]
    vid = v["id"]
    theme_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{REPO_URL}/apps/bat/{vid}")).upper()

    def rule(name: str, scope: str, fg: str | None = None, bg: str | None = None, style: str | None = None) -> dict:
        st: dict[str, str] = {}
        if fg is not None:
            st["foreground"] = fg
        if bg is not None:
            st["background"] = bg
        if style is not None:
            st["fontStyle"] = style
        return {"name": name, "scope": scope, "settings": st}

    plist_obj = {
        "name": v["name"],
        "author": AUTHOR,
        "semanticClass": f"theme.{v['mode']}.{vid}",
        "colorSpaceName": "sRGB",
        "uuid": theme_uuid,
        "settings": [
            {
                "settings": {
                    "background": ui["bg"],
                    "foreground": ui["text"],
                    "caret": ui["cursor"],
                    "lineHighlight": ui["raised"],
                    "selection": ui["selection_active"],
                    "selectionBorder": ui["border_strong"],
                    "inactiveSelection": ui["selection_bg"],
                    "findHighlight": ui["find_match"],
                    "findHighlightForeground": ui["text"],
                    "gutter": ui["surface"],
                    "gutterForeground": ui["subtle"],
                    "guide": ui["border_subtle"],
                    "activeGuide": ui["border_strong"],
                    "stackGuide": ui["border"],
                    "bracketsForeground": ui["accent"],
                    "bracketContentsForeground": ui["secondary"],
                }
            },
            rule("Comment", "comment, punctuation.definition.comment", fg=syn["comment"], style="italic"),
            rule("String", "string, string.quoted, string.template", fg=syn["string"]),
            rule("String Escape & Regex", "constant.character.escape, string.regexp", fg=syn["type"]),
            rule("Numeric Constant", "constant.numeric", fg=syn["number"]),
            rule("Language Constant", "constant.language, constant.other", fg=syn["constant"]),
            rule("Keyword", "keyword, keyword.control, keyword.other", fg=syn["keyword"], style="bold"),
            rule("Operator", "keyword.operator", fg=syn["operator"]),
            rule("Storage", "storage, storage.type, storage.modifier", fg=syn["keyword"]),
            rule("Function Name", "entity.name.function, meta.function-call, support.function", fg=syn["function"]),
            rule(
                "Type & Class Name",
                "entity.name.type, entity.name.class, entity.name.struct, entity.name.enum, entity.other.inherited-class",
                fg=syn["type"],
            ),
            rule("Tag Name", "entity.name.tag", fg=syn["tag"]),
            rule("Tag Attribute", "entity.other.attribute-name", fg=syn["property"]),
            rule("Variable", "variable, variable.other", fg=ui["text"]),
            rule("Variable Parameter", "variable.parameter", fg=syn["parameter"], style="italic"),
            rule(
                "Object Property & Key",
                "variable.other.property, variable.other.member, support.type.property-name, meta.object-literal.key",
                fg=syn["property"],
            ),
            rule("Support", "support, support.type, support.class, support.constant", fg=syn["type"]),
            rule("Punctuation", "punctuation", fg=syn["punctuation"]),
            rule("Markup Heading", "markup.heading, entity.name.section", fg=ui["accent"], style="bold"),
            rule("Markup Bold", "markup.bold", fg=ui["text"], style="bold"),
            rule("Markup Italic", "markup.italic", fg=ui["text_soft"], style="italic"),
            rule("Markup Inline Raw", "markup.inline.raw, markup.raw", fg=syn["string"]),
            rule("Markup Link", "markup.underline.link, string.other.link", fg=ui["secondary"], style="underline"),
            rule("Markup Inserted", "markup.inserted, meta.diff.header.to-file", fg=syn["diff_add"]),
            rule("Markup Deleted", "markup.deleted, meta.diff.header.from-file", fg=syn["diff_del"]),
            rule("Markup Changed", "markup.changed", fg=syn["diff_change"]),
            rule("Invalid", "invalid, invalid.illegal", fg=ui["on_accent"], bg=ui["fault_fill"]),
            rule("Invalid Deprecated", "invalid.deprecated", fg=ui["warning"], style="underline"),
        ],
    }
    return plistlib.dumps(plist_obj, fmt=plistlib.FMT_XML, sort_keys=False)


def build_bat() -> dict:
    slug = "bat"
    app_name = "bat"
    category = "CLI & TUI"
    homepage = "https://github.com/sharkdp/bat"
    fmt = "TextMate .tmTheme XML"
    install = 'Copy *.tmTheme to $(bat --config-dir)/themes/ and run bat cache --build'
    install_steps = [
        'Copy `Cyclorama Dawn.tmTheme`, `Cyclorama Steel.tmTheme`, and `Cyclorama Day.tmTheme` into `"$(bat --config-dir)/themes/"`.',
        "Rebuild bat's syntax theme cache with `bat cache --build`.",
        'Select your variant with `bat --theme="Cyclorama Dawn"` (or add `--theme="Cyclorama Dawn"` to `$(bat --config-file)`).',
    ]
    taglines = {
        "cyclorama-dawn": "TextMate .tmTheme dark syntax palette on #050507 with Beacon Orange functions, Steel keywords, and Signal numbers.",
        "cyclorama-steel": "TextMate .tmTheme steel-charcoal dark syntax palette paired with Steel Blue focus and crisp diff scopes.",
        "cyclorama-day": "TextMate .tmTheme Alabaster Day light syntax palette tuned for bright terminals and WCAG AA readability.",
    }
    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    files = []
    themes = []
    files_by_variant: dict[str, list[str]] = {}
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        fname = f"{v['name']}.tmTheme"
        xml_text = _tmtheme_bytes(v).decode("utf-8").replace("\r\n", "\n")
        _write_text(os.path.join(app_dir, fname), xml_text)
        files.append({"label": f"{v['name']} .tmTheme", "path": f"apps/{slug}/{fname}"})
        files_by_variant[vid] = [fname]

        snippet = (
            'mkdir -p "$(bat --config-dir)/themes"\n'
            f'cp "apps/bat/{fname}" "$(bat --config-dir)/themes/"\n'
            "bat cache --build\n"
            f'bat --theme="{v["name"]}" README.md'
        )
        themes.append({
            "id": vid,
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": taglines[vid],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{fname}",
            "copyLang": "sh",
            "copyLabel": f"Copy {v['name']} bat install command",
            "copySnippet": snippet,
            "swatches": _swatches(v),
        })

    _render_previews(app_name, slug, kind="tui")

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": f"apps/{slug}/Cyclorama Dawn.tmTheme",
        "files": files,
        "themes": themes,
    })

    usage_block = (
        "```sh\n"
        'mkdir -p "$(bat --config-dir)/themes"\n'
        'cp apps/bat/*.tmTheme "$(bat --config-dir)/themes/"\n'
        "bat cache --build\n"
        'bat --theme="Cyclorama Dawn" README.md\n'
        "```"
    )
    readme = _build_readme(
        app_name=app_name,
        homepage=homepage,
        intro="These `.tmTheme` files also power `syntax-theme` in [`git-delta`](../delta/README.md) once installed in bat's cache.",
        install_steps=install_steps,
        files_by_variant=files_by_variant,
        extra_files=[],
        taglines=taglines,
        usage_block=usage_block,
    )
    _write_text(os.path.join(app_dir, "README.md"), readme)

    return _manifest_entry(
        slug=slug,
        app_name=app_name,
        category=category,
        homepage=homepage,
        fmt=fmt,
        install=install,
        taglines=taglines,
    )


# ---------------------------------------------------------------------------
# 4. git-delta (apps/delta/)
# ---------------------------------------------------------------------------

def _delta_feature_block(v: dict) -> str:
    ui = v["ui"]
    is_dark = v["mode"] == "dark"
    plus_emph = mix(ui["diff_add_bg"], ui["signal"], 0.28 if is_dark else 0.24)
    minus_emph = mix(ui["diff_del_bg"], ui["fault"], 0.30 if is_dark else 0.24)
    blame = " ".join([ui["bg"], ui["surface"], ui["raised"], ui["overlay"], ui["diff_chg_bg"]])

    return (
        f'[delta "{v["id"]}"]\n'
        f"    dark = {'true' if is_dark else 'false'}\n"
        f"    light = {'false' if is_dark else 'true'}\n"
        f'    syntax-theme = {v["name"]}\n'
        f'    plus-style = syntax "{ui["diff_add_bg"]}"\n'
        f'    plus-non-emph-style = syntax "{ui["diff_add_bg"]}"\n'
        f'    plus-emph-style = syntax "{plus_emph}"\n'
        f'    plus-empty-line-marker-style = normal "{ui["diff_add_bg"]}"\n'
        f'    minus-style = syntax "{ui["diff_del_bg"]}"\n'
        f'    minus-non-emph-style = syntax "{ui["diff_del_bg"]}"\n'
        f'    minus-emph-style = syntax "{minus_emph}"\n'
        f'    minus-empty-line-marker-style = normal "{ui["diff_del_bg"]}"\n'
        "    zero-style = syntax\n"
        "    line-numbers = true\n"
        f'    line-numbers-left-style = "{ui["subtle"]}"\n'
        f'    line-numbers-right-style = "{ui["subtle"]}"\n'
        f'    line-numbers-minus-style = "{ui["fault"]}"\n'
        f'    line-numbers-plus-style = "{ui["signal"]}"\n'
        f'    line-numbers-zero-style = "{ui["subtle"]}"\n'
        f'    file-style = bold "{ui["accent"]}"\n'
        f'    file-decoration-style = "{ui["border_strong"]}" ul\n'
        "    file-added-label = [added]\n"
        "    file-copied-label = [copied]\n"
        "    file-modified-label = [modified]\n"
        "    file-removed-label = [removed]\n"
        "    file-renamed-label = [renamed]\n"
        "    hunk-header-style = file line-number syntax\n"
        f'    hunk-header-decoration-style = "{ui["border"]}" box\n'
        f'    hunk-header-file-style = bold "{ui["secondary"]}"\n'
        f'    hunk-header-line-number-style = bold "{ui["accent"]}"\n'
        f'    whitespace-error-style = reverse "{ui["fault"]}"\n'
        f'    blame-palette = "{blame}"\n'
        "    merge-conflict-begin-symbol = ~\n"
        "    merge-conflict-end-symbol = ~\n"
        f'    merge-conflict-ours-diff-header-style = bold "{ui["secondary"]}"\n'
        f'    merge-conflict-ours-diff-header-decoration-style = "{ui["border"]}" box\n'
        f'    merge-conflict-theirs-diff-header-style = bold "{ui["accent"]}"\n'
        f'    merge-conflict-theirs-diff-header-decoration-style = "{ui["border"]}" box\n'
    )


def build_delta() -> dict:
    slug = "delta"
    app_name = "git-delta"
    category = "CLI & TUI"
    homepage = "https://dandavison.github.io/delta/"
    fmt = "Git Config .gitconfig"
    install = "Include apps/delta/cyclorama.gitconfig in ~/.gitconfig and set features = cyclorama-dawn"
    install_steps = [
        "Add `[include]` with `path = /path/to/rfs-themes/apps/delta/cyclorama.gitconfig` to your `~/.gitconfig`.",
        "Set `features = cyclorama-dawn` (or `cyclorama-steel` / `cyclorama-day`) under `[delta]`.",
        "Install the matching `.tmTheme` files from `apps/bat/` and run `bat cache --build` so `syntax-theme` resolves cleanly.",
    ]
    taglines = {
        "cyclorama-dawn": "Dark git-delta diff palette with Signal Emerald additions, Signal Crimson deletions, and Beacon Orange file headers.",
        "cyclorama-steel": "Steel-charcoal dark git-delta diff palette with Steel Blue headers and calibrated blame/hunk framing.",
        "cyclorama-day": "Alabaster Day light git-delta diff palette with crisp pastel diff washes and WCAG AA line-number markers.",
    }
    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    files = [{"label": "Unified 3-Variant Pack", "path": f"apps/{slug}/cyclorama.gitconfig"}]
    themes = []
    combined_blocks = [
        f"# {BRAND_NAME} v{ver} — git-delta Named Features\n"
        f"# Author: {AUTHOR}\n"
        f"# Source: {REPO_URL}\n"
        "# Usage in ~/.gitconfig:\n"
        "#   [include]\n"
        "#       path = /path/to/rfs-themes/apps/delta/cyclorama.gitconfig\n"
        "#   [delta]\n"
        "#       features = cyclorama-dawn\n"
    ]

    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        fname = f"{vid}.gitconfig"
        block = _delta_feature_block(v)
        combined_blocks.append(block)

        standalone = (
            f"# {BRAND_NAME} v{ver} — git-delta ({v['name']})\n"
            f"# Variant: {v['name']} ({v['lx']} · {v['mode'].title()} · {v['accentRole']})\n"
            f"# Author:  {AUTHOR}\n"
            f"# Source:  {REPO_URL}\n"
            "# Usage in ~/.gitconfig:\n"
            "#   [include]\n"
            f"#       path = /path/to/rfs-themes/apps/delta/{fname}\n"
            "#   [delta]\n"
            f"#       features = {vid}\n\n"
            f"{block}"
        )
        _write_text(os.path.join(app_dir, fname), standalone)
        files.append({"label": f"{v['name']} Standalone", "path": f"apps/{slug}/{fname}"})

        themes.append({
            "id": vid,
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": taglines[vid],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{fname}",
            "copyLang": "ini",
            "copyLabel": f"Copy {v['name']} git-delta feature",
            "copySnippet": block.rstrip(),
            "swatches": _swatches(v),
        })

    _write_text(os.path.join(app_dir, "cyclorama.gitconfig"), "\n".join(combined_blocks))

    _render_previews(app_name, slug, kind="diff")

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": f"apps/{slug}/cyclorama.gitconfig",
        "files": files,
        "themes": themes,
    })

    usage_block = (
        "```gitconfig\n"
        "[include]\n"
        "    path = /path/to/rfs-themes/apps/delta/cyclorama.gitconfig\n\n"
        "[core]\n"
        "    pager = delta\n\n"
        "[delta]\n"
        "    features = cyclorama-dawn\n"
        "```"
    )
    readme = _build_readme(
        app_name=app_name,
        homepage=homepage,
        intro="Pair with [`apps/bat/`](../bat/README.md) so `syntax-theme` uses the matching Cyclorama Dawn TextMate grammar.",
        install_steps=install_steps,
        files_by_variant={vid: [f"{vid}.gitconfig"] for vid in VARIANT_ORDER},
        extra_files=[("cyclorama.gitconfig — Unified pack with all 3 named features", "cyclorama.gitconfig")],
        taglines=taglines,
        usage_block=usage_block,
    )
    _write_text(os.path.join(app_dir, "README.md"), readme)

    return _manifest_entry(
        slug=slug,
        app_name=app_name,
        category=category,
        homepage=homepage,
        fmt=fmt,
        install=install,
        taglines=taglines,
    )


# ---------------------------------------------------------------------------
# 5. fzf Fuzzy Finder (apps/fzf/)
# ---------------------------------------------------------------------------

def _fzf_pairs(v: dict) -> list[tuple[str, str]]:
    ui = v["ui"]
    active_bg = ui["selection_bg"] if v["mode"] == "light" else ui["selection_active"]
    return [
        ("bg", ui["bg"]),
        ("bg+", active_bg),
        ("fg", ui["text_soft"]),
        ("fg+", ui["text"]),
        ("hl", ui["secondary"]),
        ("hl+", ui["accent"]),
        ("info", ui["warning"]),
        ("marker", ui["signal"]),
        ("pointer", ui["accent"]),
        ("prompt", ui["accent"]),
        ("spinner", ui["secondary"]),
        ("header", ui["mute"]),
        ("border", ui["border"]),
        ("gutter", ui["surface"]),
        ("label", ui["text"]),
        ("query", ui["text"]),
    ]


def _fzf_sh(v: dict) -> str:
    pairs = _fzf_pairs(v)
    color_arg = ",".join(f"{k}:{hx}" for k, hx in pairs)
    ver = v["version"]
    return (
        f"# {BRAND_NAME} v{ver} — fzf Color Palette (POSIX sh / bash / zsh)\n"
        f"# Variant: {v['name']} ({v['lx']} · {v['mode'].title()} · {v['accentRole']})\n"
        f"# Author:  {AUTHOR}\n"
        f"# Source:  {REPO_URL}\n\n"
        f'export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS --color={color_arg}"\n'
    )


def _fzf_ps1(v: dict) -> str:
    pairs = _fzf_pairs(v)
    ver = v["version"]
    entries = "\n".join(f"  '{k}:{hx}'" for k, hx in pairs)
    return (
        f"# {BRAND_NAME} v{ver} — fzf Color Palette (PowerShell / pwsh)\n"
        f"# Variant: {v['name']} ({v['lx']} · {v['mode'].title()} · {v['accentRole']})\n"
        f"# Author:  {AUTHOR}\n"
        f"# Source:  {REPO_URL}\n\n"
        "$cycloramaFzfColors = @(\n"
        f"{entries}\n"
        ") -join ','\n\n"
        '$env:FZF_DEFAULT_OPTS = ("$env:FZF_DEFAULT_OPTS --color=$cycloramaFzfColors").Trim()\n'
    )


def build_fzf() -> dict:
    slug = "fzf"
    app_name = "fzf"
    category = "CLI & TUI"
    homepage = "https://github.com/junegunn/fzf"
    fmt = "Shell .sh & PowerShell .ps1"
    install = "Source cyclorama-dawn.sh (bash/zsh) or dot-source cyclorama-dawn.ps1 (PowerShell)"
    install_steps = [
        "Bash / Zsh: add `source /path/to/rfs-themes/apps/fzf/cyclorama-dawn.sh` to `~/.bashrc` or `~/.zshrc`.",
        "Windows PowerShell / pwsh: add `. C:\\path\\to\\rfs-themes\\apps\\fzf\\cyclorama-dawn.ps1` to your `$PROFILE`.",
        "Open a new shell session and run `fzf` to confirm the Cyclorama Dawn palette.",
    ]
    taglines = {
        "cyclorama-dawn": "Matte dark fzf palette with Beacon Orange pointers and active matches, Steel Blue highlights, and Signal markers.",
        "cyclorama-steel": "Steel-charcoal dark fzf palette with Steel Blue focus, Beacon Orange match highlights, and crisp selection contrast.",
        "cyclorama-day": "Alabaster Day light fzf palette with soft Steel active rows, burnt Beacon pointers, and AA-verified text contrast.",
    }
    app_dir = os.path.join(ROOT, "apps", slug)
    ver = VARIANTS["cyclorama-dawn"]["version"]

    files = []
    themes = []
    files_by_variant: dict[str, list[str]] = {}
    for vid in VARIANT_ORDER:
        v = VARIANTS[vid]
        sh_name = f"{vid}.sh"
        ps1_name = f"{vid}.ps1"
        sh_text = _fzf_sh(v)
        ps1_text = _fzf_ps1(v)
        _write_text(os.path.join(app_dir, sh_name), sh_text)
        _write_text(os.path.join(app_dir, ps1_name), ps1_text)
        files.append({"label": f"{v['name']} Shell (.sh)", "path": f"apps/{slug}/{sh_name}"})
        files.append({"label": f"{v['name']} PowerShell (.ps1)", "path": f"apps/{slug}/{ps1_name}"})
        files_by_variant[vid] = [sh_name, ps1_name]

        color_arg = ",".join(f"{k}:{hx}" for k, hx in _fzf_pairs(v))
        themes.append({
            "id": vid,
            "name": v["name"],
            "lx": v["lx"],
            "mode": v["mode"],
            "accentRole": v["accentRole"],
            "tagline": taglines[vid],
            "preview": f"apps/{slug}/previews/{vid}.svg",
            "file": f"apps/{slug}/{sh_name}",
            "copyLang": "sh",
            "copyLabel": f"Copy {v['name']} fzf export",
            "copySnippet": f'export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS --color={color_arg}"',
            "swatches": _swatches(v),
        })

    _render_previews(app_name, slug, kind="tui")

    _write_json(os.path.join(app_dir, "themes.json"), {
        "app": app_name,
        "slug": slug,
        "category": category,
        "homepage": homepage,
        "format": fmt,
        "install": install,
        "installSteps": install_steps,
        "author": AUTHOR,
        "brandVersion": ver,
        "primaryFile": f"apps/{slug}/cyclorama-dawn.sh",
        "files": files,
        "themes": themes,
    })

    usage_block = (
        "```sh\n"
        "# Bash / Zsh (~/.bashrc or ~/.zshrc)\n"
        "source /path/to/rfs-themes/apps/fzf/cyclorama-dawn.sh\n"
        "```\n\n"
        "```powershell\n"
        "# PowerShell ($PROFILE)\n"
        ". C:\\path\\to\\rfs-themes\\apps\\fzf\\cyclorama-dawn.ps1\n"
        "```"
    )
    readme = _build_readme(
        app_name=app_name,
        homepage=homepage,
        intro="Includes both POSIX shell (`.sh`) and PowerShell (`.ps1`) scripts defining all 16 fzf color slots.",
        install_steps=install_steps,
        files_by_variant=files_by_variant,
        extra_files=[],
        taglines=taglines,
        usage_block=usage_block,
    )
    _write_text(os.path.join(app_dir, "README.md"), readme)

    return _manifest_entry(
        slug=slug,
        app_name=app_name,
        category=category,
        homepage=homepage,
        fmt=fmt,
        install=install,
        taglines=taglines,
    )


# ---------------------------------------------------------------------------
# Entrypoint & Self-Verification
# ---------------------------------------------------------------------------

def build() -> list[dict]:
    """Build all 5 CLI & TUI app ports and return manifest entries."""
    return [
        build_starship(),
        build_oh_my_posh(),
        build_bat(),
        build_delta(),
        build_fzf(),
    ]


def verify_outputs(entries: list[dict]) -> None:
    """Parse-check every generated JSON, TOML, plist/XML, and SVG preview."""
    for entry in entries:
        slug = entry["slug"]
        app_dir = os.path.join(ROOT, "apps", slug)
        tj_path = os.path.join(app_dir, "themes.json")
        with open(tj_path, encoding="utf-8") as fh:
            tj = json.load(fh)
        assert tj["slug"] == slug, f"slug mismatch in {tj_path}"
        assert len(tj["themes"]) == 3, f"expected 3 themes in {tj_path}"

        for vid in VARIANT_ORDER:
            p1 = os.path.join(app_dir, "previews", f"{vid}.svg")
            p2 = os.path.join(ROOT, "docs", "assets", "previews", slug, f"{vid}.svg")
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                b1, b2 = f1.read(), f2.read()
            assert b1 == b2, f"preview mismatch: {p1} vs {p2}"
            ET.fromstring(b1)

        for fmeta in tj["files"]:
            fp = os.path.join(ROOT, fmeta["path"])
            assert os.path.isfile(fp), f"missing generated file: {fp}"
            raw = open(fp, "rb").read()
            assert b"\r\n" not in raw, f"CRLF detected in {fp}"
            if fp.endswith(".toml"):
                tomllib.loads(raw.decode("utf-8"))
            elif fp.endswith(".json"):
                json.loads(raw.decode("utf-8"))
            elif fp.endswith(".tmTheme"):
                ET.fromstring(raw)
                parsed = plistlib.loads(raw)
                assert "settings" in parsed and len(parsed["settings"]) > 10


if __name__ == "__main__":
    manifest_entries = build()
    verify_outputs(manifest_entries)
    print(f"[ok] built and verified {len(manifest_entries)} CLI & TUI app ports (15 variants)")
