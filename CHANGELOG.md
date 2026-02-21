# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-02-21

### Added

- **單一管線（完整保真）**：CLI 與 Figma plugin 僅保留一套實作
  - `dom_extractor_v2` + `ir_builder_v2` 為唯一 push 管線（gradient、shadow、SVG、grid、IR 2.0 等）
  - Figma plugin 單一入口：`src/code.ts` 為完整保真實作，`npm run build` 產出 `dist/code.js`
  - docs/COMPARISON_V2.md：功能矩陣（vs html-figma / 舊 v1）

### Changed

- **不再並存 v1/v2**：移除 CLI `--v2`、移除 manifest-v2、build:v2；一律使用最佳管線
- README：專案結構與說明改為單一管線、單一 plugin 建置

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
