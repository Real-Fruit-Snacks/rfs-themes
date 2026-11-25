# rfs-themes — Agent & Contributor Contract

This repository holds **Cyclorama Dawn (Steel & Beacon Orange)** theme ports for 21 everyday applications (**63 verified variants**), built deterministically from the canonical tokens in [`Real-Fruit-Snacks/rfs-brand`](https://github.com/Real-Fruit-Snacks/rfs-brand) (`brand/rfs.tokens.json`).

## Core Invariants

1. **Dark (`LX 263`, `#050507`) is the default** for all web docs and showcase previews; **Light (`LX 512`, `#F5F7F9`)** is opt-in via the theme toggle. Keep animations enabled by default.
2. **Color & Contrast:** Every text/accent/status role must satisfy WCAG AA (`≥ 4.5:1` for text & white-on-fill buttons; `≥ 3.0:1` for UI icons/borders/labels) against every surface it sits on, plus any app-specific validator (e.g., all 17 checks of PrivacyNotes' `themeCode.ts`).
3. **Gradients:** Use Cartesian `in oklab` interpolation only — never `in oklch` in CSS.
4. **Zero Native Popups / Zero External CDNs:** Never call `alert()`, `confirm()`, or `prompt()`. Keep all fonts and assets self-hosted under `docs/assets/`.
5. **Deterministic Builds (`newline="\n"`):** All generated files must use UTF-8 with LF line endings so Windows and Linux CI produce byte-identical output.
6. **Public Scope Only:** Never reference private repositories or private hostnames.

## Tooling Architecture (`tools/`)

All scripts use **Python 3.11+ standard library only** (zero third-party dependencies):

- **`tools/rfs_palette.py`** — Single source of truth for all three Cyclorama Dawn variants (`cyclorama-dawn`, `cyclorama-steel`, `cyclorama-day`), derived from `brand/rfs.tokens.json`. Exposes `VARIANTS`, `VARIANT_ORDER`, `ansi_list()`, color helpers (`mix`, `with_alpha`, `argb_hex`, `contrast`), and `verify_palette_contrast()`. Never invent ad-hoc hex colors in builders.
- **`tools/svg_previews.py`** — Shared `660x390` SVG preview renderers (`render_editor_preview`, `render_terminal_preview`, `render_cli_preview`, `render_notes_preview`, `render_browser_preview`, `render_chat_preview`, `render_utility_preview`, `render_windows_preview`) plus `write_preview_pair()`, which writes byte-identical SVGs to both `apps/<slug>/previews/` and `docs/assets/previews/<slug>/`.
- **`tools/build_windows.py`** — Zero-dependency Windows 11 builder generating Oklab-calibrated 1080p & 4K PNG wallpapers (pure-Python stdlib PNG encoder with 4×4 Bayer dithering), native `.theme` packs, backup-first `.ps1` installers, and desktop SVG previews under `apps/windows/`.
- **`tools/build_all.py`** — Master orchestrator that runs all 6 builders in deterministic order (`build-privacynotes.py`, `build_editors.py`, `build_terminals.py`, `build_cli.py`, `build_desktop.py`, `build_windows.py`), verifies referenced files and preview SVGs exist, and compiles both `apps/manifest.json` and the normalized `docs/assets/catalog.json` powering the web gallery.
- **`tools/verify-themes.py`** — CI verifier checking `rfs.tokens.json` sync, `apps/manifest.json` integrity, PrivacyNotes `pn1:` grammar and 17/17 WCAG checks, below-header `.rfs-shell` / `.rfs-scroll-region` layout, and zero `in oklch` / native modal / private-repo leaks.

## Adding a New Application Port

Each application lives in its own self-contained folder under `apps/<slug>/`:

```text
apps/<slug>/
├── README.md        # Install steps, variant list, palette mapping, and previews
├── themes.json      # Structured variant definitions referencing Cyclorama Dawn roles
├── previews/        # Clean 660x390 SVG previews (Dawn, Steel, Day)
└── <native files>   # App-ready artifacts (e.g. codes.txt, *.json, *.toml, *.conf)
```

After adding an app to the appropriate category builder:
1. Add its slug under the appropriate category in `CATEGORY_SPEC` in `tools/build_all.py`.
2. Run `python tools/build_all.py` to regenerate native artifacts, previews, `apps/manifest.json`, and `docs/assets/catalog.json`.
3. Run `python tools/verify-themes.py` to verify contrast, sync, and code invariants.
4. Update `README.md` with the new port's table row and confirm `git diff` is clean on re-running `tools/build_all.py`.
