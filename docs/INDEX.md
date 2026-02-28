# AiIRIS-pdm Docs Index

> Generate-first documentation index. Last updated: 2026-02.

---

## Overview

| Item | Description |
|------|-------------|
| **Name** | AiIRIS-pdm (AiIRIS Project Design Model) |
| **Focus** | Figma -> new frontend (Generate) |
| **Inputs** | FIGMA_TOKEN, file key, target (react/vue/html/flutter) |
| **Outputs** | New project files under the output directory |
| **Tech** | Python 3.10+, Figma REST API |

---

## Docs

| File | Purpose |
|------|---------|
| [INDEX.md](INDEX.md) | This index |
| [GENERATE_FLOW.md](GENERATE_FLOW.md) | Generate workflow details |
| [LEGACY_PUSH_PULL.md](LEGACY_PUSH_PULL.md) | Legacy push/pull/watch workflow |
| [ERSLICE_INTEGRATION.md](ERSLICE_INTEGRATION.md) | Optional ErSlice alignment |

---

## Quick Commands

```bash
# Generate (React)
figma-sync generate --file-key YOUR_FILE_KEY --target react --output ./out

# Generate (Vue)
figma-sync generate --file-key YOUR_FILE_KEY --target vue --output ./out

# Generate (HTML, multi-page)
figma-sync generate --file-key YOUR_FILE_KEY --target html --output ./out --all-pages

# Generate (Flutter)
figma-sync generate --file-key YOUR_FILE_KEY --target flutter --output ./out

# Optional utility.css
figma-sync generate --file-key YOUR_FILE_KEY --target react --output ./out --with-utility-css
```

---

*Sources: repository code and docs.*
