# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-02-21

### Added

- **V2 管線（filesV2 優化）**
  - `airis_pdm.dom_extractor_v2`：完整保真 DOM 擷取（gradient、分邊 border、inset/text shadow、SVG、pseudo、transform、grid、filter/backdrop、base64 圖、canvas 等）
  - `airis_pdm.ir_builder_v2`：IR 2.0 建構（GradientPaint、INNER_SHADOW、BACKGROUND_BLUR、text decoration/truncation、clipsContent、z-index）
  - CLI `push --v2`：使用 v2 擷取 + IR 2.0，產出與 Figma Plugin v2 相容之 payload
  - docs/COMPARISON_V2.md：v2 與 html-figma / v1 功能矩陣
  - figma_plugin/src/code_v2.ts：Figma Plugin v2 原始碼（IR 2.0 匯入；建置需另行設定）

### Changed

- README：新增 V2 管線說明、專案結構含 dom_extractor_v2 / ir_builder_v2、Figma Plugin v2 使用說明
- figma_plugin/tsconfig.json：排除 code_v2.ts 以維持主建置通過；v2 可選單獨建置

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
