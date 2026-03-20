# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`docs/FIGMA_CONSOLE_OPS.md`**：figma-console 三元件 SOP、RPC 逾時／重試參數、CLI 退出碼、故障排除、與 CI／真機邊界說明（TASK 4 補齊）。
- **`scripts/regenerate_skills_contract_goldens.py`**：一鍵再生 `skills_leaf_contracts.json`／`skills_aggregate_contracts.json`，與 `docs/SKILLS_CONTRACT.md` 維護流程對齊。
- **Nightly parity 擴充**：`nightly-parity.yml` 追加 `test_figmai_skills.py`、`test_figmai_skills_golden.py`、`test_figmai_pixel_coverage.py`、`test_figma_console_ws.py`、`test_figmai_chain_remote.py`、`test_figmai_ir_contract.py`，與主線 figmai 覆蓋面一致。
- **TASK 1 — 產物級 Parity 封閉**：新增 `tests/test_output_matrix.py`（27 組對拍測試），涵蓋 chain-local 多 target 檔案樹、codegen 位元組級冪等性、chain-remote mock RPC 序列與 state.json schema、flow 離線 manifest 正規形、flow live 五頁碰撞 manifest + router 字串級對拍、manifest 鍵序／include/exclude 排序護欄、IR contract auto-fix 護欄、CSS class/property 排序穩定性。
- **Golden fixture 擴充**：新增 `spec_multi_section.json`（3 sections 大 spec）、`spec_minimal.json`（最小 spec）、`chain_local_file_trees.json`（各 target 檔案樹 baseline）、`chain_remote_golden.json`（RPC 序列與 state schema baseline）、`manifest_offline_two_pages.json`（離線 flow manifest）、`manifest_live_five_pages_collision.json` + `router_vue_five_pages_collision.ts`（五頁碰撞 baseline）。
- **Baseline 對拍腳本**：新增 `scripts/diff_against_baseline.py`，可標準化跑 chain-local + flow offline 並比對 golden，退出碼回報差異。
- **Baseline 更新 SOP**：`docs/SNAPSHOT_PARITY_PROCESS.md` 補充§0 權威 baseline 宣告（`tests/golden/` 為唯一來源，舊 TS 不再對拍）＋§8（對拍維度表、更新步驟、審核流程、封閉聲明、白名單規則）。
- **CI 雙層 baseline 強制執行**：`ci.yml`（每次 push/PR）與 `nightly-parity.yml`（每日排程）皆跑 `test_output_matrix.py` + `scripts/diff_against_baseline.py`，任一失敗即 CI 紅燈。
- **PR template 擴充**：`.github/PULL_REQUEST_TEMPLATE.md` 新增 `test_output_matrix.py` 與 `diff_against_baseline.py` 檢查項。
- **權威 baseline 決策記錄**：`docs/SNAPSHOT_PARITY_PROCESS.md` §0 新增方案比對表（舊 TS out/ 打包 vs submodule vs 本倉 golden），正式記錄採用方案 C（本倉 `tests/golden/`）及理由。

### Fixed

- **Skills contract golden 遺失**：補回 `tests/golden/skills_leaf_contracts.json` 與 `tests/golden/skills_aggregate_contracts.json`（與 `test_figmai_skills.py` 契約測試一致），避免 collection 階段 `FileNotFoundError`。

### Changed

- **CLI 正式名稱改為 `aipdm`**：避免與 [PyPA PDM](https://pdm-project.org/) 套件管理器同名衝突；`pdm` 仍為 console script 但改呼叫 `deprecated_main`（stderr 提示改用 `aipdm`）。`figma-sync` 別名行為不變。
- **與 AiIRIS 生態 CLI 對齊**：對應倉庫建議使用 **`aihub`**（Hub）、**`aitauri`**（Engine）、**`aitdd`**（TDD）、**`aipdm`**（本套件）；Hub 側子命令 **`pdm` 已改為 `aipdm`**（仍透過同名 plugin 轉發）。
- **移倉內 TypeScript `figmai/`**：不再於本倉庫維護 FigmAI monorepo；改為 **`airis_pdm/figmai/` 純 Python**（UiIR 層＋與 `FigmaToIR` 對齊）。進階 chain／flow／pixel 技能庫仍可依需求擴充，不一定要維護獨立 TS 專案。

- **`airis_pdm/figmai`（FigmAI 對齊層）**：Figma File JSON → **UiIR**（`aipdm-ui-ir`）→ 還原為 codegen IR → `generate_from_ir`。CLI：`aipdm figmai import …`、`aipdm figmai codegen …`。
- **完整 Python FigmAI 管線（第一版）**：新增 `spec_to_design_ops`、`chain_pipeline`（`aipdm figmai chain-local`）、`flow`（`aipdm figmai flow`）、`renderers/pixel_*`（Pixel fidelity），以及 `skills`（`ReactGeneratorSkill` / `VueGeneratorSkill`）。
- **`aipdm figmai chain`（remote）**：可直接連線 `figma-console` 執行 `getNode` 拉取；可選 `--sync` 先以 `createNode` 同步 design-ops 再拉回轉碼，CLI 命名與舊 TS 版對齊。
- **`aipdm figmai chain` idempotent 同步**：加入 `StateStore`（`state.json`）保存 `pencil id ↔ figma id`，`--sync` 時先 `updateNode`，節點不存在才 `createNode`，更貼近舊 TS `StateStore` 行為。
- **刪除/搬移偵測策略**：`aipdm figmai chain --missing-node-strategy {keep|orphan|delete}`，對「mapping 有但 spec 已不存在」節點可保留、標記 orphan，或透過 `deleteNode` 直接刪除；`state.json` 新增 `orphans`。
- **parent drift 修正（moveNode）**：`chain --sync` 對既有 mapping 節點會檢查實際 `parentId`，若與本次 spec 推導父層不一致，會自動呼叫 `moveNode` 對齊；bridge 同步新增 `moveNode` RPC 與 `getNode.parentId` 序列化欄位。
- **`chain-local` 樹狀映射補齊**：由原先骨架 FRAME 改為遞迴將 design-ops 節點映射為 airis-like IR（含 children、text、styles、autoLayout、link metadata），本地鏈路產物語意完整度提升。
- **`flow` live 模式**：新增 `aipdm figmai flow --live`，直接透過 `figma-console` 的 `searchNodes/getNode` 跑批次頁面輸出（含 include/exclude、slug collision、router.ts/tsx、manifest、可選 notify），並保留原離線 JSON 模式。
- **skills 全族群補齊（Python 版）**：新增 `AnatomySkill`、`ApiSpecSkill`、`ColorAnnotationSkill`、`PropertiesSkill`、`StructureSkill`、`ScreenReaderSkill`、`AllInOneSkill`，與既有 React/Vue generator 一併輸出於 `airis_pdm.figmai.skills`。
- **IR contract / auto-fix 等價鏈（Python 版）**：新增 `figmai.ir_contract.validate_ui_ir()`，對 root/children/type/sourceType/layout/text 做驗證與修復；`chain`、`chain-remote`、`flow` 在 codegen 前統一套用，並回傳 `validation` issue 清單（`IR_VALIDATION_ERROR`）。
- **TS↔Python golden parity 測試矩陣**：新增 `tests/test_figmai_golden_parity.py` + `tests/golden/figmai_parity_matrix.json`，以固定樣本對比 `flow live`（含 slug collision/filter）、`IR auto-fix`、`chain-local` 產物摘要，建立可回歸的 parity baseline。
- **golden 覆蓋面擴大（6 組）**：新增 `tests/test_figmai_golden_expanded.py` 與四個 fixture（`spec_auth_login.json`、`spec_dashboard_cards.json`、`pixel_gradient_shadow_node.json`、`pixel_text_typography_node.json`），覆蓋真實 spec、多頁 flow、include/exclude、pixel 漸層/陰影/字體排版對拍；同步補強 pixel renderer 與 chain-local button/link 文字節點映射。
- **nightly parity 基礎設施**：新增 `.github/workflows/nightly-parity.yml`（每日 + 手動觸發），並加入 `tests/test_figmai_nightly_parity.py` 與 `tests/golden/nightly/real_project_snapshot_anonymized.json`；同時提供 `figmai.snapshot_anonymizer.anonymize_snapshot()` 用於真實輸入快照匿名化。
- **快照更新流程規範**：新增 `docs/SNAPSHOT_PARITY_PROCESS.md`（匿名化、golden 更新、審查檢查點、回滾策略）與 `.github/PULL_REQUEST_TEMPLATE.md`（要求附 anonymizer 前後 diff 與 golden 變更說明），降低團隊維護成本。
- **Code review 修正（回歸防護）**：修正 `figmai flow --live` 完成訊息頁數來源（`counts.generated`）與 pixel renderer 文字 SOLID fill 使用 `color`（非 `background-color`）；補上 CLI live count 與文字色彩 golden 斷言，避免再次回歸。
- **Pixel renderer TASK2（共用 `pixel_common`）**：多層 `box-shadow`、描邊（`INSIDE` border／`OUTSIDE` outline）、`cornerRadius`／`rectangleCornerRadii`、節點與 fill／effect **透明度鏈相乘**、多層 `fills` 背景、`IMAGE`+`imageUrl` 或占位、`MULTIPLY`／`SCREEN` 混合、`clipsContent`、`visible:false`；新增 golden 與 `tests/test_figmai_pixel_coverage.py`、`docs/PIXEL_RENDERER_COVERAGE.md`。
- **`flow` manifest／router 字串級 parity（對齊 TS diff 習慣）**：`manifest.json` 頂層與巢狀物件鍵排序、`include`／`exclude` 寫入前排序、`router.ts`／`router.tsx` 改為每行一筆 route／meta 並附尾随逗號、檔尾固定換行；新增 `tests/golden/flow_disk/*` 與逐字對拍測試，降低無謂 diff。
- **`aipdm figma-console`**：**純 Python** WebSocket 代理（`airis_pdm/figma_console_ws.py`）＋內建 `airis_pdm/assets/figma_console_bridge.js`，取代須以 Node 跑的 `figma-console-mcp`；可選依賴 `pip install -e ".[figma-console]"`（`websockets`）。
- **skills contract/golden 封頂（TASK 3）**：新增 `docs/SKILLS_CONTRACT.md`、`tests/golden/skills_*_contracts.json` 與 `tests/test_figmai_skills.py` matrix，固定 anatomy / api-spec / color-annotation / properties / structure / screen-reader / all-in-one / react / vue 的正常與邊界輸出，並統一 `SkillContractError` 驗證策略。
- **figma-console 維運 runbook（TASK 4）**：新增 `docs/FIGMA_CONSOLE_OPS.md`，整理預設 CI 與真機 smoke 切分、RPC timeout/retry/backoff 旗標、exit code 分類、常見故障排查與手動 smoke 流程。
- **手動真機 smoke workflow 骨架（TASK 4）**：新增 `.github/workflows/figma-console-smoke-manual.yml`，限定 `workflow_dispatch` + `self-hosted macOS`，執行 `searchNodes`/`getNode` 最小 smoke，並上傳 log artifact。
- **migration 狀態總表**：新增 `docs/TASK_STATUS_SUMMARY.md`，固定四個 TASK 的完成度、剩餘清單與封閉判定，作為 migration 收尾依據。
- **figma-console 診斷包規格化（TASK 4）**：手動 smoke workflow artifact 固定包含 `metadata.json`、`command-lines.txt`、`prerequisites.txt`、`proxy.log`、`searchNodes.json`、`getNode.json` 等最小診斷包，並寫入 `docs/FIGMA_CONSOLE_OPS.md`。
- **TASK 4 結案條件文件化**：在 `docs/FIGMA_CONSOLE_OPS.md` 與 `docs/TASK_STATUS_SUMMARY.md` 明列整合／韌性／維運線的 DoD，將 mock 測試、主 CI/真機切分、觀測性、診斷包與真機成功紀錄寫成硬條件。
- **真機 smoke 成功紀錄模板**：新增 `docs/reports/FIGMA_CONSOLE_SMOKE_RECORD_TEMPLATE.md`，供 self-hosted macOS / Figma Desktop 實際跑通後填寫正式成功證據，避免以 mock 或推測結果冒充真機紀錄。

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
