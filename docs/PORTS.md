# Cyclorama Dawn Application Ports (28 Apps · 84 Variants)

Complete directory of all **28 everyday application ports** (**84 verified variants** across `Cyclorama Dawn`, `Cyclorama Steel`, and `Cyclorama Day`), built deterministically from [`brand/rfs.tokens.json`](../brand/rfs.tokens.json) (`rfs-brand` `v2.1.0`).

Browse live previews, filter by category, copy snippets, and download configs at **[real-fruit-snacks.github.io/rfs-themes](https://real-fruit-snacks.github.io/rfs-themes/)**.

## Three Standard Variants

| Variant | Lighting Cue | Mode | Role |
|---|---|---|---|
| **Cyclorama Dawn** | `LX 263` | Dark (`#050507`) | Beacon Orange (`#FF9254`) primary focus, Steel Blue (`#74B8E8`) secondary |
| **Cyclorama Steel** | `LX 263` | Dark (`#050507`) | Steel Blue (`#74B8E8`) primary focus, Beacon Orange (`#FF9254`) secondary |
| **Cyclorama Day** | `LX 512` | Light (`#F5F7F9`) | Alabaster Day light workspace, burnt Beacon (`#AD3D0A`) & Steel (`#164669`) |

## Editors & IDEs (8)

| App | Format | Install Summary | Port |
|---|---|---|---|
| **VS Code** | VS Code JSON Theme Extension | Copy `apps/vscode/` into `~/.vscode/extensions/rfs-cyclorama-dawn` and pick Color Theme | [`apps/vscode/`](../apps/vscode/) |
| **Neovim** | Lua Colorscheme Plugin | Add `apps/neovim/` to your plugin manager and run `:colorscheme cyclorama-dawn` | [`apps/neovim/`](../apps/neovim/) |
| **Zed** | Zed JSON Theme (v0.2.0) | Copy `themes/cyclorama.json` into `~/.config/zed/themes/` and select a variant | [`apps/zed/`](../apps/zed/) |
| **JetBrains IDEs** | IntelliJ `.icls` + `.theme.json` | Import `.icls` under Settings → Editor → Color Scheme or load UI theme plugin | [`apps/jetbrains/`](../apps/jetbrains/) |
| [**Notepad++**](https://notepad-plus-plus.org/) | Notepad++ XML + Dark Mode `.ps1` | Run `apply-cyclorama-dawn.ps1` (copies XMLs + sets Custom Dark Mode) or copy `*.xml` to `%APPDATA%\Notepad++\themes\` | [`apps/notepad-plus-plus/`](../apps/notepad-plus-plus/) |
| [**Python IDLE**](https://docs.python.org/3/library/idle.html) | IDLE `config-highlight.cfg` | Append `apps/python-idle/config-highlight.cfg` to `~/.idlerc/config-highlight.cfg` and pick in Options → Configure IDLE → Highlights | [`apps/python-idle/`](../apps/python-idle/) |
| [**Windows PowerShell ISE**](https://learn.microsoft.com/en-us/powershell/scripting/windows-powershell/ise/introducing-the-windows-powershell-ise) | `.StorableColorTheme.ps1xml` | Run `install-cyclorama-dawn.ps1` in Windows PowerShell 5.1 or import `.StorableColorTheme.ps1xml` via Tools → Options → Manage Themes | [`apps/powershell-ise/`](../apps/powershell-ise/) |
| [**T3 Code**](https://github.com/pingdotgg/t3code) | T3 Code Theme JSON + CSS (v1) | Run `t3 theme set apps/t3code/cyclorama-dawn.json` or Settings → Themes → Import theme | [`apps/t3code/`](../apps/t3code/) |

## Terminals (8)

| App | Format | Install Summary | Port |
|---|---|---|---|
| **Windows Terminal** | JSON Schemes + PSReadLine `.ps1` | Paste scheme into `settings.json` `"schemes"` array + dot-source PSReadLine `.ps1` | [`apps/windows-terminal/`](../apps/windows-terminal/) |
| **WezTerm** | TOML Color Scheme + Lua Snippet | Copy `.toml` into `~/.config/wezterm/colors/` and set `config.color_scheme` | [`apps/wezterm/`](../apps/wezterm/) |
| **Alacritty** | TOML Theme (`v0.13+`) | Import `cyclorama-*.toml` via `general.import` in `alacritty.toml` | [`apps/alacritty/`](../apps/alacritty/) |
| **Ghostty** | Ghostty `key = value` Theme | Copy theme file to `~/.config/ghostty/themes/` and set `theme = cyclorama-dawn` | [`apps/ghostty/`](../apps/ghostty/) |
| **Kitty** | Kitty `.conf` Theme | Include `cyclorama-*.conf` in `kitty.conf` or run `kitty +kitten themes` | [`apps/kitty/`](../apps/kitty/) |
| [**Git Bash (Mintty)**](https://gitforwindows.org/) | Mintty `.minttyrc` + Git `.gitconfig` | Copy `.minttyrc` to `~/.mintty/themes/` + include `git-colors-*.gitconfig` in `~/.gitconfig` | [`apps/git-bash/`](../apps/git-bash/) |
| [**QTerminal**](https://github.com/lxqt/qterminal) | QTermWidget `.colorscheme` INI | Copy `.colorscheme` into `~/.local/share/qtermwidget6/color-schemes/` and select in Preferences | [`apps/qterminal/`](../apps/qterminal/) |
| [**Windows Console**](https://learn.microsoft.com/en-us/windows/console/) | Windows Registry `.reg` (`HKCU\Console`) | Double-click `cyclorama-dawn.reg` (or run `reg import`) and open a new `cmd.exe` window | [`apps/windows-console/`](../apps/windows-console/) |

## CLI & TUI (5)

| App | Format | Install Summary | Port |
|---|---|---|---|
| **Starship** | Starship `.toml` Palette | Copy `cyclorama-dawn.toml` to `~/.config/starship.toml` or include `palettes.toml` | [`apps/starship/`](../apps/starship/) |
| **Oh My Posh** | Oh My Posh `.omp.json` | Pass `--config apps/oh-my-posh/cyclorama-dawn.omp.json` to `oh-my-posh init` | [`apps/oh-my-posh/`](../apps/oh-my-posh/) |
| **bat** | TextMate `.tmTheme` XML | Copy `.tmTheme` files into `$(bat --config-dir)/themes` and run `bat cache --build` | [`apps/bat/`](../apps/bat/) |
| **git-delta** | Git Config `[delta]` Feature | Include `cyclorama-*.gitconfig` in `~/.gitconfig` and enable `features` | [`apps/delta/`](../apps/delta/) |
| **fzf** | Shell / PowerShell `FZF_DEFAULT_OPTS` | Source `cyclorama-dawn.sh` (Bash/Zsh) or `cyclorama-dawn.ps1` (PowerShell) | [`apps/fzf/`](../apps/fzf/) |

## Notes & Writing (2)

| App | Format | Install Summary | Port |
|---|---|---|---|
| **PrivacyNotes** | `pn1:` theme code | Settings → Design → Paste theme code (all 17/17 contrast checks passing) | [`apps/privacynotes/`](../apps/privacynotes/) |
| **Obsidian** | Obsidian Theme (`manifest.json` + `theme.css`) | Copy into `.obsidian/themes/Cyclorama Dawn/` or enable CSS snippets | [`apps/obsidian/`](../apps/obsidian/) |

## Browsers & Desktop (5)

| App | Format | Install Summary | Port |
|---|---|---|---|
| **Windows 11** | `.theme` + Oklab Wallpapers + `.ps1` | Run `install-cyclorama-dawn.ps1` (auto 1080p/4K + registry backup) or double-click `.theme` | [`apps/windows/`](../apps/windows/) |
| **Brave / Chrome / Edge** | Chromium MV3 Browser Theme | Extensions → Developer mode → Load unpacked variant folder | [`apps/chromium/`](../apps/chromium/) |
| **Discord (Vencord / BetterDiscord)** | `.theme.css` Client Theme | Drop `cyclorama-*.theme.css` into your Vencord / BetterDiscord `themes/` folder | [`apps/discord/`](../apps/discord/) |
| **qBittorrent** | QSS Stylesheet + `config.json` | qBittorrent 5.x: Behavior → Use custom UI theme → pick `config.json` (`FolderThemeSource`) | [`apps/qbittorrent/`](../apps/qbittorrent/) |
| **Flow Launcher** | WPF XAML ResourceDictionary | Copy `Cyclorama *.xaml` into `%APPDATA%\FlowLauncher\Themes\` | [`apps/flow-launcher/`](../apps/flow-launcher/) |

## Repository Layout

| Path | What it holds |
|---|---|
| `apps/<slug>/` | Self-contained theme port for each application (`themes.json`, native configs/codes, `previews/`, `README.md`) |
| `apps/manifest.json` | Machine-readable registry of all 28 supported apps and 84 variants |
| `brand/rfs.tokens.json` | Canonical Cyclorama Dawn tokens synced from `rfs-brand` `v2.1.0` |
| `tools/` | Zero-dependency Python palette engine, SVG preview renderers, master orchestrator, and CI validator |
| `docs/` | Interactive Cyclorama Dawn 28-app theme gallery published via GitHub Pages (`docs/assets/catalog.json`) |

## Build & Verify Locally

```sh
python tools/build_all.py
python tools/verify-themes.py
```
