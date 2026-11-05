---
name: droidknights-design
description: Use this skill to generate well-branded interfaces and assets for DroidKnights (Android Conference 2026), either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, mascot assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.
If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.
If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

Key entry points:
- `styles.css` — link this one file to get all tokens + fonts.
- `readme.md` — full brand guide (voice, color, type, iconography, layout).
- `tokens/` — CSS custom properties (`--dk-*`).
- `components/` — React primitives; load `_ds_bundle.js`, read `window.DroidKnightsDesignSystem_0cd94e`.
- `assets/mascot/` — galaxy droid, 1 hero + 9 poses (transparent PNG, use with soft glow over dark).
- `ui_kits/` — slide deck template, marketing landing, event collateral.
