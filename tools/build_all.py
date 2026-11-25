#!/usr/bin/env python3
"""Master orchestrator for Real-Fruit-Snacks/rfs-themes.

Runs all 6 zero-dependency theme port builders in deterministic order, then
compiles:
  - apps/manifest.json        (repo-root machine-readable registry of all 21 apps)
  - docs/assets/catalog.json  (normalized gallery catalog for docs/index.html)

Zero external dependencies (Python 3.11+ standard library only).

Usage:
    python tools/build_all.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import rfs_palette as pal  # noqa: E402

MANIFEST_PATH = os.path.join(ROOT, "apps", "manifest.json")
CATALOG_PATH = os.path.join(ROOT, "docs", "assets", "catalog.json")
BRAND_SOURCE = "https://github.com/Real-Fruit-Snacks/rfs-brand"

# Ordered categories and app slugs (21 apps across 5 categories)
CATEGORY_SPEC: list[tuple[str, str, list[str]]] = [
    ("Editors & IDEs", "editors-ides", ["vscode", "neovim", "zed", "jetbrains"]),
    ("Terminals", "terminals", ["windows-terminal", "wezterm", "alacritty", "ghostty", "kitty"]),
    ("CLI & TUI", "cli-tui", ["starship", "oh-my-posh", "bat", "delta", "fzf"]),
    ("Notes & Writing", "notes-writing", ["privacynotes", "obsidian"]),
    ("Browsers & Desktop", "browsers-desktop", ["chromium", "discord", "qbittorrent", "flow-launcher", "windows"]),
]

PRIVACYNOTES_META = {
    "category": "Notes & Writing",
    "format": "pn1: theme code",
    "install": "Settings -> Design -> Paste theme code",
    "installSteps": [
        "Copy one of the `pn1:` theme codes below (or grab all three from `apps/privacynotes/codes.txt`).",
        "Open PrivacyNotes -> Settings -> Design -> Paste theme code.",
        "Switch themes anytime from the Ninja command palette (`Ctrl+K` -> type `theme` or `cyclorama`).",
    ],
    "primaryFile": "apps/privacynotes/codes.txt",
    "files": [
        {"label": "All pn1: Theme Codes (codes.txt)", "path": "apps/privacynotes/codes.txt"},
        {"label": "Canonical Seeds & Overrides (themes.json)", "path": "apps/privacynotes/themes.json"},
        {"label": "Install & Token Guide (README.md)", "path": "apps/privacynotes/README.md"},
    ],
}


def _load_module(name: str, filename: str):
    path = os.path.join(HERE, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load builder module {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _normalize_privacynotes(raw: dict) -> tuple[dict, dict]:
    slug = raw["slug"]
    manifest_variants = []
    catalog_variants = []

    for t in raw["themes"]:
        vid = t["id"]
        pal_v = pal.VARIANTS[vid]
        seeds = t["seeds"]
        ov = t.get("overrides", {})
        is_day = t["mode"] == "light"
        swatches = [
            {"label": "BG", "hex": seeds["background"]},
            {"label": "Paper" if is_day else "Side", "hex": ov.get("paper", seeds["sidebar"]) if is_day else seeds["sidebar"]},
            {"label": "Accent", "hex": seeds["accent"]},
            {"label": "Fill", "hex": ov.get("fill", pal_v["ui"]["accent_fill"])},
            {"label": "Label", "hex": ov.get("label", pal_v["ui"]["secondary"])},
            {"label": "OK", "hex": ov.get("success", pal_v["ui"]["signal"])},
        ]

        manifest_variants.append({
            "id": vid,
            "name": t["name"],
            "lx": t["lx"],
            "mode": t["mode"],
            "accentRole": pal_v["accentRole"],
            "summary": t["tagline"],
            "preview": f"apps/{slug}/previews/{vid}.svg",
        })
        catalog_variants.append({
            "id": vid,
            "name": t["name"],
            "lx": t["lx"],
            "mode": t["mode"],
            "accentRole": pal_v["accentRole"],
            "tagline": t["tagline"],
            "preview": f"assets/previews/{slug}/{vid}.svg",
            "file": "apps/privacynotes/codes.txt",
            "copyLang": "pn1",
            "copyLabel": "Copy pn1: code",
            "copySnippet": t["code"],
            "swatches": swatches,
        })

    manifest_app = {
        "slug": slug,
        "name": raw["app"],
        "category": PRIVACYNOTES_META["category"],
        "homepage": raw["homepage"],
        "format": PRIVACYNOTES_META["format"],
        "install": PRIVACYNOTES_META["install"],
        "variants": manifest_variants,
        "path": f"apps/{slug}",
        "data": f"apps/{slug}/themes.json",
    }

    catalog_app = {
        "slug": slug,
        "name": raw["app"],
        "category": PRIVACYNOTES_META["category"],
        "homepage": raw["homepage"],
        "format": PRIVACYNOTES_META["format"],
        "install": PRIVACYNOTES_META["install"],
        "installSteps": list(PRIVACYNOTES_META["installSteps"]),
        "path": f"apps/{slug}",
        "primaryFile": PRIVACYNOTES_META["primaryFile"],
        "files": [dict(f) for f in PRIVACYNOTES_META["files"]],
        "variants": catalog_variants,
    }
    return manifest_app, catalog_app


def _normalize_standard_app(raw: dict, expected_category: str) -> tuple[dict, dict]:
    slug = raw["slug"]
    category = raw.get("category") or expected_category
    manifest_variants = []
    catalog_variants = []

    for t in raw["themes"]:
        vid = t["id"]
        pal_v = pal.VARIANTS[vid]
        manifest_variants.append({
            "id": vid,
            "name": t["name"],
            "lx": t["lx"],
            "mode": t["mode"],
            "accentRole": t.get("accentRole", pal_v["accentRole"]),
            "summary": t["tagline"],
            "preview": t.get("preview", f"apps/{slug}/previews/{vid}.svg"),
        })
        catalog_variants.append({
            "id": vid,
            "name": t["name"],
            "lx": t["lx"],
            "mode": t["mode"],
            "accentRole": t.get("accentRole", pal_v["accentRole"]),
            "tagline": t["tagline"],
            "preview": f"assets/previews/{slug}/{vid}.svg",
            "file": t["file"],
            "copyLang": t.get("copyLang", "text"),
            "copyLabel": t.get("copyLabel", f"Copy {t['name']} snippet"),
            "copySnippet": t["copySnippet"],
            "swatches": t["swatches"],
        })

    manifest_app = {
        "slug": slug,
        "name": raw["app"],
        "category": category,
        "homepage": raw["homepage"],
        "format": raw["format"],
        "install": raw["install"],
        "variants": manifest_variants,
        "path": f"apps/{slug}",
        "data": f"apps/{slug}/themes.json",
    }

    catalog_app = {
        "slug": slug,
        "name": raw["app"],
        "category": category,
        "homepage": raw["homepage"],
        "format": raw["format"],
        "install": raw["install"],
        "installSteps": list(raw.get("installSteps", [])),
        "path": f"apps/{slug}",
        "primaryFile": raw["primaryFile"],
        "files": [dict(f) for f in raw.get("files", [])],
        "variants": catalog_variants,
    }
    return manifest_app, catalog_app


def run_builders() -> int:
    """Execute all 6 theme builders in deterministic order."""
    print("==> Running build-privacynotes.py")
    build_pn = _load_module("build_privacynotes", "build-privacynotes.py")
    rc = build_pn.main()
    if rc != 0:
        print(f"[x] build-privacynotes.py exited with {rc}")
        return rc

    for mod_name, filename in (
        ("build_editors", "build_editors.py"),
        ("build_terminals", "build_terminals.py"),
        ("build_cli", "build_cli.py"),
        ("build_desktop", "build_desktop.py"),
        ("build_windows", "build_windows.py"),
    ):
        print(f"==> Running {filename}")
        mod = _load_module(mod_name, filename)
        mod.build()

    return 0


def compile_registries() -> tuple[dict, dict]:
    """Read all 21 apps/<slug>/themes.json files and emit manifest.json + catalog.json."""
    brand_tokens = pal.load_brand_tokens()
    brand_version = brand_tokens["meta"]["version"]

    manifest_apps: list[dict] = []
    catalog_apps: list[dict] = []
    categories_out: list[dict] = []

    for cat_name, cat_slug, slugs in CATEGORY_SPEC:
        categories_out.append({
            "name": cat_name,
            "slug": cat_slug,
            "count": len(slugs),
        })
        for slug in slugs:
            themes_path = os.path.join(ROOT, "apps", slug, "themes.json")
            if not os.path.exists(themes_path):
                raise FileNotFoundError(f"Missing {themes_path}")
            with open(themes_path, encoding="utf-8") as fh:
                raw = json.load(fh)

            if slug == "privacynotes":
                m_app, c_app = _normalize_privacynotes(raw)
            else:
                m_app, c_app = _normalize_standard_app(raw, cat_name)

            # Verify referenced files & previews exist on disk
            for v in m_app["variants"]:
                p = os.path.join(ROOT, v["preview"])
                if not os.path.exists(p):
                    raise FileNotFoundError(f"Missing manifest preview {v['preview']}")
            for v in c_app["variants"]:
                dp = os.path.join(ROOT, "docs", v["preview"])
                if not os.path.exists(dp):
                    raise FileNotFoundError(f"Missing docs preview docs/{v['preview']}")
                fp = os.path.join(ROOT, v["file"])
                if not os.path.exists(fp):
                    raise FileNotFoundError(f"Missing variant file {v['file']}")
            for f_entry in c_app["files"]:
                fp = os.path.join(ROOT, f_entry["path"])
                if not os.path.exists(fp):
                    raise FileNotFoundError(f"Missing app file {f_entry['path']}")

            manifest_apps.append(m_app)
            catalog_apps.append(c_app)

    total_variants = sum(len(a["variants"]) for a in catalog_apps)

    manifest = {
        "brand": pal.BRAND_NAME,
        "version": brand_version,
        "source": BRAND_SOURCE,
        "apps": manifest_apps,
    }
    catalog = {
        "brand": pal.BRAND_NAME,
        "version": brand_version,
        "source": BRAND_SOURCE,
        "stats": {
            "apps": len(catalog_apps),
            "variants": total_variants,
            "categories": len(categories_out),
        },
        "categories": categories_out,
        "apps": catalog_apps,
    }

    _write_json(MANIFEST_PATH, manifest)
    _write_json(CATALOG_PATH, catalog)
    print(
        f"[ok] wrote apps/manifest.json & docs/assets/catalog.json "
        f"({len(catalog_apps)} apps, {total_variants} variants, {len(categories_out)} categories)"
    )
    return manifest, catalog


def main() -> int:
    rc = run_builders()
    if rc != 0:
        return rc
    compile_registries()
    return 0


if __name__ == "__main__":
    sys.exit(main())
