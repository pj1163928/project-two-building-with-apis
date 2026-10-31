# Font sources

Every font here is licensed under the SIL Open Font License 1.1. Each
family's licence text sits next to it as `<Family>-OFL.txt`.

| File | Family | Use | Source | Licence |
|---|---|---|---|---|
| `PlusJakartaSans-Variable.ttf` | Plus Jakarta Sans (variable, weights 200–800) | Headings (`--font-display`, set at 800) | Google Fonts, pinned below | `PlusJakartaSans-OFL.txt` |
| `Inter-Regular.ttf`, `Inter-Medium.ttf`, `Inter-SemiBold.ttf`, `Inter-Bold.ttf` | Inter | Body text | Axcenity Engine repo, `assets/fonts/` (engine commit `4e9ca2255c20a72d9059c2f86bb450275abc55e3`) | `Inter-OFL.txt` |
| `JetBrainsMono-Regular.ttf`, `JetBrainsMono-Bold.ttf` | JetBrains Mono | Uppercase micro-labels | Axcenity Engine repo, `assets/fonts/` (same commit) | `JetBrainsMono-OFL.txt` |

## Plus Jakarta Sans

The engine repo doesn't ship this font, so it comes from Google Fonts.

- **Repository:** https://github.com/google/fonts
- **Commit:** `8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5` (2026-03-12), the
  latest commit touching `ofl/plusjakartasans/` when it was fetched on
  2026-10-30
- **Files fetched from that commit:**
  - `ofl/plusjakartasans/PlusJakartaSans[wght].ttf`, saved here as
    `PlusJakartaSans-Variable.ttf` (brackets removed for clean static
    URLs)
  - `ofl/plusjakartasans/OFL.txt`, saved here as `PlusJakartaSans-OFL.txt`
- **SHA-256 of the font file:**
  `89b3fb38aa0d275d7a731d0d817a4f1622b316b4d7fbdedcf02ee9099ff68bc8`
- **Upstream, per that commit's `METADATA.pb`:** designed by Tokotype,
  https://github.com/tokotype/PlusJakartaSans at commit
  `18d1cd2f7ea10481919d2f05c1f7064b7307fc26`
- **Copyright:** Copyright 2020 The Plus Jakarta Sans Project Authors
  (https://github.com/tokotype/PlusJakartaSans)
- **Licence:** SIL Open Font License, Version 1.1. The font is used
  unmodified apart from the file name. Under the OFL it can be bundled
  and redistributed with this software, but not sold on its own.

To update it, fetch both files from a newer google/fonts commit, then
update the commit, date and SHA-256 above.
