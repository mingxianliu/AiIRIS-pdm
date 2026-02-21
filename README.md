# AiIRIS-pdm

**AiIRIS Project Design Model — Code ↔ Figma 雙向同步（Python 版）**

將 Vue / React / HTML+CSS+JS 轉換為 Figma 可編輯的設計圖層，保留完整樹狀結構命名；Figma 修改後可回寫到原始碼。  
彙整 [figma-code-sync](https://github.com/erich/figma-code-sync) 的 IR 管線與 [ErSlice](https://github.com/openclaw/ErSlice) 的設計資產／manifest 概念。

---

## 功能總覽

| 能力 | 說明 |
|------|------|
| **Push (Code → Figma)** | Playwright 擷取 DOM → 命名引擎 → IR JSON → Figma Plugin 匯入，100% 命名控制 |
| **Pull (Figma → Code)** | Figma REST API 讀取 → IR Diff → Code Patcher 回寫 Vue/React/HTML |
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
             │  (Python)      │  │  (內建 figma_plugin/) │
             │ • DOM 擷取     │  │                    │
             │ • 命名引擎     │  │ • 讀取 IR JSON     │
             │ • IR 建構      │  │ • 建立節點 .name   │
             │ • Figma API 讀 │  │ • pluginData 回寫  │
             │ • Diff & Patch │  │                    │
             │ • design_assets│  └────────────────────┘
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
pip install playwright requests
playwright install chromium
```

### 2. Push: Code → Figma

```bash
# 預覽命名樹（不實際推送）
python -m airis_pdm.cli preview http://localhost:5173

# 生成 IR payload
python -m airis_pdm.cli push http://localhost:5173

# 指定 viewport
python -m airis_pdm.cli push http://localhost:5173 --viewport 375x812
```

產出於 `.figma-sync/`：
- `plugin-payload.json` — Figma Plugin 讀取的 payload
- `figma-import-payload.json` — 完整 IR
- `name-mapping.json` — figmaName → sourceFile 對照
- `reference-screenshot.png` — 參考截圖

### 3. Figma 匯入

1. 開啟 Figma，執行 **Code-to-Figma Sync** plugin（可沿用 [figma-code-sync](https://github.com/erich/figma-code-sync) 的 `figma_plugin/`）
2. 載入 `plugin-payload.json`，點擊 Import to Figma

### 4. Pull: Figma → Code

```bash
export FIGMA_TOKEN=your-personal-access-token
python -m airis_pdm.cli pull --file-key YOUR_FILE_KEY
python -m airis_pdm.cli pull --file-key YOUR_FILE_KEY --apply
```

---

## 專案結構

```
AiIRIS-pdm/
├── README.md
├── pyproject.toml
├── requirements.txt
├── airis_pdm/                  # 主套件
│   ├── __init__.py
│   ├── naming_engine.py        # 命名引擎（核心）
│   ├── dom_extractor_v2.py     # DOM 擷取（完整保真：gradient、shadow、SVG、grid 等）
│   ├── ir_builder_v2.py        # DOM → IR 2.0
│   ├── figma_reader.py         # Figma REST API + IR Diff
│   ├── code_patcher.py         # IR diff → 原始碼 patch
│   ├── config.py               # 設定載入
│   ├── design_assets.py        # ErSlice 風格 manifest / tokens 輔助
│   └── cli.py                  # CLI 入口
├── schemas/
│   └── ir_schema.json          # IR JSON Schema
├── figma-sync.config.json      # 設定範例
├── examples/
│   └── login-page-payload.json
└── docs/
    ├── ERSLICE_INTEGRATION.md  # 與 ErSlice 對齊說明
    └── COMPARISON_V2.md        # v2 管線功能矩陣（vs html-figma / v1）
```

### 管線（單一、完整保真）

- **DOM 擷取**：漸層、分邊 border、inset/text shadow、SVG、pseudo、CSS transform、grid、filter/backdrop-filter、base64 圖、canvas 等。
- **IR 2.0**：對應 Figma GradientPaint、INNER_SHADOW、BACKGROUND_BLUR、text decoration/truncation、clipsContent、z-index 等。
- **單一建置**：CLI `push` 與 Figma plugin 皆為此管線，無需切換選項。功能對照見 [docs/COMPARISON_V2.md](docs/COMPARISON_V2.md)。

---

## 與 ErSlice 的對齊

- **design-assets 目錄**：可選將 push 產出寫入 `design-assets/<module>/pages/<slug>/`，並產生 `erslice-manifest.json`、`completeness.json` 風格 metadata（見 `airis_pdm.design_assets`）。
- **設計 Token**：從 IR 或 CSS 擷取顏色/字型可輸出為 `tokens.css` 或 `tokens.merge.json` 索引，供 ErSlice 或設計系統使用。
- **Figma 雙向**：概念與 ErSlice 的 `figmaBidirectionalSync`、`preserveHierarchy` 一致，本專案以 Python 管線實作並與 Figma Plugin 協定相容。

詳見 [docs/ERSLICE_INTEGRATION.md](docs/ERSLICE_INTEGRATION.md)。

---

## 設定範例

`figma-sync.config.json`：

```json
{
  "figma": {
    "personalAccessToken": "YOUR_FIGMA_TOKEN",
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

---

## License

MIT — 見 [LICENSE](LICENSE)。
