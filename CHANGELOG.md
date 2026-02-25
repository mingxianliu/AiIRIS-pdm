# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-02-25 — 穩定性全面強化

本版本聚焦於**修正核心 Bug、落實 Pull --apply 寫檔、改善錯誤訊息、補強測試覆蓋率**，
並完善 CLI 使用體驗。測試覆蓋從 7 個增加至 **100 個** test case，全部通過。

### Fixed（Bug 修正）

- **`figma_reader.py` NameError**：`FigmaToIR.convert()` 使用 `children` 變數早於賦值，
  導致任何含子節點的 FRAME Pull 時直接 crash。已將賦值提至正確位置。（P0 #2）
- **截圖遺失**：`process_url_to_ir()` 重構後截圖從 `result["screenshot"]` 被靜默丟棄，
  `push` 不再產生 `reference-screenshot.png`。已改回傳 `(ir_doc, result)` tuple 並正確寫出截圖。（P0 #3）
- **smoke test 版本斷言**：`test_smoke.py` 斷言版本為 `"0.2.0"` 與實際 `"0.3.0"` 不符，CI 必失敗。（P0 #4）
- **`args.selector` 副作用**：`cmd_push_stories` 直接修改 `args.selector`，
  改用 local 變數 `sb_selector` 避免污染。（P1 #7）

### Added（新功能）

- **`pull --apply` 真正寫回原始碼**（P0 #1 / P4 #18）：
  - `CodePatcher` 全面重寫，支援 Tailwind / CSS-Modules / SCSS / inline 三種策略實際讀寫檔案
  - 新增 `find_files_by_selector(src_root, selector)`：依 CSS selector（`#id` / `.class`）
    在 srcRoot 內搜尋對應的 `.vue/.tsx/.html/.css/.scss/.module.css` 檔案
  - 新增 `url_to_local_path(url, src_root)`：將 `entryUrl` 類型字串轉換為本機路徑（若已是本機路徑則直接使用）
  - `CodePatcher` 新增 `dry_run=True` 模式（Pull 不含 `--apply` 時預覽，不寫檔）
  - Config 新增 `source.srcRoot` 對應 `--apply` 所需原始碼目錄

- **Figma API 友善錯誤訊息**（P1 #5）：
  - `cmd_pull` 包 try/except，403 提示「Token 過期」、404 提示「file key 錯誤」、其餘顯示完整訊息

- **Watch Mode asyncio 改善**（P1 #6）：
  - 改用獨立 `threading.Thread` 運行 `loop.run_forever()`，主執行緒只做 `observer.join()`
  - 完全解決主執行緒與 `asyncio.run_coroutine_threadsafe` 之間的 event loop 競爭與潛在 deadlock

- **FigmaToIR Gradient 支援**（P1 #9）：
  - `_extract_styles()` 加入 `GRADIENT_LINEAR`、`GRADIENT_RADIAL`、`GRADIENT_ANGULAR` 解析
  - 輸出至 IR `fills[]`，避免 Pull 時 Gradient 節點被誤判為「背景色消失」

- **Config 欄位驗證**（P1 #8）：
  - `validate_config(cfg)` 自動在 `load_config()` 時執行
  - 對未知頂層欄位、區塊內拼字錯誤、framework/styleStrategy 非法值、viewport 型別錯誤、srcRoot 目錄不存在給出友善警告

- **CLI UX 改善**（P3）：
  - `figma-sync --version` 正式支援（`-v` 也可用）（#17）
  - 各子指令加入 `epilog` 使用範例（`push`、`watch`、`push-stories`、`preview`、`pull`）（#16）
  - `preview` 指令補上 `--selector` 參數，與 `push`/`watch` 行為一致（#15）
  - `pull` 的所有提示訊息改為繁體中文清楚說明

### Tests（測試補強）

從 7 個增加至 **100 個 test case**：

| 測試檔案 | Cases | 涵蓋範圍 |
|----------|-------|---------|
| `test_pull_pipeline.py` | 20 | `FigmaToIR`（8）+ `IRDiffer`（6）+ `CodePatcher` dry-run（6） |
| `test_style_converter.py` | 26 | `StyleConverter` Tailwind/CSS 全屬性轉換 |
| `test_naming_engine.py` | 14 | `NamingEngine` 7 層命名優先順序、PascalCase、特殊字元 |
| `test_watch_debounce.py` | 9 | `ChangeHandler` 過濾、debounce 防抖、副檔名白名單 |
| `test_storybook_sync.py` | 11 | `cmd_push_stories` 完整流程、錯誤處理、filter |
| `test_apply_to_file.py` | 20 | 實際寫檔（Tailwind/CSS/inline）、`find_files_by_selector`、config 驗證 |

## [0.3.0] - 2026-02 — DesignOps 協作平台


本版本將 AiIRIS-pdm 從「轉檔器」升級為**完整 DesignOps 協作平台**，新增五項重大功能：

### Added

1. **Watch Mode（即時監聽並自動 Push）**
   - 指令：`figma-sync watch <url>`，依 config `source.srcRoot` 監聽檔案變更
   - 使用 `watchdog` 監聽指定目錄，變更後自動執行 push（可搭配 `--viewport`、`--selector`、`--erslice`）
   - 適合開發時保持 Code → Figma 即時同步

2. **Storybook Sync（批次轉 Figma 元件）**
   - 指令：`figma-sync push-stories <storybook_url>`（例如 `http://localhost:6006`）
   - 取得 Storybook 6.4+ 的 `/stories.json`，依 stories 逐一擷取 iframe 並產出 IR
   - 產出彙總為單一 snapshot，可一次匯入多個元件至 Figma

3. **Smart Image Compression（Base64 圖片體積優化）**
   - 實作：`airis_pdm/dom_extractor.py` 內 `captureImageData`
   - 最大邊長 1024px、保持長寬比；`<img>` / Canvas 以 `image/png` 縮放輸出
   - 顯著減少 plugin-payload.json 體積，避免傳輸與 Plugin 載入記憶體問題

4. **Smart CJK Font（中文字體 Fallback 堆疊）**
   - 實作：`airis_pdm/ir_builder.py` 之 `cjk_font_family`（支援 `list[str] | str`）
   - 預設：`["PingFang TC", "Microsoft JhengHei", "Noto Sans TC", "sans-serif"]`
   - IR 輸出 `fontFamily`（首項）與 `fontFamilyStack`（完整列表），config 可設 `export.cjkFontFamily`

5. **Layout Integrity Check（回寫保護）**
   - Pull 流程中偵測 Figma 節點「失去 Auto Layout」的變更（`layout.integrity`）
   - 若存在則顯示 **LAYOUT INTEGRITY WARNING**，列出受影響 frame，提醒回寫可能影響版面準確度
   - 避免盲目 `--apply` 導致 Auto Layout 損壞而不自知

### Changed

- 新增依賴：`watchdog`（Watch Mode 必要）
- CLI 新增子指令：`watch`、`push-stories`

---

## [0.2.1] - 2026-02

### Added

- **Base64 圖片智慧壓縮 (Smart Compression)**（`airis_pdm/dom_extractor.py`）
  - `captureImageData`：最大邊長限制 1024px、保持長寬比
  - `<img>` 與 Canvas 統一以 `image/png` 輸出並配合縮放，兼顧透明度與體積
  - 顯著減少 plugin-payload.json 體積，降低傳輸與 Figma Plugin 載入記憶體風險

- **CJK 字體優先順序堆疊 (Font Stack)**（`airis_pdm/ir_builder.py`）
  - `cjk_font_family` 支援 **列表**（`list[str] | str`）
  - 預設堆疊：`["PingFang TC", "Microsoft JhengHei", "Noto Sans TC", "sans-serif"]`
  - 偵測到 CJK 時 IR 輸出：`fontFamily`（首項）、`fontFamilyStack`（完整列表）
  - config 可透過 `export.cjkFontFamily` 覆寫；Figma Plugin 端可依序讀取 `fontFamilyStack` 嘗試載入（目前仍讀 `fontFamily` 即首項）

---

## [0.2.0] - 2025-02-21

### Added

- **單一管線（完整保真）**：CLI 與 Figma plugin 僅保留一套實作
  - `dom_extractor_v2` + `ir_builder_v2` 為唯一 push 管線（gradient、shadow、SVG、grid、IR 2.0 等）
  - Figma plugin 單一入口：`src/code.ts` 為完整保真實作，`npm run build` 產出 `dist/code.js`
  - docs/COMPARISON_V2.md：功能矩陣（vs html-figma / 舊 v1）

### Changed

- **不再並存 v1/v2**：移除 CLI `--v2`、移除 manifest-v2、build:v2；一律使用最佳管線
- README：專案結構與說明改為單一管線、單一 plugin 建置
- 移除未使用的 `dom_extractor.py`、`ir_builder.py`（僅保留 dom_extractor_v2、ir_builder_v2）
- 版本統一為 0.2.0（`__init__.py`、`pyproject.toml`）

### 後續優化 (0.2.0)

- **模組命名**：`dom_extractor_v2.py` → `dom_extractor.py`、`ir_builder_v2.py` → `ir_builder.py`，對外 API 保留 `IRBuilder` 別名。
- **README**：Figma 匯入改為本專案內建建置說明；補充 `figma-sync` 指令與測試指令。
- **測試**：新增 `tests/test_smoke.py`（匯入、公開 API、`build_ir_from_extraction` 最小呼叫）。
- **pyproject.toml**：`authors` 移除不支援的 `url` 以符合 PEP 621。

---

## [0.1.0] - 2025-02-21

### Added

- **Python 管線 (airis_pdm)**
  - `naming_engine`: 100% 命名控制（data-figma-name → 組件名 → id → class → ARIA/tag → fallback）
  - `dom_extractor`: Playwright 擷取 DOM 樹與 computed styles
  - `ir_builder`: DOM → IR 轉換，產出 plugin-payload / figma-import-payload / name-mapping
  - `figma_reader`: Figma REST API 讀取、FigmaToIR、IRDiffer
  - `code_patcher`: IR diff → Tailwind/CSS/inline 回寫建議與報告
  - `design_assets`: ErSlice 風格 manifest、completeness、design tokens 擷取
  - CLI: `push`、`preview`、`pull`（含 `--apply`、`--erslice` 選項）

- **Figma Plugin**
  - 內建於 `figma_plugin/`：依 IR 建立 Figma 節點、設定 name 與 pluginData
  - Import / Export 分頁，與 AiIRIS-pdm push 產出相容

- **文件與設定**
  - README：快速開始、架構、與 ErSlice 對齊說明
  - docs/ERSLICE_INTEGRATION.md
  - schemas/ir_schema.json、figma-sync.config.json 範例
  - examples/login-page-payload.json

### References

- 彙整 [figma-code-sync](https://github.com/erich/figma-code-sync) IR 與命名管線
- 對齊 [ErSlice](https://github.com/openclaw/ErSlice) design-assets、manifest、tokens 概念
