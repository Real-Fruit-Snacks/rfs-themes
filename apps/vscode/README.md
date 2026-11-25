# Cyclorama Dawn for VS Code

Three **Cyclorama Dawn v2.1.0 (Steel & Beacon Orange)** themes for **[VS Code](https://code.visualstudio.com/)**, built from [`Real-Fruit-Snacks/rfs-brand`](https://github.com/Real-Fruit-Snacks/rfs-brand) with WCAG AA calibrated surfaces, syntax tokens, and ANSI 0-15 terminal colors.

- **Category:** Editors & IDEs
- **Format:** `VS Code JSON Theme Extension`
- **Gallery:** [https://real-fruit-snacks.github.io/rfs-themes/](https://real-fruit-snacks.github.io/rfs-themes/)

## Install

1. Copy `apps/vscode/` to `~/.vscode/extensions/rfs-cyclorama-dawn` (or `~/.cursor/extensions/rfs-cyclorama-dawn`).
2. Reload the window (`Ctrl+Shift+P` -> **Developer: Reload Window**).
3. Open **Preferences: Color Theme** (`Ctrl+K Ctrl+T`) and select **Cyclorama Dawn**, **Cyclorama Steel**, or **Cyclorama Day**.

Works identically in **VS Code**, **Cursor**, and **Antigravity** (full workbench colors, semantic tokens, and TextMate scopes).

## Variants

| Variant | LX | Mode | Accent Role | Background | Accent | Secondary | File |
|---|---|---|---|---|---|---|---|
| **Cyclorama Dawn** | `LX 263` | `dark` | Beacon Orange | `#050507` | `#FF9254` | `#74B8E8` | [`themes/cyclorama-dawn.json`](themes/cyclorama-dawn.json) |
| **Cyclorama Steel** | `LX 263` | `dark` | Steel Blue | `#050507` | `#74B8E8` | `#FF9254` | [`themes/cyclorama-steel.json`](themes/cyclorama-steel.json) |
| **Cyclorama Day** | `LX 512` | `light` | Alabaster Day | `#F5F7F9` | `#AD3D0A` | `#164669` | [`themes/cyclorama-day.json`](themes/cyclorama-day.json) |

## Previews

### Cyclorama Dawn (`LX 263` · Beacon Orange)

Matte #050507 dark stage with Beacon Orange focus and Steel Blue secondary accents.

![Cyclorama Dawn VS Code preview](previews/cyclorama-dawn.svg)

### Cyclorama Steel (`LX 263` · Steel Blue)

Cool steel-charcoal dark stage with Steel Blue controls and Beacon Orange highlights.

![Cyclorama Steel VS Code preview](previews/cyclorama-steel.svg)

### Cyclorama Day (`LX 512` · Alabaster Day)

Crisp #F5F7F9 Alabaster Day light workspace with white panels, burnt Beacon links, and Steel buttons.

![Cyclorama Day VS Code preview](previews/cyclorama-day.svg)

## Regenerating

```sh
python tools/build_editors.py
```
