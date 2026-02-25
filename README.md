# AiIRIS-pdm

**AiIRIS Project Design Model — Code ↔ Figma 雙向同步（Python 版）**

[![CI](https://github.com/mingxianliu/AiIRIS-pdm/actions/workflows/ci.yml/badge.svg)](https://github.com/mingxianliu/AiIRIS-pdm/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Version](https://img.shields.io/badge/version-0.4.0-green)](CHANGELOG.md)

將 Vue / React / HTML+CSS+JS 轉換為 Figma 可編輯的設計圖層，保留完整樹狀結構命名；Figma 修改後可回寫到原始碼。  
彙整 [figma-code-sync](https://github.com/erich/figma-code-sync) 的 IR 管線與 [ErSlice](https://github.com/openclaw/ErSlice) 的設計資產／manifest 概念。

---

## 功能總覽

| 能力 | 說明 |
|------|------|
| **Push (Code → Figma)** | Playwright 擷取 DOM → 命名引擎 → IR JSON → Figma Plugin 匯入，100% 命名控制 |
| **Pull (Figma → Code)** | Figma REST API 讀取 → IR Diff → Code Patcher 回寫 Vue/React/HTML |
| **Pull --apply** | 實際修改原始碼（`.vue`/`.tsx`/`.css`/`.scss`），支援 Tailwind / CSS Modules / inline 策略 |
| **Watch Mode** | 監聽檔案變更並自動 Push，即時同步開發中的畫面 |
| **Storybook Sync** | 批次從 Storybook 擷取 stories，一次產出多元件 IR 供 Figma 匯入 |
| **Config 驗證** | 載入時自動驗證欄位名稱、值域與型別，提供友善警告 |
| **Smart Image** | Base64 圖片智慧壓縮（最大 1024px），減少 payload 體積 |
| **Smart CJK Font** | 中文字體 Fallback 堆疊（fontFamilyStack），跨平台顯示一致 |
| **Gradient 支援** | Pull 時正確識別 GRADIENT_LINEAR / RADIAL / ANGULAR，不再誤判為「背景色消失」 |
| **Layout Integrity** | Pull 時偵測 Auto Layout 損壞並警告，回寫保護 |
| **命名優先順序** | `data-figma-name` → 組件名 → id → 語意 class → ARIA/tag → fallback |
| **ErSlice 對齊** | 可輸出 design-assets 友善的 manifest、設計 token 索引（選用） |

---

## 架構

```
                    ┌─────────────────────────┐
                    │    IR (JSON Schema)     │
                    │  中間表示層 — 統一契約   │
                    └──────┬──────────┬────────┘
                           │          │
             ┌─────────────▼──┐  ┌────▼──────────────┐
             │  AiIRIS-pdm    │  │  Figma Plugin 端   │
             │  (Python)      │  │  (figma_plugin/)   │
             │ • DOM 擷取     │  │ • 讀取 IR JSON     │
             │ • 命名引擎     │  │ • 建立節點 .name   │
             │ • IR 建構      │  │ • pluginData 回寫  │
             │ • Figma API 讀 │  │                    │
             │ • Diff & Patch │  └────────────────────┘
             │ • design_assets│
             └────────────────┘
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

### 2. Push: Code → Figma

```bash
# 預覽命名樹（不實際推送）
figma-sync preview http://localhost:5173
figma-sync preview http://localhost:5173 --selector '#sidebar'

# 生成 IR payload
figma-sync push http://localhost:5173
figma-sync push http://localhost:5173 --viewport 375x812
figma-sync push http://localhost:5173 --selector '#login-form'

# Watch：監聽檔案變更並自動 Push（需 config 內 source.srcRoot）
figma-sync watch http://localhost:5173

# Storybook：批次擷取 stories 轉 Figma 元件（Storybook 6.4+）
figma-sync push-stories http://localhost:6006
figma-sync push-stories http://localhost:6006 --filter 'Button'
```

產出於 `.figma-sync/`：
- `plugin-payload.json` — Figma Plugin 讀取的 payload
- `figma-import-payload.json` — 完整 IR
- `name-mapping.json` — figmaName → sourceFile 對照
- `reference-screenshot.png` — 參考截圖

### 3. Figma 匯入

1. 本專案內建 **Code-to-Figma Sync** plugin：`cd figma_plugin && npm install && npm run build`，產出 `dist/code.js`、`dist/ui.html`。
2. 在 Figma 載入該 plugin，選擇 `plugin-payload.json`，點擊 Import to Figma。

### 4. Pull: Figma → Code

#### 4-1. 取得 Figma Token 與 File Key

```bash
# 1. 前往 Figma → Account Settings → Personal Access Tokens → 建立 token
# 2. Figma 文件 URL 格式：https://www.figma.com/file/{FILE_KEY}/...
export FIGMA_TOKEN=figd_xxxxxxxxxxxxxxxxxxxx
```

#### 4-2. 預覽 Diff（不修改任何檔案）

```bash
figma-sync pull --file-key YOUR_FILE_KEY
```

輸出範例：
```
📥 Pulling from Figma: YOUR_FILE_KEY

── CHANGED: LoginForm/Button ────────────────────────
  styles.backgroundColor : rgba(99, 102, 241, 1) → rgba(79, 70, 229, 1)
  text.fontSize          : 14 → 16
  styles.borderRadius    : {"topLeft":4,...} → {"topLeft":8,...}

💡 使用 --apply 將變更套用到原始碼（需設定 source.srcRoot）。
```

#### 4-3. 套用變更到原始碼（需先設定 `source.srcRoot`）

```bash
figma-sync pull --file-key YOUR_FILE_KEY --apply
```

這會依照 `figma-sync.config.json` 的 `source.styleStrategy`：

| strategy | 修改結果 |
|----------|----------|
| `tailwind` | 在對應元素的 `class="..."` 中注入 Tailwind class（如 `text-[16px]`、`bg-[#4f46e5]`） |
| `css-modules` | 找到 `.module.css` 檔案，在對應 selector 中更新/插入 CSS 屬性 |
| `scss` | 找到 `.scss` 檔案，在對應 selector 中更新/插入 CSS 屬性 |
| `inline` | 在對應元素的 `style="..."` 中注入 inline style |

**常見錯誤訊息：**

| 錯誤 | 原因 | 解法 |
|------|------|------|
| `❌ Figma API 403` | Token 無效或過期 | 至 Figma Account Settings 重新產生 token |
| `❌ Figma API 404` | file key 錯誤 | 確認 URL 中的 file key 是否正確 |
| `⚠️ source.srcRoot 未設定` | config 缺少 srcRoot | 設定 `source.srcRoot` 指向原始碼目錄 |

---

## 設定範例

`figma-sync.config.json`：

```json
{
  "figma": {
    "personalAccessToken": "figd_xxxxxxxxxxxxxxxxxxxx",
    "fileKey": "YOUR_FILE_KEY"
  },
  "source": {
    "framework": "vue",
    "styleStrategy": "tailwind",
    "entryUrl": "http://localhost:5173",
    "srcRoot": "./src"
  },
  "viewport": { "width": 1440, "height": 900 },
  "naming": {
    "separator": "/",
    "ignoreClasses": ["flex", "grid", "p-", "m-", "text-", "bg-"]
  },
  "export": {
    "snapshotDir": ".figma-sync"
  }
}
```

> **`source.srcRoot`**：Pull `--apply` 時必須設定，指向放置元件原始碼的目錄（如 `./src`），用於搜尋對應的 `.vue`/`.tsx`/`.css` 等檔案。

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
