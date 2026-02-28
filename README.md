# AiIRIS-pdm

**AiIRIS Project Design Model — Figma → New Frontend（Python 版）**

[![CI](https://github.com/mingxianliu/AiIRIS-pdm/actions/workflows/ci.yml/badge.svg)](https://github.com/mingxianliu/AiIRIS-pdm/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Version](https://img.shields.io/badge/version-0.4.0-green)](CHANGELOG.md)

從 Figma 直接產生新的前端（React / Vue / HTML / Flutter）。
彙整 [figma-code-sync](https://github.com/erich/figma-code-sync) 的 IR 管線與 [ErSlice](https://github.com/openclaw/ErSlice) 的設計資產／manifest 概念。

---

## 功能總覽

| 能力 | 說明 |
|------|------|
| **Generate (Figma → New Frontend)** | 讀取 Figma → IR → 產出 React/Vue/HTML/Flutter 專案檔 |
| **Component/Variant 規則** | `Button/Primary` → Component `Button`、Variant `Primary` |
| **分離 CSS** | 產生 `styles/app.css`，可選 `utility.css` |
| **多頁 HTML** | `index.html` 渲染第一頁，`pages/*.html` 保留所有頁面 |
| **ErSlice 對齊** | 可輸出 design-assets 友善的 manifest、設計 token 索引（選用） |

---

## 架構

```
Input: Figma file (fileKey) + FIGMA_TOKEN

                    ┌─────────────────────────┐
                    │    IR (JSON Schema)     │
                    │  中間表示層 — 統一契約   │
                    └──────────┬──────────────┘
                               │
             ┌─────────────────▼─────────────────┐
             │            AiIRIS-pdm             │
             │            (Python)               │
             │ • Figma API 讀取                  │
             │ • FigmaToIR                       │
             │ • Component/Variant 分組          │
             │ • 產生 React/Vue/HTML/Flutter     │
             │ • design_assets（選用）           │
             └────────────────────────────────────┘

Output (React): ./out/index.html, main.tsx, components/, pages/, styles/
Output (Vue):   ./out/index.html, main.ts, App.vue, components/, pages/, styles/
Output (HTML):  ./out/index.html, pages/, styles/
Output (Flutter): ./out/lib/components/, lib/pages/
Note: use --with-utility-css to emit styles/utility.css and @import it from app.css.
```

---

## 快速開始

### 1. 安裝

```bash
git clone https://github.com/mingxianliu/AiIRIS-pdm.git
cd AiIRIS-pdm
pip install -e ".[dev]"
playwright install chromium
```

或僅依賴：

```bash
pip install playwright requests watchdog
playwright install chromium
```

### 2. Generate: Figma → New Frontend

## Generate: Figma → New Frontend（不需要 push）

### 必要輸入

- `FIGMA_TOKEN`（或 `figma.personalAccessToken`）
- `fileKey`（或 `--file-key`）
- `--target`（react / vue / html / flutter）

### 輸入 / 輸出對照表

| 輸入 | 說明 | 主要輸出 |
|------|------|----------|
| `FIGMA_TOKEN` | Figma Personal Access Token | Figma 文件內容可被讀取 |
| `fileKey` | Figma file key | 生成對應頁面與元件 |
| `--target react` | 生成 React 專案檔 | `index.html`, `main.tsx`, `components/*.tsx`, `pages/*.tsx`, `*.module.css`, `styles/app.css` |
| `--target vue` | 生成 Vue 專案檔 | `index.html`, `main.ts`, `App.vue`, `components/*.vue`, `pages/*.vue`, `styles/app.css` |
| `--target html` | 生成 HTML | `index.html`（多頁時另有 `pages/*.html`）+ `styles/app.css` |
| `--target flutter` | 生成 Flutter | `lib/components/*.dart`, `lib/pages/*.dart` |
| `--all-pages` | 匯出所有頁面 | 多頁 HTML：`pages/*.html` + `index.html` 渲染第一頁 |
| `--with-utility-css` | 產生 utility.css | `styles/utility.css` + `app.css` 自動 `@import` |

### 指令範例

```bash
export FIGMA_TOKEN=figd_xxxxxxxxxxxxxxxxxxxx

# React
figma-sync generate --file-key YOUR_FILE_KEY --target react --output ./out

# Vue
figma-sync generate --file-key YOUR_FILE_KEY --target vue --output ./out

# HTML (單頁)
figma-sync generate --file-key YOUR_FILE_KEY --target html --output ./out

# HTML (多頁)
figma-sync generate --file-key YOUR_FILE_KEY --target html --output ./out --all-pages

# Flutter
figma-sync generate --file-key YOUR_FILE_KEY --target flutter --output ./out

# 可選：產生 utility.css（預設不產生）
figma-sync generate --file-key YOUR_FILE_KEY --target react --output ./out --with-utility-css
```

### 實際操作示例

```bash
export FIGMA_TOKEN=figd_xxxxxxxxxxxxxxxxxxxx
figma-sync generate --file-key YOUR_FILE_KEY --target react --output ./out --all-pages
```

預期輸出（摘要）：

```
out/
  index.html
  main.tsx
  styles/
    app.css
  components/
    ...
  pages/
    ...
```

### 實際操作示例（Vue）

```bash
export FIGMA_TOKEN=figd_xxxxxxxxxxxxxxxxxxxx
figma-sync generate --file-key YOUR_FILE_KEY --target vue --output ./out
```

### 實際操作示例（Flutter）

```bash
export FIGMA_TOKEN=figd_xxxxxxxxxxxxxxxxxxxx
figma-sync generate --file-key YOUR_FILE_KEY --target flutter --output ./out
```

### 產出結構（摘要）

- **React**：`index.html`、`main.tsx`、`components/*.tsx`、`pages/*.tsx`、`*.module.css`、`styles/app.css`
- **Vue**：`index.html`、`main.ts`、`App.vue`、`components/*.vue`、`pages/*.vue`、`styles/app.css`
- **HTML**：`index.html`（多頁時另有 `pages/*.html`）+ `styles/app.css`
- **Flutter**：`lib/components/*.dart`、`lib/pages/*.dart`

> **重要**
> `styles/app.css` 預設不包含 `utility.css`。若需要此檔，務必加上 `--with-utility-css`，才會輸出 `styles/utility.css` 並在 `app.css` 中 `@import`。

> 多頁 HTML 模式下，`index.html` 會渲染第一頁內容，並保留隱藏的導覽連結（`visually-hidden`）指向 `pages/*.html`。

### CLI 參數（Generate）

| 參數 | 必填 | 說明 |
|------|------|------|
| `--file-key` | 是 | Figma file key |
| `--target` | 是 | `react` / `vue` / `html` / `flutter` |
| `--output` | 否 | 輸出資料夾（預設 `./generated`） |
| `--page` | 否 | 指定頁面名稱 |
| `--page-index` | 否 | 指定頁面索引 |
| `--all-pages` | 否 | 匯出所有頁面 |
| `--with-utility-css` | 否 | 產生 `styles/utility.css` 並在 `app.css` 中匯入 |

### 範例輸出樹狀（React）

```
out/
  index.html
  main.tsx
  styles/
    app.css
    utility.css (only with --with-utility-css)
  components/
    Button.tsx
    Button.module.css
  pages/
    Home.tsx
    Home.module.css
```

### 範例輸出樹狀（Vue）

```
out/
  index.html
  main.ts
  App.vue
  styles/
    app.css
    utility.css (only with --with-utility-css)
  components/
    Button.vue
  pages/
    Home.vue
```

### 範例輸出樹狀（HTML）

```
out/
  index.html
  pages/
    Home.html
    Pricing.html
  styles/
    app.css
    utility.css (only with --with-utility-css)
```

### 範例輸出樹狀（Flutter）

```
out/
  lib/
    components/
      button.dart
    pages/
      home.dart
```

### 命名規則（Component / Variant）

Generator 會依 Figma layer name 拆解成 `Component/Variant`：

- `Button/Primary` → Component: `Button`、Variant: `Primary`
- `Card` → Component: `Card`、Variant: `Default`

當 Figma node 是 `COMPONENT`/`INSTANCE` 時，會優先視為可生成的元件。

---

## Legacy: Push / Pull / Watch

舊流程（Code ↔ Figma 雙向同步）已移到 [docs/LEGACY_PUSH_PULL.md](docs/LEGACY_PUSH_PULL.md)。

### Generate 設定範例（可選）

`figma-sync.config.json` 只要包含 figma 區塊即可：

```json
{
  "figma": {
    "personalAccessToken": "figd_xxxxxxxxxxxxxxxxxxxx",
    "fileKey": "YOUR_FILE_KEY"
  }
}
```

---

## 專案結構

```
AiIRIS-pdm/
├── README.md
├── CHANGELOG.md
├── pyproject.toml
├── figma-sync.config.json      # 設定範例
├── airis_pdm/                  # 主套件（Python 0.4.0）
│   ├── __init__.py
│   ├── cli.py                  # CLI：push / watch / pull / preview / push-stories
│   ├── config.py               # 設定載入 + 欄位驗證（validate_config）
│   ├── dom_extractor.py        # Playwright + DOM Walker，擷取 DOM 樹與樣式
│   ├── ir_builder.py           # DOM → IR 2.0、save_ir 寫出 JSON
│   ├── naming_engine.py        # 命名引擎（data-figma-name → 組件 → id → class → fallback）
│   ├── figma_reader.py         # Figma REST API、FigmaToIR（含 Gradient）、IRDiffer
│   ├── code_patcher.py         # IR diff → 原始碼 patch（Tailwind/CSS/inline 寫檔）
│   └── design_assets.py        # ErSlice 風格 manifest / completeness（選用）
├── figma_plugin/               # 內建 Figma Plugin（TypeScript）
│   ├── src/code.ts             # Plugin 邏輯（Gradient/Shadow/AutoLayout 全支援）
│   ├── src/ui.html             # Plugin UI
│   ├── src/__tests__/          # Jest 單元測試（純函數）
│   └── dist/                   # npm run build 產出
├── .github/workflows/ci.yml   # GitHub Actions CI（Python 測試 + TS 型別檢查）
├── schemas/
│   └── ir_schema.json          # IR JSON Schema
├── examples/
│   └── login-page-payload.json
├── tests/
│   ├── test_smoke.py
│   ├── test_ir_flattening.py
│   ├── test_pull_pipeline.py   # FigmaToIR / IRDiffer / CodePatcher mock 測試
│   ├── test_style_converter.py # StyleConverter Tailwind/CSS 轉換測試
│   ├── test_naming_engine.py   # NamingEngine 優先順序與邊界案例
│   ├── test_watch_debounce.py  # ChangeHandler 防抖與過濾測試
│   ├── test_storybook_sync.py  # cmd_push_stories mock 測試
│   └── test_apply_to_file.py   # 實際寫檔整合測試（Tailwind/CSS/inline）
└── docs/
    └── ...
```

---

## 測試

### Python 測試（100 test cases）

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Figma Plugin 測試（Jest，36 test cases）

```bash
cd figma_plugin
npm install
npm test
```

---

## CI/CD

本專案使用 GitHub Actions 自動執行：

| Job | 內容 |
|-----|------|
| **Python Tests** | Python 3.10/3.11/3.12 × ubuntu/macos 矩陣測試 |
| **Plugin TypeScript** | tsc 型別檢查 + npm run build |
| **Version Check** | 確認 pyproject.toml / `__init__.py` / cli.py 版本號一致 |

---

## 與 ErSlice 的對齊

- **design-assets 目錄**：可選將 push 產出寫入 `design-assets/<module>/pages/<slug>/`，並產生 `erslice-manifest.json`、`completeness.json` 風格 metadata（見 `airis_pdm.design_assets`）。
- **設計 Token**：從 IR 或 CSS 擷取顏色/字型可輸出為 `tokens.css` 或 `tokens.merge.json` 索引，供 ErSlice 或設計系統使用。
- **Figma 雙向**：概念與 ErSlice 的 `figmaBidirectionalSync`、`preserveHierarchy` 一致，本專案以 Python 管線實作並與 Figma Plugin 協定相容。

詳見 [docs/ERSLICE_INTEGRATION.md](docs/ERSLICE_INTEGRATION.md)。

---

## License

MIT — 見 [LICENSE](LICENSE)。
