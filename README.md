<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/cover-dark.svg">
  <img alt="rfs-themes: Cyclorama Dawn themes and ports for everyday apps" src="docs/assets/cover-light.svg" width="100%">
</picture>

**Cyclorama Dawn (`LX 263 Dark` / `LX 512 Light`)** themes and application ports for everyday tools, derived from [`Real-Fruit-Snacks/rfs-brand`](https://github.com/Real-Fruit-Snacks/rfs-brand) (`v2.0.0`).

Browse live previews and copy theme codes with one click at **[real-fruit-snacks.github.io/rfs-themes](https://real-fruit-snacks.github.io/rfs-themes/)**.

## Application Ports

| App | Category | Variants | Format | Port |
|---|---|---|---|---|
| **[PrivacyNotes](https://privacynotes.app/)** | Notes & Writing | `Cyclorama Dawn` · `Cyclorama Steel` · `Cyclorama Day` | `pn1:` theme code | [`apps/privacynotes/`](apps/privacynotes/) |

*Built as a modular multi-app hub — future ports (editors, terminals, note apps, browsers) drop straight into `apps/<app>/`.*

## Quick Copy — PrivacyNotes

Open **PrivacyNotes → Settings → Design → Paste theme code**:

- **Cyclorama Dawn** (`LX 263 Dark` · Beacon accent, Steel labels):
  ```text
  pn1:Cyclorama Dawn:050507,0C0C10,2A2C35,F4F5F8,B3B5C0,FF9254:list=0F1016,paper=050507,well=14141A,soft=D6D8E0,hover=FFB07A,fill=BD4811,fillhover=9E3B0C,danger=F06292,warning=FFC247,success=3DDC97,label=74B8E8,by=Real-Fruit-Snacks
  ```
- **Cyclorama Steel** (`LX 263 Dark` · Steel accent, Beacon labels):
  ```text
  pn1:Cyclorama Steel:050507,0C0C10,27313D,F4F5F8,B3B5C0,74B8E8:list=0E1117,paper=050507,well=131820,soft=D6DCE4,hover=99CDF2,fill=18496B,fillhover=123955,danger=F06292,warning=FFC247,success=3DDC97,label=FF9254,by=Real-Fruit-Snacks
  ```
- **Cyclorama Day** (`LX 512 Light` · Alabaster Day):
  ```text
  pn1:Cyclorama Day:F5F7F9,E9EEF3,C8D0DA,0D1016,474D59,AD3D0A:list=F0F3F7,paper=FFFFFF,well=E3E8EE,soft=252A34,hover=8B2F06,fill=18496B,fillhover=113752,danger=B51754,warning=8D5400,success=127247,label=164669,by=Real-Fruit-Snacks
  ```

## Repository Layout

| Path | What it holds |
|---|---|
| `apps/<slug>/` | Self-contained theme port for each application (`themes.json`, native configs/codes, `previews/`, `README.md`) |
| `apps/manifest.json` | Machine-readable registry of every supported app and variant |
| `brand/rfs.tokens.json` | Canonical Cyclorama Dawn tokens synced from `rfs-brand` `v2.0.0` |
| `tools/` | Zero-dependency Python generators and WCAG/app-spec contrast validators |
| `docs/` | Interactive Cyclorama Dawn theme gallery published via GitHub Pages |

## Verify Locally

```sh
python tools/build-privacynotes.py
python tools/verify-themes.py
```

See [`AGENTS.md`](AGENTS.md) for the contract when adding a new application port.
