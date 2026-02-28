# Legacy: Push / Pull / Watch

This document keeps the previous bidirectional sync workflow for reference. The current primary workflow is Generate (Figma -> New Frontend).

---

## Push (Code -> Figma)

```bash
figma-sync preview http://localhost:5173
figma-sync push http://localhost:5173
figma-sync push http://localhost:5173 --viewport 375x812
figma-sync push http://localhost:5173 --selector '#login-form'
```

Outputs under `.figma-sync/`:
- `plugin-payload.json`
- `figma-import-payload.json`
- `name-mapping.json`
- `reference-screenshot.png`

## Figma Import (Plugin)

1. Build plugin: `cd figma_plugin && npm install && npm run build`
2. In Figma, load plugin and import `plugin-payload.json`.

## Pull (Figma -> Code)

```bash
export FIGMA_TOKEN=figd_xxxxxxxxxxxxxxxxxxxx
figma-sync pull --file-key YOUR_FILE_KEY
figma-sync pull --file-key YOUR_FILE_KEY --apply
```

Style strategies:
- `tailwind`
- `css-modules`
- `scss`
- `inline`

## Watch

```bash
figma-sync watch http://localhost:5173
```

---

This legacy flow may be removed in a future release.
