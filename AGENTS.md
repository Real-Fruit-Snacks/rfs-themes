# rfs-themes — Agent & Contributor Contract

This repository holds **Cyclorama Dawn (Steel & Beacon Orange)** theme ports for third-party and everyday applications, built from the canonical tokens in [`Real-Fruit-Snacks/rfs-brand`](https://github.com/Real-Fruit-Snacks/rfs-brand) (`brand/rfs.tokens.json`).

## Core Invariants

1. **Dark (`LX 263`, `#050507`) is the default** for all web docs and showcase previews; **Light (`LX 512`, `#F5F7F9`)** is opt-in via the theme toggle. Keep animations enabled by default.
2. **Color & Contrast:** Every text/accent/status role must satisfy WCAG AA (`≥ 4.5:1` for text & white-on-fill buttons; `≥ 3.0:1` for UI icons/borders/labels) against every surface it sits on, plus any app-specific validator (e.g., all 17 checks of PrivacyNotes' `themeCode.ts`).
3. **Gradients:** Use Cartesian `in oklab` interpolation only — never `in oklch` in CSS.
4. **Zero Native Popups / Zero External CDNs:** Never call `alert()`, `confirm()`, or `prompt()`. Keep all fonts and assets self-hosted under `docs/assets/`.
5. **Public Scope Only:** Never reference private repositories or private hostnames.

## Adding a New Application Port

Each application lives in its own self-contained folder under `apps/<slug>/`:

```text
apps/<slug>/
├── README.md        # Install steps, variant list, palette mapping, and previews
├── themes.json      # Structured variant definitions referencing Cyclorama Dawn roles
├── previews/        # Clean SVG previews (dark/light variants)
└── <native files>   # App-ready artifacts (e.g. codes.txt, *.json, *.toml, *.conf)
```

After adding an app:
1. Register it in `apps/manifest.json`.
2. Add its generator/validator check in `tools/verify-themes.py`.
3. Update `README.md` and `docs/index.html` (or let `docs/app.js` load it cleanly).
4. Run `python tools/verify-themes.py` before opening a PR or pushing.
