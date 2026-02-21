# 理解 Push 程式碼（Code → Figma）

Push 的程式路徑與資料流如下。

---

## 流程總覽

```
使用者執行: figma-sync push <url>
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. CLI (cli.py)                                                  │
│    cmd_push() → 組 ExtractionConfig → 呼叫 extract_dom_tree()    │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. DOM 擷取 (dom_extractor.py)                                    │
│    Playwright 開瀏覽器 → goto(url) → page.evaluate(DOM_WALKER_JS) │
│    回傳 { tree, screenshot, viewport }                            │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. IR 建構 (ir_builder.py)                                        │
│    build_ir_from_extraction() → IRBuilderV2.build()               │
│    遞迴 _convert_node()，產出 IR 2.0 樹 + nameMapping             │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. 寫出 (ir_builder.save_ir) + 截圖                               │
│    figma-import-payload.json, name-mapping.json,                  │
│    plugin-payload.json, reference-screenshot.png                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 1. 入口：CLI `cmd_push`

**檔案**：`airis_pdm/cli.py`

- **約 35–91 行**：`async def cmd_push(args, config)`
- 從 config / args 組出 **ExtractionConfig**（viewport、framework、root_selector 等）。
- 呼叫 **`extract_dom_tree(url, extraction_config)`**（約 53 行），得到 `result = { tree, screenshot, viewport }`。
- 若 `result["tree"]` 為空則直接 return。
- 呼叫 **`build_ir_from_extraction(result, config)`**（約 61 行）得到 `ir_doc`。
- 用 **`save_ir(ir_doc, output_dir)`**（約 67 行）寫出三個 JSON。
- 把 `result["screenshot"]` 寫成 `reference-screenshot.png`。
- 選用：`--erslice` 時寫 ErSlice manifest / completeness。

關鍵依賴：`dom_extractor.extract_dom_tree`、`ir_builder.build_ir_from_extraction`、`ir_builder.save_ir`。

---

## 2. DOM 擷取：`extract_dom_tree`

**檔案**：`airis_pdm/dom_extractor.py`

- **約 935–1000 行**：`async def extract_dom_tree(url, config)`
- 用 **Playwright** 的 `async_playwright()` → `chromium.launch(headless=True)` → `new_context(viewport)` → `new_page()`。
- **`page.goto(url, wait_until="networkidle")`**：載入你給的 URL（例如 localhost:5173）。
- 可選：`wait_for_selector`、再 `wait_for_timeout(500)` 等 hydration。
- 把一包 **js_config**（rootSelector、maxDepth、detectGrid、framework、capturePseudo 等）傳進瀏覽器。
- **`raw_tree = await page.evaluate(DOM_WALKER_V2_JS, js_config)`**：在頁面內執行 **DOM_WALKER_V2_JS**（約 80–930 行），這段 JS 會：
  - 用 `config.rootSelector` 找根節點（例如 `#app, #root, body`）。
  - 遞迴走 DOM，跳過 SCRIPT/STYLE 等，對每個節點取：
    - tag、attrs、layout（getBoundingClientRect）、computed styles、
    - background（含 gradient）、border、shadow、text、image、SVG、pseudo 等。
  - 回傳一顆「原始樹」物件給 Python。
- **`screenshot_bytes = await page.screenshot(full_page=False)`**。
- `browser.close()`。
- 回傳 **`{ "tree": raw_tree, "screenshot": screenshot_bytes, "viewport": {...} }`**。

所以「擷取」發生在瀏覽器裡；Python 只負責開關瀏覽器、傳 config、接回 tree 與截圖。

---

## 3. IR 建構：`build_ir_from_extraction` → `IRBuilderV2.build`

**檔案**：`airis_pdm/ir_builder.py`

- **約 504–524 行**：`def build_ir_from_extraction(extraction_result, config)`
  - 從 config 讀 `naming`（separator、ignoreClasses）組 **NamingConfig**。
  - 建 **NamingEngine**、從 config 讀 **source**（framework、styleStrategy、entryUrl）。
  - 建 **IRBuilderV2(naming_engine, framework, style_strategy, entry_file)**。
  - 呼叫 **`builder.build(raw_tree=extraction_result["tree"], viewport=extraction_result["viewport"])`**。

- **約 46–63 行**：`IRBuilderV2.build(raw_tree, viewport)`
  - 清空 `name_mapping`、`_node_count`。
  - **`ir_tree = self._convert_node(raw_tree, parent_path="")`** 遞迴把「原始樹」轉成 IR 樹。
  - 回傳一顆文件：
    - **version**: `"2.0.0"`
    - **source**: framework、entryFile、styleStrategy、generatedAt
    - **viewport**: 傳入的 viewport
    - **nameMapping**: 建樹過程中填的 figmaName → { sourceFile, selector, componentName }
    - **stats**: { nodeCount }
    - **tree**: 根 IR 節點（給 Figma 用的那棵樹）

- **約 68–180+ 行**：`_convert_node(raw, parent_path)`
  - 可選：若啟用 smart_flatten 且該節點可壓扁，直接遞迴子節點。
  - 用 **naming_engine.resolve_name(...)** 得到 **figmaName**，再取 local name（最後一段）。
  - **figmaType**：`_determine_type(raw)`（TEXT / RECTANGLE / FRAME / AUTO_LAYOUT / IMAGE / VECTOR 等）。
  - 組 **ir_node**：figmaName、figmaType、htmlTag、layout、autoLayout（若有）、**styles**（`_convert_styles`：fills、effects、border、borderRadius…）、text、image、pluginData、children（含 pseudo 子節點）。
  - 每個節點會寫進 **name_mapping**（key = 階層路徑的 figmaName），value 含 sourceFile（entryUrl）、selector、componentName。
  - 子節點遞迴 **`_convert_node(child, parent_path)`**。

也就是：**原始樹 + 命名規則 + 樣式轉換** → **IR 2.0 文件（含 tree 與 nameMapping）**。

---

## 4. 寫出：`save_ir` + 截圖

**檔案**：`airis_pdm/ir_builder.py` 約 621–635 行

- **`save_ir(ir_doc, output_dir)`**：
  - **figma-import-payload.json**：整份 `ir_doc`（含 version、source、viewport、nameMapping、stats、**tree**）。
  - **name-mapping.json**：只寫 `ir_doc["nameMapping"]`，方便 Pull 時對照。
  - **plugin-payload.json**：只寫 **`ir_doc["tree"]`**，給 Figma Plugin 讀。

截圖由 **cli.py** 寫入 `output_dir/reference-screenshot.png`（即 `result["screenshot"]`）。

---

## 5. 資料形狀（簡要）

- **extract_dom_tree 回傳**：  
  `{ tree: { tag, attrs, layout, styles, children, ... }, screenshot: bytes, viewport: { width, height } }`  
  其中 `tree` 的 `styles` 可能含 backgroundColor、gradient、border、shadow、textContent 等（由 DOM_WALKER_JS 產出）。

- **build 產出的 ir_doc**：  
  `{ version: "2.0.0", source: {...}, viewport: {...}, nameMapping: {...}, stats: {...}, tree: ir_node }`  
  每個 **ir_node** 含：figmaName、figmaType、htmlTag、layout、styles（fills/effects/border…）、text/image、pluginData、children。

- **plugin-payload.json**：僅 **ir_doc["tree"]**，Figma Plugin 用這棵樹建立畫布上的節點。

---

## 6. 對照表：Push 用到的檔案

| 步驟 | 檔案 | 函數／重點 |
|------|------|------------|
| 入口 | `airis_pdm/cli.py` | `cmd_push()`：組 config、呼叫擷取→建 IR→寫出、寫截圖 |
| 擷取 | `airis_pdm/dom_extractor.py` | `extract_dom_tree()`：Playwright + `page.evaluate(DOM_WALKER_V2_JS)` |
| 擷取（瀏覽器內） | `airis_pdm/dom_extractor.py` | `DOM_WALKER_V2_JS`：遞迴 DOM、算樣式、回傳原始樹 |
| IR | `airis_pdm/ir_builder.py` | `build_ir_from_extraction()` → `IRBuilderV2.build()` → `_convert_node()` |
| 命名 | `airis_pdm/naming_engine.py` | `NamingEngine.resolve_name()`（被 ir_builder 使用） |
| 寫出 | `airis_pdm/ir_builder.py` | `save_ir()`：寫三個 JSON |

整體來說：**Push = 瀏覽器裡跑 DOM Walker 擷取樹與樣式 → Python 用命名引擎與 IR 建構轉成 IR 2.0 → 寫出 payload 與截圖**；Figma 端再讀 `plugin-payload.json` 建圖層。
