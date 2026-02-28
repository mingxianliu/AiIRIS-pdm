# Generate Flow (Figma -> New Frontend)

This document describes the current primary workflow: generate a new frontend directly from a Figma file. No push snapshot is required.

---

## Overview

```
User runs: figma-sync generate --file-key <KEY> --target <react|vue|html|flutter>
       |
       v
Figma REST API -> FigmaToIR -> Component/Variant grouping -> Code generator -> Files
```

---

## Steps

1) **Fetch Figma file**
- Uses `FIGMA_TOKEN` or `figma.personalAccessToken`.
- Reads `document.children` and selects page(s) by `--page`, `--page-index`, or `--all-pages`.

2) **Convert to IR**
- `FigmaToIR` converts nodes to IR (layout, styles, text, auto layout).

3) **Component grouping**
- Layer name rule: `Component/Variant`.
- Example: `Button/Primary` -> Component `Button`, Variant `Primary`.
- If node type is `COMPONENT`/`INSTANCE`, it is treated as a component.

4) **Generate code**
- **React**: TSX + CSS Modules + `index.html` + `main.tsx`.
- **Vue**: SFC + scoped styles + `index.html` + `main.ts` + `App.vue`.
- **HTML**: `index.html` (and `pages/*.html` when `--all-pages`).
- **Flutter**: Dart widgets under `lib/`.

---

## Output Notes

- `styles/app.css` is always generated.
- `styles/utility.css` is optional. It is generated only when `--with-utility-css` is provided.
- Multi-page HTML:
  - `index.html` renders the first page content.
  - Hidden footer links point to `pages/*.html` using the `visually-hidden` utility class.

---

## Example Command

```
figma-sync generate --file-key YOUR_KEY --target react --output ./out
```
